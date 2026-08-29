"""Tools de memoria expuestas al agente: lo que se sabe de ESTE usuario.

Separadas deliberadamente de `rag_tool.py` — ver CLAUDE.md, "El
diferenciador que no se puede perder".
"""

from ..memory.store import MemoryStore

_store = MemoryStore()


def get_user_profile(user_id: str) -> dict:
    """Devuelve el perfil persistido del usuario (preferencias, puntos
    débiles, notas de sesiones anteriores)."""
    return vars(_store.get_profile(user_id))


def update_user_profile(
    user_id: str,
    preferences: dict | None = None,
    weak_points: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict:
    """Actualiza el perfil del usuario con lo aprendido en esta sesión.

    Llamar al cierre de la sesión o cuando el usuario corrija algo
    explícitamente, para que la personalización persista a la sesión
    siguiente.
    """
    profile = _store.get_profile(user_id)
    if preferences:
        profile.preferences.update(preferences)
    if weak_points:
        profile.weak_points = sorted(set(profile.weak_points) | set(weak_points))
    if notes:
        profile.notes.extend(notes)
    _store.save_profile(profile)
    return vars(profile)
