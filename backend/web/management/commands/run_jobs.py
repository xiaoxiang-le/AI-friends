import time
import signal
import threading
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from web.services.jobs import run_one
from web.models.resources import WorkerHeartbeat
from django.utils.timezone import now
import os


class Command(BaseCommand):
    help = 'Process durable knowledge, memory and voice jobs; restart to resume queued jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Drain currently runnable jobs then exit')

    def handle(self, *args, **options):
        last_heartbeat = 0
        stopping = threading.Event()
        def request_stop(signum, frame):
            stopping.set()
        # PID 1 ignores unhandled SIGTERM on Linux. Finish the active job, then
        # exit without claiming another job when Compose stops this container.
        install_handler = threading.current_thread() is threading.main_thread()
        previous_handler = signal.signal(signal.SIGTERM, request_stop) if install_handler else None
        try:
            while not stopping.is_set():
                if time.monotonic()-last_heartbeat>20:
                    WorkerHeartbeat.objects.update_or_create(name=f'worker:{os.getpid()}',defaults={'updated_at':now()})
                    last_heartbeat = time.monotonic()
                close_old_connections()
                worked = run_one()
                if not worked:
                    if options['once']:
                        break
                    stopping.wait(1)
        except KeyboardInterrupt:
            stopping.set()
        finally:
            if install_handler:
                signal.signal(signal.SIGTERM, previous_handler)
            close_old_connections()
        if stopping.is_set():
            self.stdout.write('任务工作器已停止，队列保留在数据库中。')
