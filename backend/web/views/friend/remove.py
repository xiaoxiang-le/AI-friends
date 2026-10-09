from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Friend


class RemoveFriendView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            friend_id = request.data['friend_id']
            friend = Friend.objects.filter(id=friend_id, me__user=request.user).first()
            if not friend:
                return Response({'result': '好友不存在'})
            friend.delete()
            return Response({
                'result': 'success',
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })
