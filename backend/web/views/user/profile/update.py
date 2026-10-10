from django.contrib.auth.models import User
from django.db import transaction
from web.services.uploads import validate_image
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

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

            username = request.data.get('username', '')
            profile = request.data.get('profile', '')
            if not isinstance(username, str) or not isinstance(profile, str):
                return Response({'result': '用户名和简介必须为文本'}, status=400)
            username, profile = username.strip(), profile.strip()
            photo = request.FILES.get('photo', None)

            if not username:
                return Response({'result': '用户名不能为空'})
            if not profile:
                return Response({'result': '简介不能为空'})
            if len(username)>150 or len(profile)>500:
                return Response({'result': '用户名最多150字，简介最多500字'}, status=400)
            validate_image(photo)
            if username != user.username and User.objects.filter(username=username).exists():
                return Response({'result': '用户名已存在'})

            old_photo = user_profile.photo if photo else None
            with transaction.atomic():
                # A concurrent duplicate username must not partially save the
                # biography or remove the user's current avatar.
                user.username = username
                user.save(update_fields=['username'])
                if photo:
                    user_profile.photo = photo
                user_profile.profile = profile
                user_profile.update_time = now()
                user_profile.save()
                if old_photo:
                    transaction.on_commit(lambda: remove_old_photo(old_photo))

            return Response({
                'result': 'success',
                'user_id': user.id,
                'username': user.username,
                'profile': user_profile.profile,
                'photo': user_profile.photo.url,
            })
        except ValidationError:
            raise
        except Exception:
            return Response({'result': '系统异常，请稍后重试'})
