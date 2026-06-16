# 智能客服系统 — 多 Agent 协作 + 图数据库

**项目地址：** https://github.com/feng20000308-stack/crewai-customer-service

---

## 项目简介

基于 CrewAI 多 Agent 框架 + Neo4j 图数据库 + FastAPI 构建的智能客服系统。通过意图识别将用户问题路由到不同专业 Agent（产品顾问、订单管家、售后专员），Agent 自主调用工具查询 Neo4j 图数据库并生成回答。系统支持协同过滤推荐、用户相似度分析等图数据库特色能力。

---

## 技术架构

```
用户 → FastAPI → LLM意图分类 → 路由 → 专业Agent → Neo4j工具 → 中文回答
```

- **Agent 框架：** CrewAI（多 Agent 协作、任务编排、工具调用）
- **图数据库：** Neo4j 5.x（Cypher 查询、原生向量索引）
- **LLM：** 通义千问 qwen-plus（DashScope API）
- **后端：** FastAPI + Uvicorn
- **前端：** 原生 HTML/JS 聊天界面
- **部署：** Docker Compose（Neo4j + 初始化脚本 + Web 服务一键编排）

---

## 核心功能

### 1. 多 Agent 协作
- **产品顾问** — 产品搜索、参数对比、购买推荐
- **订单管家** — 订单状态查询、历史订单、物流跟踪
- **售后专员** — 退换货政策查询、售后申请、自动匹配规则
- **综合客服** — 兜底处理跨领域复杂问题

### 2. LLM 意图路由
- 用千问 LLM 做意图分类（非关键词匹配），准确识别产品咨询/订单查询/售后服务/综合咨询
- Prompt 中内置示例，支持"订单想退货"等复合意图的正确归类

### 3. 图数据库驱动
- **数据模型：** User → Order → Product → AfterSalesRule，通过关系连接
- **协同过滤推荐：** 二跳遍历（Product→User→Product），找出"买了X的人还买了什么"
- **用户相似度：** 共同购买产品分析，支持社交推荐
- **关系图谱：** 可视化用户-订单-产品-售后规则的完整链路

### 4. 自定义工具体系
- 8 个自定义 BaseTool：产品搜索、产品对比、订单查询、历史订单、售后政策、售后申请、Cypher 查询、图推荐
- 每个工具封装独立的 Cypher 查询，Agent 按需调用

### 5. Docker 容器化
- `docker-compose.yml` 编排 Neo4j + 数据初始化 + Web 服务
- `seed_data.py` 自动等待 Neo4j 就绪后导入测试数据
- 环境变量配置，API Key 不硬编码

---

## 技术亮点

| 亮点 | 说明 |
|------|------|
| **Agent 工具链** | 每个 Agent 配备领域专属工具，Agent 自主决定调用哪些工具、传什么参数 |
| **图遍历推荐** | 用 Cypher 原生图遍历做协同过滤，比 SQL JOIN 更直观高效 |
| **异步兼容** | CrewAI 同步调用通过 `asyncio.to_thread` 接入 FastAPI 异步框架 |
| **意图分类** | LLM 做意图识别，支持复合意图（"订单+退货" → 售后），比关键词匹配更准确 |
| **数据初始化** | Docker 启动时自动等待 Neo4j 就绪、清空旧数据、导入测试数据 |

---

## 项目结构

```
├── customer_service.py  # 核心：Agent定义 + 工具 + 意图路由
├── server.py            # FastAPI 后端
├── seed_data.py         # Neo4j 数据初始化
├── static/index.html    # 前端聊天界面
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose 编排
└── requirements.txt     # Python 依赖
```

---

## 涉及技术栈

`Python` `CrewAI` `Neo4j` `Cypher` `FastAPI` `Docker` `Docker Compose` `LLM` `通义千问` `DashScope` `多Agent` `图数据库` `RAG` `工具调用`

---

## 可改进方向

- 接入 embedding 模型做真正的向量语义检索（RAG）
- 增加记忆系统，支持多轮对话上下文
- 接入 LangSmith 做 Agent 调用链路追踪
- 增加更多图算法（社区发现、影响力传播等）
- 前端增加关系图谱可视化（D3.js / ECharts）
