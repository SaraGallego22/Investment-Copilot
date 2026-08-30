# CLAUDE.md

Contexto operativo para Claude Code en este repo. La descripción completa está
en [`README.md`](./README.md); el diseño en
[`docs/architecture.md`](./docs/architecture.md) y
[`docs/challenge_design.md`](./docs/challenge_design.md).

## Qué es esto

**JUSARA** — copiloto de inversión para el track *The Collaborative Partner* del
All Things Agentic Hackathon (Google Cloud). Deadline: **31 de agosto de 2026,
5:00 PM PT**.

El agente aconseja pero **nunca opera**. Su tema real no es el mercado sino el
usuario: aprende la brecha entre el perfil de riesgo que una persona **declara**
y el que su **conducta revela**, y se lo devuelve antes de que actúe en contra
de sí misma.

## El diferenciador que no se puede perder

Tres sistemas **separados y visibles**, no tres nombres para lo mismo:

- **Memoria** (`collaborative_partner/memory/`) = el usuario. Dos capas:
  declarada (onboarding) y observada (patrones aprendidos con confianza).
- **RAG** (`collaborative_partner/rag/`) = el mundo. Teoría de inversión
  descargada de SEC y CNMV, no escrita por nosotros.
- **Market API** (`market_api/`) = el entorno. Servicio aparte en Cloud Run.

Al cerrar sesión, un agente de **reflexión** reescribe el perfil observado. Ese
paso es lo que separa memoria que *aprende* de memoria que solo *recuerda*.

## Restricciones verificadas — no las cambies sin comprobarlo

Estas se verificaron en vivo contra el proyecto el 2026-08-29:

- **`GOOGLE_CLOUD_LOCATION` debe ser `global`.** Los modelos Gemini 3.5 dan 404
  en us-central1, us-east5, europe-west4, us-west1 y asia-northeast1.
- **No existe un Gemini 3.5 Pro** en Vertex. La reflexión usa el mismo Flash con
  `thinking_budget` elevado. `gemini-2.5-pro` existe pero **incumple** la regla
  del concurso ("3.5 or newer") y descalificaría la entrega.
- **`CLOUD_RUN_REGION` es distinto de `GOOGLE_CLOUD_LOCATION`.** `global` es un
  endpoint válido de Vertex pero **no** una región válida de Cloud Run.
- **`data/corpus/` y `data/index/` se commitean.** Excluirlos entregaría a los
  jueces un agente con la base de conocimiento vacía.

## Reglas de código aprendidas a golpes

- **Nada de clientes en tiempo de import.** Un `firestore.Client()` a nivel de
  módulo rompía `import collaborative_partner` en cualquier máquina sin
  credenciales. Igual con leer config: `auth.py` leía la API key al importar y
  el primer módulo de test que cargara fijaba la clave para toda la sesión.
- **El `user_id` nunca es parámetro del modelo.** Sale de la sesión ADK vía
  `ToolContext`. Cuando era argumento, el modelo se lo inventó y trató a una
  usuaria con 4 sesiones de historial como desconocida.
- **El modelo no hace aritmética.** Toda la matemática de cartera vive en
  `tools/projector.py`, determinista. Un modelo componiendo retornos a 90 días
  da un número confiado y equivocado.
- **Toda cita lleva institución.** El retriever devuelve `source_org`, no un
  nombre de archivo.

## Estructura

```
collaborative_partner/       # agente ADK
  agent.py                   # root_agent + reflection_agent
  prompts.py                 # rol, guardrails, few-shot de la confrontación
  steering.py                # fuente de verdad de configuración
  memory/  schema.py         # UserProfile: capa declarada + observada
           store.py          # JsonMemoryStore | FirestoreMemoryStore
  rag/     ingest.py         # chunking + embeddings
           retriever.py      # coseno + diversificación por fuente
  tools/   market_tool.py    # cliente HTTP del simulador
           memory_tool.py    # lectura/escritura del perfil
           rag_tool.py       # recuperación con cita
           projector.py      # aritmética determinista
market_api/                  # servicio independiente (FastAPI + GBM)
web/                         # app FastAPI + UI de 3 paneles
data/    corpus_manifest.yaml  corpus/  index/  memory/
scripts/ fetch_corpus · ingest_corpus · seed_memory · smoke_test_api
cli.py                       # check · fetch-corpus · ingest · seed · run · demo
```

## Comandos

```bash
pip install -e ".[dev]"
python cli.py check                  # modelos, market API, índice, memoria
python cli.py fetch-corpus           # descarga SEC + CNMV
python cli.py ingest                 # chunking + embeddings -> data/index/
python cli.py seed                   # perfiles de ana y beto
python cli.py demo --scenario crash  # el caso Ana vs Beto completo
python cli.py run --user ana         # sesión interactiva
uvicorn web.app:app --port 8080      # UI local
uvicorn market_api.main:app --port 8081
pytest
```

Deploy: `./market_api/deploy.sh` y `./deploy/deploy_cloud_run.sh`.

## Desplegado

| Servicio | URL |
|---|---|
| Agente + UI | https://jusara-agent-904662129922.us-central1.run.app |
| Simulador | https://jusara-market-api-904662129922.us-central1.run.app |

Proyecto GCP `agentic-507018`. La memoria en producción vive en Firestore,
colección `user_profiles`.

## Pendiente

- [ ] Grabar el video (≤4 min, con la consola de GCP visible). Guion en
      [`docs/demo_script.md`](./docs/demo_script.md).
- [ ] Subirlo a YouTube **público** (no "no listado" — las reglas lo exigen).
- [ ] Enviar en Devpost: repo, URL hosteada, descripción
      (usar [`docs/architecture.md`](./docs/architecture.md)), diagrama.
- [ ] Opcional (+0,4 puntos): post de blog y post social con
      `#AllThingsAgenticHackathon`.
