"""Adaptador de generación para la API de OpenAI (chat completions).

Alternativa de pago sin restricciones de uso comercial en la UE. Se activa con
LLM_PROVIDER=openai en el .env; el resto del sistema no cambia.

La salida JSON se fuerza con `response_format: json_schema` en modo estricto.
"""

import httpx

from app.generation.base import (
    ContextChunk,
    GenerationError,
    GenerationResult,
    Generator,
    Turno,
    parse_result,
)
from app.generation.contextualize import (
    CONTEXTUALIZE_SYSTEM_PROMPT,
    build_contextualize_prompt,
)
from app.generation.draft import DRAFT_SYSTEM_PROMPT, build_draft_prompt
from app.generation.prompt import SYSTEM_PROMPT, build_user_prompt

# JSON Schema estricto que replica el contrato de base.parse_result.
_RESPONSE_SCHEMA = {
    "name": "grounded_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answered": {"type": "boolean"},
            "answer": {"type": ["string", "null"]},
            "citations": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["answered", "answer", "citations"],
        "additionalProperties": False,
    },
}


class OpenAIGenerator(Generator):
    def __init__(self, *, model: str, api_key: str, timeout: float = 60.0):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, query: str, chunks: list[ContextChunk]) -> GenerationResult:
        if not self.api_key:
            raise GenerationError("OPENAI_API_KEY no configurada (ver .env.example)")

        # Sin `temperature`: los modelos de razonamiento (gpt-5-*) la rechazan si no
        # es la de defecto, y el JSON schema estricto ya acota la salida.
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(query, chunks)},
                ],
                "response_format": {"type": "json_schema", "json_schema": _RESPONSE_SCHEMA},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"respuesta de OpenAI sin contenido: {data!r}") from exc
        if text is None:
            # `content` llega null si el modelo rehúsa (campo `refusal`).
            raise ValueError(f"OpenAI no devolvió contenido: {data!r}")
        return parse_result(text)

    def generate_draft(self, pregunta: str, preguntas_relacionadas: list[str]) -> str:
        if not self.api_key:
            raise GenerationError("OPENAI_API_KEY no configurada (ver .env.example)")

        # Salida en texto plano (Markdown): sin response_format, a diferencia de la
        # respuesta grounded que fuerza JSON.
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_draft_prompt(pregunta, preguntas_relacionadas),
                    },
                ],
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"respuesta de OpenAI sin contenido: {data!r}") from exc
        if text is None:
            raise ValueError(f"OpenAI no devolvió contenido: {data!r}")
        return text

    def reescribir_consulta(self, mensaje: str, historial: list[Turno]) -> str:
        if not self.api_key:
            raise GenerationError("OPENAI_API_KEY no configurada (ver .env.example)")

        # Texto plano (la pregunta reescrita), sin response_format.
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": CONTEXTUALIZE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_contextualize_prompt(mensaje, historial),
                    },
                ],
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"respuesta de OpenAI sin contenido: {data!r}") from exc
        # Si el modelo devuelve vacío, se cae al mensaje original (no reescribir es seguro).
        return text.strip() if text else mensaje
