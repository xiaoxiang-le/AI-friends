from django.db.models import F
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from web.models.friend import Friend


class MemoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friend_id = request.query_params.get('friend_id')
        if not str(friend_id).isascii() or not str(friend_id).isdigit():
            return Response({'result': '好友编号不合法'}, status=400)
        friend = Friend.objects.filter(pk=friend_id, me__user=request.user).first()
        if not friend:
            return Response({'result': '好友不存在'}, status=404)
        return Response({'result': 'success', 'memory': friend.memory or '', 'version': friend.memory_version, 'enabled': friend.memory_enabled})

    def post(self, request):
        friend_id = request.data.get('friend_id')
        if not str(friend_id).isascii() or not str(friend_id).isdigit():
            return Response({'result': '好友编号不合法'}, status=400)
        memory = request.data.get('memory')
        version = request.data.get('version')
        enabled = request.data.get('enabled')
        if enabled is not None and type(enabled) is not bool:
            return Response({'result': '记忆开关不合法'}, status=400)
        if not isinstance(memory, str) or len(memory) > 5000 or type(version) is not int:
            return Response({'result': '记忆最多5000字，且需提供版本号'}, status=400)
        friends = Friend.objects.filter(pk=friend_id, me__user=request.user)
        if not friends.exists():
            return Response({'result': '好友不存在'}, status=404)
        changes = {'memory': memory, 'memory_version': F('memory_version')+1, 'update_time': now()}
        if enabled is not None:
            changes['memory_enabled'] = enabled
        if not friends.filter(memory_version=version).update(**changes):
            return Response({'result': '记忆已更新，请重新加载后修改'}, status=409)
        return Response({'result': 'success', 'version': version + 1})
