"""Small readiness probes; no provider requests or credential output."""
import os
import sys
from pathlib import Path
from urllib.request import Request, ProxyHandler, build_opener


def check_web():
    host = os.getenv('HEALTHCHECK_HOST', 'localhost')
    request = Request('http://127.0.0.1:8000/api/health/', headers={'Host': host})
    with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
        return response.status == 200


def check_worker():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    import django
    django.setup()
    from datetime import timedelta
    from django.utils.timezone import now
    from web.models.resources import WorkerHeartbeat
    # The worker runs as PID 1 in this single-worker Compose deployment.
    # Allow up to five minutes for an in-progress provider job.
    return WorkerHeartbeat.objects.filter(name='worker:1', updated_at__gte=now()-timedelta(minutes=5)).exists()


if __name__ == '__main__':
    try:
        healthy = {'web': check_web, 'worker': check_worker}[sys.argv[1]]()
    except Exception:
        healthy = False
    sys.exit(0 if healthy else 1)
