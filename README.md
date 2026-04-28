# RAG 智能客服助手

基于 RAG（检索增强生成）+ Milvus 向量数据库的智能客服系统。

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Tailwind + Zustand |
| 后端 | FastAPI + LangChain |
| 向量库 | Milvus 2.4+ |
| LLM | GPT-4o / Claude 3.5 |
| 部署 | Kubernetes |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/your-org/customer-service-rag.git
cd customer-service-rag

# 设置环境变量
export OPENAI_API_KEY=your-api-key
```

### 2. Docker Compose 启动（开发环境）

```bash
docker-compose up -d

# 访问 http://localhost:3000
```

### 3. Kubernetes 部署（生产环境）

```bash
# 1. 创建 namespace 和配置
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 2. 部署 Milvus
kubectl apply -f k8s/milvus/milvus-deployment.yaml

# 3. 部署后端和前端
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/

# 4. 部署 Ingress
kubectl apply -f k8s/ingress.yaml
```

## 项目结构

```
customer-service-rag/
├── backend/                    # Python 后端
│   ├── src/
│   │   ├── api/               # API 路由
│   │   ├── core/              # 核心配置
│   │   ├── services/          # 业务逻辑
│   │   └── models/            # 数据模型
│   └── requirements.txt
├── frontend/                   # React 前端
│   └── src/
│       ├── api/               # API 调用
│       ├── components/        # React 组件
│       └── stores/            # 状态管理
├── k8s/                       # Kubernetes 配置
└── docker-compose.yml
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息 |
| `/api/chat/history/{session_id}` | GET | 获取会话历史 |
| `/api/ingest` | POST | 上传文档 |
| `/api/health` | GET | 健康检查 |

## 开发

### 后端开发

```bash
cd backend

# 安装 uv (如果没有)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖并运行
uv sync
uv run uvicorn src.api.main:app --reload
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 知识库构建

### 方式一：脚本导入（推荐用于批量数据）

```bash
cd backend

# 导入整个目录（支持 pdf, docx, txt, md, xml, json, sqlite）
python scripts/ingest_data.py --path ./data/docs --collection customer_service_kb

# 导入 XML FAQ 文件
python scripts/ingest_data.py --path ./data/sample_faq.xml --collection faq

# 导入 Markdown 文件
python scripts/ingest_data.py --path ./data/sample_faq.md --collection faq

# 导入 SQLite 数据库（所有表）
python scripts/ingest_data.py --path ./data/app.db --collection knowledge

# 导入 SQLite 指定表
python scripts/ingest_data.py --path ./data/app.db --collection users --table users

# 自定义分块参数
python scripts/ingest_data.py --path ./data/docs \
  --collection customer_service_kb \
  --chunk-size 512 \
  --chunk-overlap 100
```

### 方式二：API 上传

```bash
# 通过 API 上传文档
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@./policy.pdf" \
  -F "collection_name=customer_service_kb" \
  -F "category=policy"
```

### 支持的数据格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| PDF | .pdf | 自动提取文本 |
| Word | .docx | 自动提取文本 |
| 文本 | .txt | 纯文本文件 |
| Markdown | .md | 自动按段落分割 |
| XML | .xml | FAQ 专用格式 |
| JSON | .json | 结构化数据 |
| SQLite | .db, .sqlite, .sqlite3 | 数据库表数据 |

### XML FAQ 格式示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<faq>
    <item>
        <question>你们支持退货吗？</question>
        <answer>7天内支持退货，商品需保持原包装完好。</answer>
        <category>售后</category>
    </item>
</faq>
```
