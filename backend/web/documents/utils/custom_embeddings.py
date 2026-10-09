import os

from langchain_core.embeddings import Embeddings
from openai import OpenAI


class CustomEmbeddings(Embeddings):
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("API_BASE")
        )

    def embed_documents(self, texts):
        batch_size = 10
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            batch = [t for t in batch if t.strip()]
            if not batch:
                continue
            response = self.client.embeddings.create(
                model="text-embedding-v4",
                input=batch,
                dimensions=1024
            )
            all_embeddings.extend([data.embedding for data in response.data])
        return all_embeddings

    def embed_query(self, text):
        return self.embed_documents([text])[0]
