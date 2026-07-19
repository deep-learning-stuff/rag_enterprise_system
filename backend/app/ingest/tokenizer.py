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


def split_into_windows(text: str, max_tokens: int, overlap: int = 40) -> list[str]:
    """Parte `text` en ventanas de <= `max_tokens` tokens, con un pequeño solape.

    Se usa para el rerank: el reranker ligero solo "ve" ~512 tokens, así que un chunk
    de ~700 hay que trocearlo para que ninguna parte quede fuera de su puntuación. El
    solape evita cortar justo por una frase clave en el borde entre ventanas.

    BGE-M3 y los rerankers XLM-RoBERTa comparten el mismo tokenizer sentencepiece, así
    que este conteo aproxima bien el del reranker (y `truncate` en el cliente es la red
    de seguridad si alguna ventana se pasase).
    """
    tok = _get_tokenizer()
    ids = tok.encode(text, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return [text]

    step = max(1, max_tokens - overlap)
    windows: list[str] = []
    for start in range(0, len(ids), step):
        windows.append(tok.decode(ids[start : start + max_tokens]))
        if start + max_tokens >= len(ids):
            break
    return windows
