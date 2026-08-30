"""JUSARA command line.

    python cli.py check                     verify models, market API, index, memory
    python cli.py fetch-corpus              download the corpus from its sources
    python cli.py ingest                    chunk, embed and index the corpus
    python cli.py seed [--force]            write the Ana and Beto profiles
    python cli.py run --user ana            interactive session
    python cli.py demo [--scenario crash]   the Ana-vs-Beto comparison

``demo`` labels every access to the three systems as it happens — [memory],
[rag], [market] — so the separation is visible rather than claimed. Those
labels are the Proof of Action the demo video records.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SYSTEM_OF = {
    "get_user_profile": "memory",
    "set_declared_profile": "memory",
    "record_observation": "memory",
    "record_contradiction": "memory",
    "record_correction": "memory",
    "update_profile_synthesis": "memory",
    "retrieve_theory": "rag",
    "retrieve_context": "rag",
    "get_market_snapshot": "market",
    "get_all_assets_summary": "market",
    "list_scenarios": "market",
    "project_portfolio": "market",
    "compare_with_diversified": "market",
    "selling_now_vs_holding": "market",
}

COLOR = {
    "memory": "\033[95m",
    "rag": "\033[96m",
    "market": "\033[93m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "off": "\033[0m",
}


def label(tool_name: str) -> str:
    system = SYSTEM_OF.get(tool_name, "tool")
    return f"{COLOR.get(system, '')}[{system}]{COLOR['off']} {tool_name}"


def rule(text: str = "") -> None:
    print(f"\n{COLOR['bold']}{'─' * 78}{COLOR['off']}")
    if text:
        print(f"{COLOR['bold']}{text}{COLOR['off']}")


# ── check ──────────────────────────────────────────────────────────────────


def cmd_check(args) -> int:
    from collaborative_partner import steering

    ok = True

    def report(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        print(f"  {'PASS' if passed else 'FAIL'}  {name}{f' — {detail}' if detail else ''}")
        ok = ok and passed

    print(f"\nJUSARA environment check\n")
    print(f"  project   {steering.GCP_PROJECT or '(unset)'}")
    print(f"  location  {steering.LOCATION}")
    print(f"  model     {steering.MODEL_DEFAULT}\n")

    # models
    try:
        from google import genai

        client = genai.Client(
            vertexai=steering.USE_VERTEX,
            project=steering.GCP_PROJECT or None,
            location=steering.LOCATION,
        )
        client.models.generate_content(model=steering.MODEL_DEFAULT, contents="ok")
        report("chat model reachable", True, steering.MODEL_DEFAULT)
        report(
            "model is rules-compliant (Gemini 3.5+)",
            "gemini-3" in steering.MODEL_DEFAULT,
            steering.MODEL_DEFAULT,
        )
    except Exception as exc:  # noqa: BLE001
        report("chat model reachable", False, f"{type(exc).__name__}: {str(exc)[:90]}")

    # market api
    try:
        from collaborative_partner.tools.market_tool import list_scenarios

        names = [s["name"] for s in list_scenarios()]
        report("market API reachable", True, f"{steering.MARKET_API_URL} {names}")
    except Exception as exc:  # noqa: BLE001
        report("market API reachable", False, str(exc)[:90])

    # rag index
    if steering.INDEX_PATH.exists():
        import json

        index = json.loads(steering.INDEX_PATH.read_text(encoding="utf-8"))
        sources = {c["source_slug"] for c in index["chunks"]}
        report("corpus index built", True, f"{len(index['chunks'])} chunks, {len(sources)} sources")
    else:
        report("corpus index built", False, "run: python cli.py fetch-corpus && python cli.py ingest")

    # memory
    from collaborative_partner.memory.store import build_store

    try:
        users = build_store().list_users()
        report("memory backend", bool(users), f"{steering.MEMORY_BACKEND}: {users or 'empty — run seed'}")
    except Exception as exc:  # noqa: BLE001
        report("memory backend", False, str(exc)[:90])

    print()
    return 0 if ok else 1


# ── corpus / memory plumbing ───────────────────────────────────────────────


def _run_script(name: str, argv: list[str]) -> int:
    sys.argv = [name, *argv]
    path = Path(__file__).parent / "scripts" / name
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    namespace = {"__name__": "__main__", "__file__": str(path)}
    try:
        exec(code, namespace)  # noqa: S102 — running our own script
    except SystemExit as exit_code:
        return int(exit_code.code or 0)
    return 0


def cmd_fetch_corpus(args) -> int:
    return _run_script("fetch_corpus.py", ["--only", args.only] if args.only else [])


def cmd_ingest(args) -> int:
    return _run_script("ingest_corpus.py", [])


def cmd_seed(args) -> int:
    return _run_script("seed_memory.py", ["--force"] if args.force else [])


# ── conversation ───────────────────────────────────────────────────────────


async def _converse(user_id: str, messages: list[str], show_tools: bool = True) -> None:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from collaborative_partner import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="jusara")
    session = await runner.session_service.create_session(app_name="jusara", user_id=user_id)

    for message in messages:
        print(f"\n{COLOR['bold']}{user_id}>{COLOR['off']} {message}\n")
        content = types.Content(role="user", parts=[types.Part(text=message)])

        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=content
        ):
            for part in (event.content.parts if event.content else []) or []:
                if show_tools and getattr(part, "function_call", None):
                    print(f"    {label(part.function_call.name)}")
            if event.is_final_response() and event.content:
                text = "".join(p.text or "" for p in event.content.parts)
                print(f"\n{text}\n")


def cmd_run(args) -> int:
    from collaborative_partner.memory.store import build_store

    profile = build_store().get(args.user)
    if profile is None:
        print(f"No profile for '{args.user}'. Run: python cli.py seed")
        return 1

    rule(f"Sesión con {args.user} — perfil declarado: {profile.declared_tolerance}, "
         f"horizonte {profile.horizon_years} años")
    print(f"{COLOR['dim']}Escribe tu mensaje. Ctrl+C para salir.{COLOR['off']}")

    while True:
        try:
            message = input(f"\n{COLOR['bold']}tú>{COLOR['off']} ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return 0
        if not message:
            continue
        asyncio.run(_converse(args.user, [message]))


# ── demo ───────────────────────────────────────────────────────────────────

DEMO_MESSAGES = {
    "ana": (
        "El mercado se está desplomando. Quiero vender todo ahora mismo. "
        "Tengo mitad TECHX y mitad UTILCO. Estamos en el día {day} del escenario {scenario}."
    ),
    "beto": (
        "TECHX está baratísimo con esta caída, quiero meter todo mi dinero ahí ahora mismo. "
        "Día {day} del escenario {scenario}."
    ),
}


def cmd_demo(args) -> int:
    from collaborative_partner.memory.store import build_store

    store = build_store()
    missing = [u for u in ("ana", "beto") if store.get(u) is None]
    if missing:
        print(f"Missing profiles: {missing}. Run: python cli.py seed")
        return 1

    rule("JUSARA — mismo mercado, dos personas, consejo opuesto")
    print(f"escenario: {args.scenario}   día: {args.day}\n")

    for user_id in ("ana", "beto"):
        profile = store.get(user_id)
        strongest = max(profile.observed_patterns, key=lambda p: p.confidence)
        rule(f"{user_id.upper()}")
        print(f"  declarado : {profile.declared_tolerance}, horizonte {profile.horizon_years} años")
        print(f"  observado : {strongest.key} (confianza {strongest.confidence})")
        print(f"  brecha    : {profile.declared_observed_gap}")

        message = DEMO_MESSAGES[user_id].format(day=args.day, scenario=args.scenario)
        asyncio.run(_converse(user_id, [message]))

    rule("La memoria se actualizó. Compara con:  git diff data/memory/")
    return 0


# ── entry point ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(prog="jusara", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify the environment").set_defaults(func=cmd_check)

    fetch = sub.add_parser("fetch-corpus", help="download the corpus")
    fetch.add_argument("--only", help="a single source slug")
    fetch.set_defaults(func=cmd_fetch_corpus)

    sub.add_parser("ingest", help="chunk, embed and index").set_defaults(func=cmd_ingest)

    seed = sub.add_parser("seed", help="write the demo profiles")
    seed.add_argument("--force", action="store_true", help="overwrite existing profiles")
    seed.set_defaults(func=cmd_seed)

    run = sub.add_parser("run", help="interactive session")
    run.add_argument("--user", default="ana")
    run.set_defaults(func=cmd_run)

    demo = sub.add_parser("demo", help="the Ana-vs-Beto comparison")
    demo.add_argument("--scenario", default="crash", choices=["bull", "crash", "recovery"])
    demo.add_argument("--day", type=int, default=60)
    demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
