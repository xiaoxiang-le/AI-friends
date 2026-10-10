import io
import json
import tempfile
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from langchain_core.messages import AIMessageChunk
from rest_framework.test import APIClient

from web.models.character import Character, Voice
from web.models.friend import Friend, Message
from web.models.user import UserProfile
from web.views.friend.message.chat.chat import MessageChatView, ACTIVE_REQUESTS
from web.views.friend.message.asr.asr import ASRView
from web.views.friend.message.memory.update import update_memory
from langchain_core.messages import AIMessage
import websockets


def image_file(name='test.png'):
    data = io.BytesIO()
    Image.new('RGB', (32, 32), '#1877f2').save(data, format='PNG')
    return SimpleUploadedFile(name, data.getvalue(), content_type='image/png')


class FunctionalTests(TestCase):
    """Exercise real local endpoints against an isolated test DB and media directory."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = tempfile.TemporaryDirectory()
        cls.settings_override = override_settings(
            MEDIA_ROOT=cls.media.name, PRIVATE_STORAGE_ROOT=cls.media.name+"/private",
            # Fast hashing only inside the isolated test database.
            PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        cls.media.cleanup()
        super().tearDownClass()

    def setUp(self):
        # Local credentials must never leak into protocol fixtures or missing-config tests.
        provider_names = ['API_KEY', 'API_BASE', 'WSS_URL', 'AI_API_KEY', 'AI_BASE_URL',
                          'AI_MODEL', 'ASR_API_KEY', 'ASR_WSS_URL', 'TTS_API_KEY',
                          'TTS_WSS_URL', 'MEMORY_MODEL', 'MEMORY_AUTO_UPDATE',
                          'ENABLE_LEGACY_KNOWLEDGE', 'VOICE_URL', 'PUBLIC_BASE_URL', 'EMBEDDING_API_KEY', 'EMBEDDING_BASE_URL', 'EMBEDDING_MODEL', 'REQUIRE_CHARACTER_REVIEW']
        provider_env = patch.dict('os.environ', {name: '' for name in provider_names})
        provider_env.start()
        self.addCleanup(provider_env.stop)
        self.client = APIClient()
        self.user = User.objects.create_user('functional_owner', password='Password123!')
        self.profile = UserProfile.objects.create(user=self.user)
        self.other = User.objects.create_user('functional_other', password='Password123!')
        UserProfile.objects.create(user=self.other)
        self.voice = Voice.objects.first()
        self.client.force_authenticate(self.user)

    def create_character(self):
        return Character.objects.create(author=self.profile, name='测试角色', voice=self.voice,
                                        profile='友好的测试角色', public_description='友好的测试角色', persona_prompt='友好的测试角色', photo=image_file(),
                                        background_image=image_file('background.png'))

    def character_payload(self, **kwargs):
        return {'name': '测试角色', 'voice_id': self.voice.id, 'profile': '友好的测试角色',
                'photo': image_file(), 'background_image': image_file('background.png'), 'public_description':'友好的测试角色', 'version':1, **kwargs}

    def test_default_voice_is_available(self):
        data = self.client.get('/api/create/character/voice/get_list/').json()
        self.assertEqual(data['result'], 'success')
        self.assertTrue(data['voices'])

    def test_register_success_and_refresh_cookie(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/user/account/register/', {'username': 'new_account',
                                   'password': 'Password123!', 'password_confirm': 'Password123!'})
        self.assertEqual(response.json()['result'], 'success')
        self.assertTrue(response.json()['access'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])

    def test_register_rejects_duplicate(self):
        data = self.client.post('/api/user/account/register/', {'username': self.user.username,
                                'password': 'Password123!', 'password_confirm': 'Password123!'}).json()
        self.assertEqual(data['result'], '用户名已存在')

    def test_register_rejects_empty_short_and_mismatch(self):
        for username, password, confirm in [('', 'Password123!', 'Password123!'),
                                            ('short', '123', '123'), ('mismatch', 'Password123!', 'wrong')]:
            with self.subTest(username=username):
                data = self.client.post('/api/user/account/register/', {'username': username,
                                        'password': password, 'password_confirm': confirm}).json()
                self.assertNotEqual(data['result'], 'success')

    def test_password_spaces_are_preserved(self):
        password = ' Password123! '
        self.client.post('/api/user/account/register/', {'username': 'spaces', 'password': password,
                         'password_confirm': password})
        self.assertTrue(User.objects.get(username='spaces').check_password(password))

    def test_login_and_bad_password(self):
        self.client.force_authenticate(None)
        for password, success in [('bad', False), ('Password123!', True)]:
            data = self.client.post('/api/user/account/login/', {'username': self.user.username,
                                    'password': password}).json()
            self.assertEqual(data['result'] == 'success', success)

    def test_refresh_and_authenticated_user_info(self):
        self.client.force_authenticate(None)
        self.client.post('/api/user/account/login/', {'username': self.user.username, 'password': 'Password123!'})
        refreshed = self.client.post('/api/user/account/refresh_token/').json()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + refreshed['access'])
        data = self.client.get('/api/user/account/get_user_info/').json()
        self.assertEqual(data['user_id'], self.user.id)

    def test_logout_removes_refresh_cookie(self):
        self.client.force_authenticate(None)
        data = self.client.post('/api/user/account/login/', {'username': self.user.username, 'password': 'Password123!'}).json()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + data['access'])
        response = self.client.post('/api/user/account/logout/')
        self.assertEqual(response.cookies['refresh_token']['max-age'], 0)
        self.assertEqual(self.client.post('/api/user/account/refresh_token/').status_code, 401)

    def test_anonymous_cannot_mutate(self):
        self.client.force_authenticate(None)
        for url in ['/api/create/character/create/', '/api/user/profile/update/',
                    '/api/friend/get_or_create/', '/api/create/character/remove/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {}).status_code, 401)

    def test_create_character_with_images(self):
        data = self.client.post('/api/create/character/create/', self.character_payload(), format='multipart').json()
        self.assertEqual(data['result'], 'success')
        self.assertEqual(Character.objects.get().author, self.profile)

    def test_create_rejects_missing_fields(self):
        for field in ['name', 'profile', 'photo', 'background_image']:
            payload = self.character_payload()
            del payload[field]
            with self.subTest(field=field):
                data = self.client.post('/api/create/character/create/', payload, format='multipart').json()
                self.assertNotEqual(data['result'], 'success')
        self.assertEqual(Character.objects.count(), 0)

    def test_create_rejects_invalid_voice(self):
        data = self.client.post('/api/create/character/create/', self.character_payload(voice_id=999999), format='multipart').json()
        self.assertEqual(data['result'], '请选择有效音色')

    def test_create_rejects_oversized_name(self):
        data = self.client.post('/api/create/character/create/', self.character_payload(name='长' * 51), format='multipart').json()
        self.assertNotEqual(data['result'], 'success')

    def test_edit_without_reuploading_images(self):
        c = self.create_character()
        photo = c.photo.name
        data = self.client.post('/api/create/character/update/', {'character_id': c.id, 'name': '更新角色',
                                'profile': '更新介绍', 'voice_id': self.voice.id, 'version':c.version}).json()
        self.assertEqual(data['result'], 'success')
        c.refresh_from_db()
        self.assertEqual(c.name, '更新角色')
        self.assertEqual(c.photo.name, photo)

    def test_edit_images(self):
        c = self.create_character()
        old = c.photo.name
        data = self.client.post('/api/create/character/update/', self.character_payload(character_id=c.id), format='multipart').json()
        self.assertEqual(data['result'], 'success')
        c.refresh_from_db()
        self.assertNotEqual(c.photo.name, old)

    def test_other_user_cannot_edit_read_editor_or_delete(self):
        c = self.create_character()
        self.client.force_authenticate(self.other)
        self.assertNotEqual(self.client.get('/api/create/character/get_single/', {'character_id': c.id}).json()['result'], 'success')
        for url in ['/api/create/character/update/', '/api/create/character/remove/']:
            self.assertNotEqual(self.client.post(url, self.character_payload(character_id=c.id), format='multipart').json()['result'], 'success')
        self.assertTrue(Character.objects.filter(id=c.id).exists())

    def test_owner_can_archive_character_and_preserve_friend(self):
        c = self.create_character()
        Friend.objects.create(me=self.profile, character=c)
        self.assertEqual(self.client.post('/api/create/character/remove/', {'character_id': c.id, 'version':c.version}).json()['result'], 'success')
        c.refresh_from_db()
        self.assertEqual(c.status, 'archived')
        self.assertEqual(Character.objects.count(), 1)
        self.assertEqual(Friend.objects.count(), 1)

    def test_discovery_search_and_pagination(self):
        self.create_character()
        for query, count in [('测试', 1), ('友好', 1), ('不存在', 0)]:
            data = self.client.get('/api/homepage/index/', {'search_query': query, 'items_count': 0}).json()
            self.assertEqual(len(data['characters']), count)
        self.assertEqual(self.client.get('/api/homepage/index/', {'items_count': 1}).json()['characters'], [])

    def test_profile_and_character_list(self):
        self.create_character()
        data = self.client.get('/api/create/character/get_list/', {'items_count': 0, 'user_id': self.user.id}).json()
        self.assertEqual(data['user_profile']['user_id'], self.user.id)
        self.assertEqual(len(data['characters']), 1)

    def test_update_user_profile(self):
        data = self.client.post('/api/user/profile/update/', {'username': 'updated_name', 'profile': '新的简介', 'photo': image_file()}, format='multipart').json()
        self.assertEqual(data['result'], 'success')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile, '新的简介')

    def test_profile_rejects_duplicate_and_empty(self):
        for username, profile in [(self.other.username, '简介'), ('', '简介'), ('new_name', '')]:
            data = self.client.post('/api/user/profile/update/', {'username': username, 'profile': profile}).json()
            self.assertNotEqual(data['result'], 'success')

    def test_friend_create_is_idempotent_and_listed(self):
        c = self.create_character()
        ids = [self.client.post('/api/friend/get_or_create/', {'character_id': c.id}).json()['friend']['id'] for _ in range(2)]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(len(self.client.get('/api/friend/get_list/', {'items_count': 0}).json()['friends']), 1)

    def test_friend_ownership_and_remove(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        self.client.force_authenticate(self.other)
        self.assertNotEqual(self.client.post('/api/friend/remove/', {'friend_id': friend.id}).json()['result'], 'success')
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/friend/remove/', {'friend_id': friend.id}).json()['result'], 'success')

    def test_history_pagination_and_isolation(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        for i in range(12):
            Message.objects.create(friend=friend, user_message=str(i), input='[]', output='reply')
        first = self.client.get('/api/friend/message/get_history/', {'friend_id': friend.id, 'last_message_id': 0}).json()['messages']
        second = self.client.get('/api/friend/message/get_history/', {'friend_id': friend.id, 'last_message_id': first[-1]['id']}).json()['messages']
        self.assertEqual((len(first), len(second)), (10, 2))
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/friend/message/get_history/', {'friend_id': friend.id, 'last_message_id': 0}).json()['messages'], [])

    @patch.dict('os.environ', {'API_KEY': '', 'API_BASE': '', 'WSS_URL': ''})
    def test_ai_and_asr_report_missing_configuration(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        response = self.client.post('/api/friend/message/chat/', {'friend_id': friend.id, 'message': '你好'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('尚未配置', response.json()['result'])
        response = self.client.post('/api/friend/message/asr/asr/', {'audio': SimpleUploadedFile('voice.pcm', b'\x00\x00')}, format='multipart')
        self.assertEqual(response.status_code, 503)

    def test_asr_rejects_missing_audio(self):
        self.assertEqual(self.client.post('/api/friend/message/asr/asr/').json()['result'], '音频不存在')

    @patch.dict('os.environ', {'WSS_URL': ''})
    def test_text_stream_persists_history_without_tts(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        class FakeGraph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='你好'), {}
                yield AIMessageChunk(content='，朋友'), {}
        stream = ''.join(MessageChatView().event_stream(FakeGraph(), {'messages': []}, friend, 'hello'))
        self.assertIn('[DONE]', stream)
        self.assertEqual(Message.objects.get().output, '你好，朋友')

    @patch.dict('os.environ', {'WSS_URL': ''})
    def test_provider_failure_is_saved_as_failed_status(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        class FailingGraph:
            async def astream(self, inputs, stream_mode):
                raise RuntimeError('provider unavailable')
                yield
        stream = ''.join(MessageChatView().event_stream(FailingGraph(), {'messages': []}, friend, 'hello'))
        self.assertIn('error', stream)
        self.assertNotIn('[DONE]', stream)
        self.assertEqual(Message.objects.get().status, 'failed')
        self.assertEqual(Message.objects.filter(status='completed').count(), 0)

    @patch.dict('os.environ', {'AI_API_KEY': 'test-secret', 'AI_BASE_URL': 'http://localhost/v1', 'AI_MODEL': 'test-model'})
    def test_capabilities_do_not_claim_verified_or_expose_secrets(self):
        data = self.client.get('/api/capabilities/').json()
        self.assertTrue(data['capabilities']['ai']['configured'])
        self.assertFalse(data['capabilities']['ai']['verified'])
        self.assertNotIn('test-secret', json.dumps(data))

    def test_full_text_persisted_without_truncation(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        class Graph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='长' * 1500), {}
        stream = ''.join(MessageChatView().event_stream(Graph(), {'messages': []}, friend, '问' * 2000))
        self.assertIn('[DONE]', stream)
        self.assertEqual(len(Message.objects.get().output), 1500)
        self.assertEqual(len(Message.objects.get().user_message), 2000)

    def test_completed_request_replays_without_second_provider_call(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        Message.objects.create(friend=friend, user_message='hello', output='saved', input='[]', request_id='retry-one')
        with patch('web.views.friend.message.chat.chat.ChatGraph.create_app') as create:
            response = self.client.post('/api/friend/message/chat/', {'friend_id': friend.id, 'message': 'hello', 'request_id': 'retry-one'})
            stream = b''.join(response.streaming_content).decode()
            self.assertIn('saved', stream)
            create.assert_not_called()
        conflict = self.client.post('/api/friend/message/chat/', {'friend_id': friend.id, 'message': 'different', 'request_id': 'retry-one'})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(Message.objects.count(), 1)

    def test_memory_ownership_and_conflicting_edits(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        data = self.client.get('/api/friend/memory/', {'friend_id': friend.id}).json()
        self.assertEqual(data['version'], 0)
        self.assertEqual(self.client.post('/api/friend/memory/', {'friend_id': friend.id, 'memory': '喜欢音乐', 'version': 0}, format='json').status_code, 200)
        self.assertEqual(self.client.post('/api/friend/memory/', {'friend_id': friend.id, 'memory': '旧编辑', 'version': 0}, format='json').status_code, 409)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/friend/memory/', {'friend_id': friend.id}).status_code, 404)
        self.assertEqual(self.client.post('/api/friend/memory/', {'friend_id': friend.id, 'memory': '', 'version': 1}, format='json').status_code, 404)

    def test_memory_clear_cannot_be_restored_by_stale_summary(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character(), memory='old')
        class Graph:
            def invoke(self, inputs):
                self_response = self_client.post('/api/friend/memory/', {'friend_id': friend.id, 'memory': '', 'version': 0}, format='json')
                assert self_response.status_code == 200
                return {'messages': [AIMessage(content='stale generated memory')]}
        self_client = self.client
        with patch('web.views.friend.message.memory.update.MemoryGraph.create_app', return_value=Graph()):
            update_memory(friend)
        friend.refresh_from_db()
        self.assertEqual(friend.memory, '')
        self.assertEqual(friend.memory_version, 1)

    def test_cancel_request_is_scoped_to_user(self):
        stop = threading.Event()
        key = (self.user.id, 'running')
        ACTIVE_REQUESTS[key] = {'stop': stop, 'friend_id': 999}
        try:
            self.client.force_authenticate(self.other)
            self.client.post('/api/friend/message/cancel/', {'request_id': 'running'})
            self.assertFalse(stop.is_set())
            self.client.force_authenticate(self.user)
            self.client.post('/api/friend/message/cancel/', {'request_id': 'running'})
            self.assertTrue(stop.is_set())
        finally:
            ACTIVE_REQUESTS.pop(key, None)

    def test_cancelled_generation_is_saved_with_status(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        stop = threading.Event()
        class Graph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='partial'), {}
                stop.set()
                await asyncio.sleep(.2)
        stream = ''.join(MessageChatView().event_stream(Graph(), {'messages': []}, friend, 'hello', stop=stop))
        self.assertNotIn('[DONE]', stream)
        self.assertEqual(Message.objects.get().status, 'cancelled')
        self.assertEqual(Message.objects.filter(status='completed').count(), 0)

    @patch.dict('os.environ', {'TTS_API_KEY': 'test', 'TTS_WSS_URL': 'ws://127.0.0.1:1', 'TTS_MODEL': 'test'})
    def test_voice_failure_keeps_successful_text_reply(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        class Graph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='text survives'), {}
        stream = ''.join(MessageChatView().event_stream(Graph(), {'messages': []}, friend, 'hello', enable_audio=True))
        self.assertIn('warning', stream)
        self.assertIn('[DONE]', stream)
        self.assertEqual(Message.objects.get().output, 'text survives')

    @patch.dict('os.environ', {'ASR_API_KEY': 'test', 'ASR_WSS_URL': 'ws://test', 'ASR_MODEL': 'test'})
    def test_asr_rejects_empty_transcript_and_invalid_pcm(self):
        with patch.object(ASRView, 'run_asr_tasks', return_value=''):
            response = self.client.post('/api/friend/message/asr/asr/', {'audio': SimpleUploadedFile('a.pcm', b'\0\0')}, format='multipart')
            self.assertEqual(response.status_code, 422)
        response = self.client.post('/api/friend/message/asr/asr/', {'audio': SimpleUploadedFile('a.pcm', b'\0')}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_asr_websocket_protocol_success_and_failure(self):
        async def run(fail):
            async def handler(ws):
                payload = json.loads(await ws.recv())
                self.assertEqual(payload['payload']['model'], 'protocol-asr')
                if fail:
                    await ws.send(json.dumps({'header': {'event': 'task-failed'}}))
                    return
                await ws.send(json.dumps({'header': {'event': 'task-started'}}))
                async for msg in ws:
                    if isinstance(msg, str):
                        await ws.send(json.dumps({'header': {'event': 'result-generated'}, 'payload': {'output': {'transcription': {'sentence_end': True, 'text': '协议测试'}}}}))
                        await ws.send(json.dumps({'header': {'event': 'task-finished'}}))
                        break
            async with websockets.serve(handler, '127.0.0.1', 0) as server:
                port = server.sockets[0].getsockname()[1]
                with patch.dict('os.environ', {'ASR_API_KEY': 'test', 'ASR_MODEL': 'protocol-asr', 'ASR_WSS_URL': f'ws://127.0.0.1:{port}'}):
                    if fail:
                        with self.assertRaises(RuntimeError):
                            await ASRView().run_asr_tasks(b'\0\0')
                    else:
                        self.assertEqual(await ASRView().run_asr_tasks(b'\0\0'), '协议测试')
        asyncio.run(run(False))
        asyncio.run(run(True))

    def test_real_sdk_against_local_openai_protocol_fixture(self):
        from web.views.friend.message.chat.graph import ChatGraph
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for text, finish in [('协议回复', None), ('', 'stop')]:
                    chunk = {'id': 'chatcmpl-test', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'protocol-model', 'choices': [{'index': 0, 'delta': {'content': text}, 'finish_reason': finish}]}
                    self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict('os.environ', {'AI_API_KEY': 'fixture-only', 'AI_BASE_URL': f'http://127.0.0.1:{server.server_port}/v1', 'AI_MODEL': 'protocol-model', 'AI_ENABLE_TOOLS': 'false'}):
                friend = Friend.objects.create(me=self.profile, character=self.create_character())
                response = self.client.post('/api/friend/message/chat/', {'friend_id': friend.id, 'message': '协议验证', 'request_id': 'sdk-test'}, format='json')
                self.assertEqual(response.status_code, 200)
                stream = b''.join(response.streaming_content).decode()
                self.assertIn('[DONE]', stream)
                self.assertEqual(Message.objects.get().output, '协议回复')
                self.assertEqual(captured[0]['model'], 'protocol-model')
                self.assertTrue(captured[0]['stream'])
                self.assertFalse(ACTIVE_REQUESTS)
        finally:
            server.shutdown()
            server.server_close()

    def test_tts_websocket_protocol_transmits_text_and_audio(self):
        from queue import Queue
        queue = Queue()
        received = []
        class Graph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='播报测试'), {}
        async def run():
            async def handler(ws):
                start = json.loads(await ws.recv())
                self.assertEqual(start['payload']['model'], 'protocol-tts')
                await ws.send(json.dumps({'header': {'event': 'task-started'}}))
                async for raw in ws:
                    data = json.loads(raw)
                    if data['header']['action'] == 'continue-task':
                        received.append(data['payload']['input']['text'])
                        await ws.send(b'fixture-audio-bytes')
                    elif data['header']['action'] == 'finish-task':
                        await ws.send(json.dumps({'header': {'event': 'task-finished'}}))
                        break
            async with websockets.serve(handler, '127.0.0.1', 0) as server:
                port = server.sockets[0].getsockname()[1]
                with patch.dict('os.environ', {'TTS_API_KEY': 'test', 'TTS_MODEL': 'protocol-tts', 'TTS_WSS_URL': f'ws://127.0.0.1:{port}'}):
                    await MessageChatView().run_tts_tasks(Graph(), {}, queue, 'test-voice')
        asyncio.run(run())
        self.assertEqual(received, ['播报测试'])
        values = []
        while not queue.empty():
            values.append(queue.get_nowait())
        self.assertTrue(any('audio' in item for item in values))

    @patch.dict('os.environ', {'AI_API_KEY': 'test', 'AI_BASE_URL': 'http://test/v1', 'AI_MODEL': 'test'})
    def test_response_closed_before_iteration_releases_active_request(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        with patch('web.views.friend.message.chat.chat.ChatGraph.create_app'):
            response = self.client.post('/api/friend/message/chat/', {'friend_id': friend.id, 'message': 'hello', 'request_id': 'never-read'}, format='json')
            self.assertIn((self.user.id, 'never-read'), ACTIVE_REQUESTS)
            response.close()
            self.assertNotIn((self.user.id, 'never-read'), ACTIVE_REQUESTS)

    def test_chat_memory_and_cancel_reject_malformed_identifiers(self):
        self.assertEqual(self.client.post('/api/friend/message/chat/', {'friend_id': ['bad'], 'message': 'hello'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/friend/message/cancel/', {'request_id': ['bad']}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/friend/memory/', {'friend_id': 'bad'}).status_code, 400)
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        for version in [True, '0']:
            self.assertEqual(self.client.post('/api/friend/memory/', {'friend_id': friend.id, 'memory': '', 'version': version}, format='json').status_code, 400)

    @patch.dict('os.environ', {'ASR_API_KEY': 'test', 'ASR_WSS_URL': 'ws://test', 'ASR_MODEL': 'test'})
    def test_asr_timeout_has_recoverable_error(self):
        with patch.object(ASRView, 'run_asr_tasks', side_effect=TimeoutError):
            response = self.client.post('/api/friend/message/asr/asr/', {'audio': SimpleUploadedFile('a.pcm', b'\0\0')}, format='multipart')
            self.assertEqual(response.status_code, 504)
            self.assertIn('超时', response.json()['result'])

    def test_requested_tts_without_configuration_warns_and_preserves_text(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        class Graph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='文字仍然可用'), {}
        stream = ''.join(MessageChatView().event_stream(Graph(), {'messages': []}, friend,
                                                      'hello', enable_audio=True))
        self.assertIn('语音播报暂不可用', stream)
        self.assertIn('[DONE]', stream)
        self.assertEqual(Message.objects.get().output, '文字仍然可用')

    def test_login_ignores_stale_access_token(self):
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired-or-invalid-token')
        response = self.client.post('/api/user/account/login/',
                                    {'username': self.user.username, 'password': 'Password123!'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], 'success')
        self.assertTrue(response.json()['access'])

    def test_register_ignores_stale_access_token_and_can_login(self):
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired-or-invalid-token')
        payload = {'username': 'stale_token_signup', 'password': 'Password123!',
                   'password_confirm': 'Password123!'}
        response = self.client.post('/api/user/account/register/', payload)
        self.assertEqual(response.json()['result'], 'success')
        new_user = User.objects.get(username=payload['username'])
        self.assertTrue(UserProfile.objects.filter(user=new_user).exists())
        response = self.client.post('/api/user/account/login/', payload)
        self.assertEqual(response.json()['result'], 'success')

    def test_refresh_uses_cookie_even_with_stale_access_header(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired-or-invalid-token')
        self.client.cookies['refresh_token'] = str(RefreshToken.for_user(self.user))
        response = self.client.post('/api/user/account/refresh_token/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['access'])
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/user/account/refresh_token/').status_code, 401)
        self.assertEqual(self.client.get('/api/user/account/get_user_info/').status_code, 401)

    def test_voice_catalog_has_multiple_compatible_options(self):
        response = self.client.get('/api/create/character/voice/get_list/').json()
        self.assertGreaterEqual(len(response['voices']), 7)
        self.assertTrue(all(item['description'] for item in response['voices']))
        with patch.dict('os.environ', {'TTS_MODEL':'custom-other-model'}):
            ids = [v['id'] for v in self.client.get('/api/create/character/voice/get_list/').json()['voices']]
            self.assertNotIn(Voice.objects.get(voice_id='longxiaochun_v3').id, ids)

    def test_nondefault_voice_is_saved_and_restored_when_editing(self):
        voice = Voice.objects.get(voice_id='longxiaochun_v3')
        response = self.client.post('/api/create/character/create/', self.character_payload(voice_id=voice.id), format='multipart')
        self.assertEqual(response.json()['result'], 'success')
        character = Character.objects.get(author=self.profile)
        self.assertEqual(character.voice_id, voice.id)
        next_voice = Voice.objects.get(voice_id='longanwen_v3')
        response = self.client.post('/api/create/character/update/',
            {'character_id':character.id,'name':character.name,'profile':character.profile,'voice_id':next_voice.id,'version':character.version})
        self.assertEqual(response.json()['result'], 'success')
        response = self.client.get('/api/create/character/get_single/', {'character_id':character.id}).json()
        self.assertEqual(response['character']['voice_id'], next_voice.id)
        self.assertGreaterEqual(len(response['voices']),7)

    def test_preview_requires_login_and_valid_voice(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/create/character/voice/preview/', {'voice_id':self.voice.id}).status_code,401)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/create/character/voice/preview/', {'voice_id':'bad'}).status_code,400)
        self.assertEqual(self.client.post('/api/create/character/voice/preview/', {'voice_id':self.voice.id}).status_code,503)

    @patch.dict('os.environ', {'TTS_API_KEY':'test','TTS_WSS_URL':'ws://test','TTS_MODEL':'cosyvoice-v3-flash'})
    def test_preview_uses_selected_provider_voice(self):
        import base64
        voice = Voice.objects.get(voice_id='longanwen_v3')
        async def synthesize(app, inputs, queue, voice_id):
            self.assertEqual(voice_id, voice.voice_id)
            queue.put_nowait({'audio':base64.b64encode(b'test-audio').decode()})
        with patch.object(MessageChatView,'run_tts_tasks',side_effect=synthesize):
            response = self.client.post('/api/create/character/voice/preview/', {'voice_id':voice.id})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Content-Type'],'audio/mpeg')
        self.assertEqual(response.content,b'test-audio')


    def test_new_character_defaults_to_private_draft(self):
        data = self.client.post('/api/create/character/create/', self.character_payload(), format='multipart').json()
        c = Character.objects.get(pk=data['character']['id'])
        self.assertEqual((c.status,c.visibility),('draft','private'))
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/homepage/index/').json()['characters'],[])
        self.assertEqual(self.client.post('/api/friend/get_or_create/',{'character_id':c.id}).status_code,404)

    def test_published_role_does_not_expose_persona(self):
        c=self.create_character()
        c.public_description='面向公众的简介'
        c.persona_prompt='不可公开的内部设定'
        c.profile='不可公开的原始设定'
        c.save()
        self.client.force_authenticate(self.other)
        data=self.client.get('/api/homepage/index/').json()['characters'][0]
        self.assertEqual(data['profile'],'面向公众的简介')
        self.assertNotIn('不可公开',json.dumps(data,ensure_ascii=False))
        self.assertEqual(self.client.get('/api/homepage/index/',{'search_query':'不可公开'}).json()['characters'],[])

    def test_character_version_conflict_does_not_overwrite(self):
        c=self.create_character()
        payload={'character_id':c.id,'name':'新版','profile':'设定','voice_id':self.voice.id,'version':1}
        self.assertEqual(self.client.post('/api/create/character/update/',payload).status_code,200)
        payload['name']='旧页面'
        self.assertEqual(self.client.post('/api/create/character/update/',payload).status_code,409)
        c.refresh_from_db()
        self.assertEqual(c.name,'新版')
        self.assertEqual(c.version,2)

    def test_archive_restore_preserves_history_and_restores_private_draft(self):
        c=self.create_character()
        friend=Friend.objects.create(character=c,me=self.profile)
        Message.objects.create(friend=friend,user_message='旧消息',output='旧回复',input='[]')
        self.assertEqual(self.client.post('/api/create/character/remove/',{'character_id':c.id,'version':1}).status_code,200)
        self.assertEqual(self.client.post('/api/friend/get_or_create/',{'character_id':c.id}).status_code,404)
        self.assertEqual(len(self.client.get('/api/friend/message/get_history/',{'friend_id':friend.id,'last_message_id':0}).json()['messages']),1)
        self.assertEqual(self.client.post('/api/create/character/restore/',{'character_id':c.id,'version':2}).status_code,200)
        c.refresh_from_db()
        self.assertEqual((c.status,c.visibility,c.version),('draft','private',3))
        self.assertEqual(Message.objects.count(),1)

    def test_friend_archive_reopening_restores_same_history(self):
        c=self.create_character()
        f=Friend.objects.create(character=c,me=self.profile)
        Message.objects.create(friend=f,user_message='内容',output='回复',input='[]')
        self.client.post('/api/friend/remove/',{'friend_id':f.id})
        self.assertEqual(self.client.get('/api/friend/get_list/').json()['friends'],[])
        reopened=self.client.post('/api/friend/get_or_create/',{'character_id':c.id}).json()['friend']
        self.assertEqual(reopened['id'],f.id)
        self.assertEqual(Message.objects.count(),1)

    def test_invalid_image_rejected_before_replacing_existing_file(self):
        c=self.create_character()
        original=c.photo.name
        fake=SimpleUploadedFile('fake.png',b'not an image',content_type='image/png')
        payload=self.character_payload(character_id=c.id,photo=fake)
        self.assertEqual(self.client.post('/api/create/character/update/',payload,format='multipart').status_code,400)
        c.refresh_from_db()
        self.assertEqual(c.photo.name,original)
        self.assertTrue(c.photo.storage.exists(original))

    def test_knowledge_index_and_cross_character_isolation(self):
        from web.services.jobs import run_one
        from web.services.knowledge import search_knowledge
        from web.models.resources import KnowledgeDocument, BackgroundJob
        c=self.create_character()
        upload=SimpleUploadedFile('指南.md','星光咖啡馆营业时间是每天九点至十八点。'.encode())
        response=self.client.post('/api/knowledge/documents/',{'character_id':c.id,'file':upload},format='multipart')
        self.assertEqual(response.status_code,202)
        self.assertTrue(run_one())
        doc=KnowledgeDocument.objects.get()
        self.assertEqual(doc.status,'ready')
        self.assertEqual(BackgroundJob.objects.get().status,'completed')
        matches=search_knowledge(c,'星光咖啡馆营业时间')
        self.assertEqual(matches[0]['name'],'指南.md')
        another=self.create_character()
        self.assertEqual(search_knowledge(another,'星光咖啡馆营业时间'),[])
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/knowledge/documents/',{'character_id':c.id}).status_code,404)
        self.assertEqual(self.client.delete('/api/knowledge/documents/',{'document_id':doc.id},format='json').status_code,404)
        self.assertEqual(self.client.get('/api/jobs/').json()['jobs'],[])

    def test_knowledge_duplicate_and_deletion_remove_index(self):
        from web.services.jobs import run_one
        from web.models.resources import KnowledgeDocument, KnowledgeChunk
        from web.services.knowledge import search_knowledge
        c=self.create_character()
        def upload():
            return self.client.post('/api/knowledge/documents/',{'character_id':c.id,'file':SimpleUploadedFile('a.txt','苹果知识内容'.encode())},format='multipart')
        self.assertFalse(upload().json()['duplicate'])
        self.assertTrue(upload().json()['duplicate'])
        self.assertEqual(KnowledgeDocument.objects.count(),1)
        run_one()
        self.assertTrue(KnowledgeChunk.objects.exists())
        did=KnowledgeDocument.objects.get().id
        self.assertEqual(self.client.delete('/api/knowledge/documents/',{'document_id':did},format='json').status_code,200)
        self.assertFalse(KnowledgeChunk.objects.exists())
        self.assertEqual(search_knowledge(c,'苹果'),[])

    def test_knowledge_rejects_wrong_type_encoding_empty_and_oversize(self):
        c=self.create_character()
        for name,raw in [('a.pdf',b'pdf'),('a.txt',b'\xff'),('empty.md',b' '),('large.txt',b'a'*(1024*1024+1))]:
            with self.subTest(name=name):
                response=self.client.post('/api/knowledge/documents/',{'character_id':c.id,'file':SimpleUploadedFile(name,raw)},format='multipart')
                self.assertEqual(response.status_code,400)

    def test_durable_memory_job_respects_disabled_and_stale_version(self):
        from web.services.jobs import enqueue_memory, run_one
        from web.models.resources import BackgroundJob
        f=Friend.objects.create(character=self.create_character(),me=self.profile,memory='保留')
        enqueue_memory(f)
        f.memory_enabled=False;f.memory_version=1;f.save()
        with patch('web.views.friend.message.memory.update.MemoryGraph.create_app') as provider:
            run_one()
            provider.assert_not_called()
        self.assertEqual(BackgroundJob.objects.get().status,'completed')
        f.refresh_from_db();self.assertEqual(f.memory,'保留')

    def test_memory_toggle_stops_prompt_usage(self):
        from web.views.friend.message.chat.chat import add_system_prompt
        f=Friend.objects.create(character=self.create_character(),me=self.profile,memory='私有记忆')
        response=self.client.post('/api/friend/memory/',{'friend_id':f.id,'memory':'私有记忆','enabled':False,'version':0},format='json')
        self.assertEqual(response.status_code,200)
        f.refresh_from_db()
        self.assertNotIn('私有记忆',add_system_prompt({'messages':[]},f)['messages'][0].content)
        self.assertFalse(self.client.get('/api/friend/memory/',{'friend_id':f.id}).json()['enabled'])

    @patch.dict('os.environ', {'TTS_API_KEY':'test','TTS_WSS_URL':'ws://test','TTS_MODEL':'cosyvoice-v3-flash'})
    def test_audio_is_persisted_and_only_owner_can_replay(self):
        import base64
        f=Friend.objects.create(character=self.create_character(),me=self.profile)
        class Graph:
            async def astream(self,inputs,stream_mode):
                yield AIMessageChunk(content='语音文字'),{}
        async def speech(app,inputs,queue,voice):
            queue.put_nowait({'audio':base64.b64encode(b'fixture-mp3').decode()})
        with patch.object(MessageChatView,'run_tts_tasks',side_effect=speech):
            stream=''.join(MessageChatView().event_stream(Graph(),{'messages':[]},f,'你好',enable_audio=True))
        self.assertIn('[DONE]',stream)
        m=Message.objects.get()
        self.assertTrue(m.audio)
        response=self.client.get(f'/api/friend/message/{m.id}/audio/')
        self.assertEqual(b''.join(response.streaming_content),b'fixture-mp3')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'/api/friend/message/{m.id}/audio/').status_code,404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/friend/message/{m.id}/audio/').status_code,401)

    def test_custom_voice_not_visible_to_other_user_or_selectable_before_ready(self):
        voice=Voice.objects.create(owner=self.profile,name='个人声音',voice_id='personal-provider',kind='custom',status='ready')
        self.assertIn(voice.id,[v['id'] for v in self.client.get('/api/create/character/voice/get_list/').json()['voices']])
        self.client.force_authenticate(self.other)
        self.assertNotIn(voice.id,[v['id'] for v in self.client.get('/api/create/character/voice/get_list/').json()['voices']])
        self.assertEqual(self.client.post('/api/create/character/create/',self.character_payload(voice_id=voice.id),format='multipart').status_code,400)
        self.client.force_authenticate(self.user)
        voice.status='preparing';voice.save()
        self.assertNotIn(voice.id,[v['id'] for v in self.client.get('/api/create/character/voice/get_list/').json()['voices']])

    def test_clone_requires_authorization_and_public_configuration(self):
        self.assertEqual(self.client.post('/api/voices/custom/',{'name':'测试','authorized':False}).status_code,400)
        self.assertEqual(self.client.post('/api/voices/custom/',{'name':'测试','authorized':True},format='json').status_code,503)

    @patch.dict('os.environ', {'TTS_API_KEY':'test','VOICE_URL':'https://provider.test/enrollment','PUBLIC_BASE_URL':'https://app.test'})
    def test_clone_wav_validation_signed_sample_and_successful_job(self):
        from web.services.jobs import run_one
        from web.models.resources import BackgroundJob
        data=io.BytesIO()
        with __import__('wave').open(data,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\x88\x13'*16000*10)
        response=self.client.post('/api/voices/custom/',{'name':'自定义温柔声','authorized':'true','sample':SimpleUploadedFile('sample.wav',data.getvalue())},format='multipart')
        self.assertEqual(response.status_code,202)
        v=Voice.objects.get(pk=response.json()['voice_id'])
        self.assertEqual(v.status,'preparing')
        captured=[]
        def provider(action,**kwargs):
            captured.append((action,kwargs))
            if action=='create_voice':
                from urllib.parse import urlsplit
                sample=self.client.get(urlsplit(kwargs['url']).path+'?'+urlsplit(kwargs['url']).query)
                self.assertEqual(sample.status_code,200)
                self.assertEqual(b''.join(sample.streaming_content),data.getvalue())
                return {'voice_id':'clone-provider-id'}
            return {'status':'OK'}
        with patch('web.services.jobs.enrollment',side_effect=provider):
            run_one()
        v.refresh_from_db()
        self.assertEqual((v.status,v.voice_id),('ready','clone-provider-id'))
        self.assertEqual(BackgroundJob.objects.get().status,'completed')
        self.assertEqual(self.client.get('/api/voice/sample/',{'token':'invalid'}).status_code,404)

    @patch.dict('os.environ', {'TTS_API_KEY':'test','VOICE_URL':'https://provider.test','PUBLIC_BASE_URL':'https://app.test'})
    def test_clone_rejects_invalid_sample(self):
        response=self.client.post('/api/voices/custom/',{'name':'声音','authorized':'true','sample':SimpleUploadedFile('fake.wav',b'fake')},format='multipart')
        self.assertEqual(response.status_code,400)

    def test_referenced_custom_voice_cannot_be_deleted(self):
        v=Voice.objects.create(owner=self.profile,name='声音',voice_id='custom',kind='custom',status='ready')
        c=self.create_character();c.voice=v;c.save()
        self.assertEqual(self.client.delete('/api/voices/custom/',{'voice_id':v.id},format='json').status_code,409)
        self.assertTrue(Character.objects.filter(pk=c.id).exists())

    def test_uncertain_voice_submission_never_creates_duplicate(self):
        from web.models.resources import BackgroundJob
        from web.services.jobs import run_one
        v=Voice.objects.create(owner=self.profile,name='未确认',voice_id='',kind='custom',status='preparing')
        j=BackgroundJob.objects.create(owner=self.profile,kind='voice',object_id=v.id,dedupe_key='uncertain-test',payload={'uncertain':True})
        with patch('web.services.jobs.enrollment') as provider:
            run_one();provider.assert_not_called()
        j.refresh_from_db();self.assertEqual(j.status,'failed')
        self.assertEqual(self.client.post('/api/jobs/',{'job_id':j.id},format='json').status_code,409)

    def test_report_feedback_is_scoped_to_reporter(self):
        from web.models.resources import Report
        c=self.create_character()
        response=self.client.post('/api/reports/',{'character_id':c.id,'reason':'不适当内容'})
        self.assertEqual(response.status_code,201)
        report=Report.objects.get();report.status='resolved';report.resolution='已处理';report.save()
        self.assertEqual(self.client.get('/api/reports/').json()['reports'][0]['resolution'],'已处理')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/reports/').json()['reports'],[])

    def test_stale_unknown_api_returns_404_instead_of_spa_html(self):
        self.assertEqual(self.client.get('/api/does-not-exist/').status_code,404)

    def test_rotated_refresh_token_and_logout_revoke_previous_cookie(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        token=str(RefreshToken.for_user(self.user))
        self.client.force_authenticate(None)
        self.client.cookies['refresh_token']=token
        response=self.client.post('/api/user/account/refresh_token/')
        self.assertEqual(response.status_code,200)
        with self.assertRaises(TokenError):RefreshToken(token)
        rotated=response.cookies['refresh_token'].value
        self.client.force_authenticate(self.user)
        self.client.cookies['refresh_token']=rotated
        self.client.post('/api/user/account/logout/')
        with self.assertRaises(TokenError):RefreshToken(rotated)

    @patch.dict('os.environ', {'AI_API_KEY':'test','AI_BASE_URL':'http://test','AI_MODEL':'test'})
    def test_db_generation_lease_blocks_other_worker_and_cancel_is_owned(self):
        from web.models.resources import GenerationLease
        from django.utils.timezone import now
        from datetime import timedelta
        f=Friend.objects.create(character=self.create_character(),me=self.profile)
        lease=GenerationLease.objects.create(friend=f,request_id='worker-one',expires_at=now()+timedelta(minutes=2))
        with patch('web.views.friend.message.chat.chat.ChatGraph.create_app'):
            response=self.client.post('/api/friend/message/chat/',{'friend_id':f.id,'message':'test','request_id':'worker-two'})
        self.assertEqual(response.status_code,409)
        self.client.force_authenticate(self.other)
        self.client.post('/api/friend/message/cancel/',{'request_id':'worker-one'})
        lease.refresh_from_db();self.assertFalse(lease.cancelled)
        self.client.force_authenticate(self.user)
        self.client.post('/api/friend/message/cancel/',{'request_id':'worker-one'})
        lease.refresh_from_db();self.assertTrue(lease.cancelled)


    def test_fun_asr_sentence_schema_and_gummy_schema_are_compatible(self):
        class Socket:
            def __aiter__(self):
                async def events():
                    for output in [{'sentence':{'text':'中间','sentence_end':False}},
                        {'sentence':{'text':'新的协议','sentence_end':True}},
                        {'transcription':{'text':'旧协议','sentence_end':True}},
                        {'sentence':{'text':'忽略心跳','sentence_end':True,'heartbeat':True}}]:
                        yield json.dumps({'header':{'event':'result-generated'},'payload':{'output':output}})
                    yield json.dumps({'header':{'event':'task-finished'}})
                return events()
        self.assertEqual(asyncio.run(ASRView().asr_receiver(Socket())),'新的协议旧协议')


    @patch.dict('os.environ',{'EMBEDDING_API_KEY':'test','EMBEDDING_BASE_URL':'https://embedding.test/v1','EMBEDDING_MODEL':'embedding-test'})
    def test_hybrid_knowledge_vectors_are_indexed_and_retrieved(self):
        from web.models.resources import KnowledgeDocument, KnowledgeChunk, BackgroundJob
        from web.services.jobs import run_one
        from web.services.knowledge import search_knowledge
        c=self.create_character()
        doc=KnowledgeDocument.objects.create(owner=self.profile,character=c,name='语义资料',sha256='a'*64,content='此地提供咖啡和茶饮。')
        BackgroundJob.objects.create(owner=self.profile,kind='knowledge',object_id=doc.id,dedupe_key='vector-job')
        with patch('web.services.embeddings.embed',return_value=[[1,0]]):run_one()
        doc.refresh_from_db();self.assertEqual(doc.index_mode,'hybrid')
        self.assertEqual(KnowledgeChunk.objects.get().vector,[1,0])
        with patch('web.services.knowledge.embed',return_value=[[1,0]]):
            self.assertEqual(search_knowledge(c,'drink')[0]['document_id'],doc.id)
        with patch('web.services.knowledge.embed',side_effect=RuntimeError):
            self.assertEqual(search_knowledge(c,'咖啡')[0]['document_id'],doc.id)

    def test_staff_health_distinguishes_config_from_success_and_is_private(self):
        from web.models.resources import ServiceObservation, WorkerHeartbeat
        ServiceObservation.objects.create(service='asr',success=True)
        ServiceObservation.objects.create(service='asr',success=False)
        WorkerHeartbeat.objects.create(name='test-worker')
        self.assertEqual(self.client.get('/api/admin/health/').status_code,403)
        self.user.is_staff=True;self.user.save()
        data=self.client.get('/api/admin/health/').json()
        self.assertTrue(data['database']);self.assertTrue(data['worker_alive'])
        self.assertFalse(data['services']['asr']['configured'])
        self.assertEqual(data['services']['asr']['success_count'],1)
        self.assertEqual(data['services']['asr']['failure_count'],1)

    def test_job_retry_limit_ownership_and_crash_recovery(self):
        from web.models.resources import BackgroundJob, KnowledgeDocument
        from web.services.jobs import run_one
        from django.utils.timezone import now
        from datetime import timedelta
        doc=KnowledgeDocument.objects.create(owner=self.profile,character=self.create_character(),name='重试',sha256='b'*64,content='知识内容')
        job=BackgroundJob.objects.create(owner=self.profile,kind='knowledge',object_id=doc.id,dedupe_key='crash-recover',status='running',updated_at=now()-timedelta(minutes=6))
        self.assertTrue(run_one());job.refresh_from_db();self.assertEqual(job.status,'completed')
        job.status='failed';job.attempts=3;job.save()
        self.assertEqual(self.client.post('/api/jobs/',{'job_id':job.id},format='json').status_code,409)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post('/api/jobs/',{'job_id':job.id},format='json').status_code,404)


    @patch.dict('os.environ',{'REQUIRE_CHARACTER_REVIEW':'true'})
    def test_public_publish_can_require_staff_review(self):
        response=self.client.post('/api/create/character/create/',self.character_payload(status='published',visibility='public'),format='multipart')
        self.assertEqual(response.status_code,200)
        c=Character.objects.get(pk=response.json()['character']['id'])
        self.assertEqual(c.status,'reviewing')
        self.assertEqual(self.client.get('/api/homepage/index/').json()['characters'],[])
        c.status='published';c.save()
        self.assertEqual(len(self.client.get('/api/homepage/index/').json()['characters']),1)

    def test_profile_update_database_failure_keeps_previous_details(self):
        from django.db import IntegrityError
        old_profile=self.profile.profile
        with patch('web.views.user.profile.update.User.save',side_effect=IntegrityError('duplicate username')):
            response=self.client.post('/api/user/profile/update/',{'username':'conflicting_name','profile':'不应部分保存'})
        self.assertNotEqual(response.json()['result'],'success')
        self.profile.refresh_from_db();self.user.refresh_from_db()
        self.assertEqual(self.profile.profile,old_profile)
        self.assertEqual(self.user.username,'functional_owner')

    def test_history_rejects_bad_cursor_and_defaults_to_latest(self):
        f=Friend.objects.create(character=self.create_character(),me=self.profile)
        self.assertEqual(self.client.get('/api/friend/message/get_history/',{'friend_id':f.id}).json()['messages'],[])
        self.assertEqual(self.client.get('/api/friend/message/get_history/',{'friend_id':f.id,'last_message_id':'invalid'}).status_code,400)

    def test_completed_chat_replay_keeps_sources_and_private_audio_metadata(self):
        from django.core.files.base import ContentFile
        f=Friend.objects.create(character=self.create_character(),me=self.profile)
        source=[{'document_id':1,'position':2,'name':'资料.md'}]
        message=Message.objects.create(friend=f,user_message='问题',output='答案',request_id='replay-metadata',sources=source)
        message.audio.save('replay.mp3',ContentFile(b'test-audio'))
        with patch('web.views.friend.message.chat.chat.ChatGraph.create_app') as factory:
            response=self.client.post('/api/friend/message/chat/',{'friend_id':f.id,'message':'问题','request_id':'replay-metadata'},format='json')
            stream=b''.join(response.streaming_content).decode()
        factory.assert_not_called()
        payload=json.loads(stream.splitlines()[0][6:])
        self.assertTrue(payload['has_audio']);self.assertEqual(payload['sources'],source)
