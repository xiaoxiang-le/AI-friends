from rest_framework.views import APIView
from rest_framework.response import Response
from web.services.provider_config import ai_config, voice_config, configured, setting


class CapabilitiesView(APIView):
    authentication_classes = []
    def get(self, request):
        capabilities = {}
        for name, config in [('ai', ai_config()), ('asr', voice_config('ASR')), ('tts', voice_config('TTS'))]:
            ready = configured(config)
            capabilities[name] = {'configured': ready, 'verified': False,
                                  'reason': '已配置，需真实调用验收' if ready else '服务尚未配置'}
        capabilities['knowledge'] = {'configured': True, 'verified': False, 'reason': '按角色隔离的本地关键词检索；文件需要处理完成'}
        capabilities['voice_clone'] = {'configured': bool(setting('VOICE_URL') and setting('PUBLIC_BASE_URL') and voice_config('TTS')['api_key']), 'verified': False, 'reason': '需要复刻接口、公网 HTTPS 样本地址和授权样本验收'}
        return Response({'result': 'success', 'capabilities': capabilities})
