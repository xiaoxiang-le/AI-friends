from django.db.models import Q
from web.models.character import Character


def accessible_characters(user):
    public = Q(status='published', visibility__in=['public', 'unlisted'])
    if user.is_authenticated:
        public |= Q(author__user=user)
    return Character.objects.filter(public).exclude(status='archived')


def character_data(character, owner=False):
    author = character.author
    data = {
        'id': character.id, 'name': character.name,
        'profile': character.public_description,
        'photo': character.photo.url if character.photo else '',
        'background_image': character.background_image.url if character.background_image else '',
        'author': {'user_id': author.user_id, 'username': author.user.username,
                   'photo': author.photo.url if author.photo else ''},
        'visibility': character.visibility, 'status': character.status,
        'version': character.version,
    }
    if owner:
        data.update(profile=character.profile, public_description=character.public_description,
                    persona_prompt=character.persona_prompt, voice_id=character.voice_id, moderation_reason=character.moderation_reason)
    return data


def positive_id(value):
    return isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).isascii() and str(value).isdigit() and int(value) > 0
