"""Almacenamiento de ficheros originales.

El resto de la app usa SOLO la interfaz `Storage` (guardar/abrir/borrar) sin saber
dónde viven los ficheros. Hoy es disco local; el día que se quiera MinIO/S3 se cambia
la implementación aquí sin tocar la lógica de ingesta.
"""
from app.config import settings
from app.storage.base import Storage
from app.storage.local import LocalStorage

# Instancia única que usa toda la app. Cambiar esta línea (no el resto del código)
# es lo único necesario para migrar a otro backend de almacenamiento.
storage: Storage = LocalStorage(settings.storage_dir)

__all__ = ["Storage", "storage"]
