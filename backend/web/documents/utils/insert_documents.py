from pathlib import Path

import lancedb
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import LanceDB
from langchain_text_splitters import RecursiveCharacterTextSplitter

from web.documents.utils.custom_embeddings import CustomEmbeddings


def insert_documents():
    from dotenv import load_dotenv
    load_dotenv()  # 从当前工作目录（需在 backend 下运行）加载 .env
    loader = TextLoader('./web/documents/data.txt', encoding='utf-8')
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    print(f"已切分成 {len(texts)} 个片段。")

    embeddings = CustomEmbeddings()
    db = lancedb.connect('./web/documents/lancedb_storage')
    vector_db = LanceDB.from_documents(
        documents=texts,
        embedding=embeddings,
        connection=db,
        table_name='my_knowledge_base',
        mode='overwrite',
    )
    print(f"已插入 {vector_db._table.count_rows()} 行数据。")