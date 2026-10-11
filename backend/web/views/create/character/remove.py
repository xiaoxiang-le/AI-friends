from django.db import transaction
from django.db.models import F, Q
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from web.models.character import Character
from web.models.friend import Friend, Message
from web.models.resources import BackgroundJob, GenerationLease
from web.services.characters import positive_id
from web.views.utils.photo import remove_old_photo


class DeleteCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        character_id, version = request.data.get('character_id'), request.data.get('version')
        if not positive_id(character_id) or not positive_id(version):
            return Response({'result': '角色编号或版本号不合法'}, status=400)
        if request.data.get('confirm') is not True:
            return Response({'result': '请确认永久删除角色及所有关联聊天和知识资料'}, status=400)
        with transaction.atomic():
            character = Character.objects.select_for_update().filter(
                pk=character_id, author__user=request.user).first()
            if not character:
                return Response({'result': '角色不存在或无权删除'}, status=404)
            if character.version != int(version):
                return Response({'result': '角色已更新，请刷新后重试'}, status=409)
            friends = Friend.objects.filter(character=character)
            jobs = BackgroundJob.objects.filter(
                Q(kind='knowledge', object_id__in=character.knowledgedocument_set.values('id')) |
                Q(kind='memory', object_id__in=friends.values('id')))
            if GenerationLease.objects.filter(friend__in=friends, expires_at__gt=now()).exists() or jobs.filter(status='running').exists():
                return Response({'result': '角色正在生成回复或处理资料，请等待任务结束后再删除'}, status=409)
            files = [character.photo, character.background_image]
            files.extend(message.audio for message in Message.objects.filter(friend__in=friends).exclude(audio=''))
            # These jobs use generic object IDs rather than foreign keys, so remove
            # them explicitly. Custom voices belong to the user and remain reusable.
            jobs.delete()
            character.delete()
            # Never remove files before the database transaction commits.
            for field in files:
                if field:
                    transaction.on_commit(lambda field=field: remove_old_photo(field), robust=True)
        return Response({'result': 'success'})


class RemoveCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        character_id = request.data.get('character_id')
        if not positive_id(character_id):
            return Response({'result': '角色编号不合法'}, status=400)
        characters = Character.objects.filter(pk=character_id, author__user=request.user)
        version = request.data.get('version')
        if version is not None and not positive_id(version):
            return Response({'result': '版本号不合法'}, status=400)
        if not characters.exists():
            return Response({'result': '角色不存在'}, status=404)
        if version is None or not characters.filter(version=version).update(
            status='archived', archived_at=now(), version=F('version') + 1, update_time=now()):
            return Response({'result': '角色已更新，请刷新后重试'}, status=409)
        return Response({'result': 'success'})


class RestoreCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        character_id = request.data.get('character_id')
        if not positive_id(character_id):
            return Response({'result': '角色编号不合法'}, status=400)
        characters = Character.objects.filter(pk=character_id, author__user=request.user, status='archived')
        if not characters.exists():
            return Response({'result': '归档角色不存在'}, status=404)
        version = request.data.get('version')
        if version is not None and not positive_id(version):
            return Response({'result': '版本号不合法'}, status=400)
        if version is None or not characters.filter(version=version).update(
            status='draft', visibility='private', archived_at=None, version=F('version')+1, update_time=now()):
            return Response({'result': '角色已更新，请刷新后重试'}, status=409)
        return Response({'result': 'success'})
