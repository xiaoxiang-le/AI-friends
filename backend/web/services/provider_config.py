"""Provider settings; legacy names remain compatible. Never return credentials."""
import os


def setting(name, legacy=None, default=''):
    return os.getenv(name) or (os.getenv(legacy) if legacy else '') or default


def ai_config():
    return dict(api_key=setting('AI_API_KEY', 'API_KEY'), base_url=setting('AI_BASE_URL', 'API_BASE'),
                model=setting('AI_MODEL'))


def voice_config(kind):
    return dict(api_key=setting(kind + '_API_KEY', 'API_KEY'),
                url=setting(kind + '_WSS_URL', 'WSS_URL'),
                model=setting(kind + '_MODEL', default='gummy-realtime-v1' if kind == 'ASR' else 'cosyvoice-v3-flash'))


def configured(config):
    return all(config.values())
