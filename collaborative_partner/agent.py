"""JUSARA — root agent and reflection agent (ADK).

Two agents, deliberately separate:

* ``root_agent`` runs the conversation. It reads memory, queries the market,
  retrieves theory, and advises — never trades.
* ``reflection_agent`` runs once at the end of a session. It reads the
  transcript and rewrites what the system believes about the user. It has no
  market or theory tools, only memory-writing ones, so it cannot wander off
  into giving advice; its single job is to learn.

Both run on Gemini Flash. The design originally escalated the reflection step
to a Pro model, but no Pro-class Gemini 3.5 model exists on Vertex (every
``gemini-3.5-pro*`` variant 404s, and 2.5 Pro violates the contest's "3.5 or
newer" rule). Reflection instead raises the *thinking budget* on the same
model: cheaper than a larger model, rules-compliant, and a better fit — the
task needs more deliberation, not more knowledge.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.genai import types

from . import steering
from .prompts import REFLECTION_INSTRUCTIONS, ROOT_AGENT_INSTRUCTIONS
from .tools.market_tool import (
    get_all_assets_summary,
    get_market_snapshot,
    list_scenarios,
)
from .tools.memory_tool import (
    get_user_profile,
    record_contradiction,
    record_correction,
    record_observation,
    set_declared_profile,
    update_profile_synthesis,
)
from .tools.projector import (
    compare_with_diversified,
    project_portfolio,
    selling_now_vs_holding,
)
from .tools.rag_tool import retrieve_theory

#: Low temperature: this agent quotes sources and reports computed numbers.
#: Creative variance here shows up as invented statistics.
ADVICE_CONFIG = types.GenerateContentConfig(temperature=0.3)

REFLECTION_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    thinking_config=types.ThinkingConfig(
        thinking_budget=steering.REFLECTION_THINKING_BUDGET
    ),
)

root_agent = LlmAgent(
    name="jusara",
    model=steering.MODEL_DEFAULT,
    description=(
        "Investment copilot that advises but never trades, and learns the gap "
        "between a user's declared risk profile and their observed behaviour."
    ),
    instruction=ROOT_AGENT_INSTRUCTIONS,
    generate_content_config=ADVICE_CONFIG,
    tools=[
        # memory — the user
        get_user_profile,
        set_declared_profile,
        record_observation,
        record_contradiction,
        record_correction,
        update_profile_synthesis,
        # rag — the world
        retrieve_theory,
        # market — the environment
        get_market_snapshot,
        get_all_assets_summary,
        list_scenarios,
        # deterministic arithmetic, so the model never improvises a number
        project_portfolio,
        compare_with_diversified,
        selling_now_vs_holding,
    ],
)

reflection_agent = LlmAgent(
    name="jusara_reflection",
    model=steering.MODEL_COMPLEX_REASONING,
    description="Reads a finished session and updates the user's observed profile.",
    instruction=REFLECTION_INSTRUCTIONS,
    generate_content_config=REFLECTION_CONFIG,
    tools=[
        get_user_profile,
        record_observation,
        record_contradiction,
        record_correction,
        update_profile_synthesis,
    ],
)

__all__ = ["root_agent", "reflection_agent"]
