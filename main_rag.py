import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# 千问 API 配置
os.environ["DASHSCOPE_API_KEY"] = "sk-c0ea6827961b4b17b80dd8025785ea1c"
os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

llm = LLM(model="dashscope/qwen-plus")

# ==================== RAG 工具 ====================

# 1. 文本切片
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """将文本按指定大小切片，带重叠"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# 2. 向量存储（用本地文件模拟，生产环境用 ChromaDB/FAISS/ Milvus）
import json
import hashlib
from pathlib import Path

class VectorStore:
    """简易向量存储，用文件模拟。生产环境替换为 ChromaDB 等。"""

    def __init__(self, store_path: str = "D:/python/crewai/rag_store"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.db_file = self.store_path / "documents.json"
        self.documents = self._load()

    def _load(self) -> list[dict]:
        if self.db_file.exists():
            return json.loads(self.db_file.read_text(encoding="utf-8"))
        return []

    def _save(self):
        self.db_file.write_text(
            json.dumps(self.documents, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add(self, text: str, metadata: dict = None):
        """添加文档片段"""
        doc_id = hashlib.md5(text.encode()).hexdigest()[:12]
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        })
        self._save()
        return doc_id

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """简易关键词匹配搜索（生产环境用向量相似度）"""
        query_lower = query.lower()
        scored = []
        for doc in self.documents:
            # 简单的关键词重叠度评分
            text_lower = doc["text"].lower()
            score = sum(1 for word in query_lower.split() if word in text_lower)
            if score > 0:
                scored.append({"score": score, **doc})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def clear(self):
        self.documents = []
        self._save()


# 全局向量存储实例
store = VectorStore()


# 3. RAG 工具：添加文档
class AddDocInput(BaseModel):
    text: str = Field(description="要添加的文档内容")
    source: str = Field(default="unknown", description="文档来源")

class AddDocTool(BaseTool):
    name: str = "add_document"
    description: str = "将文档内容添加到知识库中"
    args_schema: type[BaseModel] = AddDocInput

    def _run(self, text: str, source: str = "unknown") -> str:
        chunks = chunk_text(text)
        added = 0
        for chunk in chunks:
            if len(chunk.strip()) > 20:  # 跳过太短的片段
                store.add(chunk, {"source": source})
                added += 1
        return f"已将文档切分为 {added} 个片段并存入知识库"


# 4. RAG 工具：检索知识库
class SearchKBInput(BaseModel):
    query: str = Field(description="搜索查询")

class SearchKBTool(BaseTool):
    name: str = "search_knowledge_base"
    description: str = "从知识库中检索与查询相关的文档片段"
    args_schema: type[BaseModel] = SearchKBInput

    def _run(self, query: str) -> str:
        results = store.search(query, top_k=3)
        if not results:
            return "知识库中没有找到相关内容"
        output = []
        for i, r in enumerate(results, 1):
            output.append(f"[片段{i}] (来源: {r['metadata'].get('source', '未知')})\n{r['text']}")
        return "\n\n".join(output)


# ==================== 准备知识库数据 ====================

# 模拟一些文档
DOCS = {
    "python_guide.txt": """
Python 是一种广泛使用的高级编程语言，由 Guido van Rossum 于 1991 年首次发布。
Python 的设计哲学强调代码的可读性和简洁性。Python 支持多种编程范式，包括面向对象、
命令式、函数式和过程式编程。

Python 的主要特点包括：
1. 简单易学：语法简洁清晰，适合初学者
2. 解释型语言：不需要编译，直接运行
3. 动态类型：变量不需要声明类型
4. 丰富的标准库：内置大量模块和函数
5. 跨平台：支持 Windows、Linux、macOS

Python 的常见应用领域包括：Web 开发（Django、Flask）、数据科学（Pandas、NumPy）、
机器学习（PyTorch、TensorFlow）、自动化脚本、网络爬虫等。

Python 虚拟环境用于隔离项目依赖。常用工具包括 venv 和 conda。
创建虚拟环境的命令：python -m venv .venv
激活虚拟环境：source .venv/bin/activate（Linux）或 .venv\\Scripts\\activate（Windows）
""",

    "crewai_intro.txt": """
