# CLAUDE.md

Contexto de trabajo para Claude Code en este repo. Lee también [`hackathon-agentic.md`](./hackathon-agentic.md) — es la fuente completa del contexto del hackathon; este archivo solo resume lo operativo.

## Qué es esto

Proyecto para el **All Things Agentic Hackathon** (Gemini/Google Cloud). Deadline: **31 de agosto de 2026**.

Track elegido: **The Collaborative Partner** — un agente conversacional multi-turno con:
1. **Memoria persistente** entre sesiones (no solo dentro de un chat).
2. **RAG** sobre un corpus externo.
3. **Personalización adaptativa**: el agente aprende de correcciones del usuario y cambia su comportamiento en sesiones futuras.

### El diferenciador que no se puede perder
No es "un chatbot con RAG". Hay que mantener **memoria y RAG como dos sistemas separados y visibles**:
- **RAG** (`collaborative_partner/rag/`) = conocimiento externo (el corpus/documento).
- **Memoria** (`collaborative_partner/memory/`) = el usuario (preferencias, errores recurrentes, historial de aprendizaje).

Al cerrar una sesión, el agente debe escribir/actualizar un **perfil de usuario** explícito (paso de "reflexión"), y la demo debe mostrar ese perfil cambiando y afectando la sesión siguiente.

## Decisión pendiente (bloqueante)

Aún no se eligió **cuál** de las 5 ideas candidatas (ver sección 4 de `hackathon-agentic.md`) se construye: tutor adaptativo, compañero de lectura de documentos densos, coach de habilidades, second brain, o planificador personalizado. El código en `collaborative_partner/` está armado como esqueleto genérico con `TODO`s marcando dónde entra la decisión de dominio (tema del corpus, campos del perfil de usuario, tipo de sesión). Antes de construir features de dominio, confirmar la idea con el usuario.

## Estructura del repo

```
collaborative_partner/       # paquete del agente ADK
  __init__.py                 # expone root_agent
  agent.py                    # definición del agente raíz / orquestación
  prompts.py                  # system instructions
  tools/
    rag_tool.py                # tool de recuperación (llama a rag/retriever.py)
    memory_tool.py              # tool de lectura/escritura del perfil de usuario
  memory/
    schema.py                   # modelo del perfil de usuario (qué se recuerda)
    store.py                    # cliente de persistencia (Firestore / Memory Bank)
  rag/
    ingest.py                   # chunking + indexado del corpus
    retriever.py                # consulta al vector store

data/corpus/                 # documentos fuente para RAG (no versionar contenido pesado/privado)
scripts/
  ingest_corpus.py             # CLI para indexar data/corpus/
  seed_memory.py                # CLI para sembrar/inspeccionar memoria en dev
tests/                        # pytest
deploy/
  Dockerfile                    # imagen para Cloud Run
  deploy_cloud_run.sh
docs/
  demo_script.md                # guion de la demo (memoria + RAG + adaptación en vivo)
```

## Stack técnico

- **Framework de agente:** ADK (`google-adk`, https://github.com/google/adk-python).
- **Modelos:** **Gemini Flash** por defecto; **Gemini Pro** solo para el razonamiento final complejo. No usar Pro en el loop principal sin justificarlo.
- **Memoria persistente:** Vertex Memory Bank o Firestore (`collaborative_partner/memory/store.py` abstrae cuál).
- **RAG:** Vertex AI Search / RAG Engine, o vector store serverless. Evitar clusters siempre encendidos.
- **Deploy:** Cloud Run (scale-to-zero) o Agent Engine.

## Convenciones de costo (del propio hackathon — respetarlas en el código)

- Modelo por defecto = Flash; escalar a Pro solo puntualmente y de forma explícita.
- Cloud Run con mínimo de instancias en 0 y techo máximo definido.
- Vector search serverless, no clusters permanentes.
- Guardar solo el estado esencial en memoria; comprimir/podar memorias largas.
- Proteger cualquier endpoint público con API key/auth.

## Comandos

- `pip install -e .` — instalar dependencias del paquete.
- `python -m collaborative_partner.agent` o `adk run collaborative_partner` — correr el agente localmente (según se configure el entrypoint).
- `python scripts/ingest_corpus.py` — indexar `data/corpus/` para RAG.
- `pytest` — correr tests.

## Próximos pasos (de `hackathon-agentic.md`, sección 7)

- [ ] Elegir una de las 5 ideas candidatas.
- [ ] Definir el esquema de memoria (`collaborative_partner/memory/schema.py`).
- [ ] Definir el flujo de RAG (corpus, chunking, recuperación).
- [ ] Escribir el guion de demo (`docs/demo_script.md`) que pruebe memoria + RAG + adaptación en vivo.
- [ ] Desplegar el esqueleto en Cloud Run.
