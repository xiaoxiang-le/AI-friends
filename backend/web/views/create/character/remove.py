from django.db.models import F
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from web.models.character import Character
from web.services.characters import positive_id


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
