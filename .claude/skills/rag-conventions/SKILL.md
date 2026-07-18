---
name: rag-conventions
description: Cómo se construye el RAG de este proyecto (ingesta, chunking, embeddings, recuperación híbrida, generación grounded y lógica de gaps). Úsala SIEMPRE que trabajes en subida/parseo de documentos, chunking, embeddings, búsqueda/retrieval, el prompt de respuesta, el logging de consultas o el panel de gaps — aunque no se nombre "RAG" explícitamente. No improvises una arquitectura distinta a la de aquí.
---

# Convenciones del RAG

Este documento describe CÓMO está montado el pipeline. Las reglas de comportamiento (grounded-only, abstención, citas) están en `CLAUDE.md` y son invariantes; aquí está la implementación.

## Decisiones tomadas

- **Embeddings**: en local. Punto de partida BGE-M3 (multilingüe es/ca, denso + disperso).
- **Reranker**: en local (bge-reranker-v2-m3).
- **Generación (LLM)**: ⚠️ SIN DEFINIR TODAVÍA. La dirección es local (Ollama para desarrollo, vLLM para producción) y no usar API por defecto por privacidad, pero el modelo concreto aún no está decidido. No asumas ninguno; pregunta antes de fijarlo.
- **API como plan B**: solo si en el futuro se permite que ciertos docs salgan. En ese caso, prompt caching sobre el prefijo fijo del prompt y Batch API para el trabajo offline (borradores de gaps, etc.).

## Pipeline de ingesta

Orden fijo: `subir → parsear → chunkear → embeber → guardar`.

- **Parseo**: un parser por tipo de archivo. Conserva estructura (página, sección, encabezados) — hace falta para las citas.
- **Chunking**: recursivo con solape. Punto de partida ~500-800 tokens por chunk, ~10-15% de solape. Ajustable, pero sin romper frases a la mitad.
- **Metadata por chunk** (obligatoria): `doc_id`, `source_name`, `page`, `section`, `chunk_index`. Sin esto no hay citas.
- **Embeddings**: BGE-M3 en local (ver decisiones).

## Esquema de datos (Postgres + pgvector)

- `documents`: id, nombre, tipo, fecha de subida, estado.
- `chunks`: id, doc_id, texto, `embedding` (vector), `tsv` (tsvector para full-text), + metadata de arriba.
- `queries`: id, texto, timestamp, usuario, `answered` (bool), chunks recuperados + scores (para auditar).
- `gaps`: id, query_id, texto, `embedding`, `cluster_id` (nullable).
- `gap_clusters`: id, etiqueta, frecuencia, borrador propuesto, estado (pendiente/aprobado/descartado).

Todo cambio de esquema pasa por modelo SQLAlchemy + migración Alembic.

## Recuperación (híbrida)

1. Búsqueda vectorial: top-K por similitud coseno con pgvector (K ~20-40).
2. Full-text: top-K con tsvector (configs `spanish` y `catalan`).
3. Fusión: Reciprocal Rank Fusion (RRF) de las dos listas.
4. Rerank: bge-reranker-v2-m3 local sobre el top fusionado → top-N final (N ~5-8).
5. **Umbral**: si el mejor score tras rerank < UMBRAL → abstención + gap. No respondas por debajo del umbral.

## Generación (grounded)

- El LLM recibe SOLO los chunks del top-N como contexto. Nada de conocimiento externo.
- Contrato de salida (JSON estructurado):
  ```
  { "answered": bool, "answer": string | null, "citations": [chunk_id, ...] }
  ```
- Valida que cada `citation` apunte a un chunk que sí estaba en el contexto. Cita inválida → trátalo como no respondido.
- `answered=false` → abstención + gap. Nunca rellenes con suposiciones.

## Lógica de gaps

- Se crea un gap cuando `answered=false` O el mejor score < umbral.
- Guarda la consulta con su embedding, chunks recuperados y scores.
- **Clustering**: se embeben las preguntas-gap y se agrupan las parecidas (p.ej. HDBSCAN o umbral de coseno) → `cluster_id`.
- El panel lista `gap_clusters` por frecuencia. Por cada cluster se redacta un borrador (trabajo offline → batchable si se usa API); un humano lo revisa y, si lo aprueba, se ingesta como documento nuevo (vuelve al pipeline de ingesta).

## Serving local

- Ollama para arrancar rápido; vLLM para producción (mayor throughput con continuous batching y reutilización de prefijo/KV cache).
- Una misma GPU puede servir embeddings + reranker + LLM.

## Al implementar

- Explica el cambio antes de tocar (ver CLAUDE.md).
- No mezcles pasos del pipeline en una misma función; mantenlos separados y testeables.
- Cualquier número de arriba (K, N, tamaño de chunk, umbral) es un valor de arranque, no dogma: déjalo configurable.
