# All Things Agentic Hackathon — Contexto y plan

> Fuente: página oficial del hackathon en Devpost (`allthingsagentichackathon.devpost.com/resources`).
> Este documento resume el hackathon y fija nuestra decisión: **construir para el track "The Collaborative Partner"**.

---

## 1. Datos clave del hackathon

- **Nombre:** All Things Agentic Hackathon (patrocinado por **Gemini / Google Cloud**).
- **Fecha límite de entrega:** **31 de agosto de 2026**.
- **Participantes:** ~11.482.
- **Créditos:** Free trial en `cloud.google.com/free` + **$150 USD en créditos de Google Cloud** (se solicitan vía el credit form del evento).
- **Ayuda:** Discord de Devpost, foro de discusión, FAQs y webinars.

### Webinars relevantes (on-demand)
| Fecha | Tema | Idea central |
|-------|------|--------------|
| Ago 11 | Architecting Multi-Agent Teams: Three Orchestration Patterns of ADK | De un solo agente a un sistema multi-agente; qué patrón usar. |
| Ago 13 | Build a Long-Running Agent: Persistent Workflows with ADK | Recuperación ante fallos, aprobación humana, la "trampa de idempotencia". |
| Ago 20 | Build a Self-Evolving Agent | Un agente que reescribe sus propias instrucciones (y cómo evita "gamear" la métrica). |
| Ago 25 | Devpost Build Session Q&A con Google Cloud | Sesión de preguntas. |
| Ago 27 | **Architecting Agent Memory: Session State, Vector Search, and Managed Cloud Memory** | **"Persistencia no es memoria"; sube toda la jerarquía, de un pez de colores olvidadizo a memoria gestionada en la nube.** ← muy relevante para nuestro track. |

---

## 2. Los tres tracks (resumen)

### The Taskmaster
- **Enfoque:** flujo **event-driven** con enrutamiento autónomo. El sistema es un coordinador: detecta un cambio, decide qué sigue e interactúa con apps de principio a fin, sin guía paso a paso.
- **Ejemplos:** "Automated Product Manager" (lee transcripciones → extrae action items → crea tareas en Jira → resume en Slack); "Freelance Pipeline" (vigila inbox → revisa calendario → redacta propuesta → guarda para revisión).

### ✅ The Collaborative Partner  ← **NUESTRO TRACK**
- **Enfoque:** diálogo **multi-turno con estado**, con **recuperación de contexto en tiempo real (RAG)** y **memoria persistente**, para que el agente **se adapte y personalice** con base en interacciones pasadas en vez de empezar de cero cada vez.
- **Ejemplos oficiales:**
  - Un guía experto que ayuda a entender un documento legal denso, te hace quizzes mientras avanzas, **aprende qué conceptos te cuestan** y adapta futuras explicaciones.
  - Un asistente UI/UX para no-diseñadores que convierte una idea vaga en un wireframe y **aprende las preferencias de marca a partir de tus correcciones**.

### The Fortified Enterprise Fleet
- **Enfoque:** descubrimiento corporativo de agentes, orquestación multi-agente a escala, persistencia a largo plazo, observabilidad en runtime y seguridad. Abierto a todos.
- **Tech recomendado (Gemini Enterprise Agent Platform / GEAP):** Agent Registry, Agent Runtime + Memory Bank, Agent Identity (zero-trust), Agent Gateway (routing + policy), Model Armor (guardrails), Agent Observability.
- **Ejemplo:** "Enterprise Supply Chain Orchestrator" para onboarding de proveedores multi-semana.

---

## 3. Nuestra decisión: The Collaborative Partner

Queremos construir para **The Collaborative Partner**. Lo que el track premia (y lo que la demo debe probar):

1. **Memoria persistente** — el agente recuerda **entre sesiones**, no solo dentro de un chat.
2. **RAG** — recupera contexto real desde documentos/datos externos.
3. **Personalización adaptativa** — aprende de las correcciones del usuario y **cambia su comportamiento** en sesiones posteriores.

> **El "wow" de la demo:** mostrar que la sesión 3 es distinta a la sesión 1 *porque el agente aprendió del usuario*.