CrewAI 是一个多智能体协作框架，让多个 AI Agent 协同工作完成复杂任务。

CrewAI 的核心概念：
1. Agent：具有角色、目标和背景的 AI 实体
2. Task：分配给 Agent 的具体任务
3. Crew：一组 Agent 和 Task 的组合
4. Process：执行策略（sequential 顺序执行、hierarchical 层级执行）

Agent 可以配备工具（Tools）来扩展能力，比如搜索、读写文件、调用 API 等。
Agent 之间可以通过 delegation（委派）机制互相转派任务。

CrewAI 支持记忆系统：
- 短期记忆：单次执行内的上下文
- 长期记忆：跨执行的持久化记忆
- 实体记忆：自动追踪实体信息变化

CrewAI 使用 LiteLLM 作为底层，支持多种 LLM 提供商，包括 OpenAI、Anthropic、
DashScope（千问）、DeepSeek、Ollama 等。
""",

    "agent_patterns.txt": """
AI Agent 设计模式：

1. ReAct（Reasoning + Acting）
   Agent 先思考（Reasoning），再行动（Acting），然后观察结果，循环执行。
   这是最基础的 Agent 模式。

2. Plan-and-Execute
   Agent 先制定完整计划，然后逐步执行。适合复杂任务。

3. Reflection
   Agent 在执行后自我反思，评估结果质量，必要时重试。

4. Multi-Agent Collaboration
   多个 Agent 分工协作，各自负责擅长的领域。
   常见模式：串行（sequential）、并行（parallel）、层级（hierarchical）。

5. Tool Use
   Agent 调用外部工具扩展能力：搜索引擎、代码执行器、数据库查询等。

6. Memory-Augmented
   Agent 配备记忆系统，能够记住历史信息并在决策时参考。

RAG（Retrieval-Augmented Generation）是一种常见模式：
- 将文档切片存入向量数据库
- 用户提问时，先检索相关文档片段
- 将检索到的内容作为上下文，连同问题一起发给 LLM
- LLM 基于检索到的内容生成回答
"""
}


def init_knowledge_base():
    """初始化知识库"""
    store.clear()
    for filename, content in DOCS.items():
        chunks = chunk_text(content, chunk_size=300, overlap=50)
        for chunk in chunks:
            if len(chunk.strip()) > 20:
                store.add(chunk, {"source": filename})
    print(f"[RAG] 知识库初始化完成，共 {len(store.documents)} 个片段\n")


# ==================== Agent ====================

rag_agent = Agent(
    role="RAG 知识问答专家",
    goal="根据知识库中的内容准确回答用户问题，如果知识库中没有相关内容则如实说明",
    backstory=(
        "你是一位严谨的知识问答专家。你只基于知识库中检索到的内容来回答问题，"
        "不会编造信息。如果检索到的内容不足以回答问题，你会明确告知用户。"
        "回答时会标注信息来源。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[SearchKBTool(), AddDocTool()],
)

# ==================== Task ====================

qa_task = Task(
    description=(
        "用户提问：{question}\n\n"
        "请按以下步骤操作：\n"
        "1. 使用 search_knowledge_base 工具，搜索与问题相关的内容\n"
        "2. 如果找到相关内容，基于检索到的内容回答问题，并注明信息来源\n"
        "3. 如果没有找到相关内容，如实告知用户知识库中没有相关信息\n"
        "4. 回答要准确、简洁、结构清晰"
    ),
    expected_output="基于知识库检索结果的准确回答，附带信息来源",
    agent=rag_agent,
)

# ==================== Crew ====================

crew = Crew(
    agents=[rag_agent],
    tasks=[qa_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    # 初始化知识库
    init_knowledge_base()

    # 提问
    question = "CrewAI 的记忆系统有哪些类型？"
    print(f"[RAG] 提问：{question}\n")

    result = crew.kickoff(inputs={"question": question})

    print("\n" + "=" * 60)
    print("[RAG] 回答：")
    print("=" * 60)
    print(result)
