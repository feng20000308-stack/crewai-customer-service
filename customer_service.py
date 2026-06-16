"""
多 Agent 智能客服系统
===================
基于 CrewAI + Neo4j 图数据库，多个 Agent 协作处理客户咨询。

Agent 角色：
1. 路由员 - 理解客户意图，分配给合适的专家
2. 产品顾问 - 回答产品相关问题（参数、价格、对比、推荐）
3. 订单管家 - 处理订单查询（状态、物流、历史订单）
4. 售后专员 - 处理退换货、投诉、售后政策咨询
"""

import os
import logging
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from neo4j import GraphDatabase

logging.getLogger().setLevel(logging.ERROR)

# ==================== 配置 ====================

os.environ["DASHSCOPE_API_KEY"] = os.getenv("DASHSCOPE_API_KEY", "sk-c0ea6827961b4b17b80dd8025785ea1c")
os.environ["DASHSCOPE_BASE_URL"] = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

llm = LLM(model="dashscope/qwen-plus")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "12345678")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


# ==================== 工具定义 ====================

# ---------- 产品工具 ----------

class SearchProductInput(BaseModel):
    keyword: str = Field(description="搜索关键词：产品名、类别、描述")

class SearchProductTool(BaseTool):
    name: str = "search_product"
    description: str = "根据关键词搜索产品，返回名称、价格、类别、库存、描述"
    args_schema: type[BaseModel] = SearchProductInput

    def _run(self, keyword: str) -> str:
        with driver.session() as session:
            result = session.run("""
                MATCH (n:Product)
                WHERE n.name CONTAINS $k OR n.category CONTAINS $k OR n.desc CONTAINS $k
                RETURN n.name AS name, n.price AS price, n.category AS category,
                       n.stock AS stock, n.desc AS desc
            """, k=keyword)
            products = [dict(r) for r in result]
            if not products:
                return f"未找到与 '{keyword}' 相关的产品"
            lines = []
            for p in products:
                lines.append(f"[{p['name']}] 价格:{p['price']}元 | 类别:{p['category']} | 库存:{p['stock']} | {p['desc']}")
            return "\n".join(lines)


class ListProductsInput(BaseModel):
    placeholder: str = Field(default="", description="无需填写")

class ListProductsTool(BaseTool):
    name: str = "list_all_products"
    description: str = "列出所有在售产品及其价格、库存信息"
    args_schema: type[BaseModel] = ListProductsInput

    def _run(self, placeholder: str = "") -> str:
        with driver.session() as session:
            result = session.run("""
                MATCH (n:Product)
                RETURN n.name AS name, n.price AS price, n.category AS category, n.stock AS stock
                ORDER BY n.price DESC
            """)
            lines = ["所有产品（按价格降序）："]
            for i, r in enumerate(result, 1):
                d = dict(r)
                lines.append(f"  {i}. {d['name']} - {d['price']}元 [{d['category']}] 库存:{d['stock']}")
            return "\n".join(lines)


class CompareProductsInput(BaseModel):
    names: str = Field(description="要对比的产品名，用逗号分隔，如 'iPhone 15,MacBook Pro'")

class CompareProductsTool(BaseTool):
    name: str = "compare_products"
    description: str = "对比多个产品的参数和价格"
    args_schema: type[BaseModel] = CompareProductsInput

    def _run(self, names: str) -> str:
        name_list = [n.strip() for n in names.split(",")]
        with driver.session() as session:
            result = session.run("""
                MATCH (n:Product)
                WHERE n.name IN $names
                RETURN n.name AS name, n.price AS price, n.category AS category,
                       n.stock AS stock, n.desc AS desc
                ORDER BY n.price DESC
            """, names=name_list)
            products = [dict(r) for r in result]
            if not products:
                return "未找到这些产品，请检查产品名称"
            lines = ["产品对比：", "-" * 50]
            for p in products:
                lines.append(f"  {p['name']}")
                lines.append(f"    价格: {p['price']}元 | 类别: {p['category']}")
                lines.append(f"    库存: {p['stock']} | 描述: {p['desc']}")
                lines.append("")
            return "\n".join(lines)


