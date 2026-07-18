"""Chunking: texto por página -> trozos con solape, sin partir frases.

Estrategia (punto de arranque de la skill rag-conventions):
- Se trocea a lo largo de TODO el documento, no página a página: el contenido que
  cruza un salto de página no se parte (pensado para manuales/prosa continua).
- Cada frase recuerda de qué página viene; un chunk guarda el rango `page_start`..
  `page_end` que abarca, para poder citarlo aunque cruce páginas.
- Se empaquetan frases hasta ~`chunk_target_tokens`; al cerrar un chunk se arrastran
  las últimas frases (~`chunk_overlap_tokens`) al siguiente, para no perder contexto
  en los bordes (el solape también cruza páginas).
- Nunca se corta una frase a la mitad.
"""
import re
from dataclasses import dataclass

from app.config import settings
from app.ingest.parser import Page
from app.ingest.tokenizer import count_tokens

# Corta tras . ! ? … o en saltos de línea. Punto de arranque; se puede afinar.
_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


@dataclass
class ChunkData:
    texto: str
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int


@dataclass
class _Sentence:
    """Una frase junto con la página de la que proviene."""

    page: int
    text: str


def chunk(pages: list[Page]) -> list[ChunkData]:
    sentences = _sentences_with_pages(pages)
    return _pack(sentences, settings.chunk_target_tokens, settings.chunk_overlap_tokens)


def _sentences_with_pages(pages: list[Page]) -> list[_Sentence]:
    """Aplana el documento a una lista de frases, cada una etiquetada con su página."""
    out: list[_Sentence] = []
    for page in pages:
        for text in _split_sentences(page.text):
            out.append(_Sentence(page=page.number, text=text))
    return out


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _pack(sentences: list[_Sentence], target: int, overlap: int) -> list[ChunkData]:
    chunks: list[ChunkData] = []
    current: list[_Sentence] = []
    current_tokens = 0
    idx = 0

    for sent in sentences:
        sent_tokens = count_tokens(sent.text)
        # Si añadir esta frase se pasa del objetivo y ya hay contenido, cierra el chunk.
        if current and current_tokens + sent_tokens > target:
            chunks.append(_make_chunk(current, idx))
            idx += 1
            current, current_tokens = _overlap_tail(current, overlap)
        current.append(sent)
        current_tokens += sent_tokens

    if current:
        chunks.append(_make_chunk(current, idx))
    return chunks


def _make_chunk(sentences: list[_Sentence], idx: int) -> ChunkData:
    return ChunkData(
        texto=" ".join(s.text for s in sentences),
        page_start=sentences[0].page,
        page_end=sentences[-1].page,
        section=None,
        chunk_index=idx,
    )


def _overlap_tail(
    sentences: list[_Sentence], overlap: int
) -> tuple[list[_Sentence], int]:
    """Devuelve las últimas frases que suman ~`overlap` tokens, para arrastrarlas."""
    tail: list[_Sentence] = []
    tokens = 0
    for sent in reversed(sentences):
        sent_tokens = count_tokens(sent.text)
        if tail and tokens + sent_tokens > overlap:
            break
        tail.insert(0, sent)
        tokens += sent_tokens
    return tail, tokens
