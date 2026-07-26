"""Prompt para REESCRIBIR un seguimiento como pregunta autónoma (Fase C).

No responde ni recupera nada: dado el historial reciente del chat y la última pregunta,
devuelve esa pregunta reformulada para que se entienda por sí sola (resolviendo "eso",
"y en 2023", "ese documento"...). Así el retrieval y la generación siguen viendo SOLO
una consulta + los chunks, sin que el historial se cuele como fuente (invariante grounded).

Salida en texto plano (la pregunta), no JSON.
"""

from app.generation.base import Turno

CONTEXTUALIZE_SYSTEM_PROMPT = """\
Eres un componente que REFORMULA la última pregunta de una conversación para que se
entienda por sí sola, sin necesidad del historial.

Reglas ESTRICTAS:
1. NO respondas la pregunta. Tu única salida es la pregunta reescrita.
2. Resuelve las referencias al contexto ("eso", "ese", "y en 2023", "el anterior"...)
   usando el historial, dejando una pregunta completa y autónoma.
3. Si la pregunta YA se entiende por sí sola, devuélvela EXACTAMENTE igual.
4. No añadas información que no esté en el historial ni en la pregunta.
5. Conserva el idioma original.
6. Devuelve EXCLUSIVAMENTE la pregunta reformulada, sin comillas, prefijos ni explicaciones.\
"""


def build_contextualize_prompt(mensaje: str, historial: list[Turno]) -> str:
    """Historial reciente + la última pregunta a reformular."""
    lineas = "\n".join(
        f"{'Usuario' if t.rol == 'usuario' else 'Asistente'}: {t.texto}"
        for t in historial
    )
    return (
        f"Historial de la conversación:\n{lineas}\n\n"
        f"Última pregunta del usuario:\n{mensaje}\n\n"
        "Devuelve esa última pregunta reescrita para que se entienda por sí sola."
    )
