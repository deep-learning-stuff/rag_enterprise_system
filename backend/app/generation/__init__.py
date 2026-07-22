"""Generación grounded (Fase 5).

El servicio de respuestas usa la instancia `generator` (interfaz `Generator`) sin
acoplarse al proveedor. El proveedor y el modelo se eligen por .env (LLM_PROVIDER,
LLM_MODEL), igual que el reranker con RERANKER_MODEL: cambiar de proveedor es
cambiar una variable, no tocar código.
"""
from app.config import settings
from app.generation.base import ContextChunk, GenerationError, GenerationResult, Generator
from app.generation.gemini import GeminiGenerator
from app.generation.openai import OpenAIGenerator

# Modelo por defecto de cada proveedor si LLM_MODEL viene vacío.
_DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-5-mini",
}


def _build_generator() -> Generator:
    provider = settings.llm_provider
    if provider not in _DEFAULT_MODELS:
        raise ValueError(
            f"LLM_PROVIDER desconocido: {provider!r} (válidos: {sorted(_DEFAULT_MODELS)})"
        )
    model = settings.llm_model or _DEFAULT_MODELS[provider]
    if provider == "openai":
        return OpenAIGenerator(
            model=model, api_key=settings.openai_api_key, timeout=settings.llm_timeout
        )
    return GeminiGenerator(
        model=model, api_key=settings.gemini_api_key, timeout=settings.llm_timeout
    )


generator: Generator = _build_generator()

__all__ = [
    "ContextChunk",
    "GenerationError",
    "GenerationResult",
    "Generator",
    "generator",
]
