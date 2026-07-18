from abc import ABC, abstractmethod


class Reranker(ABC):
    """Contrato de reordenación por relevancia.

    A diferencia de la búsqueda (que compara vectores por separado), el reranker lee la
    pregunta y cada candidato JUNTOS y da una nota de cuán relevante es cada uno.
    """

    @abstractmethod
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        """Devuelve un score de relevancia por cada texto, en el MISMO orden de entrada."""
