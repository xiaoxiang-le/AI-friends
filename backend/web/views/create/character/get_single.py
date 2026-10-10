from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from web.models.character import Character
from web.services.characters import character_data, positive_id
from web.services.voice_catalog import voice_options


class GetSingleCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        character_id = request.query_params.get('character_id')
        if not positive_id(character_id):
            return Response({'result': '角色编号不合法'}, status=400)
        character = Character.objects.select_related('author__user').filter(pk=character_id, author__user=request.user).first()
        if not character:
            return Response({'result': '角色不存在或无权编辑'}, status=404)
        return Response({'result': 'success', 'character': character_data(character, owner=True),
                         'voices': voice_options(request.user)})
