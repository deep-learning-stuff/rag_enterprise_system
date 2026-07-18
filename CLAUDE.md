# CLAUDE.md — RAG interno

## Qué es esto

Sistema RAG interno para empresa. Los usuarios suben documentos y hacen preguntas; el sistema responde **únicamente** con lo que encuentra en esos documentos. Las preguntas que no se pueden responder se registran como "gaps", se agrupan en un panel y generan borradores para ampliar la base de conocimiento.

## Cómo trabajas conmigo (LEE ESTO PRIMERO)

- Antes de tocar código, explica en 2-3 frases qué vas a hacer y por qué, y espera mi OK. Nada de cambios grandes de golpe. Quiero un plan detallado
- Un cambio = una intención. Nada de refactors sorpresa mientras arreglas otra cosa.
- Si algo no está claro o hay más de una forma razonable de hacerlo, pregúntame en vez de asumir.
- Explícame las decisiones no obvias como si quisiera entender el sistema, no solo que funcione.
- Responde en español.

## Stack

- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy (Python)
- BD: PostgreSQL + pgvector
- Migraciones: Alembic
- Orquestación: Docker Compose
- Modelos (embeddings / rerank / LLM): ⚠️ POR DECIDIR (local vs API). No asumas ninguno todavía; pregúntame.

## Estructura del repo

<!-- ajusta esto a tu layout real -->

- `backend/` — FastAPI, lógica RAG, modelos SQLAlchemy, migraciones Alembic
- `frontend/` — React + Vite
- `docker-compose.yml` — Postgres (pgvector) + backend + frontend

## Comandos

<!-- completa con los reales cuando existan -->

- Levantar todo: `docker compose up`
- Backend (dev): `...`
- Tests backend: `...`
- Frontend (dev): `npm run dev` (dentro de `frontend/`)
- Nueva migración: `alembic revision --autogenerate -m "mensaje"`
- Aplicar migraciones: `alembic upgrade head`

## Reglas del RAG (INVARIANTES — no las rompas nunca)

- Nunca inventes ni respondas con conocimiento propio. Solo con los chunks recuperados.
- Si ningún chunk supera el umbral de relevancia, abstente ("no está en los documentos") y registra la consulta como gap. No fuerces una respuesta.
- Toda respuesta lleva citas a los documentos/chunks de origen. Sin cita válida, no se responde.
- Cada consulta se loguea: pregunta, chunks recuperados, scores y `answered` (bool).
- El detalle de chunking / embeddings / retrieval vive en la skill `rag-conventions`. Síguela; no improvises tu propia arquitectura.

## Convenciones de código

- Backend: type hints siempre, Pydantic para esquemas de entrada/salida, funciones cortas y con una responsabilidad.
- BD: cualquier cambio de esquema = modelo SQLAlchemy + migración Alembic. Nunca toques la BD a mano ni edites migraciones ya aplicadas.
- Frontend: <!-- rellena: estructura de componentes, gestión de estado, etc. -->

## Estilo / UI (IMPORTANTE)

No uses tus patrones visuales por defecto. Prohibido salvo que lo pida explícitamente:

- gradientes y morados/violetas de relleno
- emojis en la interfaz
- sombras exageradas y bordes muy redondeados
- "cards" genéricas y clases Tailwind sueltas sin sistema detrás

Usa los tokens y las reglas de la skill `design-system`. Si esa skill aún no existe, pregúntame antes de inventar estética.
