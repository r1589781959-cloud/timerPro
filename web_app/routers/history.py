"""
TimerPro SaaS - 历史流水 API
从 orders 表中查询 status=finished 的订单, 构造前端历史页面所需的字段
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import math

try:
    from ..database import get_db, Order, OrderPauseLog, OrderAddTime, OrderGroupBuy, GroupBuy, SystemConfig, Shop
    from ..routers.orders import get_overtime_cost_logic, get_current_shop
except ImportError:
    from database import get_db, Order, OrderPauseLog, OrderAddTime, OrderGroupBuy, GroupBuy, SystemConfig, Shop
    from routers.orders import get_overtime_cost_logic, get_current_shop

history_router = APIRouter(prefix="/api/history", tags=["history"])


def build_history_record(order: Order, db: Session, cfg: SystemConfig) -> dict:
    """将一条已结账订单构建为前端历史记录格式"""
    start_time = order.start_time or order.created_at or datetime.now()
    end_time = order.end_time or datetime.now()
    
    # 暂停
    pauses = db.query(OrderPauseLog).filter(OrderPauseLog.order_id == order.order_id).all()
    total_pause_sec = sum([p.pause_seconds or 0 for p in pauses if p.pause_end])
    
    # 加时
    added_times = db.query(OrderAddTime).filter(OrderAddTime.order_id == order.order_id).all()
    added_time_min = sum([a.minutes or 0 for a in added_times])
    
    # 团购
    all_gbs = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == order.order_id).order_by(OrderGroupBuy.id).all()
    
    # 时长计算
    raw_duration_sec = (end_time - start_time).total_seconds()
    effective_duration_sec = max(0, raw_duration_sec - total_pause_sec)
    minutes = effective_duration_sec / 60.0
    
    # 模式文本
    mode_text = order.mode
    if order.mode == "pay_later": mode_text = "先玩后付"
    elif order.mode == "fixed": mode_text = "普通定额"
    elif order.mode == "unlimited": mode_text = "全天畅玩"
    elif order.mode == "single_board": mode_text = "单板不限时"
    elif order.mode == "group_buy" and all_gbs:
        mode_text = all_gbs[0].gb_name
    
    # 时长字符串
    h_total = int(raw_duration_sec // 3600)
    m_total = int((raw_duration_sec % 3600) // 60)
    total_dur_str = f"{h_total}时{m_total}分" if h_total > 0 else f"{m_total}分"
    
    h_play = int(effective_duration_sec // 3600)
    m_play = int((effective_duration_sec % 3600) // 60)
    play_dur_str = f"{h_play}时{m_play}分" if h_play > 0 else f"{m_play}分"
    
    h_pause = int(total_pause_sec // 3600)
    m_pause = int((total_pause_sec % 3600) // 60)
    pause_dur_str = f"{h_pause}时{m_pause}分" if h_pause > 0 else (f"{m_pause}分" if m_pause > 0 else "无")
    
    # 分离直接加时和团购加时
    gb_added_min = 0
    if order.mode == "group_buy":
        for g in all_gbs[1:]:
            gb_added_min += (g.minutes or 0)
    else:
        for g in all_gbs:
            gb_added_min += (g.minutes or 0)
    direct_added_min = max(0, added_time_min - gb_added_min)
    
    # 定额/时长明细列
    fixed_str = ""
    buf = cfg.buffer_min if (cfg and cfg.buffer_min is not None) else 10
    if order.mode == "fixed":
        lm = order.limit_min or 60
        parts = [f"定额{lm}分"]
        if direct_added_min > 0:
            parts.append(f"直接加时+{direct_added_min}分")
        if gb_added_min > 0:
            gb_names = []
            added_list = all_gbs  # fixed模式所有GB都是追加的
            for g in added_list:
                gb_names.append(f"{g.gb_name}+{g.minutes or 0}分")
            parts.append(f"团购加时: {', '.join(gb_names)}")
        total_min = lm + added_time_min
        if added_time_min > 0:
            parts.append(f"总计{total_min}分")
        # 超时
        overtime_min = max(0, minutes - total_min)
        if overtime_min > buf:
            parts.append(f"超时{math.floor(overtime_min)}分")
        fixed_str = " | ".join(parts)
    elif order.mode == "group_buy" and all_gbs:
        mg = all_gbs[0]
        # 获取团购类型（如果是对象并且存在，则取其type；或者是通过名称判断，因为历史记录可能没级联）
        gb_type = mg.group_buy.type if (hasattr(mg, 'group_buy') and mg.group_buy) else "fixed"
        
        if gb_type in ("unlimited", "single_board") or ("畅玩" in (mg.gb_name or "") or "不限时" in (mg.gb_name or "")):
            parts = ["不限时"]
            if gb_added_min > 0:
                for g in all_gbs[1:]:
                    parts.append(f"团购+{g.minutes or 0}分")
            fixed_str = " | ".join(parts)
        else:
            lm = mg.minutes or 60
            parts = [f"{lm}分"]
            if direct_added_min > 0:
                parts.append(f"直接加时+{direct_added_min}分")
            if gb_added_min > 0:
                for g in all_gbs[1:]:
                    parts.append(f"团购+{g.minutes or 0}分")
            total_min = lm + added_time_min
            if added_time_min > 0:
                parts.append(f"总计{total_min}分")
            # 超时
            overtime_min = max(0, minutes - total_min)
            if overtime_min > buf:
                parts.append(f"超时{math.floor(overtime_min)}分")
            fixed_str = " | ".join(parts)
    
    # 团购信息 — gb_type 显示所有团购名, gb_voucher 汇总所有已核销团购的价值
    gb_type = ""
    gb_voucher = 0.0
    
    if order.mode == "group_buy" and all_gbs:
        mg = all_gbs[0]
        gb_type_parts = [mg.gb_name]
        # 主团购核销值
        if mg.verify_status:
            gb_model = db.query(GroupBuy).filter(GroupBuy.gb_config_id == mg.gb_config_id).first()
            gb_n = float(gb_model.persons if (gb_model and gb_model.persons) else 1)
            gb_voucher += round(float(mg.price or 0) / gb_n, 2)
        # 追加团购
        for g in all_gbs[1:]:
            gb_type_parts.append(g.gb_name)
            if g.verify_status:
                gb_voucher += round(float(g.price or 0), 2)
        gb_type = " + ".join(gb_type_parts)
    elif all_gbs:
        # fixed/pay_later 等模式的追加团购
        gb_type_parts = []
        for g in all_gbs:
            gb_type_parts.append(g.gb_name)
            if g.verify_status:
                gb_voucher += round(float(g.price or 0), 2)
        gb_type = " + ".join(gb_type_parts)
    
    # 计算账面价格 (使用 bill 相同的逻辑)
    total_price = order.actual_cost or 0.0
    actual_total = order.actual_cost or 0.0
    
    # 重新计算账面价格
    buf = cfg.buffer_min if (cfg and cfg.buffer_min is not None) else 10
    po = cfg.price_overtime if (cfg and cfg.price_overtime is not None) else 10.0
    tb = cfg.time_base if (cfg and cfg.time_base is not None) else 60
    pb = cfg.price_base if (cfg and cfg.price_base is not None) else 10.9
    
    computed_total = 0.0
    if order.mode == "pay_later":
        if minutes <= tb:
            computed_total = pb
        else:
            o = minutes - tb
            if o > buf:
                computed_total = pb + get_overtime_cost_logic(o, po, cfg)
            else:
                computed_total = pb
    elif order.mode == "fixed":
        lm = order.limit_min or 60
        at = added_time_min
        bp = pb
        extra = max(0, lm - tb)
        if extra > 0: bp += get_overtime_cost_logic(extra, po, cfg)
        if direct_added_min > 0: bp += get_overtime_cost_logic(direct_added_min, po, cfg)
        if gb_added_min > 0: bp += get_overtime_cost_logic(gb_added_min, po, cfg)
        bp = round(bp, 2)
        o = max(0, minutes - (lm + at))
        overtime = get_overtime_cost_logic(o, po, cfg) if o > buf else 0.0
        computed_total = bp + overtime
        added_gb_cost = sum([float(g.price or 0) for g in all_gbs if not g.verify_status])
        if all_gbs:
            gb_mins = sum([g.minutes or 0 for g in all_gbs])
            gb_time_cost = get_overtime_cost_logic(gb_mins, po, cfg)
            computed_total = round(computed_total - gb_time_cost + added_gb_cost, 2)
    elif order.mode == "group_buy" and all_gbs:
        mg = all_gbs[0]
        gb_n = 1
        gb_model = db.query(GroupBuy).filter(GroupBuy.gb_config_id == mg.gb_config_id).first()
        if gb_model and gb_model.persons: gb_n = gb_model.persons
        gb_vp = round(float(mg.price or 0) / gb_n, 2)
        computed_total = gb_vp
        for g in all_gbs[1:]:
            if not g.verify_status:
                computed_total += float(g.price or 0)
        added_time_cost = float(sum([a.cost or 0.0 for a in added_times]))
        computed_total += added_time_cost
    elif order.mode == "unlimited":
        computed_total = cfg.price_unlimited if (cfg and cfg.price_unlimited) else 59.9
    elif order.mode == "single_board":
        computed_total = cfg.price_single_board if (cfg and cfg.price_single_board) else 39.9
    
    total_price_val = round(computed_total, 2)
    
    # 备注 — 直接使用 order.remark，不再重复追加团购信息
    full_remark = order.remark or ""
    
    return {
        "order_id": order.order_id,
        "phone": order.phone or "",
        "mode": order.mode,
        "mode_text": mode_text,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_dur_str": total_dur_str,
        "play_dur_str": play_dur_str,
        "pause_dur_str": pause_dur_str,
        "fixed_str": fixed_str,
        "gb_type": gb_type,
        "gb_voucher": gb_voucher,
        "total_price": total_price_val,
        "actual_total": actual_total,
        "guest_count": order.guest_count or 1,
        "remark": full_remark
    }


@history_router.get("")
async def get_history(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """获取历史流水记录"""
    query = db.query(Order).filter(
        Order.shop_id == current_shop.shop_id,
        Order.status == "finished"
    )
    
    if start:
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            query = query.filter(Order.end_time >= start_dt)
        except: pass
    
    if end:
        try:
            end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Order.end_time < end_dt)
        except: pass
    
    orders = query.order_by(Order.end_time.desc()).all()
    
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == current_shop.shop_id).first()
    
    history = []
    for order in orders:
        try:
            record = build_history_record(order, db, cfg)
            history.append(record)
        except Exception as e:
            print(f"Error building history for {order.order_id}: {e}")
            continue
    
    return {"success": True, "history": history}


@history_router.delete("")
async def delete_history(
    request: dict,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """删除单条历史记录"""
    phone = request.get("phone")
    end_time_str = request.get("end_time")
    order_id = request.get("order_id")
    
    if order_id:
        order = db.query(Order).filter(Order.order_id == order_id, Order.shop_id == current_shop.shop_id).first()
    elif phone and end_time_str:
        try:
            et = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            order = db.query(Order).filter(
                Order.phone == phone,
                Order.shop_id == current_shop.shop_id,
                Order.end_time >= et - timedelta(seconds=2),
                Order.end_time <= et + timedelta(seconds=2)
            ).first()
        except:
            return {"success": False, "message": "时间格式错误"}
    else:
        return {"success": False, "message": "参数不足"}
    
    if not order:
        return {"success": False, "message": "未找到该记录"}
    
    db.delete(order)
    db.commit()
    return {"success": True, "message": "已删除"}


@history_router.post("/batch-delete")
async def batch_delete_history(
    request: dict,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """批量删除历史记录"""
    records = request.get("records", [])
    deleted = 0
    for rec in records:
        phone = rec.get("phone")
        end_time_str = rec.get("end_time")
        order_id = rec.get("order_id")
        
        order = None
        if order_id:
            order = db.query(Order).filter(Order.order_id == order_id, Order.shop_id == current_shop.shop_id).first()
        elif phone and end_time_str:
            try:
                et = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                order = db.query(Order).filter(
                    Order.phone == phone,
                    Order.shop_id == current_shop.shop_id,
                    Order.end_time >= et - timedelta(seconds=2),
                    Order.end_time <= et + timedelta(seconds=2)
                ).first()
            except:
                continue
        
        if order:
            db.delete(order)
            deleted += 1
    
    db.commit()
    return {"success": True, "message": f"已删除 {deleted} 条记录"}
