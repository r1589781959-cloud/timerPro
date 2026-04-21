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
from datetime import datetime, timedelta
import time
import math
import uuid

from ..database import get_db, Shop, User, Order, SystemConfig, GroupBuy, OrderGroupBuy, OrderPauseLog, OrderAddTime
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
        now = datetime.now()
        for o in orders:
            start_ts_str = o.start_time.strftime("%Y-%m-%d %H:%M:%S") if o.start_time else (o.created_at.strftime("%Y-%m-%d %H:%M:%S") if o.created_at else now.strftime("%Y-%m-%d %H:%M:%S"))
            
            all_gbs = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == o.order_id).order_by(OrderGroupBuy.id).all()
            
            # 只有 group_buy 模式才有"主团购券"(all_gbs[0])
            # 其他模式(fixed等)的所有 OrderGroupBuy 都是"追加团购券"
            mg = None
            gb_config_obj = None
            time_slot_end_time = None
            added_gb_list = []
            
            if o.mode == "group_buy" and all_gbs:
                mg = all_gbs[0]
                # Securely match by shop_id and gb_name to prevent ID offset bugs from config recreations
                gb_model = db.query(GroupBuy).filter(GroupBuy.shop_id == o.shop_id, GroupBuy.name == mg.gb_name).first()
                if not gb_model:
                    gb_model = db.query(GroupBuy).filter(GroupBuy.gb_config_id == mg.gb_config_id).first()
                
                gb_config_obj = {
                    "name": mg.gb_name, 
                    "price": float(mg.price or 0.0), 
                    "limit_min": mg.minutes,
                    "type": getattr(gb_model, "type", "fixed") if gb_model else "fixed",
                    "persons": getattr(gb_model, "persons", 1) if gb_model else 1,
                    "buffer_min": getattr(gb_model, "buffer_min", 10) if gb_model else 10,
                    "start_time": getattr(gb_model, "start_time", ""),
                    "end_time": getattr(gb_model, "end_time", ""),
                    "overtime_price": None  # 前端将使用 shopConfig.price_overtime
                }
                
                if gb_config_obj["type"] == "time_slot" and gb_config_obj.get("end_time"):
                    try:
                        et_h, et_m = map(int, gb_config_obj["end_time"].split(":"))
                        et_dt = (o.start_time or o.created_at or now).replace(hour=et_h, minute=et_m, second=0, microsecond=0)
                        if et_dt < (o.start_time or o.created_at or now): et_dt += timedelta(days=1)
                        time_slot_end_time = et_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except: pass
                
                # group_buy: 剩余的是追加团购券
                for g in all_gbs[1:]:
                    added_gb_list.append({
                        "name": g.gb_name,
                        "price": float(g.price or 0.0),
                        "minutes": g.minutes,
                        "verify_status": g.verify_status
                    })
            else:
                # fixed/pay_later 等: 所有 OrderGroupBuy 都是追加团购券
                for g in all_gbs:
                    added_gb_list.append({
                        "name": g.gb_name,
                        "price": float(g.price or 0.0),
                        "minutes": g.minutes,
                        "verify_status": g.verify_status
                    })
            
            added_times = db.query(OrderAddTime).filter(OrderAddTime.order_id == o.order_id).all()
            added_time_min = sum([a.minutes or 0 for a in added_times])
            added_time_cost = float(sum([a.cost or 0.0 for a in added_times]))

            pauses = db.query(OrderPauseLog).filter(OrderPauseLog.order_id == o.order_id).all()
            total_pause_sec = sum([p.pause_seconds or 0 for p in pauses if p.pause_end])
            active_pause = next((p for p in pauses if p.pause_end is None and p.pause_start), None)
            pause_start_ts = active_pause.pause_start.strftime("%Y-%m-%d %H:%M:%S") if active_pause else None
            
            suspend_start_ts = o.suspend_start_ts.strftime("%Y-%m-%d %H:%M:%S") if o.suspend_start_ts else None

            # === 服务端直接计算已用秒数，彻底避免前端浏览器时间解析差异 ===
            start_dt = o.start_time or o.created_at or now
            raw_sec = (now - start_dt).total_seconds()
            eff_sec = max(0, raw_sec - total_pause_sec)
            if active_pause and active_pause.pause_start:
                eff_sec -= max(0, (now - active_pause.pause_start).total_seconds())
            if getattr(o, "is_suspended", False) and o.suspend_start_ts:
                eff_sec -= max(0, (now - o.suspend_start_ts).total_seconds())
            elapsed_sec = int(max(0, eff_sec))

            d[str(o.order_id)] = {
                "id": o.order_id,
                "phone": o.phone,
                "mode": o.mode,
                "start_time": start_ts_str, 
                "status": o.status or "active",
                "is_paused": (o.status == "paused"),
                "is_suspended": getattr(o, "is_suspended", False),
                "suspend_locked_cost": getattr(o, "suspend_locked_cost", 0.0),
                "suspend_start_ts": suspend_start_ts,
                "limit_min": o.limit_min or 0,
                "remark": o.remark or "",
                "group_id": getattr(o, "group_id", None),
                "gb_config": gb_config_obj,
                "gb_verified": mg.verify_status if mg else False,
                "added_gb": added_gb_list,
                "added_time_min": added_time_min,
                "added_time_cost": added_time_cost,
                "time_slot_end_time": time_slot_end_time,
                "total_pause_sec": total_pause_sec,
                "pause_start_ts": pause_start_ts,
                "elapsed_sec": elapsed_sec,
                "guest_count": getattr(o, "guest_count", 1)
            }
        return {"g": d, "c": len(orders)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"g": {}, "c": 0}

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

