"""Contrato de generación grounded (Fase 5).

El generador recibe la pregunta y los chunks recuperados, y devuelve el contrato
de la skill rag-conventions: `{"answered": bool, "answer": str|null, "citations": [...]}`.
La validación de que las citas apuntan a chunks reales del contexto NO vive aquí:
es responsabilidad del servicio que orquesta (services/answers.py), porque es un
invariante del sistema, no del proveedor.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


class GenerationError(Exception):
    """El proveedor no es utilizable (p.ej. falta la API key). No es culpa del modelo."""


@dataclass
class ContextChunk:
    """Un chunk tal y como se le presenta al LLM: su id (para citar) y su texto."""

    chunk_id: int
    texto: str


@dataclass
class Turno:
    """Un turno del historial de chat (Fase C), para contextualizar un seguimiento."""

    rol: str  # "usuario" | "asistente"
    texto: str


@dataclass
class GenerationResult:
    """Salida estructurada del LLM, aún SIN validar contra el contexto."""

    answered: bool
    answer: str | None
    citations: list[int]


def parse_result(text: str) -> GenerationResult:
    """Parsea y tipa el JSON que devuelve el modelo.

    Lanza ValueError si el texto no es JSON válido o no cumple el contrato; quien
    llama lo trata como "no respondido" (nunca se fuerza una respuesta).
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"la salida del modelo no es JSON: {text[:200]!r}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("answered"), bool):
        raise ValueError(f"contrato incumplido (falta 'answered' bool): {text[:200]!r}")

    answer = data.get("answer")
    if answer is not None and not isinstance(answer, str):
        raise ValueError("contrato incumplido: 'answer' debe ser string o null")

    raw_citations = data.get("citations", [])
    if not isinstance(raw_citations, list):
        raise ValueError("contrato incumplido: 'citations' debe ser una lista")
    try:
        citations = [int(c) for c in raw_citations]
    except (TypeError, ValueError) as exc:
        raise ValueError("contrato incumplido: cada cita debe ser un chunk_id entero") from exc

    return GenerationResult(answered=data["answered"], answer=answer, citations=citations)


class Generator(ABC):
    """Contrato de generación. El resto del sistema no sabe qué proveedor hay detrás."""

    @abstractmethod
    def generate(self, query: str, chunks: list[ContextChunk]) -> GenerationResult:
        """Genera la respuesta grounded a partir de la pregunta y los chunks dados."""

    @abstractmethod
    def generate_draft(self, pregunta: str, preguntas_relacionadas: list[str]) -> str:
        """Genera el ESQUELETO Markdown de un documento que cubriría un gap.

        No responde la pregunta ni inventa hechos: estructura el documento con
        marcadores para que un humano lo complete (ver app.generation.draft).
        """

    @abstractmethod
    def reescribir_consulta(self, mensaje: str, historial: list[Turno]) -> str:
        """Reescribe un seguimiento como pregunta AUTÓNOMA usando el historial reciente.

        No responde ni recupera nada: solo resuelve las referencias al contexto ("eso",
        "y en 2023"...) para dejar una consulta que se entienda por sí sola (Fase C). Si
        ya era autónoma, devuelve el mensaje tal cual.
        """
