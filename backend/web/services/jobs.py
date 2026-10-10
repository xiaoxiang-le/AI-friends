from datetime import timedelta
from urllib.parse import urlencode
import requests
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.utils.timezone import now
from web.models.character import Voice
from web.models.friend import Friend
from web.models.resources import BackgroundJob, KnowledgeDocument, KnowledgeChunk
from web.services.private_files import private_storage
from web.services.provider_config import setting, voice_config


def enrollment(action, **kwargs):
    url = setting('VOICE_URL')
    if not url.startswith('https://'):
        raise ValueError('复刻服务需要配置 HTTPS 接口')
    response = requests.post(url, headers={'Authorization': f"Bearer {voice_config('TTS')['api_key']}"},
        json={'model': 'voice-enrollment', 'input': {'action': action, **kwargs}}, timeout=(5, 30))
    response.raise_for_status()
    data = response.json()
    if data.get('code') or not isinstance(data.get('output'), dict):
        raise ValueError('供应商未接受此次音色操作')
    return data['output']


def enqueue_memory(friend):
    return BackgroundJob.objects.get_or_create(dedupe_key=f'memory:{friend.id}:{friend.memory_version}',
        defaults={'owner': friend.me, 'kind': 'memory', 'object_id': friend.id,
                  'payload': {'version': friend.memory_version}})[0]


def process(job):
    if job.kind == 'knowledge':
        from web.services.embeddings import embedding_config, embed
        from web.services.provider_config import configured
        doc = KnowledgeDocument.objects.get(pk=job.object_id, owner=job.owner)
        KnowledgeDocument.objects.filter(pk=doc.id).update(status='processing')
        texts = [doc.content[start:start+1000] for start in range(0,len(doc.content),800)]
        config = embedding_config()
        vectors = embed(texts) if configured(config) else [[] for _ in texts]
        with transaction.atomic():
            doc = KnowledgeDocument.objects.select_for_update().get(pk=job.object_id, owner=job.owner)
            doc.chunks.all().delete()
            KnowledgeChunk.objects.bulk_create([KnowledgeChunk(document=doc, position=i+1,
                content=text,vector=vectors[i]) for i,text in enumerate(texts)])
            doc.status, doc.error = 'ready', ''
            doc.index_mode = 'hybrid' if configured(config) else 'keyword'
            doc.embedding_model = config['model'] if configured(config) else ''
            doc.save(update_fields=['status','error','index_mode','embedding_model'])
    elif job.kind == 'memory':
        friend = Friend.objects.get(pk=job.object_id, me=job.owner)
        if friend.memory_enabled and friend.memory_version == job.payload.get('version'):
            from web.views.friend.message.memory.update import update_memory
            update_memory(friend)
    elif job.kind == 'voice':
        voice = Voice.objects.get(pk=job.object_id, owner=job.owner)
        if not voice.voice_id:
            # Mark uncertain before the non-idempotent provider request; a crash must
            # not silently submit a second paid enrollment task.
            job.payload['uncertain'] = True
            job.save(update_fields=['payload'])
            token = signing.dumps({'job': job.id}, salt='voice-sample')
            sample_url = setting('PUBLIC_BASE_URL').rstrip('/')+'/api/voice/sample/?'+urlencode({'token': token})
            output = enrollment('create_voice', target_model=voice.target_model,
                prefix=f'af{voice.id}'[:10], url=sample_url)
            voice.voice_id = output.get('voice_id', '')
            if not voice.voice_id:
                raise ValueError('供应商未返回音色编号')
            voice.save(update_fields=['voice_id'])
            job.payload['uncertain'] = False
            job.save(update_fields=['payload'])
        output = enrollment('query_voice', voice_id=voice.voice_id)
        if output.get('status') == 'DEPLOYING':
            # Polling is safe: it never creates another provider resource.
            if job.attempts >= 60:
                raise TimeoutError('音色复刻等待超时')
            job.status, job.available_at = 'queued', now()+timedelta(seconds=10)
            job.save(update_fields=['status', 'available_at'])
            return False
        if output.get('status') != 'OK':
            raise ValueError('音色样本未通过供应商审核')
        voice.status, voice.error = 'ready', ''
        voice.save(update_fields=['status', 'error'])
        private_storage().delete(job.payload['sample'])
        job.payload.pop('sample', None)
        job.save(update_fields=['payload'])
    elif job.kind == 'voice_delete':
        voice = Voice.objects.get(pk=job.object_id, owner=job.owner)
        if voice.character_set.exists():
            raise ValueError('此音色仍被角色引用，请先更换角色音色')
        if voice.voice_id:
            enrollment('delete_voice', voice_id=voice.voice_id)
        for creation in BackgroundJob.objects.filter(kind='voice', object_id=voice.id):
            if creation.payload.get('sample'):
                private_storage().delete(creation.payload['sample'])
        voice.delete()
    else:
        raise ValueError('未知任务类型')
    return True


def run_one():
    # A stale lease is recoverable after worker termination. Conditional UPDATE
    # also allows multiple workers to claim different jobs without double work.
    stale = now()-timedelta(minutes=5)
    BackgroundJob.objects.filter(status='running', updated_at__lt=stale).update(status='queued')
    for candidate in BackgroundJob.objects.filter(status='queued', available_at__lte=now()).order_by('id')[:10]:
        if not BackgroundJob.objects.filter(pk=candidate.pk, status='queued').update(
            status='running', attempts=F('attempts')+1, updated_at=now()):
            continue
        job = BackgroundJob.objects.get(pk=candidate.pk)
        try:
            if job.kind == 'voice' and job.payload.get('uncertain'):
                raise ValueError('复刻提交结果未确认，请管理员核对供应商资源后处理')
            if process(job):
                BackgroundJob.objects.filter(pk=job.pk).update(status='completed', error='', updated_at=now())
        except (KnowledgeDocument.DoesNotExist, Voice.DoesNotExist, Friend.DoesNotExist):
            BackgroundJob.objects.filter(pk=job.pk).update(status='cancelled', error='资源已删除', updated_at=now())
        except Exception as error:
            message = str(error) if isinstance(error, (ValueError, TimeoutError)) else '任务执行失败，请检查服务配置后重试'
            if job.payload.get('uncertain'):
                message = '复刻提交结果未确认，请管理员核对供应商资源后处理'
            BackgroundJob.objects.filter(pk=job.pk).update(status='failed', error=message[:200], updated_at=now())
            if job.kind == 'knowledge':
                KnowledgeDocument.objects.filter(pk=job.object_id).update(status='failed', error=message[:200])
            if job.kind in ['voice', 'voice_delete']:
                Voice.objects.filter(pk=job.object_id).update(status='failed', error=message[:200])
        return True
    return False