# ==========================================
# 3. 暂停/恢复/计费/结账
# ==========================================

def get_overtime_cost_logic(over_mins: float, hourly_p: float, c) -> float:
    if over_mins <= 0: return 0.0
    calc_mode = (getattr(c, "calc_mode", None) or "step")
    if calc_mode == "exact":
        return round((over_mins / 60.0) * hourly_p, 2)
    n = int(getattr(c, "step_n", None) or 15)
    y = float(getattr(c, "step_y", None) or 10.0)
    k = float(getattr(c, "step_k", None) or 2.0)
    ceil_x = int(getattr(c, "ceil_x", None) or 5)
    hrs = int(over_mins // 60)
    rem = int(over_mins % 60)
    rem_cost = 0.0
    if rem > 0:
        if 60 - rem <= ceil_x:
            rem_cost = hourly_p
        else:
            blocks = rem // n
            if (rem % n) >= (n / k): blocks += 1
            rem_cost = blocks * y
            if rem_cost > hourly_p: rem_cost = hourly_p
    return round(hrs * hourly_p + rem_cost, 2)

@tables_router.post("/pause")
async def toggle_pause_table(request: dict, db: Session=Depends(get_db)):
    oid = request.get("order_id") or request.get("orderId") or request.get("id")
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if not order: return {"success": False, "message": "未找到订单"}
    if order.status not in ["active", "paused"]: return {"success": False, "message": f"状态[{order.status}]不可操作"}
    
    now = datetime.now()
    if order.status == "active":
        # 暂停
        order.status = "paused"
        pause_log = OrderPauseLog(
            order_id=order.order_id,
            pause_start=now,
            pause_type="pause"
        )
        db.add(pause_log)
        db.commit()
        return {"success": True, "message": "已暂停计费"}
    else:
        # 恢复
        order.status = "active"
        log = db.query(OrderPauseLog).filter(
            OrderPauseLog.order_id == order.order_id,
            OrderPauseLog.pause_end == None
        ).order_by(desc(OrderPauseLog.pause_start)).first()
        
        if log:
            log.pause_end = now
            log.pause_seconds = int((now - log.pause_start).total_seconds())
        
        db.commit()
        return {"success": True, "message": "已恢复计费"}

@tables_router.post("/bill")
async def get_table_bill(request: dict, db: Session=Depends(get_db)):
    oid = request.get("orderId") or request.get("id") or request.get("order_id")
    if not oid: return {"success": False, "message": "请求缺少订单ID"}
    
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if not order:
        return {"success": False, "message": f"未找到订单({oid})"}
    
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == order.shop_id).first()
    if not cfg: cfg = SystemConfig(price_base=29.9, time_base=60, price_overtime=15.0, buffer_min=10)
    
    now = datetime.now()
    end_time = now if order.status != "finished" else (order.end_time or now)
    start_time = order.start_time or order.created_at
    buf = cfg.buffer_min if cfg.buffer_min is not None else 10
    
    # 1. 计算暂停时间
    total_pause_sec = 0
    pause_logs = db.query(OrderPauseLog).filter(OrderPauseLog.order_id == order.order_id).all()
    for log in pause_logs:
        if log.pause_seconds:
            total_pause_sec += log.pause_seconds
        elif log.pause_end is None and log.pause_start:
            total_pause_sec += int((end_time - log.pause_start).total_seconds())
            
    raw_duration_sec = (end_time - start_time).total_seconds()
    effective_duration_sec = max(0, raw_duration_sec - total_pause_sec)
    minutes = math.floor(effective_duration_sec / 60)
    
    # 2. 获取加时信息
    added_time_min = 0
    added_time_cost = 0.0
    added_time_logs = db.query(OrderAddTime).filter(OrderAddTime.order_id == order.order_id).all()
    for atl in added_time_logs:
        added_time_min += (atl.minutes or 0)
        added_time_cost += (atl.cost or 0.0)
        
    # 3. 获取附加团购券 (非本单主模式，是在游玩中途加的券)
    added_gb_cost = 0.0
    if order.mode == "group_buy":
        added_gb_logs = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == order.order_id, OrderGroupBuy.timestamp > order.start_time).all()
    else:
        # fixed 等模式: 所有 OrderGroupBuy 都是追加的
        added_gb_logs = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == order.order_id).all()
    added_gbs = []
    gb_added_minutes = 0
    for gbl in added_gb_logs:
        added_gbs.append({"name": gbl.gb_name, "price": float(gbl.price or 0), "minutes": gbl.minutes or 0, "verify_status": gbl.verify_status})
        gb_added_minutes += (gbl.minutes or 0)
        if not gbl.verify_status:
            added_gb_cost += float(gbl.price or 0.0)
    direct_added_minutes = max(0, added_time_min - gb_added_minutes)
            
    # 4. 基础计费计算
    total_price = 0.0
    gb_extra_cost = 0.0
    gb_voucher_price = 0.0
    mode_text = order.mode
    over_info = "正常"
    fixed_str = "--"
    
    # 获取主团购记录 (timestamp与start_time相近，或者最早一条)
    main_gb = db.query(OrderGroupBuy).filter(OrderGroupBuy.order_id == order.order_id).order_by(OrderGroupBuy.id).first()
    gb_verified = main_gb.verify_status if main_gb else False
    
    if order.mode == "group_buy" and main_gb:
        mode_text = main_gb.gb_name
        bp = float(main_gb.price or 0.0)
        
        # Match current gb by name to prevent ID offset mismatches
        current_gb = db.query(GroupBuy).filter(GroupBuy.shop_id == order.shop_id, GroupBuy.name == main_gb.gb_name).first()
        if not current_gb:
            current_gb = main_gb.group_buy
            
        gb_n = float(current_gb.persons if (current_gb and current_gb.persons) else 1)
        gb_voucher_price = round(bp / gb_n, 2)
        
        gb_type = current_gb.type if current_gb else "fixed"
        if gb_type in ("unlimited", "single_board"):
            total_price = gb_voucher_price
            over_info = "不限时"
        else:
            lm = main_gb.minutes or (current_gb.limit_min if current_gb else 60)
            at = added_time_min
            over = 0
            
            if gb_type == "time_slot" and current_gb and current_gb.end_time:
                # 解析时段结束时间 (HH:MM)
                try:
                    et_str = current_gb.end_time
                    et_hour, et_min = map(int, et_str.split(":"))
                    et_dt = start_time.replace(hour=et_hour, minute=et_min, second=0, microsecond=0)
                    if et_dt < start_time: et_dt += timedelta(days=1)
                    over = max(0, minutes - ((et_dt - start_time).total_seconds()/60))
                except:
                    over = max(0, minutes - (lm + at))
            else:
                over = max(0, minutes - (lm + at))
                
            if over > buf:
                po_gb = cfg.price_overtime if cfg.price_overtime is not None else 10.0
                gb_extra_cost = get_overtime_cost_logic(math.floor(over), po_gb, cfg)
                total_price = gb_voucher_price + gb_extra_cost
                over_info = f"超时 {math.floor(over)}分"
            else:
                total_price = gb_voucher_price

    elif order.mode == "pay_later":
        mode_text = "先玩后付"
        tb = cfg.time_base if cfg.time_base is not None else 60
        pb = cfg.price_base if cfg.price_base is not None else 29.9
        if minutes <= tb:
            total_price = pb
        else:
            o = minutes - tb
            if o > buf:
                total_price = pb + get_overtime_cost_logic(o, cfg.price_overtime if cfg.price_overtime is not None else 10.0, cfg)
            else:
                total_price = pb

    elif order.mode == "fixed":
        mode_text = "普通定额"
        lm = order.limit_min or 60
        at = added_time_min
        po = cfg.price_overtime if cfg.price_overtime is not None else 10.0
        tb = cfg.time_base if cfg.time_base is not None else 60
        pb = cfg.price_base if cfg.price_base is not None else 10.9
        fixed_str = f"{lm}分"
        
        # 正确算法: price_base 覆盖 time_base 分钟
        bp = pb
        extra_in_package = max(0, lm - tb)
        extra_package_cost = 0.0
        if extra_in_package > 0:
            extra_package_cost = get_overtime_cost_logic(extra_in_package, po, cfg)
            bp += extra_package_cost
        
        # 只对【直接加时】的分钟数做阶梯计价
        # 团购加时的分钟数通过 section 5 的 gb_time_cost 扣除处理
        direct_add_cost = 0.0
        if direct_added_minutes > 0:
            direct_add_cost = get_overtime_cost_logic(direct_added_minutes, po, cfg)
            bp += direct_add_cost
        if gb_added_minutes > 0:
            bp += get_overtime_cost_logic(gb_added_minutes, po, cfg)
        bp = round(bp, 2)
        
        # 实际超时
        o = max(0, minutes - (lm + at))
        overtime_cost = get_overtime_cost_logic(o, po, cfg) if o > buf else 0.0
        if o > buf: over_info = f"超时 {math.floor(o)}分"
        
        total_price = bp + overtime_cost

    elif order.mode in ("unlimited", "single_board"):
        mode_text = "全天畅玩" if order.mode == "unlimited" else "单板不限时"
        total_price = (cfg.price_unlimited if cfg.price_unlimited is not None else 59.9) if order.mode == "unlimited" else (cfg.price_single_board if cfg.price_single_board is not None else 39.9)
        over_info = "不限时"

    # 5. 合并加团购等其它扣费项
    # 注意: fixed 模式下 bp 已经包含了加时的阶梯费用，不能再加 added_time_cost
    if order.mode == "fixed":
        if added_gb_logs:
            gb_minutes = sum([g.minutes or 0 for g in added_gb_logs])
            gb_time_cost = get_overtime_cost_logic(gb_minutes, cfg.price_overtime if cfg.price_overtime is not None else 10.0, cfg)
            total_price = round(total_price - gb_time_cost + added_gb_cost, 2)
    else:
        # group_buy / pay_later / unlimited: 统一加上 added_gb_cost + added_time_cost
        total_price = round(total_price + added_gb_cost + added_time_cost, 2)
        
    actual_total = total_price
    if order.mode == "group_buy" and gb_verified:
        # 已核销: 不收券面价, 只收超时 + 添加项
        actual_total = round(gb_extra_cost + added_gb_cost + added_time_cost, 2)
        
    # 时间中文字符串
    h_play = int(effective_duration_sec // 3600)
    m_play = int((effective_duration_sec % 3600) // 60)
    raw_play_str = f"{h_play}时{m_play}分" if h_play > 0 else f"{m_play}分"
    
    h_pause = int(total_pause_sec // 3600)
    m_pause = int((total_pause_sec % 3600) // 60)
    pause_time_str = f"{h_pause}时{m_pause}分" if h_pause > 0 else (f"{m_pause}分" if m_pause > 0 else "无")
    
    status_text = "上机中"
    if order.status == "paused": status_text = "暂停中"
    if getattr(order, "is_suspended", False): status_text = "已挂账"
    
    cost_detail_str = f"账面总额: ¥{total_price} | 实收(去核销): ¥{actual_total}"

    # === 费用明细 ===
    lm_val = order.limit_min or 0
    tb_val = (cfg.time_base if cfg.time_base is not None else 60) if order.mode in ("fixed", "pay_later") else 0
    pb_val = (cfg.price_base if cfg.price_base is not None else 10.9) if order.mode in ("fixed", "pay_later") else 0
    po_val = cfg.price_overtime if cfg.price_overtime is not None else 10.0
    
    detail_items = []
    if order.mode == "fixed":
        detail_items.append({"label": f"开台定额 {lm_val}分 (基准{tb_val}分)", "amount": round(pb_val + (extra_package_cost if 'extra_package_cost' in dir() else 0), 2)})
        if direct_added_minutes > 0:
            detail_items.append({"label": f"直接加时 +{direct_added_minutes}分钟", "amount": round(direct_add_cost if 'direct_add_cost' in dir() else 0, 2)})
        for gb in added_gbs:
            st = "已核销" if gb.get("verify_status") else "未核销"
            gb_price = float(gb.get("price", 0))
            amt = 0 if gb.get("verify_status") else gb_price
            gb_min = gb.get("minutes", 0)
            detail_items.append({"label": f"加团购 {gb.get('name','')} +{gb_min}分 ({st})", "amount": round(amt, 2)})
        if overtime_cost > 0:
            detail_items.append({"label": f"超时 {math.floor(o)}分", "amount": round(overtime_cost, 2)})
    elif order.mode == "pay_later":
        play_str = raw_play_str
        detail_items.append({"label": f"计费时长 {play_str}", "amount": round(total_price, 2)})
    elif order.mode == "group_buy":
        gb_vp_display = 0 if gb_verified else round(gb_voucher_price if 'gb_voucher_price' in dir() else 0, 2)
        gb_status = "已核销" if gb_verified else "未核销"
        detail_items.append({"label": f"团购券面价 ({gb_status})", "amount": gb_vp_display})
        if gb_extra_cost > 0:
            detail_items.append({"label": f"超时费", "amount": round(gb_extra_cost, 2)})
        if direct_added_minutes > 0:
            detail_items.append({"label": f"直接加时 +{direct_added_minutes}分钟", "amount": round(added_time_cost, 2)})
        for gb in added_gbs:
            st = "已核销" if gb.get("verify_status") else "未核销"
            amt = 0 if gb.get("verify_status") else float(gb.get("price", 0))
            gb_min = gb.get("minutes", 0)
            detail_items.append({"label": f"加团购 {gb.get('name','')} +{gb_min}分 ({st})", "amount": round(amt, 2)})
    elif order.mode in ("unlimited", "single_board"):
        label = "全天畅玩" if order.mode == "unlimited" else "单板不限时"
        detail_items.append({"label": label, "amount": round(total_price, 2)})

    return {
        "success": True, 
        "bill": {
            "order_id": order.order_id,
            "mode_text": mode_text,
            "fixed_str": fixed_str,
            "limit_min": lm_val,
            "total_limit_min": lm_val + added_time_min,
            "added_time_min": added_time_min,
            "direct_added_time_min": direct_added_minutes,
            "gb_added_time_min": gb_added_minutes,
            "total_dur_str": f"{int(raw_duration_sec // 3600)}时{int((raw_duration_sec % 3600) // 60)}分",
            "play_dur_str": raw_play_str,
            "pause_dur_str": pause_time_str,
            "pause_str": pause_time_str,
            "over_info": over_info,
            "cost_detail_str": cost_detail_str,
            "status_text": status_text,
            "actual_total": round(actual_total, 2),
            "total_price": round(total_price, 2),
            "remark": order.remark or "",
            "added_gb": added_gbs,
            "detail_items": detail_items
        }
    }

@tables_router.post("/checkout")
async def checkout_table(request: dict, db: Session=Depends(get_db)):
    oid = request.get("order_id") or request.get("orderId") or request.get("id")
    cost = request.get("final_total") or request.get("finalTotal", 0.0)
    remark = request.get("remark", "")
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if order:
        order.status = "finished"
        order.end_time = datetime.now()
        order.actual_cost = float(cost)
        if remark:
            order.remark = remark
        
        # 将任何未结束的暂停结束掉
        log = db.query(OrderPauseLog).filter(
            OrderPauseLog.order_id == order.order_id,
            OrderPauseLog.pause_end == None
        ).first()
        if log:
            log.pause_end = order.end_time
            log.pause_seconds = int((order.end_time - log.pause_start).total_seconds())
        
        db.commit()
        return {
            "success": True, 
            "message": "结账成功",
            "bill": {
                "actual_total": round(float(cost), 2),
                "order_id": order.order_id
            }
        }
    return {"success": False, "message": "结账失败：找不到订单"}

@tables_router.delete("/{order_id}")
async def delete_order_table(order_id: str, db: Session=Depends(get_db)):
    """前端 forceCancelOrder 发送 DELETE /api/tables/{id}"""
    order = db.query(Order).filter(Order.order_id == str(order_id)).first()
    if order:
        db.delete(order)
        db.commit()
        return {"success": True, "message": "强制删除成功"}
    return {"success": False, "message": "找不到该订单"}

@tables_router.post("/force_cancel")
async def force_cancel_table(request: dict, db: Session=Depends(get_db)):
    oid = request.get("order_id") or request.get("id")
    if not oid: return {"success": False, "message": "参数错误"}
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if order:
        db.delete(order)
        db.commit()
        return {"success": True, "message": "强制删除成功"}
    return {"success": False, "message": "找不到该订单"}

@tables_router.post("/suspend")
async def suspend_table(request: dict, db: Session=Depends(get_db)):
    oid = request.get("order_id") or request.get("id")
    cost = request.get("locked_cost", 0.0)
    if not oid: return {"success": False, "message": "参数错误"}
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if order:
        if getattr(order, "is_suspended", False):
            return {"success": False, "message": "该单已在挂账中"}
            
        order.is_suspended = True
        order.suspend_locked_cost = float(cost)
        order.suspend_start_ts = datetime.now()
        
        # 挂账时自动结束当前的游玩暂停
        log = db.query(OrderPauseLog).filter(
            OrderPauseLog.order_id == order.order_id,
            OrderPauseLog.pause_end == None
        ).first()
        if log:
            log.pause_end = order.suspend_start_ts
            log.pause_seconds = int((order.suspend_start_ts - log.pause_start).total_seconds())

        db.commit()
        return {"success": True, "message": "挂账成功"}
    return {"success": False, "message": "找不到订单"}

@tables_router.post("/cancel_suspend")
@tables_router.post("/cancel-suspend")
async def cancel_suspend_table(request: dict, db: Session=Depends(get_db)):
    oid = request.get("order_id") or request.get("id")
    if not oid: return {"success": False, "message": "参数错误"}
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if order:
        if not getattr(order, "is_suspended", False):
            return {"success": False, "message": "该单未处于挂账状态"}
            
        if order.suspend_start_ts:
            now = datetime.now()
            p = OrderPauseLog(
                order_id=order.order_id,
                pause_start=order.suspend_start_ts,
                pause_end=now,
                pause_seconds=int((now - order.suspend_start_ts).total_seconds()),
                pause_type="suspend_wait"
            )
            db.add(p)
            
        order.is_suspended = False
        order.suspend_locked_cost = 0.0
        order.suspend_start_ts = None
        db.commit()
        return {"success": True, "message": "已恢复正常计费"}
    return {"success": False, "message": "找不到订单"}
# ==========================================
# 3b. 备注 / 核销 / 加时
# ==========================================

@tables_router.post("/remark")
async def update_remark(request: dict, db: Session=Depends(get_db)):
    oid = request.get("order_id") or request.get("id")
    remark = request.get("remark", "")
    if not oid: return {"success": False, "message": "参数错误"}
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if not order: return {"success": False, "message": "找不到订单"}
    order.remark = remark
    db.commit()
    return {"success": True, "message": "备注已更新"}

@tables_router.post("/verify")
async def toggle_verify(request: dict, db: Session=Depends(get_db)):
    """切换团购核销状态(主团购 or 附属团购券)"""
    oid = request.get("order_id") or request.get("id")
    verified = request.get("verified", False)
    added_gb_index = request.get("added_gb_index")
    if not oid: return {"success": False, "message": "参数错误"}
    
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if not order: return {"success": False, "message": "找不到订单"}
    
    all_gbs = db.query(OrderGroupBuy).filter(
        OrderGroupBuy.order_id == order.order_id
    ).order_by(OrderGroupBuy.id).all()
    
    status_text = "已核销" if verified else "未核销"
    
    if added_gb_index is not None:
        # 修改附属团购券的核销状态
        # 对于 group_buy 模式: all_gbs[0] 是主券, added_gb 从 all_gbs[1] 开始
        # 对于 fixed 等其他模式: 没有主券, added_gb 从 all_gbs[0] 开始
        if order.mode == "group_buy":
            real_idx = int(added_gb_index) + 1  # 跳过主券
        else:
            real_idx = int(added_gb_index)  # 无主券，直接定位
            
        if real_idx < 0 or real_idx >= len(all_gbs):
            return {"success": False, "message": "找不到指定的团购券"}
        all_gbs[real_idx].verify_status = verified
    else:
        # 修改主团购核销状态
        if order.mode != "group_buy":
            return {"success": False, "message": "仅团购订单可操作主团购核销"}
        if all_gbs:
            all_gbs[0].verify_status = verified
        
        # 联动同 group_id 的其他成员
        if order.group_id:
            sibling_orders = db.query(Order).filter(
                Order.group_id == order.group_id,
                Order.order_id != order.order_id
            ).all()
            for sib in sibling_orders:
                sib_gb = db.query(OrderGroupBuy).filter(
                    OrderGroupBuy.order_id == sib.order_id
                ).first()
                if sib_gb:
                    sib_gb.verify_status = verified
    
    # 同步更新备注中的核销状态标记（与 legacy 行为一致）
    remark = order.remark or ""
    # 保留非加团购行
    preserved_lines = [ln for ln in remark.splitlines() if not ln.strip().startswith("【加团购】")]
    preserved = "\n".join(preserved_lines).strip()
    
    # 重建加团购行（根据 order 模式，确定哪些是"附属"团购券）
    added_gb_records = all_gbs[1:] if order.mode == "group_buy" else all_gbs
    added_lines = []
    for gb in added_gb_records:
        st = "已核销" if gb.verify_status else "未核销"
        atime = gb.add_time or ""
        nm = gb.gb_name or ""
        pr = float(gb.price or 0.0)
        added_lines.append(f"【加团购】{atime} {nm} ({st}) ¥{pr:.2f}")
    
    if added_lines:
        order.remark = ("\n".join([preserved] + added_lines)).strip() if preserved else "\n".join(added_lines)
    
    db.commit()
    return {"success": True, "message": f"核销状态已更新为: {status_text}"}

@tables_router.post("/add-time")
async def add_time(request: dict, db: Session=Depends(get_db)):
    """加时间(直接加分钟数) or 加团购券(从配置中选一个团购方案追加)"""
    oid = request.get("order_id") or request.get("id")
    mode = request.get("mode", "direct")  # "direct" or "group_buy"
    if not oid: return {"success": False, "message": "参数错误"}
    
    order = db.query(Order).filter(Order.order_id == str(oid)).first()
    if not order: return {"success": False, "message": "找不到订单"}
    
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == order.shop_id).first()
    po = cfg.price_overtime if (cfg and cfg.price_overtime is not None) else 10.0
    now = datetime.now()
    add_time_str = now.strftime("%H:%M")
    
    if mode == "direct":
        add_min = int(request.get("minutes", 0))
        if add_min <= 0:
            return {"success": False, "message": "请输入正整数分钟"}
        
        # 计算加时费用
        add_price = round((add_min / 60.0) * po, 2)
        
        # 写入 OrderAddTime 表
        at_record = OrderAddTime(
            order_id=order.order_id,
            minutes=add_min,
            cost=add_price,
            add_time=add_time_str,
            remark=f"直接加时 +{add_min}分钟"
        )
        db.add(at_record)
        
        # 追加备注
        note = f"【加时】{add_time_str} +{add_min}分钟 ¥{add_price:.2f}"
        order.remark = f"{order.remark or ''}\n{note}".strip()
        
        db.commit()
        return {"success": True, "message": f"已添加 {add_min} 分钟，额外费用 ¥{add_price:.2f}"}
    
    elif mode == "group_buy":
        gb_name = request.get("gb_name")
        gb_verified = request.get("gb_verified", False)
        if not gb_name:
            return {"success": False, "message": "请选择团购券"}
        
        # 从配置中查找
        selected_gb = db.query(GroupBuy).filter(
            GroupBuy.shop_id == order.shop_id,
            GroupBuy.name == gb_name
        ).first()
        if not selected_gb:
            return {"success": False, "message": f"未找到团购券配置: {gb_name}"}
        
        # 只允许单人计时长类型的团购
        gb_persons = selected_gb.persons if selected_gb.persons else 1
        if gb_persons != 1:
            return {"success": False, "message": "中途加团购仅支持单人团购券"}
        gb_type = selected_gb.type if selected_gb.type else "fixed"
        if gb_type != "fixed":
            return {"success": False, "message": f"中途加团购仅支持计时长类型(fixed)，当前类型: {gb_type}"}
        
        add_min = selected_gb.limit_min or 60
        add_price = float(selected_gb.price or 0.0)
        
        # 写入 OrderGroupBuy 表 (作为追加团购券)
        ogb = OrderGroupBuy(
            order_id=order.order_id,
            gb_config_id=selected_gb.gb_config_id,
            gb_name=selected_gb.name,
            price=add_price,
            minutes=add_min,
            verify_status=gb_verified,
            add_time=add_time_str,
            timestamp=now
        )
        db.add(ogb)
        
        # 同时写入 OrderAddTime 加时记录
        at_record = OrderAddTime(
            order_id=order.order_id,
            minutes=add_min,
            cost=0.0,  # 团购券的时间不额外收费，费用在券价里
            add_time=add_time_str,
            remark=f"加团购券 {selected_gb.name}"
        )
        db.add(at_record)
        
        # 追加备注
        verify_text = "已核销" if gb_verified else "未核销"
        note = f"【加团购】{add_time_str} {selected_gb.name} ({verify_text}) ¥{add_price:.2f}"
        order.remark = f"{order.remark or ''}\n{note}".strip()
        
        db.commit()
        return {"success": True, "message": f"已添加团购券: {selected_gb.name}，时间 {add_min}分钟，价格 ¥{add_price:.2f}"}
    
    return {"success": False, "message": "无效的 mode，应为 'direct' 或 'group_buy'"}

# ==========================================
# 4. 设置
# ==========================================

@config_router.get("/shop")
async def get_shop_config(current_shop: Shop=Depends(get_current_shop), db: Session=Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == current_shop.shop_id).first()
    if not cfg:
        cfg = SystemConfig(shop_id=current_shop.shop_id, price_base=29.9, time_base=60, price_overtime=15.0)
        db.add(cfg)
        db.commit()
    
    gbs = db.query(GroupBuy).filter(GroupBuy.shop_id == current_shop.shop_id).all()
    gb_list = []
    for gx in gbs:
        gb_list.append({
            "id": gx.gb_config_id,
            "name": gx.name,
            "type": gx.type,
            "price": gx.price,
            "persons": gx.persons,
            "limit_min": gx.limit_min,
            "start_time": gx.start_time,
            "end_time": gx.end_time
        })
        
    return {
        "price_base": cfg.price_base if cfg.price_base is not None else 29.9,
        "time_base": cfg.time_base if cfg.time_base is not None else 60,
        "price_overtime": cfg.price_overtime if cfg.price_overtime is not None else 10.0,
        "buffer_min": cfg.buffer_min if cfg.buffer_min is not None else 10,
        "calc_mode": cfg.calc_mode or "step",
        "step_n": cfg.step_n if cfg.step_n is not None else 15,
        "step_y": cfg.step_y if cfg.step_y is not None else 10.0,
        "step_k": cfg.step_k if cfg.step_k is not None else 2.0,
        "ceil_x": cfg.ceil_x if cfg.ceil_x is not None else 5,
        "price_unlimited": cfg.price_unlimited if cfg.price_unlimited is not None else 59.9,
        "price_single_board": cfg.price_single_board if cfg.price_single_board is not None else 39.9,
        "group_buys": gb_list
    }

@config_router.put("/shop")
async def update_shop_config(request: dict, current_shop: Shop=Depends(get_current_shop), db: Session=Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == current_shop.shop_id).first()
    if not cfg:
        cfg = SystemConfig(shop_id=current_shop.shop_id)
        db.add(cfg)
        db.commit()
        
    data = request.get("config", {})
    if not data: return {"success": False, "message": "无效的数据"}
    
    for k, v in data.items():
        if hasattr(cfg, k) and k != 'group_buys':
            setattr(cfg, k, v)
            
    # 同步团购选项
    if "group_buys" in data:
        db.query(GroupBuy).filter(GroupBuy.shop_id == current_shop.shop_id).delete()
        for idx, gb_data in enumerate(data["group_buys"]):
            new_gb = GroupBuy(
                shop_id=current_shop.shop_id,
                name=gb_data.get("name", "未命名"),
                type=gb_data.get("type", "fixed"),
                price=float(gb_data.get("price", 0.0)),
                persons=int(gb_data.get("persons", 1)),
                limit_min=int(gb_data.get("limit_min", 60)),
                start_time=gb_data.get("start_time", "00:00"),
                end_time=gb_data.get("end_time", "23:59"),
                sort_order=idx
            )
            db.add(new_gb)
    
    db.commit()
    return {"success": True, "message": "计费规则已更新"}
