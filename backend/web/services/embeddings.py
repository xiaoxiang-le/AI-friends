from openai import OpenAI
from web.services.provider_config import setting


def embedding_config():
    return dict(api_key=setting('EMBEDDING_API_KEY'), base_url=setting('EMBEDDING_BASE_URL'), model=setting('EMBEDDING_MODEL'))


def embed(texts):
    config = embedding_config()
    with OpenAI(api_key=config['api_key'], base_url=config['base_url'], timeout=15, max_retries=0) as client:
        output = []
        for start in range(0, len(texts), 16):
            response = client.embeddings.create(model=config['model'], input=texts[start:start+16])
            output.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
    if len(output) != len(texts):
        raise ValueError('嵌入服务未返回完整向量')
    return output
