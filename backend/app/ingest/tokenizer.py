"""Tokenizer de BGE-M3 para contar tokens al chunkear.

Se carga SOLO el tokenizer (no los pesos del modelo): es ligero y no necesita GPU.
La primera llamada descarga los ficheros del tokenizer desde HuggingFace y los cachea.
"""
from functools import lru_cache

from transformers import AutoTokenizer

from app.config import settings


@lru_cache(maxsize=1)
def _get_tokenizer():
    return AutoTokenizer.from_pretrained(settings.embedding_model_name)


def count_tokens(text: str) -> int:
    """Número de tokens de `text` tal y como los verá BGE-M3 (sin tokens especiales)."""
    return len(_get_tokenizer().encode(text, add_special_tokens=False))
