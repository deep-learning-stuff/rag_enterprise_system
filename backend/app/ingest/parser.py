"""Parseo de documentos: fichero -> texto por página.

Un parser por tipo. Conservamos el número de página porque hace falta para las citas
(regla del RAG: sin metadata de origen no hay cita válida).
"""
from dataclasses import dataclass
from typing import BinaryIO

from pypdf import PdfReader


@dataclass
class Page:
    """Un fragmento de texto con su página de origen."""

    number: int
    text: str


def parse(stream: BinaryIO, tipo: str) -> list[Page]:
    """Extrae el texto del fichero, agrupado por página."""
    if tipo == "pdf":
        return _parse_pdf(stream)
    if tipo in {"txt", "md", "markdown", "text"}:
        return _parse_text(stream)
    raise ValueError(f"Tipo de archivo no soportado para parseo: {tipo!r}")


def _parse_pdf(stream: BinaryIO) -> list[Page]:
    reader = PdfReader(stream)
    pages: list[Page] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:  # se ignoran páginas vacías (p.ej. solo imágenes)
            pages.append(Page(number=i, text=text))
    return pages


def _parse_text(stream: BinaryIO) -> list[Page]:
    text = stream.read().decode("utf-8", errors="replace").strip()
    # Un fichero de texto plano no tiene páginas: lo tratamos como página 1.
    return [Page(number=1, text=text)] if text else []
