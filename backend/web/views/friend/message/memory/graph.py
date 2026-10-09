import os
from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from web.services.provider_config import ai_config, setting


class MemoryGraph:
    @staticmethod
    def create_app():
        config = ai_config()
        llm = ChatOpenAI(
            model=setting('MEMORY_MODEL', default=config['model']),
            openai_api_key=config['api_key'],
            openai_api_base=config['base_url'],
            timeout=45, max_retries=0,
        )

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]

        def model_call(state: AgentState) -> AgentState:
            res = llm.invoke(state['messages'])
            return {'messages': [res]}

        graph = StateGraph(AgentState)
        graph.add_node('agent', model_call)

        graph.add_edge(START, 'agent')
        graph.add_edge('agent', END)

        return graph.compile()
