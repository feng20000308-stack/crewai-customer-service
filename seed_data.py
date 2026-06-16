"""初始化 Neo4j 测试数据"""
import os
import time
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "12345678")


def wait_for_neo4j(max_retries=30):
    """等待 Neo4j 启动"""
    for i in range(max_retries):
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            print("[seed] Neo4j 连接成功")
            return True
        except Exception:
            print(f"[seed] 等待 Neo4j 启动... ({i+1}/{max_retries})")
            time.sleep(2)
    raise RuntimeError("Neo4j 启动超时")


def seed():
    wait_for_neo4j()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        # 清空旧数据
        session.run("MATCH (n) DETACH DELETE n")

        # 创建产品
        products = [
            {"name": "iPhone 15", "price": 5999, "category": "手机", "stock": 100, "desc": "苹果最新款手机"},
            {"name": "MacBook Pro", "price": 12999, "category": "电脑", "stock": 50, "desc": "苹果笔记本电脑"},
            {"name": "AirPods Pro", "price": 1899, "category": "配件", "stock": 200, "desc": "苹果无线降噪耳机"},
            {"name": "iPad Air", "price": 4799, "category": "平板", "stock": 80, "desc": "苹果平板电脑"},
            {"name": "Apple Watch", "price": 2999, "category": "配件", "stock": 150, "desc": "苹果智能手表"},
        ]
        for p in products:
            session.run("CREATE (p:Product {name: $name, price: $price, category: $category, stock: $stock, desc: $desc})", **p)
        print(f"[seed] 创建 {len(products)} 个产品")

        # 创建用户
        users = [
            {"name": "张三", "phone": "13800138001", "address": "北京市朝阳区", "level": "VIP"},
            {"name": "李四", "phone": "13800138002", "address": "上海市浦东新区", "level": "普通"},
            {"name": "王五", "phone": "13800138003", "address": "广州市天河区", "level": "VIP"},
        ]
        for u in users:
            session.run("CREATE (u:User {name: $name, phone: $phone, address: $address, level: $level})", **u)
        print(f"[seed] 创建 {len(users)} 个用户")

        # 创建售后规则
        rules = [
            {"name": "七天无理由", "condition": "签收7天内", "action": "直接退款", "need_reason": False},
            {"name": "质量问题", "condition": "商品有质量问题", "action": "换货或退款", "need_reason": True},
            {"name": "物流问题", "condition": "物流延迟超过3天", "action": "补偿优惠券", "need_reason": False},
        ]
        for r in rules:
            session.run("CREATE (r:AfterSalesRule {name: $name, condition: $condition, action: $action, need_reason: $need_reason})", **r)
        print(f"[seed] 创建 {len(rules)} 条售后规则")

        # 创建订单和关系
        orders = [
            {"user": "张三", "order_no": "ORD20240101001", "amount": 5999, "time": "2024-01-01", "status": "已发货", "product": "iPhone 15"},
            {"user": "张三", "order_no": "ORD20240103001", "amount": 1899, "time": "2024-01-03", "status": "待发货", "product": "AirPods Pro"},
            {"user": "张三", "order_no": "ORD20240106001", "amount": 12999, "time": "2024-01-06", "status": "已完成", "product": "MacBook Pro"},
            {"user": "李四", "order_no": "ORD20240102001", "amount": 12999, "time": "2024-01-02", "status": "已完成", "product": "MacBook Pro"},
            {"user": "李四", "order_no": "ORD20240105001", "amount": 1899, "time": "2024-01-05", "status": "已完成", "product": "AirPods Pro"},
            {"user": "王五", "order_no": "ORD20240104001", "amount": 5999, "time": "2024-01-04", "status": "已完成", "product": "iPhone 15"},
            {"user": "王五", "order_no": "ORD20240107001", "amount": 1899, "time": "2024-01-07", "status": "已发货", "product": "AirPods Pro"},
        ]
        for o in orders:
            session.run("""
                MATCH (u:User {name: $user}), (p:Product {name: $product})
                CREATE (o:Order {order_no: $order_no, amount: $amount, time: $time, status: $status})
                CREATE (u)-[:PURCHASED]->(o)-[:CONTAINS]->(p)
            """, **o)
        print(f"[seed] 创建 {len(orders)} 个订单")

        # 产品-售后规则关系
        product_rules = {
            "iPhone 15": ["七天无理由", "质量问题"],
            "AirPods Pro": ["七天无理由", "质量问题"],
            "MacBook Pro": ["七天无理由", "质量问题"],
            "iPad Air": ["七天无理由", "质量问题"],
            "Apple Watch": ["七天无理由", "质量问题", "物流问题"],
        }
        for product, rule_names in product_rules.items():
            for rule in rule_names:
                session.run("""
                    MATCH (p:Product {name: $product}), (r:AfterSalesRule {name: $rule})
                    CREATE (p)-[:HAS_RULE]->(r)
                """, product=product, rule=rule)
        print("[seed] 创建产品-售后规则关系")

    driver.close()
    print("[seed] 数据初始化完成!")


if __name__ == "__main__":
    seed()
