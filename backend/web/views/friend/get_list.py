from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from web.models.friend import Friend
from web.services.characters import accessible_characters, character_data


class GetListFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            offset = max(0, int(request.query_params.get('items_count', 0)))
        except (ValueError, TypeError):
            return Response({'result': '分页参数不合法'}, status=400)
        available = set(accessible_characters(request.user).values_list('id', flat=True))
        rows = Friend.objects.filter(me__user=request.user, archived_at__isnull=True).select_related('character__author__user').order_by('-update_time', '-id')[offset:offset+20]
        return Response({'result': 'success', 'friends': [
            {'id': f.id, 'character': character_data(f.character), 'available': f.character_id in available,
             'last_interaction': f.update_time.isoformat()} for f in rows]})
