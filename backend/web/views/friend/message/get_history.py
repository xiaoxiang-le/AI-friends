from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.models.friend import Message
from web.services.characters import positive_id


class GetHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friend_id = request.query_params.get('friend_id')
        cursor = request.query_params.get('last_message_id', '0')
        if not positive_id(friend_id) or not str(cursor).isascii() or not str(cursor).isdigit():
            return Response({'result': '好友编号或历史游标不合法'}, status=400)
        try:
            last_message_id = int(cursor)
            queryset = Message.objects.filter(friend_id=friend_id, friend__me__user=request.user)
            if last_message_id > 0:
                queryset = queryset.filter(pk__lt=last_message_id)

            messages_raw = queryset.order_by("-id")[:10]
            messages = [
                {"id": m.id, "user_message": m.user_message, "output": m.output, "status": m.status, "error": m.error, "has_audio": bool(m.audio), "sources": m.sources}
                for m in messages_raw
            ]
            return Response({"result": "success", "messages": messages})
        except Exception:
            return Response({"result": "系统异常，请稍后重试"})
