"""Prompt grounded-only, compartido por todos los proveedores.

El prompt es idéntico venga el modelo de donde venga: cambiar de proveedor no debe
cambiar el comportamiento del sistema. Lo único específico de cada adaptador es CÓMO
se fuerza la salida JSON (cada API tiene su mecanismo de salida estructurada).
"""

from app.generation.base import ContextChunk

SYSTEM_PROMPT = """\
Eres el motor de respuesta de un sistema RAG interno de empresa. Reglas ESTRICTAS:

1. Responde ÚNICAMENTE con la información contenida en los fragmentos proporcionados.
   Tienes PROHIBIDO usar conocimiento propio o completar con suposiciones.
2. Si los fragmentos no contienen la información para responder la pregunta, devuelve
   answered=false y answer=null. Abstenerse es la respuesta correcta en ese caso.
3. Si respondes, cita los fragmentos en los que te basas: incluye su chunk_id en
   "citations". Una respuesta sin citas no es válida.
4. Responde en el mismo idioma en el que está formulada la pregunta.

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta:
{"answered": <bool>, "answer": <string o null>, "citations": [<chunk_id>, ...]}\
"""


def build_user_prompt(query: str, chunks: list[ContextChunk]) -> str:
    """Pregunta + fragmentos numerados por chunk_id (el id que el modelo debe citar)."""
    fragmentos = "\n\n".join(
        f"[chunk_id={c.chunk_id}]\n{c.texto}" for c in chunks
    )
    return f"Pregunta: {query}\n\nFragmentos:\n\n{fragmentos}"
