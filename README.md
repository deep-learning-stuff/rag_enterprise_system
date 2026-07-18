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
