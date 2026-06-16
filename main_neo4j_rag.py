import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from neo4j import GraphDatabase

# 千问 API 配置
os.environ["DASHSCOPE_API_KEY"] = "sk-c0ea6827961b4b17b80dd8025785ea1c"
os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

llm = LLM(model="dashscope/qwen-plus")

# ==================== Neo4j 连接 ====================

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "12345678"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


# ==================== 工具 ====================

# 工具1：Cypher 查询
class CypherQueryInput(BaseModel):
    query: str = Field(description="Cypher 查询语句，例如 MATCH (n:Product) RETURN n")

class CypherQueryTool(BaseTool):
    name: str = "query_neo4j"
    description: str = (
        "执行 Cypher 查询语句，从 Neo4j 图数据库中检索数据。"
        "支持查询产品、用户、订单、售后规则等。"
        "注意：不要对 embedding 属性使用 toString()。"
    )
    args_schema: type[BaseModel] = CypherQueryInput

    def _run(self, query: str) -> str:
        try:
            with driver.session() as session:
                result = session.run(query)
                records = []
                for r in result:
                    row = {}
                    for key in r.keys():
                        val = r[key]
                        # 处理节点类型
                        if hasattr(val, "labels"):
                            props = {k: v for k, v in dict(val).items() if k != "embedding"}
                            row[key] = {"labels": list(val.labels), "properties": props}
                        # 处理关系类型
                        elif hasattr(val, "type"):
                            row[key] = {"type": val.type, "properties": dict(val)}
                        # 处理普通值（跳过 embedding 数组）
                        elif isinstance(val, list) and len(val) > 10:
                            row[key] = f"[向量，维度={len(val)}]"
                        else:
                            row[key] = val
                    records.append(row)
                if not records:
                    return "查询结果为空"
                return "\n".join([str(r) for r in records])
        except Exception as e:
            return f"查询错误：{e}"


# 工具2：搜索产品
class SearchProductInput(BaseModel):
    keyword: str = Field(description="搜索关键词，如产品名、类别、描述等")

class SearchProductTool(BaseTool):
    name: str = "search_product"
    description: str = "根据关键词搜索产品信息，支持按名称、类别、描述模糊匹配"
    args_schema: type[BaseModel] = SearchProductInput

    def _run(self, keyword: str) -> str:
        with driver.session() as session:
            result = session.run("""
                MATCH (n:Product)
                WHERE n.name CONTAINS $keyword
                   OR n.category CONTAINS $keyword
                   OR n.desc CONTAINS $keyword
                RETURN n.name AS name, n.price AS price, n.category AS category,
                       n.stock AS stock, n.desc AS desc
            """, keyword=keyword)
            products = [dict(r) for r in result]
            if not products:
                return f"没有找到包含 '{keyword}' 的产品"
            output = []
            for p in products:
                output.append(
                    f"产品: {p['name']}\n"
                    f"  价格: {p['price']}元\n"
                    f"  类别: {p['category']}\n"
                    f"  库存: {p['stock']}\n"
                    f"  描述: {p['desc']}"
                )
            return "\n\n".join(output)


# 工具3：查看数据库结构
class ExploreGraphInput(BaseModel):
    placeholder: str = Field(default="无", description="无需填写")

class ExploreGraphTool(BaseTool):
    name: str = "explore_graph"
    description: str = "查看 Neo4j 数据库的整体结构：有哪些标签、每个标签有多少节点、关系类型等"
    args_schema: type[BaseModel] = ExploreGraphInput

    def _run(self, placeholder: str = "无") -> str:
        with driver.session() as session:
            output = []

            # 标签和节点数
            result = session.run("MATCH (n) RETURN labels(n) AS label, count(n) AS cnt ORDER BY cnt DESC")
            output.append("节点统计:")
            for r in result:
                output.append(f"  {r['label']}: {r['cnt']}个")

            # 关系类型
            result = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt ORDER BY cnt DESC")
            output.append("\n关系统计:")
            for r in result:
                output.append(f"  {r['type']}: {r['cnt']}条")

            return "\n".join(output)


# ==================== Agent ====================

data_agent = Agent(
    role="Neo4j 图数据库分析师",
    goal="理解用户的自然语言问题，构造合适的 Cypher 查询语句，从 Neo4j 中获取数据并给出准确回答",
    backstory=(
        "你是一位精通 Neo4j 和 Cypher 查询语言的数据分析师。"
        "你能理解用户的自然语言需求，转化为精确的图数据库查询。"
        "你会先了解数据库结构，再构造查询，最后用通俗语言解释结果。"
        "注意：不要对 embedding 属性使用 toString()，那是向量数据。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[CypherQueryTool(), SearchProductTool(), ExploreGraphTool()],
)

# ==================== Task ====================

query_task = Task(
    description=(
        "用户问题：{question}\n\n"
        "请按以下步骤回答：\n"
        "1. 如果不了解数据库结构，先用 explore_graph 工具查看\n"
        "2. 根据问题构造合适的查询（用 search_product 或 query_neo4j）\n"
        "3. 用通俗易懂的中文回答用户，附上关键数据\n"
        "4. 如果涉及多个实体的关系，说明它们之间的关联"
    ),
    expected_output="基于 Neo4j 数据的准确回答，用中文呈现，包含关键数据",
    agent=data_agent,
)

# ==================== Crew ====================

crew = Crew(
    agents=[data_agent],
    tasks=[query_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    questions = [
        "iPhone15 多少钱？",
        "帮我查一下所有苹果产品，按价格从高到低排列",
        "库存最多的产品是什么？",
        "有哪些售后规则？",
    ]

    for q in questions:
        print(f"\n{'='*60}")
        print(f"[问] {q}")
        print("="*60)
        result = crew.kickoff(inputs={"question": q})
        print(f"\n[答] {result}")
        print("-"*60)

    driver.close()