### Diferenciador clave (no omitir)
El error típico en este track es hacer "un chatbot con RAG" y llamarlo memoria. Para destacar:
- **Separar explícitamente memoria de RAG.** RAG = conocimiento externo. Memoria = recordar *al usuario* (preferencias, errores, historial).
- **Mostrar la "reflexión":** al cerrar una sesión, el agente escribe/actualiza un **perfil del usuario** (p. ej. en Memory Bank o Firestore) — y en la demo se ve ese perfil actualizándose.
- **Probar la adaptación en vivo:** corregir al agente durante la demo y mostrar que ese cambio **persiste** en la siguiente sesión.

---

## 4. Ideas candidatas (ordenadas de más a menos "seguras de construir")

1. **Tutor adaptativo de un tema técnico** (ej. SQL, un framework, finanzas personales)
   - RAG sobre un temario/libro. Evalúa, **detecta puntos débiles** y ajusta dificultad + estilo de ejemplos.
   - Demo: la memoria guarda un "perfil de dominio" ("le cuestan los JOINs, prefiere ejemplos con deporte") y la siguiente sesión arranca reforzando eso.

2. **Compañero de lectura de documentos densos** (legal / contratos / pólizas / normativa)
   - Explica cláusula por cláusula, hace quizzes y **recuerda qué conceptos ya dominas** para no repetirlos.

3. **Coach de habilidades** (entrevistas, negociación, oratoria, escritura)
   - Simula escenarios, da feedback y **guarda tu progreso** para trabajar tus debilidades sesión a sesión. Fácil de mostrar "antes/después".

4. **Asistente de investigación personal ("second brain")**
   - Le das artículos/notas/links (RAG sobre *tu* corpus) y con el tiempo **aprende tus intereses y tu estilo de resumen**.

5. **Planificador personalizado** (comidas / fitness / finanzas)
   - Aprende restricciones y preferencias y **corrige el plan según tu feedback real** ("no me gustó el lunes → ajusta y recuérdalo"). Muy visual y relatable.

---

## 5. Stack técnico sugerido

- **Framework de agente:** Agent Development Kit (**ADK**) — `github.com/google/adk-python`.
- **Memoria persistente:** Vertex **Memory Bank** (memoria gestionada cross-session) o **Firestore** (NoSQL simple para estado/memoria) si se quiere algo más controlado.
- **RAG:** Vertex AI Search / RAG Engine, o un **vector store serverless** (evitar clusters siempre encendidos).
- **Modelos:** **Gemini Flash** por defecto; **Gemini Pro** solo para el razonamiento final complejo.
- **Deploy:** **Cloud Run** (scale-to-zero, URL pública) o Agent Engine.
- **On-ramp de aprendizaje:** **GEAR** (Gemini Enterprise Agent Ready) — gratis, 35 créditos mensuales de labs, training oficial de ADK. Empezar por el path "Introduction to Agents".

### Otras herramientas mencionadas
- Gemini API & Google AI Studio (modelos, quickstarts, multimodal).
- Antigravity SDK (runtime pre-empaquetado integrado con Gemini).
- Genkit (framework open-source para apps con IA — JS/Go/Python).

---

## 6. Pro tips de costos (del propio hackathon)

- **Gemini Flash primero**; reservar Pro solo para el razonamiento final complejo.
- **Scale to zero:** mínimo de instancias en 0 → no se cobra cuando está inactivo.
- **Empezar pequeño + caps de instancias:** RAM/CPU mínimos y techo máximo de copias para evitar picos.
- **Vector search serverless:** evitar clusters de base de datos siempre encendidos.
- **Storage liviano:** guardar solo estado esencial, comprimir memorias largas, limpiar artefactos temporales.
- **Budget alerts** activadas en Google Cloud Console.
- **Endpoints seguros:** proteger las URLs públicas de Cloud Run con API keys/auth.
- **Apagar tras la demo:** grabar la evidencia del agente corriendo en GCP y luego apagar/borrar recursos no usados.

---

## 7. Próximos pasos

- [ ] Elegir **una** de las ideas de la sección 4.
- [ ] Definir el **esquema de memoria** (qué se recuerda del usuario y cómo se actualiza).
- [ ] Definir el **flujo de RAG** (corpus, chunking, recuperación).
- [ ] Escribir el **guion de la demo** que prueba memoria + RAG + adaptación en vivo.
- [ ] Montar el esqueleto en **ADK** y desplegar en **Cloud Run**.
