"""Built-in voices verified against the CosyVoice v3 Flash catalogue."""
from web.models.character import Voice
from web.services.provider_config import voice_config

VOICE_NAMES = {
    'longanyang': '阳光男声',
    'longxiaochun_v3': '亲切女声',
    'longxiaoxia_v3': '沉稳女声',
    'longyumi_v3': '青春女声',
    'longanyun_v3': '温柔男声',
    'longanwen_v3': '温柔女声',
    'longanli_v3': '干练女声',
}

VOICE_DETAILS = {
    'longanyang': '阳光男声 · 明亮开朗',
    'longxiaochun_v3': '亲切女声 · 积极亲切',
    'longxiaoxia_v3': '沉稳女声 · 清晰从容',
    'longyumi_v3': '青春女声 · 活泼亲切',
    'longanyun_v3': '温暖男声 · 居家陪伴',
    'longanwen_v3': '优雅女声 · 知性温柔',
    'longanli_v3': '利落女声 · 沉着清爽',
}

def available_voices():
    voices = Voice.objects.order_by('id')
    if voice_config('TTS')['model'] != 'cosyvoice-v3-flash':
        # Preserve existing/custom voices; do not advertise Flash-only additions.
        voices = voices.exclude(voice_id__in=[key for key in VOICE_DETAILS if key != 'longanyang'])
    return voices

def voice_options():
    return [{'id':voice.id, 'name':VOICE_NAMES.get(voice.voice_id, voice.name),
             'description':VOICE_DETAILS.get(voice.voice_id, '自定义音色')}
            for voice in available_voices()]
