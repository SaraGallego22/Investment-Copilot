"""Esquema del perfil de usuario (la "memoria" del agente).

Esto es lo que separa memoria de RAG: no es conocimiento del corpus,
es lo que el agente sabe sobre ESTE usuario a través de sesiones.

TODO: ajustar los campos según la idea elegida. Ejemplos según
hackathon-agentic.md sección 4:
- Tutor adaptativo: `weak_topics`, `preferred_example_style`, `difficulty_level`.
- Compañero de lectura: `mastered_concepts`, `reading_pace`.
- Coach de habilidades: `recurring_mistakes`, `scenario_history`.
- Second brain: `interests`, `preferred_summary_style`.
- Planificador: `constraints`, `disliked_options`, `past_feedback`.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UserProfile:
    user_id: str
    preferences: dict = field(default_factory=dict)
    weak_points: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()
