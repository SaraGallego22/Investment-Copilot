"""CLI de desarrollo: inspecciona o siembra el perfil de un usuario en memoria.

Uso:
    python scripts/seed_memory.py <user_id>
"""

import sys

from collaborative_partner.memory.store import MemoryStore


def main(user_id: str) -> None:
    store = MemoryStore()
    profile = store.get_profile(user_id)
    print(profile)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python scripts/seed_memory.py <user_id>")
        sys.exit(1)
    main(sys.argv[1])
