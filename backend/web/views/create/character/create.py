from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from web.models.character import Character
from web.models.user import UserProfile
from web.services.voice_catalog import available_voices
from web.services.provider_config import setting
from web.services.uploads import validate_image
from web.services.characters import character_data


class CreateCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get('name', '')
        profile = request.data.get('profile', '')
        description = request.data.get('public_description', '')
        persona = request.data.get('persona_prompt', '')
        if not all(isinstance(v, str) for v in [name, profile, description, persona]):
            return Response({'result': '角色字段必须为文本'}, status=400)
        name, profile = name.strip(), profile.strip()
        if not name or len(name) > 50:
            return Response({'result': '角色名字需为1至50个字符'}, status=400)
        if not profile or len(profile) > 100000 or len(persona) > 100000 or len(description) > 200:
            return Response({'result': '介绍不能为空，公开简介最多200字，角色设定最多100000字'}, status=400)
        status = request.data.get('status', 'draft')
        visibility = request.data.get('visibility', 'private')
        if status not in ['draft', 'published'] or visibility not in ['private', 'unlisted', 'public']:
            return Response({'result': '发布状态或可见范围不合法'}, status=400)
        if status == 'published' and visibility == 'public' and not description.strip():
            return Response({'result': '公开发布需要填写公开简介'}, status=400)
        photo, background = request.FILES.get('photo'), request.FILES.get('background_image')
        if not photo or not background:
            return Response({'result': '头像和聊天背景不能为空'}, status=400)
        validate_image(photo)
        validate_image(background)
        voice_id = request.data.get('voice_id')
        voice = available_voices(request.user).filter(pk=voice_id).first() if str(voice_id).isascii() and str(voice_id).isdigit() else None
        if voice_id not in [None, '', 'none'] and not voice:
            return Response({'result': '请选择有效音色'}, status=400)
        if status=='published' and visibility=='public' and setting('REQUIRE_CHARACTER_REVIEW',default='false')=='true':
            status='reviewing'
        with transaction.atomic():
            character = Character.objects.create(author=UserProfile.objects.get(user=request.user),
                name=name, profile=profile, persona_prompt=persona or profile,
                public_description=description.strip(), photo=photo,
                background_image=background, voice=voice, status=status, visibility=visibility)
        return Response({'result': 'success', 'character': character_data(character, owner=True)})