# ---------- 订单工具 ----------

class QueryOrderInput(BaseModel):
    query: str = Field(description="查询条件：订单号、用户名、或产品名")

class QueryOrderTool(BaseTool):
    name: str = "query_order"
    description: str = (
        "查询订单信息。可按订单号、用户名或产品名查询。"
        "返回订单号、金额、时间、状态、关联产品和用户。"
    )
    args_schema: type[BaseModel] = QueryOrderInput

    def _run(self, query: str) -> str:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User)-[:PURCHASED]->(o:Order)-[:CONTAINS]->(p:Product)
                WHERE o.order_no CONTAINS $q
                   OR u.name CONTAINS $q
                   OR p.name CONTAINS $q
                RETURN u.name AS user, u.level AS level, u.phone AS phone, u.address AS address,
                       o.order_no AS order_no, o.amount AS amount, o.time AS time, o.status AS status,
                       p.name AS product, p.price AS price
            """, q=query)
            orders = [dict(r) for r in result]
            if not orders:
                return f"未找到与 '{query}' 相关的订单"
            lines = []
            for o in orders:
                lines.append(
                    f"订单号: {o['order_no']}\n"
                    f"  客户: {o['user']}({o['level']}) | 电话: {o['phone']}\n"
                    f"  地址: {o['address']}\n"
                    f"  产品: {o['product']} | 金额: {o['amount']}元\n"
                    f"  下单时间: {o['time']} | 状态: {o['status']}"
                )
            return "\n\n".join(lines)


class UserOrderHistoryInput(BaseModel):
    username: str = Field(description="用户名，如 '张三'")

class UserOrderHistoryTool(BaseTool):
    name: str = "user_order_history"
    description: str = "查看某用户的全部历史订单"
    args_schema: type[BaseModel] = UserOrderHistoryInput

    def _run(self, username: str) -> str:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User {name: $name})-[:PURCHASED]->(o:Order)-[:CONTAINS]->(p:Product)
                RETURN o.order_no AS order_no, o.amount AS amount, o.time AS time,
                       o.status AS status, p.name AS product
                ORDER BY o.time DESC
            """, name=username)
            orders = [dict(r) for r in result]
            if not orders:
                return f"用户 '{username}' 没有历史订单"
            lines = [f"{username} 的历史订单："]
            for o in orders:
                lines.append(f"  {o['order_no']} | {o['product']} | {o['amount']}元 | {o['time']} | {o['status']}")
            return "\n".join(lines)


# ---------- 售后工具 ----------

class AfterSalesPolicyInput(BaseModel):
    product_name: str = Field(description="产品名称，如 'iPhone 15'")

