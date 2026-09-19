from datetime import datetime
from typing import List, Dict, Any, Tuple
from app.orchestrator.candidate_generator import CandidateSlot

class ScheduleSegmentItem:
    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        power_level_kw: float,
        expected_renewable_pct: float,
        expected_cost_inr: float,
        expected_co2_g: float,
        segment_reason: str
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.power_level_kw = power_level_kw
        self.expected_renewable_pct = expected_renewable_pct
        self.expected_cost_inr = expected_cost_inr
        self.expected_co2_g = expected_co2_g
        self.segment_reason = segment_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "power_level_kw": round(self.power_level_kw, 2),
            "expected_renewable_pct": round(self.expected_renewable_pct, 2),
            "expected_cost_inr": round(self.expected_cost_inr, 2),
            "expected_co2_g": round(self.expected_co2_g, 2),
            "segment_reason": self.segment_reason
        }


def build_schedule_segments(
    scored_slots: List[CandidateSlot],
    energy_required_kwh: float,
    preference: str,
    flexibility: str,
    ready_by: datetime
) -> Tuple[List[ScheduleSegmentItem], str]:
    """
    Selects optimal slots and constructs consolidated schedule segments with an explainable summary line.
    """
    if not scored_slots or energy_required_kwh <= 0:
        return [], "No feasible charging slots available."

    # Sort/select slots according to flexibility & preference
    selected_slots_with_energy: List[Tuple[CandidateSlot, float]] = []
    remaining_energy = energy_required_kwh

    if flexibility == "Low" or preference == "Fastest":
        # Low flexibility or Fastest strictly takes earliest feasible slots
        slots_to_consider = sorted(scored_slots, key=lambda s: s.start_time)
    elif flexibility == "Medium":
        # Medium flexibility: find the best contiguous or semi-contiguous block
        # We find a starting index that maximizes score while finishing before ready_by
        slots_to_consider = _select_medium_flex_slots(scored_slots, energy_required_kwh)
    else:
        # High flexibility: take highest scoring slots first, regardless of chronology
        # (excluding critical slots where possible)
        sorted_by_score = sorted(scored_slots, key=lambda s: s.total_score, reverse=True)
        # Filter out critical if enough non-critical exist
        non_critical = [s for s in sorted_by_score if not s.is_critical]
        candidate_pool = non_critical if sum(s.max_energy_kwh for s in non_critical) >= energy_required_kwh else sorted_by_score
        
        # Pick top slots until energy requirement is met
        chosen: List[CandidateSlot] = []
        accumulated_e = 0.0
        for s in candidate_pool:
            chosen.append(s)
            accumulated_e += s.max_energy_kwh
            if accumulated_e >= energy_required_kwh:
                break
        
        # Re-sort chronologically
        slots_to_consider = sorted(chosen, key=lambda s: s.start_time)

    # Allocate energy to slots
    for slot in slots_to_consider:
        if remaining_energy <= 1e-4:
            break
        energy_this_slot = min(slot.max_energy_kwh, remaining_energy)
        selected_slots_with_energy.append((slot, energy_this_slot))
        remaining_energy -= energy_this_slot

    if not selected_slots_with_energy:
        return [], "Could not allocate energy across candidate slots."

    # Build discrete slots and merge contiguous ones
    raw_segments: List[ScheduleSegmentItem] = []
    for slot, energy_kwh in selected_slots_with_energy:
        cost = energy_kwh * slot.tariff_inr_per_kwh
        co2 = energy_kwh * slot.carbon_intensity_gco2_per_kwh
        reason = _generate_slot_reason(slot)
        
        raw_segments.append(ScheduleSegmentItem(
            start_time=slot.start_time,
            end_time=slot.end_time,
            power_level_kw=slot.max_power_kw,
            expected_renewable_pct=slot.renewable_share_pct,
            expected_cost_inr=cost,
            expected_co2_g=co2,
            segment_reason=reason
        ))

    # Merge contiguous segments
    merged_segments = _merge_contiguous_segments(raw_segments)

    # Generate summary line
    summary_line = _generate_summary_line(
        merged_segments,
        preference,
        flexibility,
        ready_by,
        scored_slots[0].start_time if scored_slots else None
    )

    return merged_segments, summary_line


