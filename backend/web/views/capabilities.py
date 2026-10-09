from rest_framework.views import APIView
from rest_framework.response import Response
from web.services.provider_config import ai_config, voice_config, configured


class CapabilitiesView(APIView):
    def get(self, request):
        capabilities = {}
        for name, config in [('ai', ai_config()), ('asr', voice_config('ASR')), ('tts', voice_config('TTS'))]:
            ready = configured(config)
            capabilities[name] = {'configured': ready, 'verified': False,
                                  'reason': '已配置，需真实调用验收' if ready else '服务尚未配置'}
        return Response({'result': 'success', 'capabilities': capabilities})
