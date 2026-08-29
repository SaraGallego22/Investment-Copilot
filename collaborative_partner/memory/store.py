"""Persistence for the user profile.

Two backends behind one interface:

* ``JsonMemoryStore`` — one file per user under ``data/memory/``. The default
  for local development, tests and the demo. Files are written with stable
  key order and an indent so ``git diff data/memory/ana.json`` reads clearly:
  in the demo that diff *is* the proof that the agent learned something.
* ``FirestoreMemoryStore`` — the same data in Firestore, used in the deployed
  service so persistence is real and auditable in the Cloud console.

Pick with ``MEMORY_BACKEND``. The Firestore SDK is imported inside the method
that needs it, never at module import, so the package stays importable on a
machine with no GCP credentials.
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from .. import steering
from .schema import UserProfile


class BaseMemoryStore(ABC):
    """Interface every backend implements."""

    @abstractmethod
    def get(self, user_id: str) -> UserProfile | None:
        """Return the stored profile, or None if this user is unknown."""

    @abstractmethod
    def save(self, profile: UserProfile) -> None:
        """Persist the profile, overwriting any previous version."""

    @abstractmethod
    def list_users(self) -> list[str]:
        """Every user id known to this store."""

    def get_or_create(self, user_id: str, **defaults) -> UserProfile:
        """Fetch the profile, or build a fresh one for a first-time user."""
        return self.get(user_id) or UserProfile(user_id=user_id, **defaults)


class JsonMemoryStore(BaseMemoryStore):
    """One JSON file per user. Human-readable on purpose."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or steering.MEMORY_PATH)

    def _file(self, user_id: str) -> Path:
        return self.path / f"{user_id}.json"

    def get(self, user_id: str) -> UserProfile | None:
        f = self._file(user_id)
        if not f.exists():
            return None
        return UserProfile.model_validate_json(f.read_text(encoding="utf-8"))

    def save(self, profile: UserProfile) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        payload = profile.model_dump(mode="json")
        text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

        # Write to a temp file in the same directory, then replace. A crash
        # mid-write leaves the previous profile intact instead of a truncated
        # file the next session cannot parse.
        fd, tmp = tempfile.mkstemp(dir=self.path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self._file(profile.user_id))
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def list_users(self) -> list[str]:
        if not self.path.exists():
            return []
        return sorted(p.stem for p in self.path.glob("*.json"))


class FirestoreMemoryStore(BaseMemoryStore):
    """The same profiles in Firestore, for the deployed service."""

    def __init__(self, collection: str | None = None) -> None:
        from google.cloud import firestore  # imported here, not at module load

        self._client = firestore.Client(project=steering.GCP_PROJECT or None)
        self._collection = self._client.collection(collection or steering.FIRESTORE_COLLECTION)

    def get(self, user_id: str) -> UserProfile | None:
        doc = self._collection.document(user_id).get()
        if not doc.exists:
            return None
        return UserProfile.model_validate(doc.to_dict())

    def save(self, profile: UserProfile) -> None:
        self._collection.document(profile.user_id).set(profile.model_dump(mode="json"))

    def list_users(self) -> list[str]:
        return sorted(d.id for d in self._collection.stream())


def build_store(backend: str | None = None) -> BaseMemoryStore:
    """Construct the configured backend."""
    choice = (backend or steering.MEMORY_BACKEND).lower()
    if choice == "json":
        return JsonMemoryStore()
    if choice == "firestore":
        return FirestoreMemoryStore()
    raise ValueError(f"Unknown MEMORY_BACKEND '{choice}'. Use 'json' or 'firestore'.")


#: Backwards-compatible alias for the original scaffold's class name.
MemoryStore = JsonMemoryStore
