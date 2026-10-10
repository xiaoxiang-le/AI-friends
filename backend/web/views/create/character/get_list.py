from rest_framework.response import Response
from rest_framework.views import APIView
from web.models.character import Character
from web.models.user import UserProfile
from web.services.characters import character_data, positive_id


class GetListCharacterView(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not positive_id(user_id):
            return Response({'result': '用户编号不合法'}, status=400)
        profile = UserProfile.objects.select_related('user').filter(user_id=user_id).first()
        if not profile:
            return Response({'result': '用户不存在'}, status=404)
        try:
            offset = max(0, int(request.query_params.get('items_count', 0)))
        except (ValueError, TypeError):
            return Response({'result': '分页参数不合法'}, status=400)
        owner = request.user.is_authenticated and request.user.id == profile.user_id
        rows = Character.objects.filter(author=profile).select_related('author__user')
        if not owner:
            rows = rows.filter(status='published', visibility='public')
        elif request.query_params.get('archived') == 'true':
            rows = rows.filter(status='archived')
        else:
            rows = rows.exclude(status='archived')
        return Response({'result': 'success', 'user_profile': {
            'user_id': profile.user_id, 'username': profile.user.username,
            'profile': profile.profile, 'photo': profile.photo.url if profile.photo else ''},
            'characters': [character_data(c) for c in rows.order_by('-id')[offset:offset+20]]})
