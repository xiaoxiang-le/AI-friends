from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ....models.user import UserProfile
from rest_framework_simplejwt.tokens import RefreshToken


class Register(APIView):
    # Public credential endpoints must not authenticate a stale access token.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')
            password_confirm = request.data.get('password_confirm', '')

            if not username:
                return Response({'result': '用户名不能为空'})
            if not password:
                return Response({'result': '密码不能为空'})
            if password != password_confirm:
                return Response({'result': '两次密码不一致'})
            if len(password) < 6:
                return Response({'result': '密码长度不能少于6位'})

            if User.objects.filter(username=username).exists():
                return Response({'result': '用户名已存在'})

            user = User.objects.create_user(username=username, password=password)
            UserProfile.objects.create(user=user)

            refresh = RefreshToken.for_user(user)
            user_profile = UserProfile.objects.get(user=user)
            response = Response({
                'result': 'success',
                'access': str(refresh.access_token),
                'user_id': user.id,
                'username': user.username,
                'photo': user_profile.photo.url if user_profile.photo else '',
                'profile': user_profile.profile,
            })
            # 开发环境使用 http，不能设置 secure=True，否则浏览器不会发送 cookie
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                samesite='Lax',
                secure=False,   # 本地开发必须为 False，生产环境再改回 True
                max_age=86400 * 7,
            )
            return response
        except Exception:
            return Response({'result': '系统异常，请稍后重试'})
