# 智能客服系统

基于 CrewAI + Neo4j 图数据库的多 Agent 智能客服系统。

## 架构

```
用户输入 → LLM意图分类 → 路由到对应Agent → Neo4j图查询 → 中文回答
```

### Agent 角色
- **产品顾问** — 产品价格、参数、对比、推荐
- **订单管家** — 订单状态、物流、历史查询
- **售后专员** — 退换货、投诉、售后政策
- **综合客服** — 兜底，处理复杂/跨领域问题

### 图数据库特色
- 协同过滤推荐（买了X的人还买了什么）
- 用户相似度分析（共同购买行为）
- 产品关系图谱（用户→订单→产品→售后规则）

## 快速启动

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd crewai

# 2. 设置环境变量
export DASHSCOPE_API_KEY=your-api-key

# 3. 启动
docker compose up -d

# 4. 进入交互模式
docker compose attach customer-service
```

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 Neo4j（需要本地有 Neo4j 5.x）

# 3. 初始化数据
python seed_data.py

# 4. 运行
python customer_service.py
```

## 项目结构

```
├── customer_service.py  # 主程序（Agent + 工具 + 路由）
├── seed_data.py         # Neo4j 数据初始化
├── requirements.txt     # Python 依赖
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose 编排
└── README.md
```

## 技术栈

- **CrewAI** — 多 Agent 协作框架
- **Neo4j 5.x** — 图数据库（原生向量索引）
- **DashScope (千问)** — LLM
- **Docker** — 容器化部署
