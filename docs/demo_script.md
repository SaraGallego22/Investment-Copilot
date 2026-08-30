# Demo video script — JUSARA

> **Hard limit: 4 minutes.** The rules say only the first four minutes may be
> evaluated. This script runs to **3:30**, leaving room to breathe.
>
> **Must appear on screen:** the backend running on Google Cloud (Cloud Run
> console, Firestore console, or a `.run.app` URL). This is a scored
> requirement, not a nicety — see `rules.md` §8, *Demo & Production Readiness*.
>
> Narrate in Spanish, add English subtitles. Both are permitted.

---

## Before you press record

A cold `min-instances=0` container fails the first request. Wake both services
and confirm the state is clean:

```bash
curl https://jusara-market-api-904662129922.us-central1.run.app/health
curl https://jusara-agent-904662129922.us-central1.run.app/api/health
python cli.py check                      # all five checks must pass
python scripts/seed_memory.py --backend firestore --force   # reset the personas
git status --short                       # working tree clean, so the diff is legible
```

Open these tabs in advance: the web UI, `data/memory/ana.json` in the editor,
and the Firestore console at collection `user_profiles`.

---

## 0:00 – 0:30 · The problem

> Cada bróker te hace rellenar un cuestionario de riesgo. Marcas "moderado" y
> esa etiqueta guía tus consejos durante años.
>
> Pero es una autoevaluación hecha una vez, en calma, por alguien imaginando
> cómo se sentiría al perder dinero. Luego el mercado cae un 20% y esa misma
> persona intenta venderlo todo.
>
> Morningstar lo mide: entre 2015 y 2024 los fondos rindieron 8,2% anual y sus
> inversores solo 7,0%. Ese 1,2% se destruyó por *cuándo* la gente compró y
> vendió. El perfil declarado no es el real, y nadie mide la diferencia.

**On screen:** the README problem section, or a title card with 8,2% vs 7,0%.

---

## 0:30 – 1:00 · The three systems

> JUSARA mantiene tres sistemas separados y auditables.

**On screen:** the architecture diagram, then the running UI.

> **Memoria**: lo que sabemos de esta persona, en dos capas — lo que declara y
> lo que su conducta demuestra.
> **RAG**: teoría de inversión de la SEC y de la CNMV española. Descargada de
> sus fuentes, no escrita por nosotros.
> **Market API**: un simulador determinista, en su propio servicio de Cloud Run.
>
> No son tres nombres para lo mismo. Se ven por separado en pantalla.

---

## 1:00 – 1:30 · The two profiles

**On screen:** click **ana**, then **beto** in the left panel. The right panel
fills with each profile.

> Ana se declara **moderada**, horizonte de 10 años. Pero su capa observada dice
> otra cosa: en la sesión 2 pidió vender con una caída del 5%; en la 4 quería
> pasar todo a efectivo. Confianza 0,7.
>
> Beto se declara **agresivo**. Y en las subidas lo es. Pero en la sesión 3, con
> una caída leve, escribió tres veces pidiendo explicaciones.
>
> Perfiles declarados opuestos. Los dos se contradicen a sí mismos.

---

## 1:30 – 2:45 · The crash, side by side  ← **the climax**

**On screen:** scenario `crash`, day 60. Same market for both.

> Mismo mercado. El índice cae un 40%, TECHX un 55%.

Ask as **Ana**: *"quiero vender todo ahora"*

> Fíjate en las etiquetas: memoria, mercado, RAG. Los tres sistemas trabajando.

**Point at the answer.** Key beats:

> Le nombra su patrón con las sesiones 2 y 4. Cita a Odean y a la SEC. Y le dice
> algo incómodo: en este escenario, vender hoy habría sido mejor. No lo esconde
> para reforzar su consejo.

Switch to **Beto**, ask: *"TECHX está baratísimo, quiero meter todo ahí"*

> Mismo mercado, mismo día. Consejo opuesto.
>
> Y el dato que lo hace honesto: la investigación de Vanguard dice que invertir
> de golpe gana al escalonamiento dos de cada tres veces. Dosificar **no**
> maximiza su rentabilidad. Reduce la probabilidad de que abandone el plan — que
> en su caso ya pasó.

---

## 2:45 – 3:10 · It learns, and it is on Google Cloud

**On screen:** the right panel — the changed pattern is highlighted.

> Al cerrar la sesión el agente reflexiona y reescribe el perfil. La confianza
> subió de 0,7 a 0,8, con la evidencia de hoy.

**Cut to the Firestore console.** Refresh the `ana` document.

> Y esto no es un archivo local: es Firestore. Dos servicios en Cloud Run, el
> agente y el simulador, y la memoria persistida en Google Cloud.

**Cut to the Cloud Run console** showing both services green.

---

## 3:10 – 3:30 · Close

> Memoria que aprende a esta persona. RAG que fundamenta el consejo en fuentes
> reales y citadas. Un simulador que nos deja someter al agente a cualquier
> mercado.
>
> JUSARA no ejecuta operaciones. Aconseja, y sobre todo te devuelve tu propio
> patrón antes de que actúes en contra de ti mismo.
>
> Proyecto educativo, datos simulados, no es asesoramiento financiero regulado.

---

## Golden rules

- **The simulator is deterministic.** Same seed, same prices, every run. Nothing
  can surprise you live.
- **Seeded history plus one live update is honest.** A system with cross-session
  memory cannot be demonstrated from zero in four minutes. Show the prior
  sessions as seed data, then let the jury watch a single real update.
- **Never say "buy" or "sell".** The agent does not, and neither should the
  narration.
- **Say the data is simulated**, at least once, clearly.
- If a take goes wrong, re-run `seed_memory.py --force` before the next one, or
  the confidence numbers will drift between shots.

## Fallback if the UI misbehaves

`python cli.py demo --scenario crash` runs the whole Ana-vs-Beto comparison in
the terminal with `[memory]`, `[rag]` and `[market]` labels on every call. The
rules accept terminal logs as Proof of Action, so the demo survives a broken
front end.
