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


class KnowledgeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cid = request.query_params.get('character_id')
        if not positive_id(cid):
            return Response({'result': '角色编号不合法'}, status=400)
        if not Character.objects.filter(pk=cid, author__user=request.user).exists():
            return Response({'result': '角色不存在'}, status=404)
        docs = KnowledgeDocument.objects.filter(character_id=cid, owner__user=request.user).order_by('-id')
        return Response({'result': 'success', 'documents': [
            {'id': d.id, 'name': d.name, 'status': d.status, 'error': d.error, 'index_mode':d.index_mode,
             'job_id': BackgroundJob.objects.filter(kind='knowledge', object_id=d.id).values_list('id', flat=True).first()}
            for d in docs]})

    def post(self, request):
        cid = request.data.get('character_id')
        if not positive_id(cid):
            return Response({'result': '角色编号不合法'}, status=400)
        character = Character.objects.filter(pk=cid, author__user=request.user).first()
        if not character:
            return Response({'result': '角色不存在'}, status=404)
        upload = request.FILES.get('file')
        if not upload or Path(upload.name).suffix.lower() not in ['.txt', '.md'] or upload.size > 1024*1024:
            return Response({'result': '请上传1MB以内的 UTF-8 TXT 或 Markdown 文件'}, status=400)
        raw = upload.read()
        try:
            content = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({'result': '文件须为 UTF-8 编码'}, status=400)
        if not content.strip() or '\x00' in content or len(content)>200000:
            return Response({'result': '知识文件为空或内容无效，最多200000字'}, status=400)
        if KnowledgeDocument.objects.filter(character=character).count() >= 20:
            return Response({'result': '每个角色最多20份知识文件'}, status=400)
        with transaction.atomic():
            doc, created = KnowledgeDocument.objects.get_or_create(character=character,
                sha256=hashlib.sha256(raw).hexdigest(), defaults={'owner': character.author,
                'name': Path(upload.name).name[:150], 'content': content})
            job, _ = BackgroundJob.objects.get_or_create(dedupe_key=f'knowledge:{doc.id}',
                defaults={'owner': character.author, 'kind': 'knowledge', 'object_id': doc.id})
        return Response({'result': 'success', 'document_id': doc.id, 'job': job_data(job), 'duplicate': not created}, status=202)

    def delete(self, request):
        did = request.data.get('document_id')
        if not positive_id(did):
            return Response({'result': '文件编号不合法'}, status=400)
        with transaction.atomic():
            doc = KnowledgeDocument.objects.filter(pk=did, owner__user=request.user).first()
            if not doc:
                return Response({'result': '文件不存在'}, status=404)
            BackgroundJob.objects.filter(kind='knowledge', object_id=doc.id).delete()
            doc.delete()
        return Response({'result': 'success'})


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


