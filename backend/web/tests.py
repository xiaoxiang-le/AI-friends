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
            MEDIA_ROOT=cls.media.name,
            # Fast hashing only inside the isolated test database.
            PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        cls.media.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('functional_owner', password='Password123!')
        self.profile = UserProfile.objects.create(user=self.user)
        self.other = User.objects.create_user('functional_other', password='Password123!')
        UserProfile.objects.create(user=self.other)
        self.voice = Voice.objects.first()
        self.client.force_authenticate(self.user)

    def create_character(self):
        return Character.objects.create(author=self.profile, name='测试角色', voice=self.voice,
                                        profile='友好的测试角色', photo=image_file(),
                                        background_image=image_file('background.png'))

    def character_payload(self, **kwargs):
        return {'name': '测试角色', 'voice_id': self.voice.id, 'profile': '友好的测试角色',
                'photo': image_file(), 'background_image': image_file('background.png'), **kwargs}

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
                                'profile': '更新介绍', 'voice_id': self.voice.id}).json()
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

    def test_owner_can_delete_character_and_related_friend(self):
        c = self.create_character()
        Friend.objects.create(me=self.profile, character=c)
        self.assertEqual(self.client.post('/api/create/character/remove/', {'character_id': c.id}).json()['result'], 'success')
        self.assertEqual(Character.objects.count(), 0)
        self.assertEqual(Friend.objects.count(), 0)

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
    def test_provider_failure_is_not_saved_as_empty_reply(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        class FailingGraph:
            async def astream(self, inputs, stream_mode):
                raise RuntimeError('provider unavailable')
                yield
        stream = ''.join(MessageChatView().event_stream(FailingGraph(), {'messages': []}, friend, 'hello'))
        self.assertIn('error', stream)
        self.assertNotIn('[DONE]', stream)
        self.assertEqual(Message.objects.count(), 0)


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


    def test_cancelled_generation_is_not_saved(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        stop = threading.Event()
        class Graph:
            async def astream(self, inputs, stream_mode):
                yield AIMessageChunk(content='partial'), {}
                stop.set()
                await asyncio.sleep(.2)
        stream = ''.join(MessageChatView().event_stream(Graph(), {'messages': []}, friend, 'hello', stop=stop))
        self.assertNotIn('[DONE]', stream)
        self.assertEqual(Message.objects.count(), 0)


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


    @patch.dict('os.environ', {'AI_API_KEY': 'test', 'AI_BASE_URL': 'http://test/v1', 'AI_MODEL': 'test'})
    def test_response_closed_before_iteration_releases_active_request(self):
        friend = Friend.objects.create(me=self.profile, character=self.create_character())
        with patch('web.views.friend.message.chat.chat.ChatGraph.create_app'):
            response = self.client.post('/api/friend/message/chat/', {'friend_id': friend.id, 'message': 'hello', 'request_id': 'never-read'}, format='json')
            self.assertIn((self.user.id, 'never-read'), ACTIVE_REQUESTS)
            response.close()
            self.assertNotIn((self.user.id, 'never-read'), ACTIVE_REQUESTS)


    @patch.dict('os.environ', {'ASR_API_KEY': 'test', 'ASR_WSS_URL': 'ws://test', 'ASR_MODEL': 'test'})
    def test_asr_timeout_has_recoverable_error(self):
        with patch.object(ASRView, 'run_asr_tasks', side_effect=TimeoutError):
            response = self.client.post('/api/friend/message/asr/asr/', {'audio': SimpleUploadedFile('a.pcm', b'\0\0')}, format='multipart')
            self.assertEqual(response.status_code, 504)
            self.assertIn('超时', response.json()['result'])
