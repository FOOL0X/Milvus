#!/usr/bin/env python3
"""测试 embedding 是否使用 GPU"""
import torch
from sentence_transformers import SentenceTransformer

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device: {torch.cuda.get_device_name(0)}")
print(f"MPS available (Apple Silicon): {torch.backends.mps.is_available()}")
print(f"MPS built: {torch.backends.mps.is_built()}")

# 测试 MPS 设备
if torch.backends.mps.is_available():
    print("\n尝试在 MPS 上运行测试...")
    try:
        x = torch.ones(3, 3, device="mps")
        print(f"MPS device test passed: {x}")
    except Exception as e:
        print(f"MPS device test failed: {e}")

# 加载模型并检查设备 - 使用 HF 官方模型
model_name = "BAAI/bge-m3"
print(f"\n加载模型: {model_name}")
model = SentenceTransformer(model_name)
print(f"Model device: {model.device}")
print(f"Model embedding dimension: {model.get_sentence_embedding_dimension()}")

# 测试编码
test_text = "BGE-M3"
emb = model.encode([test_text])
print(f"\nEmbedding shape: {emb.shape}")
print(f"Embedding sample (first 5 dims): {emb[0][:5].tolist()}")