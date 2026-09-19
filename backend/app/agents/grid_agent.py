from typing import Optional
from crewai import Agent, LLM
from app.agents.tools.grid_data_tool import fetch_grid_data
from app.agents.tools.session_data_tool import fetch_session_data
from app.agents.tools.station_data_tool import fetch_station_data

def get_grid_agent(llm: Optional[LLM] = None) -> Agent:
    kwargs = {}
    if llm is not None:
        kwargs["llm"] = llm
    return Agent(
        role="Grid Agent",
        goal="Determine how charging affects local grid conditions and recommend full power, reduced power, or delay.",
        backstory="You are a specialist analyst focused on grid stability. You evaluate grid stress, but you do not make the final charging schedule decision.",
        tools=[fetch_grid_data, fetch_session_data, fetch_station_data],
        verbose=True,
        allow_delegation=False,
        **kwargs
    )
