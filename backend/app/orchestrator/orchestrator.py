from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.charging_session import ChargingSession
from app.models.station import Station
from app.orchestrator.candidate_generator import generate_candidate_slots, CandidateSlot
from app.orchestrator.constraint_validator import (
    validate_agent_outputs,
    validate_feasibility,
    apply_hard_constraints_to_slots,
    SchedulingValidationError
)
from app.orchestrator.scoring_engine import score_candidate_slots
from app.orchestrator.schedule_builder import build_schedule_segments, ScheduleSegmentItem

class ScheduleResult:
    def __init__(
        self,
        status: str,
        segments: List[Dict[str, Any]],
        summary_line: str,
        candidate_windows: List[Dict[str, Any]],
        is_feasible: bool = True
    ):
        self.status = status
        self.segments = segments
        self.summary_line = summary_line
        self.candidate_windows = candidate_windows
        self.is_feasible = is_feasible

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "segments": self.segments,
            "summary_line": self.summary_line,
            "candidate_windows": self.candidate_windows
        }


class Orchestrator:
    """
    VoltSync Deterministic Orchestrator.
    Combines outputs from 4 specialist agents, enforces hard physical/grid/deadline
    constraints, scores candidate windows, and generates final charging schedules.
    """

    def create_schedule(
        self,
        session: ChargingSession,
        station: Station,
        agent_outputs: Dict[str, Any],
        db: Session
    ) -> ScheduleResult:
        # Step 1: Validate agent outputs
        is_valid, validation_err = validate_agent_outputs(agent_outputs)
        if not is_valid:
            raise SchedulingValidationError(validation_err)

        # Step 2: Determine effective maximum charging power
        charger_cap = station.charger_rating if station and station.charger_rating else session.max_charging_power_kw
        effective_power_kw = min(session.max_charging_power_kw, charger_cap)

        # Ensure timezone-aware datetimes
        arrival = session.arrival_time
        ready_by = session.ready_by
        if arrival.tzinfo is None:
            arrival = arrival.replace(tzinfo=timezone.utc)
        if ready_by.tzinfo is None:
            ready_by = ready_by.replace(tzinfo=timezone.utc)

        # Step 3: Hard physical feasibility check
        is_feasible, infeasible_reason = validate_feasibility(
            arrival_time=arrival,
            ready_by=ready_by,
            energy_required_kwh=session.energy_required_kwh,
            max_power_kw=effective_power_kw
        )

        if not is_feasible:
            return ScheduleResult(
                status="Infeasible",
                segments=[],
                summary_line=infeasible_reason or "Requested energy cannot be delivered before the ready-by time at the available charging power.",
                candidate_windows=[],
                is_feasible=False
            )

        # Step 4: Derive station region for dataset lookups
        region = f"{station.state} - {station.district_city_village}".strip() if station else "Default"

        # Step 5: Generate 15-minute candidate slots
        slots = generate_candidate_slots(
            arrival_time=arrival,
            ready_by=ready_by,
            max_power_kw=effective_power_kw,
            region=region,
            db=db
        )

        if not slots:
            return ScheduleResult(
                status="Infeasible",
                segments=[],
                summary_line="Requested energy cannot be delivered before the ready-by time at the available charging power.",
                candidate_windows=[],
                is_feasible=False
            )

        # Step 6: Apply hard constraints (grid safety / critical stress flagging)
        slots = apply_hard_constraints_to_slots(slots, agent_outputs.get("grid", {}))

        # Step 7: Score candidates based on preference, flexibility, and grid penalties
        scored_slots = score_candidate_slots(
            slots=slots,
            preference=session.preference,
            flexibility=session.flexibility
        )

        # Step 8: Build schedule segments and summary line
        segments, summary_line = build_schedule_segments(
            scored_slots=scored_slots,
            energy_required_kwh=session.energy_required_kwh,
            preference=session.preference,
            flexibility=session.flexibility,
            ready_by=ready_by
        )

        if not segments:
            return ScheduleResult(
                status="Infeasible",
                segments=[],
                summary_line="Requested energy cannot be delivered before the ready-by time at the available charging power.",
                candidate_windows=[],
                is_feasible=False
            )

        # Step 9: Format candidate windows for explainability
        candidate_windows_data = [
            {
                "start_time": s.start_time,
                "end_time": s.end_time,
                "expected_renewable_pct": s.renewable_share_pct,
                "expected_cost_inr": round(s.tariff_inr_per_kwh * (s.max_power_kw * s.duration_hours), 2),
                "expected_co2_g": round(s.carbon_intensity_gco2_per_kwh * (s.max_power_kw * s.duration_hours), 2),
                "grid_stress_pct": s.grid_stress_pct,
                "ranking_reason": f"Score: {s.total_score:.2f} (Renewable: {s.renewable_share_pct:.1f}%, Cost: ₹{s.tariff_inr_per_kwh:.2f}/kWh, Grid: {s.grid_stress_pct:.1f}%)"
            }
            for s in scored_slots
        ]

        return ScheduleResult(
            status="Scheduled",
            segments=[seg.to_dict() for seg in segments],
            summary_line=summary_line,
            candidate_windows=candidate_windows_data,
            is_feasible=True
        )
