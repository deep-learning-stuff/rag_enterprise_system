import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.storage.base import Storage


class LocalStorage(Storage):
    """Implementación en disco local. La `ref` es el nombre del fichero dentro de `base_dir`.

    Se antepone un UUID al nombre original para evitar colisiones si dos usuarios suben
    ficheros con el mismo nombre.
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: BinaryIO, *, filename: str) -> str:
        ref = f"{uuid.uuid4().hex}_{filename}"
        with open(self.base_dir / ref, "wb") as f:
            shutil.copyfileobj(data, f)
        return ref

    def open(self, ref: str) -> BinaryIO:
        return open(self._path(ref), "rb")

    def delete(self, ref: str) -> None:
        self._path(ref).unlink(missing_ok=True)

    def _path(self, ref: str) -> Path:
        # Evita que una `ref` maliciosa (p.ej. "../..") escape de base_dir.
        path = (self.base_dir / ref).resolve()
        if self.base_dir.resolve() not in path.parents:
            raise ValueError(f"ref inválida: {ref!r}")
        return path
