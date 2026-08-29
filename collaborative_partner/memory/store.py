"""Persistencia del perfil de usuario.

Abstrae el backend real (Vertex Memory Bank o Firestore, ver
hackathon-agentic.md sección 5) detrás de una interfaz simple para que
el resto del agente no dependa del proveedor concreto.
"""

from __future__ import annotations

import os
from dataclasses import asdict

from .schema import UserProfile

_COLLECTION = os.getenv("FIRESTORE_COLLECTION_USER_PROFILES", "user_profiles")


class MemoryStore:
    """Cliente de memoria persistente. Implementación por defecto: Firestore."""

    def __init__(self) -> None:
        from google.cloud import firestore  # import local: evita costo si no se usa

        self._client = firestore.Client()
        self._collection = self._client.collection(_COLLECTION)

    def get_profile(self, user_id: str) -> UserProfile:
        doc = self._collection.document(user_id).get()
        if not doc.exists:
            return UserProfile(user_id=user_id)
        return UserProfile(**doc.to_dict())

    def save_profile(self, profile: UserProfile) -> None:
        profile.touch()
        self._collection.document(profile.user_id).set(asdict(profile))
