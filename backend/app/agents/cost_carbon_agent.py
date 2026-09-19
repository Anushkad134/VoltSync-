from typing import Optional
from crewai import Agent, LLM
from app.agents.tools.tariff_carbon_tool import fetch_tariff_carbon_data

def get_cost_carbon_agent(llm: Optional[LLM] = None) -> Agent:
    kwargs = {}
    if llm is not None:
        kwargs["llm"] = llm
    return Agent(
        role="Cost & Carbon Agent",
        goal="Evaluate financial and carbon implications of candidate charging windows.",
        backstory="You are a specialist analyst calculating electricity cost and carbon emissions. You identify the cheapest and lowest-carbon windows but you do not make the final charging schedule decision.",
        tools=[fetch_tariff_carbon_data],
        verbose=True,
        allow_delegation=False,
        **kwargs
    )
