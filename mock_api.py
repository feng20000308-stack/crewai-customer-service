"""
模拟真实业务 API
================
模拟电商系统的后端接口，Agent 通过工具调用这些接口完成业务操作。
实际项目中替换为真实 API 地址即可。
"""

import uuid
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="电商模拟 API")


# ==================== 数据模型 ====================

class RefundRequest(BaseModel):
    order_no: str
    reason: str
    amount: float = 0  # 0 表示全额退款

class CancelOrderRequest(BaseModel):
    order_no: str

class CreateOrderRequest(BaseModel):
    user_name: str
    product_name: str

class LogisticsQuery(BaseModel):
    order_no: str

class CouponRequest(BaseModel):
    user_name: str
    amount: float
    reason: str


# ==================== 模拟数据存储 ====================

refunds_db = []
coupons_db = []
orders_extra = {}  # 额外订单状态


# ==================== API 接口 ====================

@app.post("/api/refund/apply")
async def apply_refund(req: RefundRequest):
    """申请退款"""
    refund_no = f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
    refund = {
        "refund_no": refund_no,
        "order_no": req.order_no,
        "reason": req.reason,
        "amount": req.amount,
        "status": "审核中",
        "created_at": datetime.now().isoformat(),
        "estimated_time": "1-3个工作日",
    }
    refunds_db.append(refund)
    return {
        "code": 200,
        "message": "退款申请已提交",
        "data": refund,
    }


@app.get("/api/refund/status/{refund_no}")
async def refund_status(refund_no: str):
    """查询退款状态"""
    for r in refunds_db:
        if r["refund_no"] == refund_no:
            return {"code": 200, "data": r}
    return {"code": 404, "message": "退款单不存在"}


@app.post("/api/order/cancel")
async def cancel_order(req: CancelOrderRequest):
    """取消订单"""
    return {
        "code": 200,
        "message": f"订单 {req.order_no} 已取消",
        "data": {
            "order_no": req.order_no,
            "status": "已取消",
            "cancelled_at": datetime.now().isoformat(),
        },
    }


@app.post("/api/order/create")
async def create_order(req: CreateOrderRequest):
    """创建订单"""
    order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
    return {
        "code": 200,
        "message": "订单创建成功",
        "data": {
            "order_no": order_no,
            "user_name": req.user_name,
            "product_name": req.product_name,
            "status": "待支付",
            "created_at": datetime.now().isoformat(),
        },
    }


@app.post("/api/logistics/track")
async def track_logistics(req: LogisticsQuery):
    """物流追踪"""
    # 模拟物流信息
    logistics_data = {
        "ORD20240101001": {
            "order_no": "ORD20240101001",
            "carrier": "顺丰速运",
            "tracking_no": "SF1234567890",
            "status": "运输中",
            "current_location": "北京分拣中心",
            "tracks": [
                {"time": "2024-01-01 10:00", "info": "商家已发货"},
                {"time": "2024-01-01 18:00", "info": "包裹已到达北京分拣中心"},
                {"time": "2024-01-02 08:00", "info": "包裹正在派送中"},
            ],
        },
        "ORD20240103001": {
            "order_no": "ORD20240103001",
            "carrier": "中通快递",
            "tracking_no": "ZT9876543210",
            "status": "待发货",
            "current_location": "商家仓库",
            "tracks": [
                {"time": "2024-01-03 09:00", "info": "订单已确认，等待发货"},
            ],
        },
        "ORD20240107001": {
            "order_no": "ORD20240107001",
            "carrier": "京东物流",
            "tracking_no": "JD0011223344",
            "status": "已签收",
            "current_location": "广州市天河区",
            "tracks": [
                {"time": "2024-01-07 10:00", "info": "商家已发货"},
                {"time": "2024-01-08 06:00", "info": "包裹到达广州分拣中心"},
                {"time": "2024-01-08 14:00", "info": "快递员正在派送"},
                {"time": "2024-01-08 16:30", "info": "已签收，签收人：本人"},
            ],
        },
    }
    data = logistics_data.get(req.order_no)
    if data:
        return {"code": 200, "data": data}
    return {"code": 404, "message": f"订单 {req.order_no} 暂无物流信息"}


@app.post("/api/coupon/grant")
async def grant_coupon(req: CouponRequest):
    """发放优惠券"""
    coupon_no = f"CPN{uuid.uuid4().hex[:8].upper()}"
    coupon = {
        "coupon_no": coupon_no,
        "user_name": req.user_name,
        "amount": req.amount,
        "reason": req.reason,
        "valid_until": "2024-12-31",
        "status": "已发放",
    }
    coupons_db.append(coupon)
    return {
        "code": 200,
        "message": f"已向 {req.user_name} 发放 {req.amount} 元优惠券",
        "data": coupon,
    }


@app.get("/api/product/recommend/{user_name}")
async def recommend(user_name: str):
    """个性化推荐（基于购买历史）"""
    # 模拟推荐数据
    recommendations = {
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
    data = recommendations.get(user_name, [])
    return {"code": 200, "data": data}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
