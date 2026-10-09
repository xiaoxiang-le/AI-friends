from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response(
                {"result": "refresh token 不存在"},
                status=401,
            )

        try:
            token = RefreshToken(refresh_token)
        except Exception:
            return Response(
                {"result": "refresh token 过期了"},
                status=401,
            )

        # 是否旋转 refresh token
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
            token.set_jti()
            response = Response(
                {
                    "result": "success",
                    "access": str(token.access_token),
                }
            )
            # 开发环境使用 http，不能设置 secure=True，否则浏览器不会发送 cookie
            response.set_cookie(
                key="refresh_token",
                value=str(token),
                httponly=True,
                samesite="Lax",
                secure=False,   # 本地开发必须为 False，生产环境再改回 True
                max_age=86400 * 7,
            )
            return response

        # 不旋转时也返回新的 access token
        return Response(
            {
                "result": "success",
                "access": str(token.access_token),
            }
        )