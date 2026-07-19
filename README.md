# RAG interno

Sistema RAG interno para empresa. Los usuarios suben documentos y hacen preguntas; el
sistema responde **únicamente** con lo que encuentra en esos documentos.

> **Estado actual:** esqueleto del proyecto. Levanta la infraestructura (BD + backend +
> frontend) y verifica que se hablan entre sí. **Todavía no hay lógica de RAG**
> (embeddings, retrieval ni modelo de generación).

## Stack

- **Frontend:** React + Vite + TypeScript
- **Backend:** FastAPI + SQLAlchemy
- **Base de datos:** PostgreSQL + pgvector
- **Migraciones:** Alembic
- **Orquestación:** Docker Compose

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y **arrancado**
  (incluye `docker compose`).

Nada más: Python y Node se ejecutan dentro de los contenedores, no hace falta instalarlos
en tu máquina.

## Cómo levantarlo

Desde la raíz del proyecto:

```bash
docker compose up --build
```

La **primera vez** tarda un poco (construye las imágenes, instala dependencias de Python y
de Node). Las siguientes veces arranca en segundos.

Al terminar, tendrás tres servicios en marcha:

| Servicio     | URL                              | Qué es                                    |
| ------------ | -------------------------------- | ----------------------------------------- |
| **Frontend** | http://localhost:5173            | Pantalla de verificación del esqueleto    |
| **Backend**  | http://localhost:8000/health     | Endpoint de diagnóstico (`status` + `db`) |
| **API docs** | http://localhost:8000/docs       | Documentación interactiva (Swagger)       |

### Qué deberías ver

- En **http://localhost:5173**: una tarjeta "RAG interno" con **Backend: responde** y
  **Base de datos: ok**, ambas en verde. Eso confirma que frontend, backend y base de
  datos se comunican correctamente.
- En **http://localhost:8000/health**: `{"status":"ok","db":"ok"}`.

## Qué ocurre al arrancar

1. Se levanta **PostgreSQL** (imagen `pgvector/pgvector`) y se espera a que esté listo.
2. El **backend** aplica las migraciones (`alembic upgrade head`): habilita la extensión
   `pgvector` y crea la tabla de ejemplo `documents`. Después arranca la API.
3. El **frontend** arranca Vite, que reenvía las peticiones `/health` al backend por la red
   interna de Docker.

## Comandos útiles

```bash
# Levantar (reconstruyendo imágenes si cambió el Dockerfile o las dependencias)
docker compose up --build

# Levantar en segundo plano
docker compose up -d

# Ver logs (todos o de un servicio)
docker compose logs -f
docker compose logs -f backend

# Parar los servicios
docker compose down

# Parar y BORRAR también los datos de la base de datos (empezar de cero)
docker compose down -v
```

El código de `backend/` y `frontend/` está montado como volumen: al editarlo, los
servicios recargan en caliente (uvicorn `--reload` y Vite HMR). No hace falta reconstruir
para cambios de código; solo si cambias dependencias o los `Dockerfile`.

## Configuración

Los valores por defecto (usuario/contraseña de la BD, puertos) funcionan tal cual. Si
quieres cambiarlos, copia `.env.example` a `.env` y edítalo:

```bash
cp .env.example .env
```

Docker Compose lee `.env` automáticamente.

## Modelos de IA (embeddings y reranker)

