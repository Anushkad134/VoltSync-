import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_decision import AgentDecision
from app.agents.driver_agent import get_driver_agent
from app.agents.renewable_agent import get_renewable_agent
from app.agents.grid_agent import get_grid_agent
from app.agents.cost_carbon_agent import get_cost_carbon_agent
from app.agents.llm_config import get_primary_llm, get_fallback_llm, create_llm_instance
from app.agents.crew import run_agents_for_session, build_crew_pipeline, safe_extract_pydantic
from app.schemas.agent import (
    DriverAgentOutput,
    RenewableAgentOutput,
    GridAgentOutput,
    CostCarbonAgentOutput
)
from app.core.config import settings


@pytest.fixture
def agent_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Patch SessionLocal in crew.py
    monkeypatch.setattr("app.agents.crew.SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    yield db
    db.close()


# ==============================================================================
# 1. LLM Factory & Agent Injection Tests
# ==============================================================================
def test_llm_factories():
    primary = get_primary_llm()
    assert "gpt-oss-120b" in primary.model
    assert primary.timeout == settings.LLM_TIMEOUT_SECONDS

    fallback = get_fallback_llm()
    assert "qwen3.8-27b" in fallback.model


def test_agent_factories_with_injected_llm():
    custom_llm = create_llm_instance(model="openai/gpt-4o")
    
    driver = get_driver_agent(llm=custom_llm)
    assert driver.role == "Driver Agent"
    assert "gpt-4o" in driver.llm.model

    renewable = get_renewable_agent(llm=custom_llm)
    assert renewable.role == "Renewable Agent"
    assert "gpt-4o" in renewable.llm.model

    grid = get_grid_agent(llm=custom_llm)
    assert grid.role == "Grid Agent"
    assert "gpt-4o" in grid.llm.model

    cost_carbon = get_cost_carbon_agent(llm=custom_llm)
    assert cost_carbon.role == "Cost & Carbon Agent"
    assert "gpt-4o" in cost_carbon.llm.model


# ==============================================================================
# 2. Primary Execution Success (No Fallback)
# ==============================================================================
def test_primary_llm_success(agent_db):
    session_id = "SES_PRIMARY_SUCCESS"

    mock_driver_out = DriverAgentOutput(
        session_id=session_id,
        energy_required_kwh=30.0,
        estimated_duration_min=45,
        urgency="Medium",
        flexibility="High",
        preference="Greenest",
        available_window_start=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        available_window_end=datetime(2026, 6, 15, 15, 0, tzinfo=timezone.utc),
        reason="Primary LLM analysis"
    )

    with patch("app.agents.crew.Crew.kickoff") as mock_kickoff, \
         patch("app.agents.crew.safe_extract_pydantic") as mock_extract:
        
        mock_extract.side_effect = [
            (mock_driver_out.model_dump(mode="json"), True),
            ({}, True),
            ({}, True),
            ({}, True)
        ]

        res = run_agents_for_session(
            session_id=session_id,
            region="Maharashtra - Mumbai",
            start_time="2026-06-15T09:00:00Z",
            end_time="2026-06-15T15:00:00Z"
        )

        assert res["fallback_used"] is False
        assert res["selected_llm"] == settings.PRIMARY_LLM_MODEL
        assert res["crew_execution_success"] is True
        assert mock_kickoff.call_count == 1

        # Check DB records
        decisions = agent_db.query(AgentDecision).filter(AgentDecision.session_id == session_id).all()
        assert len(decisions) == 4
        driver_dec = next(d for d in decisions if d.agent_type == "driver")
        assert driver_dec.status == "success"
        assert driver_dec.input_context["fallback_used"] is False


# ==============================================================================
# 3. HTTP 429 Rate Limit Triggers Fallback
# ==============================================================================
def test_primary_429_rate_limit_triggers_fallback(agent_db):
    session_id = "SES_429_FALLBACK"

    call_count = 0
    def mock_kickoff_side_effect(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("HTTP 429: Too Many Requests / Rate Limit Exceeded")
        return "Fallback Success"

    with patch("app.agents.crew.Crew.kickoff", side_effect=mock_kickoff_side_effect, autospec=True), \
         patch("app.agents.crew.safe_extract_pydantic") as mock_extract:
        
        mock_extract.return_value = ({"status": "ok"}, True)

        res = run_agents_for_session(
            session_id=session_id,
            region="Maharashtra - Mumbai",
            start_time="2026-06-15T09:00:00Z",
            end_time="2026-06-15T15:00:00Z"
        )

        assert res["fallback_used"] is True
        assert res["selected_llm"] == settings.FALLBACK_LLM_MODEL
        assert "429" in res["failure_reason"]
        assert call_count == 2

        # Verify persisted decisions
        decisions = agent_db.query(AgentDecision).filter(AgentDecision.session_id == session_id).all()
        assert len(decisions) == 4
        for d in decisions:
            assert d.input_context["fallback_used"] is True
            assert d.input_context["selected_llm"] == settings.FALLBACK_LLM_MODEL
            assert "429" in d.input_context["failure_reason"]


# ==============================================================================
# 4. Timeout Triggers Fallback
# ==============================================================================
def test_primary_timeout_triggers_fallback(agent_db):
    session_id = "SES_TIMEOUT_FALLBACK"

    call_count = 0
    def mock_kickoff_side_effect(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Request timed out after 30 seconds")
        return "Fallback Success"

    with patch("app.agents.crew.Crew.kickoff", side_effect=mock_kickoff_side_effect, autospec=True), \
         patch("app.agents.crew.safe_extract_pydantic") as mock_extract:
        
        mock_extract.return_value = ({"status": "ok"}, True)

        res = run_agents_for_session(
            session_id=session_id,
            region="Maharashtra - Mumbai",
            start_time="2026-06-15T09:00:00Z",
            end_time="2026-06-15T15:00:00Z"
        )

        assert res["fallback_used"] is True
        assert res["selected_llm"] == settings.FALLBACK_LLM_MODEL
        assert "timed out" in res["failure_reason"]


# ==============================================================================
# 5. Provider Outage / Connection Error Triggers Fallback
# ==============================================================================
def test_primary_provider_outage_triggers_fallback(agent_db):
    session_id = "SES_OUTAGE_FALLBACK"

    call_count = 0
    def mock_kickoff_side_effect(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("503 Service Unavailable: Provider backend is down")
        return "Fallback Success"

    with patch("app.agents.crew.Crew.kickoff", side_effect=mock_kickoff_side_effect, autospec=True), \
         patch("app.agents.crew.safe_extract_pydantic") as mock_extract:
        
        mock_extract.return_value = ({"status": "ok"}, True)

        res = run_agents_for_session(
            session_id=session_id,
            region="Maharashtra - Mumbai",
            start_time="2026-06-15T09:00:00Z",
            end_time="2026-06-15T15:00:00Z"
        )

        assert res["fallback_used"] is True
        assert "503" in res["failure_reason"]


# ==============================================================================
# 6. Output Parsing Failure Safety (No DB Crash)
# ==============================================================================
def test_corrupted_output_parsing_safety(agent_db):
    session_id = "SES_PARSING_FAIL_SAFE"

    with patch("app.agents.crew.Crew.kickoff", return_value="Raw LLM Response"), \
         patch("app.agents.crew.safe_extract_pydantic") as mock_extract:
        
        # Simulate parsing error returning (empty, False)
        mock_extract.return_value = ({}, False)

        res = run_agents_for_session(
            session_id=session_id,
            region="Maharashtra - Mumbai",
            start_time="2026-06-15T09:00:00Z",
            end_time="2026-06-15T15:00:00Z"
        )

        # Execution completed safely without throwing uncaught exceptions
        assert res["driver_ok"] is False

        decisions = agent_db.query(AgentDecision).filter(AgentDecision.session_id == session_id).all()
        assert len(decisions) == 4
        for d in decisions:
            assert d.status == "failed"
            assert d.output_data is None


# ==============================================================================
# 7. Both Primary and Fallback Failing Gracefully
# ==============================================================================
def test_both_llms_failing_gracefully(agent_db):
    session_id = "SES_ALL_FAIL"

    with patch("app.agents.crew.Crew.kickoff", side_effect=Exception("Total Outage"), autospec=True):
        res = run_agents_for_session(
            session_id=session_id,
            region="Maharashtra - Mumbai",
            start_time="2026-06-15T09:00:00Z",
            end_time="2026-06-15T15:00:00Z"
        )

        assert res["crew_execution_success"] is False
        assert res["fallback_used"] is True
        assert "Total Outage" in res["failure_reason"]

        decisions = agent_db.query(AgentDecision).filter(AgentDecision.session_id == session_id).all()
        assert len(decisions) == 4
        for d in decisions:
            assert d.status == "failed"