class AfterSalesPolicyTool(BaseTool):
    name: str = "check_after_sales_policy"
    description: str = "查看某产品适用的售后政策（退换货规则、保修等）"
    args_schema: type[BaseModel] = AfterSalesPolicyInput

    def _run(self, product_name: str) -> str:
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Product)-[:HAS_RULE]->(r:AfterSalesRule)
                WHERE p.name CONTAINS $name
                RETURN p.name AS product, r.name AS rule, r.condition AS condition,
                       r.action AS action, r.need_reason AS need_reason
            """, name=product_name)
            rules = [dict(r) for r in result]
            if not rules:
                # 查看产品是否存在
                result2 = session.run("MATCH (p:Product) WHERE p.name CONTAINS $name RETURN p.name", name=product_name)
                if list(result2):
                    return f"该产品暂无特殊售后政策，适用通用售后规则"
                return f"未找到产品 '{product_name}'"
            lines = [f"{rules[0]['product']} 的售后政策："]
            for r in rules:
                reason = "（需提供理由）" if r["need_reason"] else ""
                lines.append(f"  [{r['rule']}] 条件: {r['condition']} → {r['action']}{reason}")
            return "\n".join(lines)


class ApplyAfterSalesInput(BaseModel):
    order_no: str = Field(description="订单号")
    reason: str = Field(default="", description="申请原因，如 '质量问题'、'不想要了' 等")

class ApplyAfterSalesTool(BaseTool):
    name: str = "apply_after_sales"
    description: str = "为订单申请售后服务，自动匹配适用的售后规则"
    args_schema: type[BaseModel] = ApplyAfterSalesInput

    def _run(self, order_no: str, reason: str = "") -> str:
        with driver.session() as session:
            # 查订单
            result = session.run("""
                MATCH (u:User)-[:PURCHASED]->(o:Order {order_no: $no})-[:CONTAINS]->(p:Product)
                RETURN u.name AS user, o.status AS status, o.time AS time,
                       p.name AS product, p.price AS price
            """, no=order_no)
            order = result.single()
            if not order:
                return f"未找到订单 {order_no}"

            order = dict(order)
            lines = [f"订单 {order_no} 售后申请："]
            lines.append(f"  客户: {order['user']} | 产品: {order['product']} | 金额: {order['price']}元")
            lines.append(f"  订单状态: {order['status']} | 下单时间: {order['time']}")

            # 查适用规则
            result = session.run("""
                MATCH (p:Product {name: $product})-[:HAS_RULE]->(r:AfterSalesRule)
                RETURN r.name AS rule, r.condition AS condition, r.action AS action, r.need_reason AS need_reason
            """, product=order["product"])
            rules = [dict(r) for r in result]

            if not rules:
                lines.append("\n该产品暂无适用的售后规则，需人工审核。")
                return "\n".join(lines)

            # 匹配规则
            matched = []
            reason_lower = reason.lower()
            for r in rules:
                if "质量" in reason_lower and "质量" in r["condition"]:
                    matched.append(r)
                elif "物流" in reason_lower and "物流" in r["condition"]:
                    matched.append(r)
                elif not r["need_reason"]:
                    matched.append(r)  # 无理由规则默认匹配

            if matched:
                lines.append("\n适用的售后规则：")
                for r in matched:
                    lines.append(f"  [{r['rule']}] {r['condition']} → {r['action']}")
            else:
                lines.append(f"\n未自动匹配到规则。可用规则：")
                for r in rules:
                    lines.append(f"  [{r['rule']}] {r['condition']}（需提供理由）")

            return "\n".join(lines)


# ---------- 通用查询工具 ----------

class CypherQueryInput(BaseModel):
    query: str = Field(description="Cypher 查询语句")

class CypherQueryTool(BaseTool):
    name: str = "query_neo4j"
    description: str = "执行自定义 Cypher 查询，用于处理其他工具无法覆盖的复杂查询"
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
                        if hasattr(val, "labels"):
                            props = {k: v for k, v in dict(val).items() if k != "embedding"}
                            row[key] = props
                        elif isinstance(val, list) and len(val) > 10:
                            row[key] = f"[向量,维度={len(val)}]"
                        else:
                            row[key] = val
                    records.append(row)
                return "\n".join([str(r) for r in records]) if records else "查询结果为空"
        except Exception as e:
            return f"查询错误: {e}"


# ---------- 图数据库特色工具（体现 Neo4j 优势）----------

class RecommendByPurchaseInput(BaseModel):
    product_name: str = Field(description="产品名称，如 'iPhone 15'")

class RecommendByPurchaseTool(BaseTool):
    name: str = "recommend_by_purchase"
    description: str = (
        "【图推荐】根据购买行为推荐产品。"
        "找出买了某产品的用户还买了哪些其他产品（协同过滤）。"
        "这是图数据库的经典场景，关系型数据库需要多次 JOIN 才能实现。"
    )
    args_schema: type[BaseModel] = RecommendByPurchaseInput

    def _run(self, product_name: str) -> str:
        with driver.session() as session:
            # 图查询：通过 User 节点做"二跳"查询
            # Product → 被购买 → User → 购买了 → 其他Product
            result = session.run("""
                MATCH (p:Product)<-[:CONTAINS]-(o:Order)<-[:PURCHASED]-(u:User)
                      -[:PURCHASED]->(o2:Order)-[:CONTAINS]->(other:Product)
                WHERE p.name CONTAINS $name AND other <> p
                RETURN other.name AS name, other.price AS price, other.category AS category,
                       count(DISTINCT u) AS buyer_count
                ORDER BY buyer_count DESC
            """, name=product_name)
            recs = [dict(r) for r in result]
            if not recs:
                return f"暂无基于 '{product_name}' 购买行为的推荐数据"
            lines = [f"买了 {product_name} 的用户还买了："]
            for r in recs:
                lines.append(f"  {r['name']} - {r['price']}元 [{r['category']}] ({r['buyer_count']}人也买了)")
            return "\n".join(lines)


class UserSimilarityInput(BaseModel):
    username: str = Field(description="用户名，如 '张三'")

class UserSimilarityTool(BaseTool):
    name: str = "find_similar_users"
    description: str = (
        "【图分析】找到与某用户购买行为相似的其他用户。"
        "通过共同购买的产品建立用户相似度，是社交推荐的基础。"
    )
    args_schema: type[BaseModel] = UserSimilarityInput

    def _run(self, username: str) -> str:
        with driver.session() as session:
            # 找共同购买了相同产品的用户
            result = session.run("""
                MATCH (u1:User {name: $name})-[:PURCHASED]->(o1:Order)-[:CONTAINS]->(p:Product)
                      <-[:CONTAINS]-(o2:Order)<-[:PURCHASED]-(u2:User)
                WHERE u1 <> u2
                RETURN u2.name AS name, u2.level AS level, u2.address AS address,
                       collect(DISTINCT p.name) AS common_products,
                       count(DISTINCT p) AS similarity
                ORDER BY similarity DESC
            """, name=username)
            users = [dict(r) for r in result]
            if not users:
                return f"暂未找到与 '{username}' 购买行为相似的用户"
            lines = [f"与 {username} 购买行为相似的用户："]
            for u in users:
                lines.append(f"  {u['name']}({u['level']}) - 共同购买: {', '.join(u['common_products'])}")
            return "\n".join(lines)


class ProductRelationGraphInput(BaseModel):
    product_name: str = Field(default="", description="产品名称（可选，不填则展示全图）")

class ProductRelationGraphTool(BaseTool):
    name: str = "show_product_relations"
    description: str = (
        "【图可视化】展示产品的关系网络：哪些用户买了、适用什么售后规则。"
        "体现图数据库的关系遍历优势。"
    )
    args_schema: type[BaseModel] = ProductRelationGraphInput

    def _run(self, product_name: str = "") -> str:
        with driver.session() as session:
            if product_name:
                result = session.run("""
                    MATCH (u:User)-[:PURCHASED]->(o:Order)-[:CONTAINS]->(p:Product)
                          -[:HAS_RULE]->(r:AfterSalesRule)
                    WHERE p.name CONTAINS $name
                    RETURN u.name AS user, u.level AS level,
                           o.order_no AS order, o.status AS status,
                           p.name AS product, p.price AS price,
                           r.name AS rule, r.action AS action
                """, name=product_name)
            else:
                result = session.run("""
                    MATCH (u:User)-[:PURCHASED]->(o:Order)-[:CONTAINS]->(p:Product)
                    OPTIONAL MATCH (p)-[:HAS_RULE]->(r:AfterSalesRule)
                    RETURN u.name AS user, u.level AS level,
                           o.order_no AS order, o.status AS status,
                           p.name AS product, p.price AS price,
                           r.name AS rule, r.action AS action
                """)

            records = [dict(r) for r in result]
            if not records:
                return "暂无数据"

            lines = ["产品关系图谱：", ""]
            for rec in records:
                rule_info = f" → 售后: [{rec['rule']}] {rec['action']}" if rec.get('rule') else ""
                lines.append(
                    f"  {rec['user']}({rec['level']})"
                    f" --购买--> {rec['order']}({rec['status']})"
                    f" --包含--> {rec['product']}({rec['price']}元)"
                    f"{rule_info}"
                )
            return "\n".join(lines)


# ---------- 业务操作工具（本地函数模拟）----------

import uuid as _uuid

# 模拟数据
_refunds_db = []
_coupons_db = []
_logistics_db = {
    "ORD20240101001": {
        "carrier": "顺丰速运", "tracking_no": "SF1234567890",
        "status": "运输中", "location": "北京分拣中心",
        "tracks": [
            {"time": "2024-01-01 10:00", "info": "商家已发货"},
            {"time": "2024-01-01 18:00", "info": "包裹已到达北京分拣中心"},
            {"time": "2024-01-02 08:00", "info": "包裹正在派送中"},
        ],
    },
    "ORD20240103001": {
        "carrier": "中通快递", "tracking_no": "ZT9876543210",
        "status": "待发货", "location": "商家仓库",
        "tracks": [{"time": "2024-01-03 09:00", "info": "订单已确认，等待发货"}],
    },
    "ORD20240107001": {
        "carrier": "京东物流", "tracking_no": "JD0011223344",
        "status": "已签收", "location": "广州市天河区",
        "tracks": [
            {"time": "2024-01-07 10:00", "info": "商家已发货"},
            {"time": "2024-01-08 06:00", "info": "包裹到达广州分拣中心"},
            {"time": "2024-01-08 14:00", "info": "快递员正在派送"},
            {"time": "2024-01-08 16:30", "info": "已签收，签收人：本人"},
        ],
    },
}
_recommendations_db = {
    "张三": [
        {"name": "AirPods Pro", "price": 1899, "reason": "iPhone 用户常搭配购买", "score": 0.95},
        {"name": "Apple Watch", "price": 2999, "reason": "苹果生态热门配件", "score": 0.82},
    ],
    "李四": [
        {"name": "iPhone 15", "price": 5999, "reason": "MacBook 用户常搭配购买", "score": 0.88},
        {"name": "iPad Air", "price": 4799, "reason": "生产力工具组合", "score": 0.75},
    ],
    "王五": [
        {"name": "MacBook Pro", "price": 12999, "reason": "iPhone + AirPods 用户升级选择", "score": 0.90},
        {"name": "Apple Watch", "price": 2999, "reason": "苹果全家桶推荐", "score": 0.78},
    ],
}


class ApplyRefundInput(BaseModel):
    order_no: str = Field(description="订单号")
    reason: str = Field(description="退款原因，如 '不想要了'、'质量问题'、'买错了'")

class ApplyRefundTool(BaseTool):
    name: str = "apply_refund"
    description: str = "为用户申请退款，返回退款单号和状态"
    args_schema: type[BaseModel] = ApplyRefundInput

    def _run(self, order_no: str, reason: str) -> str:
        refund_no = f"REF{_uuid.uuid4().hex[:8].upper()}"
        record = {"refund_no": refund_no, "order_no": order_no, "reason": reason, "status": "审核中"}
        _refunds_db.append(record)
        print(f"[退款申请] 订单:{order_no} 原因:{reason} -> 退款单:{refund_no}")
        return (
            f"退款申请已提交\n"
            f"  退款单号: {refund_no}\n"
            f"  订单号: {order_no}\n"
            f"  原因: {reason}\n"
            f"  状态: 审核中\n"
            f"  预计到账: 1-3个工作日"
        )


class QueryRefundInput(BaseModel):
    refund_no: str = Field(description="退款单号")

class QueryRefundTool(BaseTool):
    name: str = "query_refund"
    description: str = "查询退款申请的处理状态"
    args_schema: type[BaseModel] = QueryRefundInput

    def _run(self, refund_no: str) -> str:
        for r in _refunds_db:
            if r["refund_no"] == refund_no:
                return f"退款单 {refund_no}: 状态={r['status']}, 订单={r['order_no']}"
        return f"未找到退款单 {refund_no}"


class CancelOrderInput(BaseModel):
    order_no: str = Field(description="要取消的订单号")

class CancelOrderTool(BaseTool):
    name: str = "cancel_order"
    description: str = "取消用户的未完成订单"
    args_schema: type[BaseModel] = CancelOrderInput

    def _run(self, order_no: str) -> str:
        # 检查订单状态
        with driver.session() as session:
            result = session.run("""
                MATCH (o:Order {order_no: $no}) RETURN o.status AS status
            """, no=order_no)
            record = result.single()
            if not record:
                return f"订单 {order_no} 不存在"
            status = record["status"]
            if status == "已完成":
                return f"订单 {order_no} 已完成，无法取消。如需退货请申请退款。"
            # 更新状态
            session.run("""
                MATCH (o:Order {order_no: $no}) SET o.status = '已取消'
            """, no=order_no)
        print(f"[取消订单] 订单:{order_no} -> 已取消")
        return f"订单 {order_no} 已成功取消"


class TrackLogisticsInput(BaseModel):
    order_no: str = Field(description="订单号")

class TrackLogisticsTool(BaseTool):
    name: str = "track_logistics"
    description: str = "查询订单的物流信息，包括快递公司、运单号、物流轨迹"
    args_schema: type[BaseModel] = TrackLogisticsInput

    def _run(self, order_no: str) -> str:
        d = _logistics_db.get(order_no)
        if not d:
            return f"订单 {order_no} 暂无物流信息"
        lines = [
            f"物流信息 - 订单 {order_no}:",
            f"  快递: {d['carrier']} | 运单号: {d['tracking_no']}",
            f"  状态: {d['status']} | 当前位置: {d['location']}",
            "  物流轨迹:",
        ]
        for t in d["tracks"]:
            lines.append(f"    [{t['time']}] {t['info']}")
        print(f"[物流查询] 订单:{order_no} 状态:{d['status']}")
        return "\n".join(lines)


class GrantCouponInput(BaseModel):
    user_name: str = Field(description="用户名")
    amount: float = Field(description="优惠券金额，如 50、100")
    reason: str = Field(description="发放原因，如 '物流延迟补偿'、'售后安抚'")

class GrantCouponTool(BaseTool):
    name: str = "grant_coupon"
    description: str = "向用户发放优惠券，用于售后补偿"
    args_schema: type[BaseModel] = GrantCouponInput

    def _run(self, user_name: str, amount: float, reason: str) -> str:
        coupon_no = f"CPN{_uuid.uuid4().hex[:8].upper()}"
        _coupons_db.append({"coupon_no": coupon_no, "user": user_name, "amount": amount})
        print(f"[发放优惠券] 用户:{user_name} 金额:{amount}元 原因:{reason} -> 券号:{coupon_no}")
        return f"优惠券已发放: {coupon_no} | {user_name} | {amount}元 | 有效期至 2024-12-31"


class GetRecommendationInput(BaseModel):
    user_name: str = Field(description="用户名，如 '张三'")

class GetRecommendationTool(BaseTool):
    name: str = "get_recommendation"
    description: str = "获取用户的个性化产品推荐，基于购买历史"
    args_schema: type[BaseModel] = GetRecommendationInput

    def _run(self, user_name: str) -> str:
        data = _recommendations_db.get(user_name, [])
        if not data:
            return f"暂无 {user_name} 的推荐数据"
        lines = [f"为 {user_name} 推荐的产品："]
        for r in data:
            lines.append(f"  {r['name']} - {r['price']}元 ({r['reason']}, 匹配度:{r['score']})")
        print(f"[个性化推荐] 用户:{user_name} -> {len(data)}个推荐")
        return "\n".join(lines)


# ==================== Agent 定义 ====================

# 1. 产品顾问
product_advisor = Agent(
    role="产品顾问",
    goal="准确回答客户关于产品的所有问题，包括价格、参数、对比、推荐",
    backstory=(
        "你是一位专业的产品顾问，对所有在售产品了如指掌。"
        "你能根据客户需求推荐最合适的产品，并清晰对比不同产品的优劣。"
        "回答简洁专业，重点突出价格和核心卖点。"
    ),
    verbose=False,
    allow_delegation=False,
    llm=llm,
    tools=[SearchProductTool(), ListProductsTool(), CompareProductsTool(),
           RecommendByPurchaseTool(), ProductRelationGraphTool(),
           GetRecommendationTool()],
)

# 2. 订单管家
order_manager = Agent(
    role="订单管家",
    goal="帮客户查询订单状态、物流信息、历史订单，提供准确的订单信息",
    backstory=(
        "你是一位细心的订单管家，能快速查到任何订单的详细信息。"
        "你会主动告知订单状态、预计时间，并提醒客户需要注意的事项。"
    ),
    verbose=False,
    allow_delegation=False,
    llm=llm,
    # memory=True,
    tools=[QueryOrderTool(), UserOrderHistoryTool(), TrackLogisticsTool()],
)

# 3. 售后专员
after_sales = Agent(
    role="售后专员",
    goal="处理客户的售后需求：退换货、投诉、政策咨询，让客户满意",
    backstory=(
        "你是一位耐心的售后专员，熟悉所有售后政策和流程。"
        "你会先了解客户问题，再查询适用的售后规则，给出最优解决方案。"
        "遇到无法自动处理的问题，会建议转人工客服。"
        "态度温和，以解决问题为导向。"
    ),
    verbose=False,
    allow_delegation=False,
    llm=llm,
    # memory=True,
    tools=[AfterSalesPolicyTool(), ApplyAfterSalesTool(), QueryOrderTool(),
           ApplyRefundTool(), CancelOrderTool(), GrantCouponTool()],
)

# 4. 综合客服（兜底）
general_cs = Agent(
    role="综合客服",
    goal="处理不属于产品、订单、售后的其他问题，或需要综合信息的复杂问题",
    backstory=(
        "你是一位经验丰富的综合客服，能处理各种复杂或跨领域的问题。"
        "你可以同时查询产品、订单、售后信息，给出全面的回答。"
        "如果问题超出能力范围，会诚实告知并建议联系人工客服。"
    ),
    verbose=False,
    allow_delegation=False,
    llm=llm,
    tools=[SearchProductTool(), QueryOrderTool(), AfterSalesPolicyTool(),
           UserOrderHistoryTool(), ListProductsTool(), CypherQueryTool(),
           RecommendByPurchaseTool(), UserSimilarityTool(), ProductRelationGraphTool(),
           ApplyRefundTool(), CancelOrderTool(), TrackLogisticsTool(),
           GrantCouponTool(), GetRecommendationTool()],
)


# ==================== Task 定义 ====================

product_task = Task(
    description=(
        "客户咨询（产品类）：{question}\n\n"
        "请：\n"
        "1. 用工具查询相关产品信息\n"
        "2. 准确回答客户问题\n"
        "3. 如有多款产品，主动做对比\n"
        "4. 适当推荐，但不要过度推销"
    ),
    expected_output="专业、简洁的产品咨询回答",
    agent=product_advisor,
)

order_task = Task(
    description=(
        "客户咨询（订单类）：{question}\n\n"
        "请：\n"
        "1. 用工具查询订单信息\n"
        "2. 告知订单状态和关键信息\n"
        "3. 如果有异常（如延迟），主动提醒\n"
        "4. 提供后续操作建议"
    ),
    expected_output="清晰的订单查询结果和建议",
    agent=order_manager,
)

after_sales_task = Task(
    description=(
        "客户咨询（售后类）：{question}\n\n"
        "请：\n"
        "1. 了解客户的具体问题\n"
        "2. 查询适用的售后政策\n"
        "3. 给出解决方案\n"
        "4. 如需申请售后，帮客户操作\n"
        "5. 态度温和，以解决问题为导向"
    ),
    expected_output="售后问题的解决方案，附带适用政策说明",
    agent=after_sales,
)

general_task = Task(
    description=(
        "客户咨询：{question}\n\n"
        "这是一个综合问题，请：\n"
        "1. 分析客户的真实需求\n"
        "2. 用工具查询相关信息（产品、订单、售后等）\n"
        "3. 给出全面、准确的回答\n"
        "4. 如涉及多个方面，分点说明"
    ),
    expected_output="全面、专业的客服回答",
    agent=general_cs,
)


# ==================== 路由逻辑 ====================

def classify_intent(question: str) -> str:
    """用 LLM 做意图分类"""
    import json
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY", "sk-c0ea6827961b4b17b80dd8025785ea1c"),
        base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": (
                "你是一个意图分类器。根据用户的客服咨询内容，判断意图类别。\n"
                "只返回以下JSON格式，不要有其他内容：\n"
                '{"intent": "类别"}\n\n'
                "可选类别及示例：\n\n"
                "1. product - 产品咨询\n"
                "   例：iPhone 15 多少钱？/ 有什么手机推荐？/ 帮我对比 MacBook 和 iPad / 你们卖什么产品\n\n"
                "2. order - 订单查询\n"
                "   例：我的订单到哪了？/ 张三有哪些订单？/ ORD20240101001 发货了吗？/ 查一下我的历史订单\n\n"
                "3. after_sales - 售后服务\n"
                "   例：我想退货 / 耳机坏了怎么办？/ 订单 ORD001 有质量问题要退款 / 怎么保修？/ 我要投诉\n\n"
                "4. general - 其他\n"
                "   例：你好 / 今天天气怎么样？/ 你们公司地址在哪？\n\n"
                "注意：如果同时涉及订单和售后（如\"订单XXX想退货\"），归为 after_sales。"
            )},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )

    try:
        result = json.loads(response.choices[0].message.content.strip())
        intent = result.get("intent", "general")
        if intent in ("product", "order", "after_sales", "general"):
            return intent
    except (json.JSONDecodeError, KeyError):
        pass
    return "general"


def run_customer_service(question: str) -> str:
    """根据意图路由到对应的 Agent"""
    intent = classify_intent(question)
    task_map = {
        "product": product_task,
        "order": order_task,
        "after_sales": after_sales_task,
        "general": general_task,
    }
    agent_map = {
        "product": product_advisor,
        "order": order_manager,
        "after_sales": after_sales,
        "general": general_cs,
    }
    intent_names = {
        "product": "产品咨询",
        "order": "订单查询",
        "after_sales": "售后服务",
        "general": "综合咨询",
    }

    print(f"[路由] 识别意图: {intent_names[intent]}")

    crew = Crew(
        agents=[agent_map[intent]],
        tasks=[task_map[intent]],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff(inputs={"question": question})
    return result


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("  智能客服系统已启动（输入 quit 退出）")
    print("  可以问：产品信息、订单查询、售后问题、综合咨询")
    print("=" * 60)

    # 演示问题
    demo_questions = [
        "iPhone 15 多少钱？有什么特点？",
        "我的订单 ORD20240101001 想退货，因为质量问题",
        "帮我查一下订单 ORD20240101001 的物流",
        "张三有什么个性化推荐？",
    ]

    for q in demo_questions:
        print(f"\n{'='*60}")
        print(f"[客户] {q}")
        print("="*60)
        answer = run_customer_service(q)
        print(f"\n[客服] {answer}")
        print("-"*60)

    # 交互模式
    print("\n\n进入交互模式（输入 quit 退出）：")
    while True:
        question = input("\n[客户] ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if not question:
            continue
        answer = run_customer_service(question)
        print(f"\n[客服] {answer}")

    driver.close()
