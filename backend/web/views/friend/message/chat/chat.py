import asyncio
import base64
import json
import os
import threading
import uuid
from queue import Queue

import websockets
from django.http import StreamingHttpResponse
from langchain_core.messages import HumanMessage, BaseMessageChunk, SystemMessage, AIMessage
from rest_framework.renderers import BaseRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Friend, Message, SystemPrompt
from web.views.friend.message.chat.graph import ChatGraph
from web.views.friend.message.memory.update import update_memory


class SSERenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'txt'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return json.dumps(data, ensure_ascii=False).encode('utf-8')


def add_system_prompt(state, friend):
    msgs = state['messages']
    system_prompts = SystemPrompt.objects.filter(title='回复').order_by('order_number')
    prompt = ''
    for sp in system_prompts:
        prompt += sp.prompt
    prompt += f'\n【角色性格】\n{friend.character.profile}\n'
    prompt += f'【长期记忆】\n{friend.memory}\n'
    return {'messages': [SystemMessage(prompt)] + msgs}


def add_recent_messages(state, friend):
    msgs = state['messages']
    message_raw = list(Message.objects.filter(friend=friend).order_by('-id')[:10])
    message_raw.reverse()
    messages = []
    for m in message_raw:
        messages.append(HumanMessage(m.user_message))
        messages.append(AIMessage(m.output))
    return {'messages': msgs[:1] + messages + msgs[-1:]}


class MessageChatView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [SSERenderer]
    def post(self, request):
        friend_id = request.data.get('friend_id')
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({
                'result': '消息不能为空'
            })
        friends = Friend.objects.filter(pk=friend_id, me__user=request.user)
        if not friends.exists():
            return Response({
                'result': '好友不存在'
            })
        friend = friends.first()
        if not os.getenv('API_KEY') or not os.getenv('API_BASE'):
            return Response({'result': 'AI 对话服务尚未配置，请联系管理员'}, status=503, content_type='application/json')
        try:
            app = ChatGraph.create_app()
        except Exception:
            return Response({'result': 'AI 对话服务暂时不可用，请稍后重试'}, status=503, content_type='application/json')

        inputs = {
            'messages': [HumanMessage(message)]
        }
        inputs = add_system_prompt(inputs, friend)
        inputs = add_recent_messages(inputs, friend)

        response = StreamingHttpResponse(
            self.event_stream(app, inputs, friend, message),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


    async def tts_sender(self, app, inputs, mq, ws, task_id):
        async for msg, metadata in app.astream(inputs, stream_mode="messages"):
            if isinstance(msg, BaseMessageChunk):
                if msg.content:
                    await ws.send(json.dumps({
                        "header": {
                            "action": "continue-task",
                            "task_id": task_id,  # 随机uuid
                            "streaming": "duplex"
                        },
                        "payload": {
                            "input": {
                                "text": msg.content,
                            }
                        }
                    }))
                    mq.put_nowait({'content': msg.content})
                if hasattr(msg, 'usage_metadata') and msg.usage_metadata:
                    mq.put_nowait({'usage': msg.usage_metadata})
        await ws.send(json.dumps({
            "header": {
                "action": "finish-task",
                "task_id": task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {}  # input不能省去，否则会报错
            }
        }))


    async def tts_receiver(self, mq, ws):
        async for msg in ws:
            if isinstance(msg, bytes):
                audio = base64.b64encode(msg).decode('utf-8')
                mq.put_nowait({'audio': audio})
            else:
                data = json.loads(msg)
                event = data['header']['event']
                if event in ['task-finished', 'task-failed']:
                    break


    async def run_tts_tasks(self, app, inputs, mq, voice_id):
        task_id = uuid.uuid4().hex
        api_key = os.getenv('API_KEY')
        wss_url = os.getenv('WSS_URL')
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        async with websockets.connect(wss_url, additional_headers=headers) as ws:
            await ws.send(json.dumps({
                "header": {
                    "action": "run-task",
                    "task_id": task_id,  # 随机uuid
                    "streaming": "duplex"
                },
                "payload": {
                    "task_group": "audio",
                    "task": "tts",
                    "function": "SpeechSynthesizer",
                    "model": "cosyvoice-v3-flash",
                    "parameters": {
                        "text_type": "PlainText",
                        "voice": voice_id,  # 音色
                        "format": "mp3",  # 音频格式
                        "sample_rate": 22050,  # 采样率
                        "volume": 50,  # 音量
                        "rate": 1.25,  # 语速
                        "pitch": 1  # 音调
                    },
                    "input": {  # input不能省去，不然会报错
                    }
                }
            }))
            async for msg in ws:
                if json.loads(msg)['header']['event'] == 'task-started':
                    break
            await asyncio.gather(
                self.tts_sender(app, inputs, mq, ws, task_id),
                self.tts_receiver(mq, ws),
            )


    async def run_text_task(self, app, inputs, mq):
        async for msg, metadata in app.astream(inputs, stream_mode='messages'):
            if isinstance(msg, BaseMessageChunk):
                if msg.content:
                    mq.put_nowait({'content': msg.content})
                if getattr(msg, 'usage_metadata', None):
                    mq.put_nowait({'usage': msg.usage_metadata})

    def work(self, app, inputs, mq, voice_id):
        try:
            if os.getenv('WSS_URL'):
                asyncio.run(self.run_tts_tasks(app, inputs, mq, voice_id))
            else:
                asyncio.run(self.run_text_task(app, inputs, mq))
        except Exception:
            mq.put_nowait({'error': 'AI 或语音服务请求失败，请稍后重试'})
        finally:
            mq.put_nowait(None)


    def event_stream(self, app, inputs, friend, message):
        mq = Queue()
        voice_id = 'longanyang'
        if friend.character.voice and friend.character.voice.voice_id:
            voice_id = friend.character.voice.voice_id
        thread = threading.Thread(target=self.work, args=(app, inputs, mq, voice_id))
        thread.start()

        full_output = ''
        full_usage = {}
        while True:
            msg = mq.get()
            if not msg:
                break
            if msg.get('error'):
                yield f"data: {json.dumps({'error': msg['error']}, ensure_ascii=False)}\n\n"
                return
            if msg.get('content', None):
                full_output += msg['content']
                yield f"data: {json.dumps({'content': msg['content']}, ensure_ascii=False)}\n\n"
            if msg.get('audio', None):
                yield f"data: {json.dumps({'audio': msg['audio']}, ensure_ascii=False)}\n\n"
            if msg.get('usage', None):
                full_usage = msg['usage']

        if not full_output:
            yield f"data: {json.dumps({'error': 'AI 服务没有返回回复，请重试'}, ensure_ascii=False)}\n\n"
            return
        input_tokens = full_usage.get('input_tokens', 0)
        output_tokens = full_usage.get('output_tokens', 0)
        total_tokens = full_usage.get('total_tokens', 0)
        Message.objects.create(
            friend=friend,
            user_message=message[:500],
            input=json.dumps(
                [m.model_dump() for m in inputs['messages']],
                ensure_ascii=False,
            )[:10000],
            output=full_output[:500],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        yield 'data: [DONE]\n\n'
        if Message.objects.filter(friend=friend).count() % 10 == 0:
            try:
                update_memory(friend)
            except Exception:
                pass