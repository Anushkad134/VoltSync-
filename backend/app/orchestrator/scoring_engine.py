from typing import List, Dict, Any
from app.orchestrator.candidate_generator import CandidateSlot

PREFERENCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Fastest": {
        "speed": 0.50,
        "grid": 0.20,
        "renewable": 0.15,
        "cost": 0.10,
        "carbon": 0.05,
    },
    "Cheapest": {
        "cost": 0.50,
        "grid": 0.20,
        "renewable": 0.15,
        "carbon": 0.10,
        "speed": 0.05,
    },
    "Greenest": {
        "renewable": 0.50,
        "carbon": 0.20,
        "grid": 0.15,
        "cost": 0.10,
        "speed": 0.05,
    },
}

GRID_PENALTIES = {
    "low": 0.0,
    "moderate": 0.10,
    "high": 0.30,
    "critical": 0.80,
}

def get_grid_penalty(grid_stress_pct: float, is_critical: bool) -> float:
    if is_critical or grid_stress_pct >= 90.0:
        return GRID_PENALTIES["critical"]
    elif grid_stress_pct >= 75.0:
        return GRID_PENALTIES["high"]
    elif grid_stress_pct >= 50.0:
        return GRID_PENALTIES["moderate"]
    return GRID_PENALTIES["low"]


def score_candidate_slots(
    slots: List[CandidateSlot],
    preference: str,
    flexibility: str
) -> List[CandidateSlot]:
    """
    Scores each candidate slot based on driver preference, flexibility, and grid stress.
    """
    if not slots:
        return []

    weights = PREFERENCE_WEIGHTS.get(preference, PREFERENCE_WEIGHTS["Fastest"])

    # Compute min/max bounds across candidate slots for relative normalization
    tariffs = [s.tariff_inr_per_kwh for s in slots]
    carbons = [s.carbon_intensity_gco2_per_kwh for s in slots]
    
    min_tariff, max_tariff = min(tariffs), max(tariffs)
    min_carbon, max_carbon = min(carbons), max(carbons)

    tariff_span = max_tariff - min_tariff if max_tariff > min_tariff else 1.0
    carbon_span = max_carbon - min_carbon if max_carbon > min_carbon else 1.0

    n_slots = len(slots)

    for idx, slot in enumerate(slots):
        # 1. Speed score: earlier slots score higher
        # Range: 1.0 (earliest) down to ~0.0 (latest)
        speed_score = 1.0 - (idx / max(n_slots, 1))

        # 2. Renewable score: 0 to 1
        renewable_score = max(0.0, min(1.0, slot.renewable_share_pct / 100.0))

        # 3. Cost score: lower tariff = higher score (0 to 1)
        cost_score = 1.0 - ((slot.tariff_inr_per_kwh - min_tariff) / tariff_span)
        cost_score = max(0.0, min(1.0, cost_score))

        # 4. Carbon score: lower carbon intensity = higher score (0 to 1)
        carbon_score = 1.0 - ((slot.carbon_intensity_gco2_per_kwh - min_carbon) / carbon_span)
        carbon_score = max(0.0, min(1.0, carbon_score))

        # 5. Grid score: lower stress = higher score, minus discrete tier penalties
        base_grid_score = max(0.0, min(1.0, 1.0 - (slot.grid_stress_pct / 100.0)))
        penalty = get_grid_penalty(slot.grid_stress_pct, slot.is_critical)
        grid_score = max(0.0, base_grid_score - penalty)

        slot.speed_score = speed_score
        slot.renewable_score = renewable_score
        slot.cost_score = cost_score
        slot.carbon_score = carbon_score
        slot.grid_score = grid_score

        # Base weighted score
        total = (
            weights["speed"] * speed_score +
            weights["renewable"] * renewable_score +
            weights["cost"] * cost_score +
            weights["carbon"] * carbon_score +
            weights["grid"] * grid_score
        )

        # Flexibility adjustment
        if flexibility == "Low":
            # Low flexibility prioritizes deadline and earliest start strongly
            total = (total * 0.3) + (speed_score * 0.7)
        elif flexibility == "Medium":
            # Medium gives moderate boost to preference optimization with modest speed baseline
            total = (total * 0.8) + (speed_score * 0.2)
        elif flexibility == "High":
            # High flexibility fully optimizes for preference & green/cost windows
            total = total

        # Critical grid stress hard restriction
        if slot.is_critical:
            total = total * 0.1

        slot.total_score = total

    return slots
