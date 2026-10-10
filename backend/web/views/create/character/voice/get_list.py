from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.services.voice_catalog import voice_options


class GetVoiceList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            voices = voice_options(request.user)
            return Response({
                'result': 'success',
                'voices': voices,
            })
        except Exception:
            return Response({
                'result': '系统异常，请稍后重试'
            })