Todo corre **en local**, sin llamar a APIs externas (privacidad). Dos modelos, servidos
cada uno por su contenedor de [TEI](https://github.com/huggingface/text-embeddings-inference):

- **Embeddings** (`embeddings`): `BAAI/bge-m3` — convierte cada chunk y cada pregunta en un
  vector para la búsqueda por significado.
- **Reranker** (`reranker`): reordena los candidatos recuperados por relevancia real y da la
  nota con la que se decide la abstención ("no está en los documentos").

### Cambiar el modelo del reranker

Por defecto se usa un reranker **ligero** (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`,
~0.5 GB) que arranca en cualquier equipo, **incluso con poca RAM**. En una máquina con más
memoria (o con GPU) puedes usar el **grande**, más preciso, sin tocar código: solo cambia
una variable en tu `.env`:

```bash
# .env
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

Luego recrea el servicio:

```bash
docker compose up -d --force-recreate reranker
```

> **Aviso de memoria:** el modelo grande necesita ~2.5 GB extra en Docker. Junto a los
> embeddings no cabe en un Docker de ~8 GB (equipos de 16 GB de RAM): el contenedor se cae
> por falta de memoria. Úsalo en equipos de 32 GB+ o con GPU. Puedes comprobar cuánta
> memoria tiene tu Docker con `docker info --format '{{.MemTotal}}'`.

El código no sabe qué modelo hay detrás (habla con el reranker por HTTP tras una
abstracción): cambiar de modelo es solo cambiar qué sirve el contenedor.

### Reranker ligero y longitud: rerank por ventanas

El reranker ligero solo procesa **512 tokens** por texto, pero los chunks son de ~700.
Para no perder la cola de los chunks largos, el cliente **trocea cada chunk en ventanas**
que caben en ese límite (`RERANKER_WINDOW_TOKENS`, ~450 por defecto), puntúa todas y se
queda con el **máximo**. Así el reranker "lee" el chunk entero, esté donde esté la parte
relevante. `truncate: true` se mantiene solo como red de seguridad.

Por qué importa: sin esto, una pregunta cuya respuesta cae al final de un chunk largo se
infravaloraba (el reranker no la veía) y el sistema se abstenía por error. Con las ventanas,
la relevancia se calcula sobre todo el texto.

Notas:

- **Solo afecta al paso de rerank.** El embedding (BGE-M3) ya procesaba el chunk entero
  (hasta 8192 tokens); la búsqueda vectorial nunca perdió nada.
- Con el **modelo grande** (`bge-reranker-v2-m3`, 8192 tokens) cada chunk cabe en una sola
  ventana: sube `RERANKER_WINDOW_TOKENS` por env (p.ej. 7000) y no se trocea.

### Abstención (cuándo responde y cuándo dice "no está en los documentos")

Tras el rerank por ventanas, la relevancia separa muy bien lo que está en los documentos de
lo que no (relevante ≥ ~0.8, ruido ≤ ~0.05). Por eso la abstención usa **un único umbral**
sobre el score del reranker (`RELEVANCE_THRESHOLD`, 0.5): por debajo → no se responde y la
consulta se registrará como *gap*. Es robusto al crecer la base de documentos, porque el
reranker juzga la relevancia real de cada par pregunta-chunk, no depende de cuántos haya.
El coseno se sigue mostrando en la respuesta como traza de depuración, pero **no** decide la
abstención (su margen entre relevante y ruido es demasiado estrecho para ser fiable).

## Estructura del proyecto

```
rag_para_empresa/
├── docker-compose.yml       # Postgres (pgvector) + backend + frontend
├── .env.example             # Variables de entorno (credenciales, puertos)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── entrypoint.sh        # Corre migraciones y arranca la API
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py          # FastAPI + endpoint /health
│   │   ├── config.py        # Configuración (DATABASE_URL)
│   │   ├── db.py            # Engine, sesión y Base de SQLAlchemy
│   │   └── models/          # Modelos SQLAlchemy (documents de ejemplo)
│   └── migrations/          # Migraciones Alembic
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts       # Proxy /health -> backend
    └── src/                 # App.tsx (pantalla de verificación) + estilos
```

## Solución de problemas

- **`failed to connect to the docker API` / `daemon is not running`**: abre Docker Desktop
  y espera a que esté en marcha antes de ejecutar `docker compose up`.
- **Un puerto está ocupado** (5173, 8000 o 5432): cambia el puerto correspondiente en tu
  `.env` (`FRONTEND_PORT`, `BACKEND_PORT`, `DB_PORT`).
- **Cambios raros en la base de datos**: `docker compose down -v` borra el volumen de datos
  y arranca limpio en el siguiente `up`.
