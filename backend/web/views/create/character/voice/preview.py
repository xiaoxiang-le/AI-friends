import asyncio
import base64
from queue import Queue

from django.http import HttpResponse
from langchain_core.messages import AIMessageChunk
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.services.provider_config import configured, voice_config
from web.services.voice_catalog import available_voices
from web.views.friend.message.chat.chat import MessageChatView


class PreviewVoice(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        voice_id = str(request.data.get('voice_id', ''))
        if not voice_id.isascii() or not voice_id.isdigit():
            return Response({'result':'请选择有效音色'}, status=400)
        voice = available_voices().filter(id=voice_id).first()
        if not voice:
            return Response({'result':'该音色不可用，请重新选择'}, status=400)
        if not configured(voice_config('TTS')):
            return Response({'result':'语音试听暂不可用，请联系管理员'}, status=503)
        class PreviewGraph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='你好，很高兴认识你。今天想聊些什么？'), {}
        queue = Queue()
        try:
            asyncio.run(asyncio.wait_for(MessageChatView().run_tts_tasks(
                PreviewGraph(), {}, queue, voice.voice_id), timeout=20))
        except TimeoutError:
            return Response({'result':'音色试听超时，请稍后重试'}, status=504)
        except Exception:
            return Response({'result':'音色试听失败，请稍后重试'}, status=503)
        chunks = []
        while not queue.empty():
            data = queue.get_nowait()
            if data.get('audio'):
                chunks.append(base64.b64decode(data['audio']))
        if not chunks:
            return Response({'result':'未生成试听音频，请稍后重试'}, status=503)
        response = HttpResponse(b''.join(chunks), content_type='audio/mpeg')
        response['Cache-Control'] = 'private, no-store'
        return response
