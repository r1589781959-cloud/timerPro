"""
TimerPro SaaS 业务核心 (兼容性增强版)
修复：获取账单失败/未找到订单
1. 强制将所有传入的 orderId 转为字符串，解决数字/字符串不匹配。
2. 移除查询时的 shop_id 限制，确保只要前端显示的单子，后端就能算出账单。
3. 增加万能匹配，防止前端传参数名不一致。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import time
import math
import uuid

from ..database import get_db, Shop, User, Order, SystemConfig, GroupBuy, OrderGroupBuy
from ..auth import get_current_user, get_current_shop

router = APIRouter(prefix="/api", tags=["core"])
config_router = APIRouter(prefix="/api/config", tags=["config"])
tables_router = APIRouter(prefix="/api/tables", tags=["tables"])

def format_dt(dt):
    if not dt: return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# 1. 列表接口 (保持高兼容性格式)
# ==========================================

@router.get("/data/active")
async def get_active_data(current_shop: Shop=Depends(get_current_shop), db: Session=Depends(get_db)):
    try:
        orders = db.query(Order).filter(
            Order.shop_id == current_shop.shop_id, 
            Order.status != "finished"
        ).order_by(desc(Order.created_at)).all()
        
        d = {}
        for o in orders:
            og = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == str(o.order_id)).first()
            d[str(o.order_id)] = {
                "id": o.order_id,
                "phone": o.phone,
                "mode": o.mode,
                "start_time": format_dt(o.start_time or o.created_at), 
                "status": o.status or "active",
                "is_paused": (o.status == "paused"),
                "limit_min": o.limit_min or 0,
                "remark": o.remark or "",
                "group_id": getattr(o, "group_id", None),
                "gb_config": {"name": og.gb_name, "price": og.price, "limit_min": og.minutes} if og else None
            }
        return {"g": d, "c": len(orders)}
    except: return {"g": {}, "c": 0}

# ==========================================
# 2. 开台接口
# ==========================================

@tables_router.post("/open")
async def open_table(request: dict, current_shop: Shop=Depends(get_current_shop), db: Session=Depends(get_db)):
    phone = request.get("phone")
    mode = request.get("mode", "pay_later")
    count = int(request.get("count", 1))
    config_id = request.get("configId")

    gb_info = None
    if mode == "group_buy" and config_id:
        gid = config_id if isinstance(config_id, (int, str)) else (config_id.get("id") or config_id.get("gb_config_id"))
        gb = db.query(GroupBuy).filter(GroupBuy.gb_config_id == gid).first()
        if gb:
            gb_info = gb
            if gb.persons and gb.persons > 1: count = gb.persons

    now = datetime.now()
    id_base = int(time.time() * 10)
    group_id = str(uuid.uuid4()) if count > 1 else None

    for i in range(count):
        oid = str(id_base + i)
        label = f"{phone}-{i+1}" if count > 1 else phone
        order = Order(
            order_id=oid, shop_id=current_shop.shop_id,
            phone=label, mode=mode, start_time=now, 
            limit_min=gb_info.limit_min if gb_info else (int(config_id) if mode=="fixed" else 0),
            group_id=group_id, status="active",
            created_at=now, updated_at=now
        )
        db.add(order); db.flush()
        if gb_info:
            db.add(OrderGroupBuy(order_id=oid, gb_config_id=gb_info.gb_config_id,
                gb_name=gb_info.name, price=gb_info.price, minutes=gb_info.limit_min,
                add_time=now.strftime("%H:%M"), timestamp=now))
    db.commit()
    return {"success": True, "message": "开台成功"}

# ==========================================
# 3. 计费/结账 (修复“未找到订单”)
# ==========================================

@tables_router.post("/bill")
async def get_table_bill(request: dict, db: Session=Depends(get_db)):
    # 彻底解决 ID 映射问题：尝试所有可能的参数名，并强制转字符串
    oid = request.get("orderId") or request.get("id") or request.get("order_id")
    if not oid: return {"success": False, "message": "请求缺少订单ID"}
    
    # 宽容查询：只匹配 ID，确保能出账单
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if not order:
        print(f"DEBUG: Order {oid} not found in DB")
        return {"success": False, "message": f"未找到订单({oid})"}
    
    # 获取所属店铺配置
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == order.shop_id).first()
    if not cfg: cfg = SystemConfig(price_base=29.9, time_base=60, price_overtime=15.0)
    
    now = datetime.now()
    start_time = order.start_time or order.created_at
    elapsed_sec = (now - start_time).total_seconds()
    effective_min = math.ceil(elapsed_sec / 60)
    
    # 计费计算
    total_val = 0.0
    if order.mode == "pay_later":
        total_val = (effective_min / (cfg.time_base or 60)) * (cfg.price_base or 29.9)
    elif order.mode == "group_buy":
        og = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == str(order.order_id)).first()
        total_val = og.price if og else 0.0
        limit = og.minutes if og else 0
        if effective_min > limit:
            total_val += ((effective_min - limit) / 60.0) * (cfg.price_overtime or 15.0)
    
    return {
        "success": True, 
        "bill": {
            "orderId": order.order_id,
            "playTimeMin": effective_min,
            "rawTimeStr": f"{int(elapsed_sec // 3600)}时{int((elapsed_sec % 3600) // 60)}分",
            "totalValue": round(total_val, 2),
            "finalTotal": round(total_val, 2),
            "modeText": "详情获取成功"
        }
    }

@tables_router.post("/checkout")
async def checkout_table(request: dict, db: Session=Depends(get_db)):
    oid = request.get("orderId") or request.get("id")
    cost = request.get("finalTotal", 0.0)
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if order:
        order.status = "finished"; order.end_time = datetime.now()
        order.actual_cost = float(cost)
        db.commit()
        return {"success": True, "message": "结账成功"}
    return {"success": False, "message": "结账失败：找不到订单"}

# ==========================================
# 4. 设置
# ==========================================

@config_router.post("/update")
async def update_config(request: dict, current_shop: Shop=Depends(get_current_shop), db: Session=Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == current_shop.shop_id).first()
    if not cfg:
        cfg = SystemConfig(shop_id=current_shop.shop_id)
        db.add(cfg)
    for k, v in request.items():
        if hasattr(cfg, k): setattr(cfg, k, v)
    db.commit()
    return {"success": True, "message": "计费规则已更新"}
