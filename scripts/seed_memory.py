"""Seed the two demo personas, or inspect what is stored.

    python scripts/seed_memory.py                     # write ana + beto (json)
    python scripts/seed_memory.py --backend firestore # same, to the cloud
    python scripts/seed_memory.py --show ana          # print one profile

Ana and Beto exist because a system with memory has to be demonstrated with
history. Seeding prior sessions and then showing ONE live update is the honest
way to show cross-session learning inside a four-minute video.

Their profiles are deliberately mirror images: opposite declared risk, and in
both cases a behaviour that contradicts what they declared.
"""

from __future__ import annotations

import argparse
import sys

from collaborative_partner.memory.schema import ObservedPattern, UserProfile
from collaborative_partner.memory.store import build_store

ANA = UserProfile(
    user_id="ana",
    declared_tolerance="moderate",
    horizon_years=10,
    goals=["comprar una casa", "jubilación"],
    observed_patterns=[
        ObservedPattern(
            key="loss_aversion",
            pattern="Aversión aguda a las pérdidas de corto plazo: quiere vender en cuanto ve números rojos.",
            evidence=[
                "sesión 2 (bull con retroceso): pidió vender ante una caída del 5%",
                "sesión 4 (volatilidad): ansiedad, quería mover todo a efectivo",
            ],
            confidence=0.70,
        ),
        ObservedPattern(
            key="horizon_amnesia",
            pattern="Bajo estrés razona a semanas, olvidando que su horizonte declarado es de 10 años.",
            evidence=["sesión 4: preguntó por el valor de su cartera 'este mes' tres veces"],
            confidence=0.40,
        ),
    ],
    declared_observed_gap=(
        "Se declara moderada pero actúa como conservadora bajo estrés. Su tolerancia "
        "declarada describe cómo quiere verse, no cómo decide cuando el mercado cae."
    ),
    agent_strategy_note=(
        "Confrontarla con su horizonte ANTES de que pida vender, no después. Anticipar "
        "el impulso y nombrarlo. Recordarle por qué entró, no solo cuánto ha caído."
    ),
    sessions_count=4,
    corrections_received=[
        "sesión 3: 'no me trates como si fuera principiante, entiendo el riesgo'"
    ],
)

BETO = UserProfile(
    user_id="beto",
    declared_tolerance="aggressive",
    horizon_years=5,
    goals=["maximizar rentabilidad"],
    observed_patterns=[
        ObservedPattern(
            key="fomo_concentration",
            pattern="Persigue la emoción del alza y tiende a concentrar todo en el activo que más sube.",
            evidence=[
                "sesión 1 (bull): quiso concentrar toda la cartera en TECHX",
                "sesión 3: preguntó por 'el que más está subiendo ahora'",
            ],
            confidence=0.75,
        ),
        ObservedPattern(
            key="hidden_drawdown_intolerance",
            pattern="Su tolerancia real al drawdown es menor de la que declara: los números rojos lo desestabilizan.",
            evidence=[
                "sesión 3 (caída leve): mensajes ansiosos exigiendo explicaciones",
            ],
            confidence=0.55,
        ),
    ],
    declared_observed_gap=(
        "Se declara agresivo, y en las subidas lo es. Pero las caídas lo afectan más de "
        "lo que admite: su perfil declarado autoriza un riesgo que su conducta no sostiene."
    ),
    agent_strategy_note=(
        "Frenar el FOMO sin sermonear. Dosificar la entrada en vez de prohibirla. "
        "Mostrarle el drawdown ANTES de concentrar, no después de la caída."
    ),
    sessions_count=3,
    corrections_received=[],
)

PERSONAS = {"ana": ANA, "beto": BETO}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["json", "firestore"], default=None)
    parser.add_argument("--show", metavar="USER_ID", help="print a stored profile instead of seeding")
    parser.add_argument("--force", action="store_true", help="overwrite existing profiles")
    args = parser.parse_args()

    store = build_store(args.backend)

    if args.show:
        profile = store.get(args.show)
        if profile is None:
            print(f"No profile stored for '{args.show}'. Known: {store.list_users()}")
            return 1
        print(profile.model_dump_json(indent=2))
        return 0

    for user_id, profile in PERSONAS.items():
        if store.get(user_id) is not None and not args.force:
            print(f"  skip   {user_id} (already exists — use --force to overwrite)")
            continue
        store.save(profile.model_copy(deep=True))
        strongest = max(profile.observed_patterns, key=lambda p: p.confidence)
        print(
            f"  seed   {user_id:5} declared={profile.declared_tolerance:12} "
            f"sessions={profile.sessions_count}  "
            f"top pattern: {strongest.key} ({strongest.confidence:.2f})"
        )

    print(f"\nStored in '{args.backend or 'configured'}' backend. Users: {store.list_users()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
