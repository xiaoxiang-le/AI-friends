import asyncio
import json
import os
import uuid

import websockets
from web.services.provider_config import voice_config, configured
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class ASRView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio = request.FILES.get('audio')
        if not audio:
            return Response({
                'result': '音频不存在'
            })
        if audio.size > 16000 * 2 * 60 or audio.size == 0 or audio.size % 2:
            return Response({'result': '请上传60秒以内的16kHz单声道PCM16音频'}, status=400)
        if not configured(voice_config('ASR')):
            return Response({'result': '语音识别服务尚未配置，请联系管理员'}, status=503)
        pcm_data = audio.read()
        try:
            text = asyncio.run(asyncio.wait_for(self.run_asr_tasks(pcm_data), timeout=45))
        except TimeoutError:
            return Response({'result': '语音识别超时，请重新录音'}, status=504)
        except Exception:
            return Response({'result': '语音识别失败，请稍后重试'}, status=503)
        if not text.strip():
            return Response({'result': '未识别到有效语音，请重新录音'}, status=422)
        return Response({
            'result': 'success',
            'text': text,
        })

    async def asr_sender(self, pcm_data, ws, task_id):
        chunk = 3200
        for i in range(0, len(pcm_data), chunk):
            await ws.send(pcm_data[i: i + chunk])
            await asyncio.sleep(0.01)
        await ws.send(json.dumps({
            "header": {
                "action": "finish-task",
                "task_id": task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {}
            }
        }))

    async def asr_receiver(self, ws):
        text = ''
        async for msg in ws:
            data = json.loads(msg)
            event = data['header']['event']
            if event == 'result-generated':
                output = data['payload']['output']
                if output.get('transcription', None) and output['transcription']['sentence_end']:
                    text += output['transcription']['text']
            elif event == 'task-failed':
                raise RuntimeError('ASR provider failed')
            elif event == 'task-finished':
                break
        return text

    async def run_asr_tasks(self, pcm_data):
        task_id = uuid.uuid4().hex
        config = voice_config('ASR')
        api_key = config['api_key']
        wss_url = config['url']
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        async with websockets.connect(wss_url, additional_headers=headers) as ws:
            await ws.send(json.dumps({
                "header": {
                    "streaming": "duplex",
                    "task_id": task_id,
                    "action": "run-task"
                },
                "payload": {
                    "model": config['model'],
                    "parameters": {
                        "sample_rate": 16000,
                        "format": "pcm",
                        "transcription_enabled": True,
                    },
                    "input": {},
                    "task": "asr",
                    "task_group": "audio",
                    "function": "recognition"
                }
            }))
            async for msg in ws:
                event = json.loads(msg)['header']['event']
                if event == 'task-failed':
                    raise RuntimeError('ASR provider failed')
                if event == 'task-started':
                    break
            _, text = await asyncio.gather(
                self.asr_sender(pcm_data, ws, task_id),
                self.asr_receiver(ws),
            )
            return text
