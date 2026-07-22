"""Adaptador de generación para la API de Gemini (Google AI Studio).

Elegido como default de desarrollo por su capa gratuita (ver README: no válida para
uso comercial en la UE — al pasar a producción se cambia de proveedor por .env).

Se llama por REST con httpx (sin SDK), igual que el resto de clientes del proyecto.
La salida JSON se fuerza con `responseMimeType` + `responseSchema` de la API.
"""

import httpx

from app.generation.base import (
    ContextChunk,
    GenerationError,
    GenerationResult,
    Generator,
    parse_result,
)
from app.generation.prompt import SYSTEM_PROMPT, build_user_prompt

# Esquema OpenAPI (subset de Gemini) que replica el contrato de base.parse_result.
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answered": {"type": "BOOLEAN"},
        "answer": {"type": "STRING", "nullable": True},
        "citations": {"type": "ARRAY", "items": {"type": "INTEGER"}},
    },
    "required": ["answered", "answer", "citations"],
}


class GeminiGenerator(Generator):
    def __init__(self, *, model: str, api_key: str, timeout: float = 60.0):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, query: str, chunks: list[ContextChunk]) -> GenerationResult:
        if not self.api_key:
            raise GenerationError("GEMINI_API_KEY no configurada (ver .env.example)")

        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [
                    {"role": "user", "parts": [{"text": build_user_prompt(query, chunks)}]}
                ],
                "generationConfig": {
                    # Extracción, no creatividad: lo más determinista posible.
                    "temperature": 0,
                    "responseMimeType": "application/json",
                    "responseSchema": _RESPONSE_SCHEMA,
                },
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Si Gemini bloquea la respuesta (safety) no hay `parts`; se trata como salida
        # inválida (ValueError) y el servicio lo convertirá en abstención.
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"respuesta de Gemini sin contenido: {data!r}") from exc
        return parse_result(text)
