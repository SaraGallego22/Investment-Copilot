"""Root agent definition (ADK).

Esqueleto genérico: una vez elegida la idea concreta (ver CLAUDE.md,
"Decision pendiente"), este agente probablemente se divida en
sub-agentes especializados (p.ej. quiz_agent, explainer_agent) usando
uno de los patrones de orquestación de ADK.
"""

from google.adk.agents import Agent

from . import steering
from .prompts import ROOT_AGENT_INSTRUCTIONS
from .tools.memory_tool import (
    get_user_profile,
    record_contradiction,
    record_correction,
    record_observation,
    set_declared_profile,
    update_profile_synthesis,
)
from .tools.rag_tool import retrieve_context

root_agent = Agent(
    name="collaborative_partner",
    model=steering.MODEL_DEFAULT,
    description="Compañero colaborativo con memoria persistente y RAG.",
    instruction=ROOT_AGENT_INSTRUCTIONS,
    tools=[
        retrieve_context,
        get_user_profile,
        set_declared_profile,
        record_observation,
        record_contradiction,
        record_correction,
        update_profile_synthesis,
    ],
)
