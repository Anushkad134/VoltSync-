from typing import Optional
from crewai import Agent, LLM
from app.agents.tools.session_data_tool import fetch_session_data
from app.agents.tools.station_data_tool import fetch_station_data

def get_driver_agent(llm: Optional[LLM] = None) -> Agent:
    kwargs = {}
    if llm is not None:
        kwargs["llm"] = llm
    return Agent(
        role="Driver Agent",
        goal="Understand the driver's charging requirements and identify the session's urgency and flexibility.",
        backstory="You are a specialist analyst representing the EV driver's interests. You ensure charging requirements are met but you do not make the final charging schedule decision.",
        tools=[fetch_session_data, fetch_station_data],
        verbose=True,
        allow_delegation=False,
        **kwargs
    )
