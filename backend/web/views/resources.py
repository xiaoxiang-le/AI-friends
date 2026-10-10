import hashlib
from array import array
import math
import io
import uuid
import wave
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from web.models.character import Character, Voice
from web.models.friend import Message
from web.models.resources import KnowledgeDocument, BackgroundJob, Report
from web.models.user import UserProfile
from web.services.characters import accessible_characters, positive_id
from web.services.private_files import private_storage
from web.services.provider_config import setting, voice_config


def job_data(job):
    return {'id': job.id, 'kind': job.kind, 'object_id': job.object_id, 'status': job.status,
            'attempts': job.attempts, 'error': job.error,
            'retryable': job.status == 'failed' and job.attempts < 3 and not job.payload.get('uncertain')}


class JobsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = BackgroundJob.objects.filter(owner__user=request.user).order_by('-id')[:50]
        return Response({'result': 'success', 'jobs': [job_data(j) for j in jobs]})

    def post(self, request):
        jid = request.data.get('job_id')
        if not positive_id(jid):
            return Response({'result': '任务编号不合法'}, status=400)
        with transaction.atomic():
            job = BackgroundJob.objects.select_for_update().filter(pk=jid, owner__user=request.user).first()
            if not job:
                return Response({'result': '任务不存在'}, status=404)
            if not job_data(job)['retryable']:
                return Response({'result': '此任务不可重试或已达3次上限'}, status=409)
            if job.kind == 'memory':
                from web.models.friend import Friend
                friend = Friend.objects.get(pk=job.object_id, me=job.owner)
                job.payload['version'] = friend.memory_version
            job.status, job.error, job.available_at = 'queued', '', now()
            job.save()
        return Response({'result': 'success', 'job': job_data(job)})


