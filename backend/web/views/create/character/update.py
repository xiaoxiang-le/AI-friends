from django.db import transaction
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from web.models.character import Character
from web.services.voice_catalog import available_voices
from web.services.provider_config import setting
from web.services.uploads import validate_image
from web.services.characters import positive_id, character_data
from web.views.utils.photo import remove_old_photo


class UpdateCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        character_id = request.data.get('character_id')
        if not positive_id(character_id):
            return Response({'result': '角色编号不合法'}, status=400)
        name, profile = request.data.get('name', ''), request.data.get('profile', '')
        description, persona = request.data.get('public_description'), request.data.get('persona_prompt')
        if not isinstance(name, str) or not isinstance(profile, str) or any(v is not None and not isinstance(v, str) for v in [description, persona]):
            return Response({'result': '角色字段必须为文本'}, status=400)
        name, profile = name.strip(), profile.strip()
        if not name or len(name) > 50 or not profile or len(profile) > 100000:
            return Response({'result': '名字需为1至50字，角色介绍需为1至100000字'}, status=400)
        if (description is not None and len(description) > 200) or (persona is not None and len(persona) > 100000):
            return Response({'result': '公开简介最多200字，角色设定最多100000字'}, status=400)
        photo, background = request.FILES.get('photo'), request.FILES.get('background_image')
        validate_image(photo)
        validate_image(background)
        voice_id = request.data.get('voice_id')
        voice = available_voices(request.user).filter(pk=voice_id).first() if str(voice_id).isascii() and str(voice_id).isdigit() else None
        if voice_id not in [None, '', 'none'] and not voice:
            return Response({'result': '请选择有效音色'}, status=400)
        with transaction.atomic():
            character = Character.objects.select_for_update().filter(pk=character_id, author__user=request.user).first()
            if not character:
                return Response({'result': '角色不存在或无权修改'}, status=404)
            version = request.data.get('version')
            if version is None or str(version) != str(character.version):
                return Response({'result': '角色已更新，请重新加载后修改'}, status=409)
            status, visibility = request.data.get('status', character.status), request.data.get('visibility', character.visibility)
            if status not in ['draft', 'published'] or visibility not in ['private', 'unlisted', 'public']:
                return Response({'result': '请先恢复已归档角色，或选择有效发布状态'}, status=400)
            public_text = description if description is not None else character.public_description
            if status == 'published' and visibility == 'public' and not public_text.strip():
                return Response({'result': '公开发布需要填写公开简介'}, status=400)
            old_images = []
            if photo:
                old_images.append(character.photo)
                character.photo = photo
            if background:
                old_images.append(character.background_image)
                character.background_image = background
            character.name, character.profile, character.voice = name, profile, voice
            if description is not None:
                character.public_description = description
            if persona is not None:
                character.persona_prompt = persona
            elif not character.persona_prompt:
                character.persona_prompt = profile
            if status=='published' and visibility=='public' and setting('REQUIRE_CHARACTER_REVIEW',default='false')=='true':
                status='reviewing'
            character.moderation_reason=''
            character.status, character.visibility = status, visibility
            character.version += 1
            character.update_time = now()
            character.save()
            for image in old_images:
                transaction.on_commit(lambda image=image: remove_old_photo(image))
        return Response({'result': 'success', 'character': character_data(character, owner=True)})
