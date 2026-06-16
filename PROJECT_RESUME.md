# 智能客服系统 — 多 Agent 协作 + 图数据库

**项目地址：** https://github.com/feng20000308-stack/crewai-customer-service

---

## 项目简介

基于 CrewAI 多 Agent 框架 + Neo4j 图数据库 + FastAPI 构建的智能客服系统。通过 LLM 意图识别将用户问题自动路由到不同专业 Agent，Agent 自主调用工具完成业务操作。支持对话记忆、人工审核、协同过滤推荐等能力。

---

## 技术架构

```
用户 → FastAPI → Redis(对话记忆) → LLM意图分类 → 路由 → 专业Agent → Neo4j/业务工具 → 回答
```

---

## 核心功能

### 1. 多 Agent 协作

| Agent | 职责 | 工具 |
|-------|------|------|
| 产品顾问 | 产品搜索、参数对比、推荐 | SearchProduct / ListProducts / CompareProducts / GetRecommendation |
| 订单管家 | 订单查询、物流追踪 | QueryOrder / UserOrderHistory / TrackLogistics |
| 售后专员 | 退换货、退款申请、取消订单 | AfterSalesPolicy / ApplyRefund / CancelOrder / GrantCoupon |
| 综合客服 | 兜底处理跨领域问题 | 全部工具 + Cypher 查询 + 审批工具 |

### 2. LLM 意图路由

- 用通义千问做意图分类（非关键词匹配），Prompt 内置分类示例
- 支持复合意图识别（如"订单想退货"→归为售后服务）
- 四类意图：产品咨询 / 订单查询 / 售后服务 / 综合咨询

### 3. 对话记忆

- Redis 存储对话历史，1 小时过期，key 前缀隔离不同项目
- Redis 不可用时自动降级为内存存储
- 每次请求携带全部历史对话，Agent 能理解"它"、"那个"等指代词

### 4. 人工审核机制

- 敏感操作（退款、取消订单）不直接执行，生成待审核工单
- Agent 告知客户"已提交，待审核"
- 管理员可通过 `list_pending_approvals` 查看待审工单
- 通过 `approve_request` 审批通过或拒绝，通过后自动执行

### 5. 图数据库驱动

| 场景 | Cypher 查询 | 体现的图能力 |
|------|------------|-------------|
| 协同过滤推荐 | Product→User→Product 二跳遍历 | 关系网络推荐 |
| 用户相似度 | User→Product←User 共同购买 | 社交分析 |
| 关系图谱 | User→Order→Product→Rule 全路径 | 多跳遍历 |
| 售后规则匹配 | Product→HAS_RULE→AfterSalesRule | 属性关系查询 |

### 6. 业务操作工具

| 工具 | 功能 | 审核 |
|------|------|------|
| apply_refund | 申请退款 | 需审核 |
| cancel_order | 取消订单 | 需审核 |
| track_logistics | 查物流轨迹 | 直接执行 |
| grant_coupon | 发放优惠券 | 直接执行 |
| get_recommendation | 个性化推荐 | 直接执行 |

---

## 技术亮点

| 亮点 | 说明 |
|------|------|
| **Agent 工具链** | 每个 Agent 配备领域专属工具，Agent 自主决定调用哪些工具、传什么参数 |
| **图遍历推荐** | 用 Cypher 原生图遍历做协同过滤，比 SQL JOIN 更直观高效 |
| **对话记忆** | Redis 存储历史 + 自动降级，支持上下文指代消解 |
| **人工审核** | 敏感操作走审批流，通过后自动执行，兼顾效率与安全 |
| **异步兼容** | CrewAI 同步调用通过 `asyncio.to_thread` 接入 FastAPI 异步框架 |
| **意图分类** | LLM 做意图识别，Prompt 内置示例，支持复合意图 |
| **容器化部署** | Docker Compose 一键编排 Neo4j + Redis + Web 服务 |

---

## 项目结构

```
├── customer_service.py   # 核心：Agent + 工具 + 意图路由 + 业务逻辑
├── server.py             # FastAPI 后端（对话记忆 + API 接口）
├── seed_data.py          # Neo4j 数据初始化脚本
├── static/index.html     # 前端聊天界面
├── Dockerfile            # Docker 镜像
├── docker-compose.yml    # Docker Compose 编排（Neo4j + Redis + Web）
├── requirements.txt      # Python 依赖
└── .env                  # 环境变量配置
```

---

## 技术栈

`Python` `CrewAI` `Neo4j` `Cypher` `FastAPI` `Redis` `Docker` `Docker Compose` `LLM` `通义千问` `DashScope` `多Agent` `图数据库` `意图分类` `对话记忆` `人工审核`

---

## 可改进方向

- 接入 embedding 模型做向量语义检索（RAG）
- 接入 LangSmith 做 Agent 调用链路追踪
- 前端增加关系图谱可视化（D3.js / ECharts）
- 增加更多图算法（社区发现、影响力传播）
- 接入真实业务系统 API（ERP、CRM、物流平台）
