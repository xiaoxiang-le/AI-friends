from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ....models.user import UserProfile
from rest_framework_simplejwt.tokens import RefreshToken


class Login(APIView):
    # Public credential endpoints must not authenticate a stale access token.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')

            if not username or not password:
                return Response({'result': '用户名和密码不能为空'})

            user = authenticate(username=username, password=password)
            if not user:
                return Response({'result': '用户名或密码错误'})

            # 取用户扩展信息
            user_profile = UserProfile.objects.filter(user=user).first()
            photo_url = ''
            profile = ''
            if user_profile:
                photo_url = getattr(user_profile.photo, 'url', '') or ''
                profile = user_profile.profile

            refresh = RefreshToken.for_user(user)
            response = Response({
                'result': 'success',
                'access': str(refresh.access_token),
                'user_id': user.id,
                'username': user.username,
                'photo': photo_url,
                'profile': profile,
            })
            # 开发环境使用 http，不能设置 secure=True，否则浏览器不会发送 cookie
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                samesite='Lax',
                secure=not settings.DEBUG,   # 本地开发必须为 False，生产环境再改回 True
                max_age=86400 * 7,
            )
            return response
        except Exception:
            return Response({'result': '系统异常，请稍后重试'})