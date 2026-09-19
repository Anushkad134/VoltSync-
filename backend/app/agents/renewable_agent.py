from typing import Optional
from crewai import Agent, LLM
from app.agents.tools.renewable_data_tool import fetch_renewable_data
from app.agents.tools.weather_data_tool import fetch_weather_data

def get_renewable_agent(llm: Optional[LLM] = None) -> Agent:
    kwargs = {}
    if llm is not None:
        kwargs["llm"] = llm
    return Agent(
        role="Renewable Agent",
        goal="Identify charging periods with strong renewable availability.",
        backstory="You are a specialist analyst assessing renewable energy availability (solar, wind, hydro). You identify green windows but you do not make the final charging schedule decision.",
        tools=[fetch_renewable_data, fetch_weather_data],
        verbose=True,
        allow_delegation=False,
        **kwargs
    )
