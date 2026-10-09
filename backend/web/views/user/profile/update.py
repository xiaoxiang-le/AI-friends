from django.contrib.auth.models import User
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.views.utils.photo import remove_old_photo
from ....models.user import UserProfile


class UpdateProfile(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user_profile = UserProfile.objects.filter(user=user).first()
            if not user_profile:
                return Response({'result': '用户资料不存在'}, status=400)

            username = (request.data.get('username') or '').strip()
            profile = (request.data.get('profile') or '').strip()[:500]
            photo = request.FILES.get('photo', None)

            if not username:
                return Response({'result': '用户名不能为空'})
            if not profile:
                return Response({'result': '简介不能为空'})
            if username != user.username and User.objects.filter(username=username).exists():
                return Response({'result': '用户名已存在'})

            if photo:
                remove_old_photo(user_profile.photo)
                user_profile.photo = photo
            user_profile.profile = profile
            user_profile.update_time = now()
            user_profile.save()

            user.username = username
            user.save()

            return Response({
                'result': 'success',
                'user_id': user.id,
                'username': user.username,
                'profile': user_profile.profile,
                'photo': user_profile.photo.url,
            })
        except Exception:
            return Response({'result': '系统异常，请稍后重试'})