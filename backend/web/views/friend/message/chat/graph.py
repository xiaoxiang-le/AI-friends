import os
from typing import TypedDict, Annotated, Sequence

import lancedb
from django.utils.timezone import localtime, now
from langchain_community.vectorstores import LanceDB
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode

from web.documents.utils.custom_embeddings import CustomEmbeddings
from web.services.provider_config import ai_config, setting
from django.conf import settings


class ChatGraph:
    @staticmethod
    def create_app():
        @tool
        def get_time() -> str:
            """当需要查询精确时间时，调用此函数。返回格式为：[年-月-日 时:分:秒]"""
            return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')
        

        @tool
        def search_knowledge_base(query: str) -> str:
            """当用户查询阿里云百炼平台的相关信息时，调用此函数， 输入为要查询的问题，输出为查询结果"""
            db = lancedb.connect(str(settings.BASE_DIR / 'web/documents/lancedb_storage'))
            embeddings = CustomEmbeddings()
            vector_db = LanceDB(
                connection=db,
                embedding=embeddings,
                table_name='my_knowledge_base',
            )
            docs = vector_db.similarity_search(query, k=3)
            context = '\n\n'.join([f'内容片段：{i + 1}\n{doc.page_content}' for i, doc in enumerate(docs)])
            return f'从知识库中找到以下相关信息：\n\n{context}\n'


        # The legacy shared knowledge table is opt-in until resource isolation is implemented.
        tools = [get_time]
        if setting('ENABLE_LEGACY_KNOWLEDGE') == 'true':
            tools.append(search_knowledge_base)

        config = ai_config()
        llm = ChatOpenAI(
            model=config['model'],
            openai_api_key=config['api_key'],
            openai_api_base=config['base_url'],
            timeout=45,
            max_retries=0,
            streaming=True,
            model_kwargs={
                "stream_options": {
                    "include_usage": True,  #输出token的消耗数量
                }
            }
        )
        if setting('AI_ENABLE_TOOLS', default='true') == 'true':
            llm = llm.bind_tools(tools)

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]

        async def model_call(state: AgentState) -> AgentState:
            res = await llm.ainvoke(state['messages'])
            return {'messages': [res]}
        
        def should_continue(state: AgentState) -> str:
            last_message = state['messages'][-1]
            if last_message.tool_calls:
                return "tools"
            return "end"

        tool_node = ToolNode(tools)
        
        graph = StateGraph(AgentState)
        graph.add_node('agent', model_call)
        graph.add_node('tools', tool_node)

        graph.add_edge(START, 'agent')
        graph.add_conditional_edges(
            'agent',
            should_continue,
            {
                'tools': 'tools',
                'end': END,
            }
        )
        graph.add_edge('tools', 'agent')

        return graph.compile().with_config({'recursion_limit': 8})
