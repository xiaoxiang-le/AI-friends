import re
import math
from web.services.embeddings import embedding_config, embed
from web.services.provider_config import configured
from web.models.resources import KnowledgeChunk


def terms(text):
    text = text.lower()
    words = set(re.findall(r'[a-z0-9_]{2,}', text))
    for phrase in re.findall(r'[\u4e00-\u9fff]+', text):
        words.update(phrase[i:i+2] for i in range(len(phrase)-1))
    return words


def search_knowledge(character, query):
    query_terms = terms(query)
    if not query_terms:
        return []
    candidates = KnowledgeChunk.objects.filter(document__character=character,
        document__owner=character.author, document__status='ready').select_related('document')
    config = embedding_config()
    query_vector = None
    if configured(config) and candidates.filter(document__embedding_model=config['model']).exists():
        try: query_vector = embed([query])[0]
        except Exception: pass  # Keyword retrieval remains available during embedding failure.
    matches = []
    for chunk in candidates:
        overlap = query_terms & terms(chunk.content)
        score = len(overlap) / len(query_terms)
        if query_vector and chunk.vector and chunk.document.embedding_model == config['model'] and len(chunk.vector)==len(query_vector):
            norm = math.sqrt(sum(x*x for x in chunk.vector)*sum(x*x for x in query_vector))
            similarity = sum(a*b for a,b in zip(chunk.vector,query_vector))/norm if norm else 0
            if similarity>.3: score += similarity
        if score>0: matches.append((score, chunk))
    matches.sort(key=lambda item: (-item[0], item[1].id))
    return [{'document_id': c.document_id, 'name': c.document.name, 'position': c.position,
             'content': c.content[:1200]} for _, c in matches[:3]]
