from abc import ABC, abstractmethod


class Embedder(ABC):
    """Contrato de generación de embeddings.

    El pipeline usa SOLO esta interfaz, sin saber si por detrás hay un servicio HTTP,
    el modelo en proceso o una API. Cambiar la implementación no toca la lógica de ingesta.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Devuelve un vector por cada texto de entrada, en el mismo orden."""
