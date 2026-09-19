import logging
import time
from typing import Dict, Any, Tuple, Optional
from crewai import Crew, Task, LLM

from app.agents.driver_agent import get_driver_agent
from app.agents.renewable_agent import get_renewable_agent
from app.agents.grid_agent import get_grid_agent
from app.agents.cost_carbon_agent import get_cost_carbon_agent
from app.agents.llm_config import get_primary_llm, get_fallback_llm
from app.core.config import settings
from app.schemas.agent import (
    DriverAgentOutput,
    RenewableAgentOutput,
    GridAgentOutput,
    CostCarbonAgentOutput
)
from app.models.agent_decision import AgentDecision
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def build_crew_pipeline(
    session_id: str,
    region: str,
    start_time: str,
    end_time: str,
    llm: Optional[LLM] = None
) -> Tuple[Crew, Task, Task, Task, Task]:
    """
    Builds the 4-agent crew and their associated tasks with an injected LLM instance.
    """
    driver_agent = get_driver_agent(llm=llm)
    renewable_agent = get_renewable_agent(llm=llm)
    grid_agent = get_grid_agent(llm=llm)
    cost_carbon_agent = get_cost_carbon_agent(llm=llm)

    driver_task = Task(
        description=f"Analyze charging requirements for session {session_id}.",
        expected_output="Structured data containing energy required, estimated duration, urgency, flexibility, preference, available window, and reason.",
        agent=driver_agent,
        output_pydantic=DriverAgentOutput
    )

    renewable_task = Task(
        description=f"Analyze renewable availability in region '{region}' between {start_time} and {end_time}.",
        expected_output="Structured data containing green windows, the greenest window, forecast confidence, and reason.",
        agent=renewable_agent,
        output_pydantic=RenewableAgentOutput
    )

    grid_task = Task(
        description=f"Analyze grid stress in region '{region}' between {start_time} and {end_time} for session {session_id}.",
        expected_output="Structured data containing grid stress classification, station load classification, recommended action, urgency override, and reason.",
        agent=grid_agent,
        output_pydantic=GridAgentOutput
    )

    cost_task = Task(
        description=f"Analyze cost and carbon intensity in region '{region}' between {start_time} and {end_time}.",
        expected_output="Structured data containing candidate windows, cheapest window, lowest carbon window, and tradeoff summary.",
        agent=cost_carbon_agent,
        output_pydantic=CostCarbonAgentOutput
    )

    crew = Crew(
        agents=[driver_agent, renewable_agent, grid_agent, cost_carbon_agent],
        tasks=[driver_task, renewable_task, grid_task, cost_task],
        verbose=False
    )

    return crew, driver_task, renewable_task, grid_task, cost_task


def safe_extract_pydantic(task: Task, expected_model) -> Tuple[Dict[str, Any], bool]:
    """
    Safely extracts and validates Pydantic output from a completed CrewAI Task.
    Returns (data_dict, is_valid) where data_dict is JSON-serializable.
    """
    try:
        if hasattr(task, 'output') and task.output is not None:
            # Check pydantic attribute on task output
            if hasattr(task.output, 'pydantic') and task.output.pydantic is not None:
                if isinstance(task.output.pydantic, expected_model):
                    return task.output.pydantic.model_dump(mode="json"), True
                elif isinstance(task.output.pydantic, dict):
                    validated = expected_model.model_validate(task.output.pydantic)
                    return validated.model_dump(mode="json"), True

            # If raw json string is available
            raw = getattr(task.output, 'raw', None)
            if raw and isinstance(raw, str):
                import json
                parsed = json.loads(raw)
                validated = expected_model.model_validate(parsed)
                return validated.model_dump(mode="json"), True
    except Exception as e:
        logger.warning(f"Failed to parse Pydantic output for task: {e}")

    return {}, False


