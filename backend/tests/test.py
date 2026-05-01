from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="qwen3-embedding:0.6b-q8_0")

# 嵌入查询
query_vec = embeddings.embed_query("查询内容")
print("查询向量:", query_vec)

# 嵌入文档
doc_vecs = embeddings.embed_documents(["文档1", "文档2"])
print("文档向量:", doc_vecs)