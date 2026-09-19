import pytest
from app.agents.driver_agent import get_driver_agent
from app.agents.renewable_agent import get_renewable_agent
from app.agents.grid_agent import get_grid_agent
from app.agents.cost_carbon_agent import get_cost_carbon_agent
from app.schemas.agent import (
    DriverAgentOutput,
    RenewableAgentOutput,
    GridAgentOutput,
    CostCarbonAgentOutput
)
from app.models.agent_decision import AgentDecision

def test_driver_agent_initialization():
    agent = get_driver_agent()
    assert agent.role == "Driver Agent"
    assert len(agent.tools) == 2

def test_renewable_agent_initialization():
    agent = get_renewable_agent()
    assert agent.role == "Renewable Agent"
    assert len(agent.tools) == 2

def test_grid_agent_initialization():
    agent = get_grid_agent()
    assert agent.role == "Grid Agent"
    assert len(agent.tools) == 3

def test_cost_carbon_agent_initialization():
    agent = get_cost_carbon_agent()
    assert agent.role == "Cost & Carbon Agent"
    assert len(agent.tools) == 1

def test_agent_decision_model():
    decision = AgentDecision(
        session_id="S-123",
        agent_type="driver",
        input_context={"test": 1},
        output_data={"result": "ok"},
        status="success",
        execution_duration_ms=150
    )
    assert decision.session_id == "S-123"
    assert decision.agent_type == "driver"
    assert decision.status == "success"

def test_driver_agent_output_schema():
    output = DriverAgentOutput(
        session_id="S-1",
        energy_required_kwh=42.5,
        estimated_duration_min=85,
        urgency="High",
        flexibility="Medium",
        preference="Greenest",
        available_window_start="2026-01-10T10:00:00Z",
        available_window_end="2026-01-10T15:30:00Z",
        reason="Moderate flexibility"
    )
    assert output.energy_required_kwh == 42.5

