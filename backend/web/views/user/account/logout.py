from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        token = request.COOKIES.get('refresh_token')
        if token:
            try: RefreshToken(token).blacklist()
            except Exception: pass
        response = Response({
            'result': 'success',
        })
        response.delete_cookie('refresh_token')
        return response