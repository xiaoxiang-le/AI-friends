import time
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
        try:
            while True:
                if time.monotonic()-last_heartbeat>20:
                    WorkerHeartbeat.objects.update_or_create(name=f'worker:{os.getpid()}',defaults={'updated_at':now()})
                    last_heartbeat = time.monotonic()
                close_old_connections()
                worked = run_one()
                if not worked:
                    if options['once']:
                        break
                    time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write('任务工作器已停止，队列保留在数据库中。')
