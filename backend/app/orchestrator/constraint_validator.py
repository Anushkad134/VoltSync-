from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from app.orchestrator.candidate_generator import CandidateSlot

class SchedulingValidationError(Exception):
    pass

def validate_agent_outputs(agent_outputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates all 4 specialist agent outputs before use by the orchestrator.
    Returns (is_valid, error_message).
    """
    required_agents = ["driver", "renewable", "grid", "cost_carbon"]
    for agent_key in required_agents:
        if agent_key not in agent_outputs or not agent_outputs[agent_key]:
            return False, f"Missing required agent output for '{agent_key}'."

    # Validate Driver Agent Output
    driver_data = agent_outputs["driver"]
    if not isinstance(driver_data, dict):
        return False, "Driver agent output must be a dictionary."
    energy_req = driver_data.get("energy_required_kwh")
    if energy_req is None or energy_req <= 0:
        return False, f"Invalid energy_required_kwh: {energy_req}. Must be > 0."
    pref = driver_data.get("preference")
    if pref not in ["Fastest", "Cheapest", "Greenest"]:
        return False, f"Invalid preference: {pref}."
    flex = driver_data.get("flexibility")
    if flex not in ["Low", "Medium", "High"]:
        return False, f"Invalid flexibility: {flex}."

    # Validate Renewable Agent Output
    ren_data = agent_outputs["renewable"]
    if not isinstance(ren_data, dict):
        return False, "Renewable agent output must be a dictionary."
    green_windows = ren_data.get("green_windows", [])
    for gw in green_windows:
        r_share = gw.get("renewable_share_pct", 0)
        if r_share < 0 or r_share > 100:
            return False, f"Invalid renewable_share_pct in green windows: {r_share}."

    # Validate Grid Agent Output
    grid_data = agent_outputs["grid"]
    if not isinstance(grid_data, dict):
        return False, "Grid agent output must be a dictionary."
    grid_stress_pct = grid_data.get("grid_stress_pct", 0)
    if grid_stress_pct < 0 or grid_stress_pct > 100:
        return False, f"Invalid grid_stress_pct: {grid_stress_pct}."
    grid_stress_level = grid_data.get("grid_stress", "Low")
    if grid_stress_level not in ["Low", "Moderate", "High", "Critical"]:
        return False, f"Invalid grid_stress level: {grid_stress_level}."

    # Validate Cost/Carbon Agent Output
    cost_data = agent_outputs["cost_carbon"]
    if not isinstance(cost_data, dict):
        return False, "Cost & Carbon agent output must be a dictionary."
    c_windows = cost_data.get("candidate_windows", [])
    for cw in c_windows:
        if cw.get("cost_inr", 0) < 0:
            return False, f"Invalid negative cost_inr: {cw.get('cost_inr')}."
        if cw.get("carbon_intensity_gco2_per_kwh", 0) < 0:
            return False, f"Invalid negative carbon intensity: {cw.get('carbon_intensity_gco2_per_kwh')}."

    return True, None


def validate_feasibility(
    arrival_time: datetime,
    ready_by: datetime,
    energy_required_kwh: float,
    max_power_kw: float
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether the requested charging session is physically feasible.
    Returns (is_feasible, reason_if_infeasible).
    """
    if max_power_kw <= 0:
        return False, "Available charging power is 0 or negative."

    if ready_by <= arrival_time:
        return False, "Ready-by time must be strictly after arrival time."

    duration_hours = (ready_by - arrival_time).total_seconds() / 3600.0
    max_possible_energy = max_power_kw * duration_hours

    if max_possible_energy < (energy_required_kwh - 1e-4):
        return False, "Requested energy cannot be delivered before the ready-by time at the available charging power."

    return True, None


def apply_hard_constraints_to_slots(
    slots: List[CandidateSlot],
    grid_agent_output: Dict[str, Any]
) -> List[CandidateSlot]:
    """
    Applies hard constraints to individual candidate slots:
    - Flags critical grid stress slots so they can be restricted or rejected.
    """
    is_grid_critical_override = (
        grid_agent_output.get("grid_stress") == "Critical" or
        grid_agent_output.get("grid_stress_pct", 0) >= 90.0
    )

    for slot in slots:
        if is_grid_critical_override or slot.grid_stress_pct >= 90.0:
            slot.is_critical = True

    return slots
