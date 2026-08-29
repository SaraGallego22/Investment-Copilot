"""Root agent definition (ADK).

Esqueleto genérico: una vez elegida la idea concreta (ver CLAUDE.md,
"Decision pendiente"), este agente probablemente se divida en
sub-agentes especializados (p.ej. quiz_agent, explainer_agent) usando
uno de los patrones de orquestación de ADK.
"""

import os

from google.adk.agents import Agent

from .prompts import ROOT_AGENT_INSTRUCTIONS
from .tools.memory_tool import get_user_profile, update_user_profile
from .tools.rag_tool import retrieve_context

MODEL_DEFAULT = os.getenv("MODEL_DEFAULT", "gemini-flash")

root_agent = Agent(
    name="collaborative_partner",
    model=MODEL_DEFAULT,
    description="Compañero colaborativo con memoria persistente y RAG.",
    instruction=ROOT_AGENT_INSTRUCTIONS,
    tools=[retrieve_context, get_user_profile, update_user_profile],
)
