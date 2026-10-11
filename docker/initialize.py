"""Prepare mutable storage, schema and static assets before long-lived services."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')


def main():
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command

    for directory in (settings.DATA_DIR, settings.MEDIA_ROOT, settings.PRIVATE_STORAGE_ROOT, settings.STATIC_ROOT):
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Fail before migrations if a bind mount is not writable by UID 10001.
        with tempfile.TemporaryFile(dir=directory):
            pass
    avatar = Path(settings.MEDIA_ROOT) / 'user/photos/default.png'
    if not avatar.exists():
        avatar.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(settings.BASE_DIR / 'media/user/photos/default.png', avatar)
    call_command('migrate', interactive=False)
    call_command('collectstatic', interactive=False, clear=True)


if __name__ == '__main__':
    main()
