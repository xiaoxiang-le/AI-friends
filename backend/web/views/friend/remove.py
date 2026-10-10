from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from web.models.friend import Friend
from web.services.characters import positive_id


class RemoveFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        friend_id = request.data.get('friend_id')
        if not positive_id(friend_id):
            return Response({'result': '好友编号不合法'}, status=400)
        if not Friend.objects.filter(pk=friend_id, me__user=request.user).update(archived_at=now()):
            return Response({'result': '好友不存在'}, status=404)
        return Response({'result': 'success'})
