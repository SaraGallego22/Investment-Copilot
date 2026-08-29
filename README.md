# Collaborative Partner — All Things Agentic Hackathon

Agente conversacional con **memoria persistente entre sesiones** y **RAG**, construido para el track *The Collaborative Partner* del [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/resources) (Gemini / Google Cloud).

Contexto completo del hackathon y de la decisión de track: [`hackathon-agentic.md`](./hackathon-agentic.md).
Contexto operativo para trabajar en este repo: [`CLAUDE.md`](./CLAUDE.md).

## Idea

> Pendiente de elegir entre las 5 candidatas listadas en `hackathon-agentic.md` (tutor adaptativo, compañero de lectura, coach de habilidades, second brain, planificador personalizado).

## Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows
pip install -e .
cp .env.example .env       # completar credenciales/proyecto de GCP
python scripts/ingest_corpus.py
adk run collaborative_partner
```

## Estructura

Ver [`CLAUDE.md`](./CLAUDE.md#estructura-del-repo).
