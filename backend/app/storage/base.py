from abc import ABC, abstractmethod
from typing import BinaryIO


class Storage(ABC):
    """Contrato de almacenamiento de ficheros.

    Una `ref` (referencia) es un identificador opaco que devuelve `save` y que sirve
    para recuperar o borrar el fichero después. Quien la usa NO debe asumir que es una
    ruta de disco: con MinIO/S3 sería otra cosa.
    """

    @abstractmethod
    def save(self, data: BinaryIO, *, filename: str) -> str:
        """Guarda el contenido de `data` y devuelve su `ref`."""

    @abstractmethod
    def open(self, ref: str) -> BinaryIO:
        """Abre el fichero identificado por `ref` para lectura en binario."""

    @abstractmethod
    def delete(self, ref: str) -> None:
        """Borra el fichero identificado por `ref`. No falla si ya no existe."""