def _select_medium_flex_slots(slots: List[CandidateSlot], energy_required: float) -> List[CandidateSlot]:
    """Finds best contiguous block of slots for Medium flexibility."""
    n = len(slots)
    slots_chronological = sorted(slots, key=lambda s: s.start_time)
    
    # Estimate slots needed
    avg_slot_e = slots_chronological[0].max_energy_kwh if slots_chronological else 1.0
    slots_needed = max(1, int(energy_required / avg_slot_e + 0.99))
    
    if slots_needed >= n:
        return slots_chronological

    best_start = 0
    best_avg_score = -1.0
    for i in range(n - slots_needed + 1):
        window = slots_chronological[i:i + slots_needed]
        avg_score = sum(s.total_score for s in window) / slots_needed
        if avg_score > best_avg_score:
            best_avg_score = avg_score
            best_start = i

    return slots_chronological[best_start:best_start + slots_needed]


def _merge_contiguous_segments(segments: List[ScheduleSegmentItem]) -> List[ScheduleSegmentItem]:
    if not segments:
        return []

    merged: List[ScheduleSegmentItem] = []
    current = segments[0]

    for next_seg in segments[1:]:
        if next_seg.start_time == current.end_time and abs(next_seg.power_level_kw - current.power_level_kw) < 1e-3:
            # Merge
            total_cost = current.expected_cost_inr + next_seg.expected_cost_inr
            total_co2 = current.expected_co2_g + next_seg.expected_co2_g
            
            cur_dur = (current.end_time - current.start_time).total_seconds()
            next_dur = (next_seg.end_time - next_seg.start_time).total_seconds()
            total_dur = cur_dur + next_dur
            
            avg_renewable = (
                (current.expected_renewable_pct * cur_dur + next_seg.expected_renewable_pct * next_dur) / total_dur
                if total_dur > 0 else current.expected_renewable_pct
            )

            # Combined reason
            reason = current.segment_reason
            if next_seg.segment_reason != current.segment_reason and "renewable" in next_seg.segment_reason.lower():
                reason = next_seg.segment_reason

            current = ScheduleSegmentItem(
                start_time=current.start_time,
                end_time=next_seg.end_time,
                power_level_kw=current.power_level_kw,
                expected_renewable_pct=avg_renewable,
                expected_cost_inr=total_cost,
                expected_co2_g=total_co2,
                segment_reason=reason
            )
        else:
            merged.append(current)
            current = next_seg

    merged.append(current)
    return merged


def _generate_slot_reason(slot: CandidateSlot) -> str:
    if slot.renewable_share_pct >= 60.0:
        return f"High renewable availability ({slot.renewable_share_pct:.1f}%) with manageable grid stress."
    elif slot.tariff_inr_per_kwh <= 7.0:
        return f"Low tariff window (₹{slot.tariff_inr_per_kwh:.2f}/kWh) optimizing session cost."
    elif slot.grid_stress_pct < 40.0:
        return f"Optimal grid stability window ({slot.grid_stress_pct:.1f}% grid stress)."
    return "Balanced charging window meeting deadline and power constraints."


def _generate_summary_line(
    segments: List[ScheduleSegmentItem],
    preference: str,
    flexibility: str,
    ready_by: datetime,
    initial_arrival: datetime
) -> str:
    ready_by_str = ready_by.strftime("%H:%M")
    
    if not segments:
        return "No charging segments could be scheduled."

    first_start = segments[0].start_time
    avg_ren = sum(s.expected_renewable_pct for s in segments) / len(segments)

    if flexibility == "Low":
        return f"Charging starts immediately because the requested ready-by time ({ready_by_str}) leaves insufficient flexibility for a later green window."

    if preference == "Greenest":
        if initial_arrival and (first_start - initial_arrival).total_seconds() > 900:
            return f"Charging is shifted to the midday renewable-rich window to reduce carbon emissions ({avg_ren:.1f}% renewable) while meeting your {ready_by_str} ready-by time."
        return f"Charging is optimized for highest renewable energy ({avg_ren:.1f}% renewable) while meeting your {ready_by_str} ready-by time."

    if preference == "Cheapest":
        if initial_arrival and (first_start - initial_arrival).total_seconds() > 900:
            return f"Charging is shifted to the lowest-cost feasible period while avoiding high grid stress and meeting your {ready_by_str} deadline."
        return f"Charging is scheduled during the lowest-cost feasible period while avoiding high grid stress."

    # Fastest
    return f"Charging is scheduled for fastest completion by {ready_by_str} while respecting grid and station limits."
