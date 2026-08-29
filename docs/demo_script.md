# Guion de demo

> Pendiente — completar una vez elegida la idea (ver `hackathon-agentic.md`, sección 4)
> y el esquema de memoria (`collaborative_partner/memory/schema.py`).

El objetivo del guion es probar, en vivo, las tres cosas que premia el track
*The Collaborative Partner* (ver `CLAUDE.md`):

1. **Sesión 1:** el agente interactúa con el usuario sin conocerlo. Usa RAG
   para responder sobre el corpus. Al cierre, escribe/actualiza el perfil
   de usuario (mostrar el documento de memoria cambiando en vivo).
2. **Corrección en vivo:** el usuario corrige algo explícito (una
   preferencia, un error del agente). Mostrar que `update_user_profile` se
   dispara y el perfil persiste.
3. **Sesión 2 (nueva sesión, mismo `user_id`):** el agente arranca ya
   adaptado — distinto tono/dificultad/ejemplos — **porque** leyó el perfil
   guardado en la sesión 1, no porque esté en el mismo historial de chat.

El "wow" es que la sesión 2 se vea distinta a la sesión 1 sin que el
usuario tenga que repetir nada.
