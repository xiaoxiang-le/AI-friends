from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from web.models.friend import Friend
from web.models.user import UserProfile
from web.services.characters import accessible_characters, character_data, positive_id


class GetOrCreateFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        character_id = request.data.get('character_id')
        if not positive_id(character_id):
            return Response({'result': '角色编号不合法'}, status=400)
        character = accessible_characters(request.user).select_related('author__user').filter(pk=character_id).first()
        if not character:
            return Response({'result': '角色未发布、已归档或无权访问'}, status=404)
        friend, _ = Friend.objects.get_or_create(character=character, me=UserProfile.objects.get(user=request.user))
        if friend.archived_at:
            friend.archived_at = None
            friend.save(update_fields=['archived_at'])
        return Response({'result': 'success', 'friend': {'id': friend.id, 'character': character_data(character)}})
