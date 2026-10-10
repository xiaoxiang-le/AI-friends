from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateStorage(FileSystemStorage):
    @property
    def location(self):
        return str(Path(getattr(settings, 'PRIVATE_STORAGE_ROOT', Path(settings.BASE_DIR) / 'private_storage')).resolve())


def private_storage():
    return PrivateStorage()
