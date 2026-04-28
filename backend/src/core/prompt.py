from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage


RAG_PROMPT_TEMPLATE = """你是一个专业的智能客服助手。请根据提供的参考文档回答用户问题。

参考文档:
{context}

用户问题: {question}

请遵循以下规则:
1. 只根据提供的参考文档回答，不要编造信息
2. 如果参考文档中没有相关信息，请明确告知用户
3. 回答要准确、专业、友好
4. 如果涉及政策或规定，引用具体的文档来源

回答:"""

RAG_PROMPT = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)


CHAT_PROMPT_TEMPLATE = """你是一个专业的智能客服助手。请根据提供的参考文档和对话历史回答用户问题。

参考文档:
{context}

对话历史:
{chat_history}

当前问题: {question}

请遵循以下规则:
1. 只根据提供的参考文档和对话历史回答，不要编造信息
2. 如果参考文档中没有相关信息，请明确告知用户
3. 回答要准确、专业、友好
4. 如果涉及政策或规定，引用具体的文档来源
5. 结合对话历史，保持对话的连贯性

回答:"""


def create_chat_prompt():
    return ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的智能客服助手。"),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{question}"),
    ])


def format_chat_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return ""

    formatted = []
    for msg in chat_history:
        if msg["role"] == "user":
            formatted.append(f"用户: {msg['content']}")
        else:
            formatted.append(f"助手: {msg['content']}")

    return "\n".join(formatted)
