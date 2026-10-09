import asyncio
import base64
import json
import os
import threading
import uuid
from queue import Queue, Empty
from django.db import close_old_connections
from web.services.provider_config import ai_config, voice_config, configured, setting

ACTIVE_REQUESTS = {}
ACTIVE_LOCK = threading.Lock()



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


class CancelChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_id = request.data.get('request_id')
        if not isinstance(request_id, str) or not (1 <= len(request_id) <= 64):
            return Response({'result': '请求编号不合法'}, status=400)
        with ACTIVE_LOCK:
            active = ACTIVE_REQUESTS.get((request.user.id, request_id))
            if active:
                active['stop'].set()
        return Response({'result': 'success'})


class ChatStreamResponse(StreamingHttpResponse):
    def __init__(self, *args, stop, key, **kwargs):
        self.stop = stop
        self.key = key
        super().__init__(*args, **kwargs)

    def close(self):
        self.stop.set()
        with ACTIVE_LOCK:
            ACTIVE_REQUESTS.pop(self.key, None)
        super().close()


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
        if not str(friend_id).isascii() or not str(friend_id).isdigit():
            return Response({'result': '好友编号不合法'}, status=400)
        raw = request.data.get('message')
        if not isinstance(raw, str) or len(raw) > 10000:
            return Response({'result': '消息需为文本，最多10000字'}, status=400)
        message = raw.strip()
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
        request_id = request.data.get('request_id') or uuid.uuid4().hex
        if not isinstance(request_id, str) or not (1 <= len(request_id) <= 64):
            return Response({'result': '请求编号不合法'}, status=400)
        previous = Message.objects.filter(friend=friend, request_id=request_id).first()
        if previous:
            if previous.user_message != message:
                return Response({'result': '请求编号已被其他消息使用'}, status=409)
            data = json.dumps({'content': previous.output}, ensure_ascii=False)
            return StreamingHttpResponse(iter([f'data: {data}\n\n', 'data: [DONE]\n\n']), content_type='text/event-stream')
        if not configured(ai_config()):
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

        key = (request.user.id, request_id)
        stop = threading.Event()
        with ACTIVE_LOCK:
            if any(v['friend_id'] == friend.id for v in ACTIVE_REQUESTS.values()):
                return Response({'result': '此会话正在生成，请停止或等待完成'}, status=409)
            ACTIVE_REQUESTS[key] = {'friend_id': friend.id, 'stop': stop}
        response = ChatStreamResponse(
            self.event_stream(app, inputs, friend, message, request_id, stop, key,
                              request.data.get('enable_audio') is True),
            content_type='text/event-stream',
            stop=stop, key=key,
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
                if event == 'task-failed':
                    raise RuntimeError('TTS provider failed')
                if event == 'task-finished':
                    break


    async def run_tts_tasks(self, app, inputs, mq, voice_id):
        task_id = uuid.uuid4().hex
        config = voice_config('TTS')
        api_key = config['api_key']
        wss_url = config['url']
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
                    "model": config['model'],
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
                event = json.loads(msg)['header']['event']
                if event == 'task-failed':
                    raise RuntimeError('TTS provider failed')
                if event == 'task-started':
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

    async def run_generation(self, app, inputs, mq, voice_id, stop, enable_audio):
        # Text remains usable when a separate voice provider fails.
        content = []
        class TextQueue:
            def put_nowait(self, item):
                if item.get('content'):
                    content.append(item['content'])
                mq.put_nowait(item)
        task = asyncio.create_task(self.run_text_task(app, inputs, TextQueue()))
        async def cancelled():
            while not stop.is_set():
                await asyncio.sleep(.1)
        watcher = asyncio.create_task(cancelled())
        try:
            done, _ = await asyncio.wait([task, watcher], timeout=90, return_when=asyncio.FIRST_COMPLETED)
            if task not in done:
                task.cancel()
                if stop.is_set():
                    return
                raise TimeoutError('generation timeout')
            await task
            if enable_audio and configured(voice_config('TTS')) and content and not stop.is_set():
                class SpeechGraph:
                    async def astream(self, inputs, stream_mode):
                        from langchain_core.messages import AIMessageChunk
                        yield AIMessageChunk(content=''.join(content)), {}
                class AudioQueue:
                    def put_nowait(self, item):
                        if 'audio' in item:
                            mq.put_nowait(item)
                speech = asyncio.create_task(self.run_tts_tasks(SpeechGraph(), {}, AudioQueue(), voice_id))
                try:
                    done, _ = await asyncio.wait([speech, watcher], timeout=30, return_when=asyncio.FIRST_COMPLETED)
                    if speech not in done:
                        speech.cancel()
                        if stop.is_set():
                            return
                        raise TimeoutError('speech timeout')
                    await speech
                except Exception:
                    mq.put_nowait({'warning': '语音播报失败，文字回复已保留'})
                finally:
                    if not speech.done():
                        speech.cancel()
                    await asyncio.gather(speech, return_exceptions=True)
        finally:
            task.cancel()
            watcher.cancel()
            await asyncio.gather(task, watcher, return_exceptions=True)

    def work(self, app, inputs, mq, voice_id, stop, enable_audio):
        try:
            asyncio.run(self.run_generation(app, inputs, mq, voice_id, stop, enable_audio))
        except TimeoutError:
            mq.put_nowait({'error': 'AI 对话超时，请稍后重试'})
        except Exception:
            mq.put_nowait({'error': 'AI 对话服务请求失败，请稍后重试'})
        finally:
            mq.put_nowait(None)


    def event_stream(self, app, inputs, friend, message, request_id=None, stop=None, key=None, enable_audio=False):
        stop = stop or threading.Event()
        try:
            yield from self._event_stream(app, inputs, friend, message, request_id, stop, enable_audio)
        finally:
            stop.set()
            with ACTIVE_LOCK:
                ACTIVE_REQUESTS.pop(key, None)

    def _event_stream(self, app, inputs, friend, message, request_id, stop, enable_audio):
        mq = Queue()
        voice_id = 'longanyang'
        if friend.character.voice and friend.character.voice.voice_id:
            voice_id = friend.character.voice.voice_id
        thread = threading.Thread(target=self.work, args=(app, inputs, mq, voice_id, stop, enable_audio), daemon=True)
        thread.start()

        full_output = ''
        full_usage = {}
        while True:
            if stop.is_set():
                yield f'data: {json.dumps({"error": "已停止生成"}, ensure_ascii=False)}\n\n'
                return
            try:
                msg = mq.get(timeout=1)
            except Empty:
                yield ': heartbeat\n\n'
                continue
            if not msg:
                break
            if msg.get('error'):
                yield f"data: {json.dumps({'error': msg['error']}, ensure_ascii=False)}\n\n"
                return
            if msg.get('warning'):
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            if msg.get('content', None):
                full_output += msg['content']
                yield f"data: {json.dumps({'content': msg['content']}, ensure_ascii=False)}\n\n"
            if msg.get('audio', None):
                yield f"data: {json.dumps({'audio': msg['audio']}, ensure_ascii=False)}\n\n"
            if msg.get('usage', None):
                full_usage = msg['usage']

        if stop.is_set():
            return
        if not full_output:
            yield f"data: {json.dumps({'error': 'AI 服务没有返回回复，请重试'}, ensure_ascii=False)}\n\n"
            return
        input_tokens = full_usage.get('input_tokens', 0)
        output_tokens = full_usage.get('output_tokens', 0)
        total_tokens = full_usage.get('total_tokens', 0)
        Message.objects.create(
            friend=friend,
            user_message=message,
            request_id=request_id,
            input=json.dumps(
                [m.model_dump() for m in inputs['messages']],
                ensure_ascii=False,
            ),
            output=full_output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        yield 'data: [DONE]\n\n'
        if setting('MEMORY_AUTO_UPDATE', default='false') == 'true' and Message.objects.filter(friend=friend).count() % 10 == 0:
            def refresh_memory():
                close_old_connections()
                try:
                    update_memory(Friend.objects.get(pk=friend.pk))
                except Exception:
                    pass
                finally:
                    close_old_connections()
            threading.Thread(target=refresh_memory, daemon=True).start()
