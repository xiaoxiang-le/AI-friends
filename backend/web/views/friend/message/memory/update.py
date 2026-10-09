from django.utils.timezone import now
from langchain_core.messages import SystemMessage, HumanMessage

from web.models.friend import SystemPrompt, Message, Friend
from django.db.models import F
from web.views.friend.message.memory.graph import MemoryGraph


def create_system_message():
    system_prompts = SystemPrompt.objects.filter(title='记忆').order_by('order_number')
    prompt = '提取用户明确表达且适合长期保存的信息，合并旧记忆，最多5000字。不要把角色设定或推测当作用户事实。'
    for sp in system_prompts:
        prompt += sp.prompt
    return SystemMessage(prompt)


def create_human_message(friend):
    prompt = f'【原始记忆】\n{friend.memory}\n'
    prompt += f'【最近对话】\n'
    messages = list(Message.objects.filter(friend=friend).order_by('-id')[:10])
    messages.reverse()
    for m in messages:
        prompt += f'user: {m.user_message}\n'
        prompt += f'ai: {m.output}\n'
    return HumanMessage(prompt)


def update_memory(friend):
    version = friend.memory_version
    app = MemoryGraph.create_app()

    inputs = {
        'messages': [
            create_system_message(),
            create_human_message(friend),
        ]
    }

    res = app.invoke(inputs)
    content = res['messages'][-1].content
    if not isinstance(content, str):
        return
    # A user edit/clear invalidates any generation based on an older snapshot.
    Friend.objects.filter(pk=friend.pk, memory_version=version).update(
        memory=content[:5000], memory_version=F('memory_version') + 1, update_time=now())
