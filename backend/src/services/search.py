from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Milvus
from ..core.embeddings import embedding_service
from ..core.config import settings
from ..models.schemas import SourceDoc


class SearchService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0
        )
        self.vector_store = None

    def get_vector_store(self):
        if self.vector_store is None:
            self.vector_store = Milvus(
                embedding_function=embedding_service.embeddings,
                connection_args={"uri": settings.MILVUS_URI},
                collection_name=settings.DEFAULT_COLLECTION
            )
        return self.vector_store

    def similarity_search(self, query: str, top_k: int = None) -> list[SourceDoc]:
        if top_k is None:
            top_k = settings.TOP_K

        vector_store = self.get_vector_store()
        docs = vector_store.similarity_search_with_score(query, k=top_k)

        sources = []
        for doc, score in docs:
            sources.append(SourceDoc(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                score=round(score, 4)
            ))

        return sources

    def get_retriever(self, top_k: int = None):
        vector_store = self.get_vector_store()
        return vector_store.as_retriever(
            search_kwargs={"k": top_k or settings.TOP_K}
        )


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0
        )
        self.search_service = SearchService()

    def chat(self, question: str, chat_history: list[dict] = None, top_k: int = None):
        if chat_history is None:
            chat_history = []

        retriever = self.search_service.get_retriever(top_k)

        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            return_source_documents=True,
            combine_docs_chain_kwargs={
                "prompt": self._get_prompt()
            }
        )

        result = chain.invoke({
            "question": question,
            "chat_history": [(msg["content"], "") for msg in chat_history if msg["role"] == "user"]
        })

        sources = []
        for doc in result.get("source_documents", []):
            sources.append(SourceDoc(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                score=None
            ))

        return {
            "answer": result["answer"],
            "sources": sources
        }

    def _get_prompt(self):
        from langchain_core.prompts import ChatPromptTemplate

        template = """你是一个专业的智能客服助手。请根据提供的参考文档回答用户问题。

参考文档:
{context}

对话历史:
{chat_history}

当前问题: {question}

请遵循以下规则:
1. 只根据提供的参考文档回答，不要编造信息
2. 如果参考文档中没有相关信息，请明确告知用户
3. 回答要准确、专业、友好
4. 保持对话的连贯性

回答:"""

        return ChatPromptTemplate.from_template(template)


search_service = SearchService()
chat_service = ChatService()