def run_agents_for_session(
    session_id: str,
    region: str,
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """
    Executes the 4-agent CrewAI pipeline with automatic Primary -> Fallback LLM recovery.
    Primary: settings.PRIMARY_LLM_MODEL (openai/gpt-oss-120b)
    Fallback: settings.FALLBACK_LLM_MODEL (qwen/qwen3.8-27b)
    """
    start_t = time.time()
    selected_llm = settings.PRIMARY_LLM_MODEL
    fallback_used = False
    failure_reason: Optional[str] = None
    crew_execution_success = False

    # 1. Attempt with Primary LLM
    try:
        primary_llm = get_primary_llm()
        crew, d_task, r_task, g_task, c_task = build_crew_pipeline(
            session_id, region, start_time, end_time, llm=primary_llm
        )
        logger.info(f"Running CrewAI with Primary LLM ({settings.PRIMARY_LLM_MODEL}) for session {session_id}...")
        crew.kickoff()
        crew_execution_success = True
    except Exception as primary_err:
        failure_reason = str(primary_err)
        logger.warning(
            f"Primary LLM ({settings.PRIMARY_LLM_MODEL}) failed for session {session_id}: {primary_err}. "
            f"Initiating automatic fallback to {settings.FALLBACK_LLM_MODEL}..."
        )

        # 2. Automatic Fallback with Fallback LLM
        try:
            fallback_used = True
            selected_llm = settings.FALLBACK_LLM_MODEL
            fallback_llm = get_fallback_llm()
            crew, d_task, r_task, g_task, c_task = build_crew_pipeline(
                session_id, region, start_time, end_time, llm=fallback_llm
            )
            logger.info(f"Running CrewAI with Fallback LLM ({settings.FALLBACK_LLM_MODEL}) for session {session_id}...")
            crew.kickoff()
            crew_execution_success = True
        except Exception as fallback_err:
            failure_reason = f"Primary: {failure_reason} | Fallback: {str(fallback_err)}"
            logger.error(f"Both Primary and Fallback LLMs failed for session {session_id}: {failure_reason}")
            crew_execution_success = False

    duration_ms = int((time.time() - start_t) * 1000)

    # 3. Extract outputs safely
    d_data, d_ok = safe_extract_pydantic(d_task, DriverAgentOutput) if crew_execution_success else ({}, False)
    r_data, r_ok = safe_extract_pydantic(r_task, RenewableAgentOutput) if crew_execution_success else ({}, False)
    g_data, g_ok = safe_extract_pydantic(g_task, GridAgentOutput) if crew_execution_success else ({}, False)
    c_data, c_ok = safe_extract_pydantic(c_task, CostCarbonAgentOutput) if crew_execution_success else ({}, False)

    # 4. Safe Database Persistence
    db = SessionLocal()
    try:
        def make_decision(agent_type: str, data: Dict[str, Any], is_ok: bool, context: Dict[str, Any]) -> AgentDecision:
            status_val = "success" if (crew_execution_success and is_ok) else "failed"
            meta_context = {
                **context,
                "selected_llm": selected_llm,
                "fallback_used": fallback_used,
            }
            if failure_reason:
                meta_context["failure_reason"] = failure_reason

            return AgentDecision(
                session_id=session_id,
                agent_type=agent_type,
                input_context=meta_context,
                output_data=data if is_ok else None,
                status=status_val,
                execution_duration_ms=duration_ms
            )

        decisions = [
            make_decision("driver", d_data, d_ok, {"session_id": session_id}),
            make_decision("renewable", r_data, r_ok, {"region": region, "start_time": start_time, "end_time": end_time}),
            make_decision("grid", g_data, g_ok, {"region": region, "start_time": start_time, "end_time": end_time, "session_id": session_id}),
            make_decision("cost_carbon", c_data, c_ok, {"region": region, "start_time": start_time, "end_time": end_time})
        ]

        db.add_all(decisions)
        db.commit()
    except Exception as db_err:
        logger.error(f"Failed to persist agent decisions for session {session_id}: {db_err}")
        db.rollback()
    finally:
        db.close()

    return {
        "session_id": session_id,
        "selected_llm": selected_llm,
        "fallback_used": fallback_used,
        "failure_reason": failure_reason,
        "execution_duration_ms": duration_ms,
        "crew_execution_success": crew_execution_success,
        "driver_ok": d_ok,
        "renewable_ok": r_ok,
        "grid_ok": g_ok,
        "cost_carbon_ok": c_ok
    }
