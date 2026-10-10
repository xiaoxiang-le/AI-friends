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


class CustomVoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        voices = Voice.objects.filter(owner__user=request.user).order_by('-id')
        return Response({'result': 'success', 'voices': [
            {'id': v.id, 'name': v.name, 'status': v.status, 'error': v.error,
             'job_id': BackgroundJob.objects.filter(kind='voice', object_id=v.id).values_list('id', flat=True).first()}
            for v in voices]})

    def post(self, request):
        name = request.data.get('name')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 50:
            return Response({'result': '音色名字需为1至50字'}, status=400)
        if request.data.get('authorized') not in [True, 'true']:
            return Response({'result': '请确认你拥有样本的声音使用授权'}, status=400)
        base = setting('PUBLIC_BASE_URL').rstrip('/')
        url = urlsplit(base)
        if not setting('VOICE_URL') or not voice_config('TTS')['api_key'] or url.scheme != 'https' or not url.hostname or url.hostname in ['localhost', '127.0.0.1']:
            return Response({'result': '音色复刻需要管理员配置 VOICE_URL 和可公网访问的 HTTPS PUBLIC_BASE_URL'}, status=503)
        owner = UserProfile.objects.get(user=request.user)
        if Voice.objects.filter(owner=owner).count() >= 10:
            return Response({'result': '每个用户最多10个自定义音色'}, status=400)
        sample = request.FILES.get('sample')
        if not sample or sample.size > 10*1024*1024:
            return Response({'result': '请上传10MB以内的 WAV 样本'}, status=400)
        raw = sample.read()
        try:
            with wave.open(io.BytesIO(raw)) as audio:
                duration = audio.getnframes()/audio.getframerate()
                if audio.getnchannels()!=1 or audio.getsampwidth()!=2 or audio.getframerate()<16000 or not 10<=duration<=20 or audio.getcomptype()!='NONE':
                    raise ValueError()
                samples=array('h',audio.readframes(audio.getnframes()))
                if not samples or math.sqrt(sum(value*value for value in samples)/len(samples))<150 or sum(abs(value)>32700 for value in samples)/len(samples)>.1:
                    raise ValueError()
        except (wave.Error, EOFError, ValueError, ZeroDivisionError):
            return Response({'result': '样本须为10至20秒、单声道、16位、至少16kHz的 PCM WAV，不能静音或严重削波'}, status=400)
        sample_path = private_storage().save(f'voice/{uuid.uuid4().hex}.wav', ContentFile(raw))
        try:
            with transaction.atomic():
                voice = Voice.objects.create(owner=owner, name=name.strip(), voice_id='', kind='custom',
                    status='preparing', target_model=voice_config('TTS')['model'])
                job = BackgroundJob.objects.create(owner=owner, kind='voice', object_id=voice.id,
                    dedupe_key=f'voice:{voice.id}', payload={'sample': sample_path})
        except Exception:
            private_storage().delete(sample_path)
            raise
        return Response({'result': 'success', 'voice_id': voice.id, 'job': job_data(job)}, status=202)

    def delete(self, request):
        vid = request.data.get('voice_id')
        if not positive_id(vid):
            return Response({'result': '音色编号不合法'}, status=400)
        voice = Voice.objects.filter(pk=vid, owner__user=request.user).first()
        if not voice:
            return Response({'result': '音色不存在'}, status=404)
        if Character.objects.filter(voice=voice).exists():
            return Response({'result': '请先为引用此音色的角色更换音色'}, status=409)
        if voice.status in ['preparing', 'deleting']:
            return Response({'result': '音色任务进行中，请等待任务结束'}, status=409)
        with transaction.atomic():
            voice.status = 'deleting'
            voice.save(update_fields=['status'])
            job, _ = BackgroundJob.objects.get_or_create(dedupe_key=f'voice-delete:{voice.id}',
                defaults={'owner': voice.owner, 'kind': 'voice_delete', 'object_id': voice.id})
        return Response({'result': 'success', 'job': job_data(job)}, status=202)


class VoiceSampleView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            payload = signing.loads(request.query_params.get('token', ''), salt='voice-sample', max_age=1800)
            job = BackgroundJob.objects.get(pk=payload['job'], kind='voice', status__in=['queued', 'running'])
            sample = job.payload['sample']
            return FileResponse(private_storage().open(sample, 'rb'), content_type='audio/wav')
        except (signing.BadSignature, KeyError, BackgroundJob.DoesNotExist, FileNotFoundError):
            raise Http404()


class MessageAudioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        message = Message.objects.filter(pk=message_id, friend__me__user=request.user).first()
        if not message or not message.audio:
            raise Http404()
        response = FileResponse(message.audio.open('rb'), content_type='audio/mpeg')
        response['Cache-Control'] = 'private, no-store'
        return response


