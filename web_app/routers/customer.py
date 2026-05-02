"""
顾客端号牌/二维码接口
"""
from datetime import datetime
import io
import math
import secrets
from typing import Optional
from urllib.parse import quote
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_shop
from ..database import (
    CustomerAccessCode,
    GroupBuy,
    Order,
    OrderAddTime,
    OrderGroupBuy,
    OrderPauseLog,
    Shop,
    SystemConfig,
    get_db,
)
from .orders import get_overtime_cost_logic


customer_router = APIRouter(prefix="/api/customer", tags=["customer"])
customer_codes_router = APIRouter(prefix="/api/customer-codes", tags=["customer-codes"])


def _get_base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{scheme}://{host}"

def _customer_universal_url(request: Request, shop_code: str) -> str:
    base = _get_base_url(request)
    return f"{base}/customer.html?shop={quote(str(shop_code or ''))}"


def _safe_file_name(value: str) -> str:
    keep = []
    for ch in str(value or "").strip():
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "code"


def _load_label_font(size: int):
    from PIL import ImageFont
    for font_path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _make_qr_png_bytes(url: str, label: str = "", include_label: bool = False) -> bytes:
    import qrcode
    from PIL import Image, ImageDraw

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if include_label and label:
        font = _load_label_font(34)
        padding = 18
        label_height = 72
        canvas = Image.new("RGB", (img.width, img.height + label_height), "white")
        canvas.paste(img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        text = str(label)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = max(padding, (canvas.width - text_w) // 2)
        y = img.height + (label_height - text_h) // 2 - 2
        draw.text((x, y), text, fill=(17, 24, 39), font=font)
        img = canvas

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _format_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours}小时{minutes}分{secs}秒"
    if minutes:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def _active_order_query(db: Session, shop_id: int):
    return db.query(Order).filter(
        Order.shop_id == shop_id,
        Order.status != "finished"
    )


def _find_active_order_by_label(db: Session, shop_id: int, label: str) -> Optional[Order]:
    return _active_order_query(db, shop_id).filter(
        or_(
            Order.customer_code_label == label,
            Order.phone == label
        )
    ).order_by(Order.created_at.desc()).first()


def _effective_seconds(order: Order, db: Session, now: datetime) -> tuple[int, int]:
    start_time = order.start_time or order.created_at or now
    end_time = order.end_time or now
    total_pause_sec = 0
    pause_logs = db.query(OrderPauseLog).filter(OrderPauseLog.order_id == order.order_id).all()
    for log in pause_logs:
        if log.pause_seconds:
            total_pause_sec += log.pause_seconds
        elif log.pause_end is None and log.pause_start:
            total_pause_sec += int((end_time - log.pause_start).total_seconds())
    if order.is_suspended and order.suspend_start_ts:
        total_pause_sec += int((now - order.suspend_start_ts).total_seconds())
    raw_duration_sec = int((end_time - start_time).total_seconds())
    return max(0, raw_duration_sec - total_pause_sec), total_pause_sec


def _estimate_order_cost(order: Order, db: Session, cfg: SystemConfig, minutes: int) -> float:
    if order.is_suspended:
        return round(float(order.suspend_locked_cost or 0.0), 2)

    if not cfg:
        cfg = SystemConfig(price_base=10.9, time_base=60, price_overtime=10.9, buffer_min=10)

    added_time_logs = db.query(OrderAddTime).filter(OrderAddTime.order_id == order.order_id).all()
    added_time_min = sum([a.minutes or 0 for a in added_time_logs])
    added_time_cost = float(sum([a.cost or 0.0 for a in added_time_logs]))

    all_gbs = db.query(OrderGroupBuy).filter(
        OrderGroupBuy.order_id == order.order_id
    ).order_by(OrderGroupBuy.id).all()

    added_gbs = all_gbs[1:] if order.mode == "group_buy" else all_gbs
    gb_added_minutes = sum([g.minutes or 0 for g in added_gbs])
    added_gb_cost = sum([float(g.price or 0.0) for g in added_gbs if not g.verify_status])
    direct_added_minutes = max(0, added_time_min - gb_added_minutes)

    buf = cfg.buffer_min if cfg.buffer_min is not None else 10
    po = cfg.price_overtime if cfg.price_overtime is not None else 10.0
    tb = cfg.time_base if cfg.time_base is not None else 60
    pb = cfg.price_base if cfg.price_base is not None else 10.9

    total = 0.0
    if order.mode == "pay_later":
        total = pb
        over = minutes - tb
        if over > buf:
            total += get_overtime_cost_logic(over, po, cfg)
    elif order.mode == "fixed":
        limit_min = order.limit_min or 60
        total = pb + get_overtime_cost_logic(max(0, limit_min - tb), po, cfg)
        if direct_added_minutes:
            total += get_overtime_cost_logic(direct_added_minutes, po, cfg)
        if gb_added_minutes:
            total += get_overtime_cost_logic(gb_added_minutes, po, cfg)
        over = minutes - (limit_min + added_time_min)
        if over > buf:
            total += get_overtime_cost_logic(over, po, cfg)
        if added_gbs:
            total -= get_overtime_cost_logic(gb_added_minutes, po, cfg)
            total += added_gb_cost
    elif order.mode == "group_buy" and all_gbs:
        main_gb = all_gbs[0]
        current_gb = db.query(GroupBuy).filter(
            GroupBuy.shop_id == order.shop_id,
            GroupBuy.name == main_gb.gb_name
        ).first()
        persons = current_gb.persons if (current_gb and current_gb.persons) else 1
        voucher_price = round(float(main_gb.price or 0.0) / persons, 2)
        gb_type = current_gb.type if current_gb else "fixed"
        total = 0.0 if main_gb.verify_status else voucher_price
        if gb_type not in ("unlimited", "single_board"):
            limit_min = main_gb.minutes or (current_gb.limit_min if current_gb else 60)
            over = minutes - (limit_min + added_time_min)
            if over > buf:
                total += get_overtime_cost_logic(math.floor(over), po, cfg)
        total += added_gb_cost + added_time_cost
    elif order.mode == "unlimited":
        total = cfg.price_unlimited if cfg.price_unlimited is not None else 59.9
    elif order.mode == "single_board":
        total = cfg.price_single_board if cfg.price_single_board is not None else 39.9

    return round(max(0.0, total), 2)


def _mode_text(order: Order, main_gb: Optional[OrderGroupBuy] = None) -> str:
    if order.mode == "pay_later":
        return "先玩后付"
    if order.mode == "fixed":
        return "固定时长"
    if order.mode == "unlimited":
        return "全天畅玩"
    if order.mode == "single_board":
        return "单板不限时"
    if order.mode == "group_buy" and main_gb:
        return main_gb.gb_name
    if order.mode == "group_buy":
        return "团购套餐"
    return order.mode or "未知模式"


def _build_order_details(order: Order, db: Session, cfg: SystemConfig, effective_sec: int, estimated: float) -> dict:
    minutes = math.floor(effective_sec / 60)
    all_gbs = db.query(OrderGroupBuy).filter(
        OrderGroupBuy.order_id == order.order_id
    ).order_by(OrderGroupBuy.id).all()
    added_time_logs = db.query(OrderAddTime).filter(
        OrderAddTime.order_id == order.order_id
    ).order_by(OrderAddTime.created_at).all()

    main_gb = all_gbs[0] if order.mode == "group_buy" and all_gbs else None
    added_gbs = all_gbs[1:] if order.mode == "group_buy" else all_gbs

    cfg = cfg or SystemConfig(price_base=10.9, time_base=60, price_overtime=10.9, buffer_min=10)
    buffer_min = cfg.buffer_min if cfg.buffer_min is not None else 10
    base_time = cfg.time_base if cfg.time_base is not None else 60
    base_price = float(cfg.price_base if cfg.price_base is not None else 10.9)
    overtime_price = float(cfg.price_overtime if cfg.price_overtime is not None else 10.0)

    added_time_min = sum([a.minutes or 0 for a in added_time_logs])
    direct_added_min = added_time_min
    gb_added_min = sum([g.minutes or 0 for g in added_gbs])
    if gb_added_min:
        direct_added_min = max(0, added_time_min - gb_added_min)

    limit_min = None
    included_text = ""
    main_group_buy = None
    if order.mode == "pay_later":
        limit_min = base_time
        included_text = f"基础 {base_time} 分钟"
    elif order.mode == "fixed":
        limit_min = (order.limit_min or 60) + added_time_min
        included_text = f"固定 {order.limit_min or 60} 分钟"
    elif order.mode == "group_buy" and main_gb:
        gb_model = db.query(GroupBuy).filter(
            GroupBuy.shop_id == order.shop_id,
            GroupBuy.name == main_gb.gb_name
        ).first()
        gb_type = gb_model.type if gb_model else "fixed"
        persons = gb_model.persons if (gb_model and gb_model.persons) else 1
        main_group_buy = {
            "name": main_gb.gb_name,
            "price": round(float(main_gb.price or 0.0), 2),
            "per_person_price": round(float(main_gb.price or 0.0) / persons, 2),
            "persons": persons,
            "type": gb_type,
            "minutes": main_gb.minutes or (gb_model.limit_min if gb_model else 0),
            "verify_status": bool(main_gb.verify_status),
            "status_text": "已核销" if main_gb.verify_status else "未核销",
        }
        if gb_type not in ("unlimited", "single_board"):
            limit_min = (main_group_buy["minutes"] or 60) + added_time_min
            included_text = f"团购 {main_group_buy['minutes'] or 60} 分钟"
        else:
            included_text = "不限时"
    elif order.mode == "unlimited":
        included_text = "不限时"
    elif order.mode == "single_board":
        included_text = "单板不限时"

    remaining_sec = None
    over_sec = 0
    progress_percent = None
    time_status = "不限时" if limit_min is None else "正常"
    if limit_min is not None:
        total_limit_sec = max(0, limit_min * 60)
        remaining_sec = total_limit_sec - effective_sec
        progress_percent = round((effective_sec / total_limit_sec) * 100, 1) if total_limit_sec else 0
        if remaining_sec < 0:
            over_sec = abs(remaining_sec)
            time_status = "已超时"
        elif remaining_sec <= buffer_min * 60:
            time_status = "临近结束"

    add_times = [
        {
            "minutes": a.minutes or 0,
            "cost": round(float(a.cost or 0.0), 2),
            "add_time": a.add_time or "",
            "remark": a.remark or "",
        }
        for a in added_time_logs
        if (a.cost or 0.0) > 0 or "直接" in (a.remark or "")
    ]

    added_group_buys = [
        {
            "name": g.gb_name,
            "price": round(float(g.price or 0.0), 2),
            "minutes": g.minutes or 0,
            "verify_status": bool(g.verify_status),
            "status_text": "已核销" if g.verify_status else "未核销",
            "add_time": g.add_time or "",
        }
        for g in added_gbs
    ]

    cost_items = []
    if order.mode == "pay_later":
        cost_items.append({"label": f"基础计费 {base_time} 分钟", "amount": base_price})
        if minutes > base_time + buffer_min:
            cost_items.append({"label": f"超时 {minutes - base_time} 分钟", "amount": None})
    elif order.mode == "fixed":
        cost_items.append({"label": included_text, "amount": None})
    elif order.mode == "group_buy" and main_group_buy:
        amount = 0.0 if main_group_buy["verify_status"] else main_group_buy["per_person_price"]
        cost_items.append({"label": f"主团购券 ({main_group_buy['status_text']})", "amount": amount})
    elif order.mode in ("unlimited", "single_board"):
        cost_items.append({"label": included_text, "amount": estimated})

    for item in add_times:
        cost_items.append({"label": f"直接加时 +{item['minutes']} 分钟", "amount": item["cost"]})
    for gb in added_group_buys:
        amount = 0.0 if gb["verify_status"] else gb["price"]
        cost_items.append({"label": f"追加团购 {gb['name']} ({gb['status_text']})", "amount": amount})

    return {
        "mode_text": _mode_text(order, main_gb),
        "included_text": included_text,
        "limit_min": limit_min,
        "total_limit_text": f"{limit_min}分钟" if limit_min is not None else "不限时",
        "remaining_sec": remaining_sec,
        "remaining_text": _format_duration(remaining_sec) if remaining_sec is not None and remaining_sec >= 0 else "已超时",
        "over_sec": over_sec,
        "over_text": _format_duration(over_sec) if over_sec else "无",
        "time_status": time_status,
        "progress_percent": progress_percent,
        "buffer_min": buffer_min,
        "base_time": base_time,
        "base_price": base_price,
        "overtime_price": overtime_price,
        "added_time_min": added_time_min,
        "direct_added_min": direct_added_min,
        "gb_added_min": gb_added_min,
        "main_group_buy": main_group_buy,
        "added_times": add_times,
        "added_group_buys": added_group_buys,
        "cost_items": cost_items,
    }


def _build_customer_payload(db: Session, shop: Shop, access_label: str, order: Order) -> dict:
    now = datetime.now()
    if order.group_id:
        orders = _active_order_query(db, shop.shop_id).filter(
            Order.group_id == order.group_id
        ).order_by(Order.created_at).all()
    else:
        orders = [order]

    cfg = db.query(SystemConfig).filter(SystemConfig.shop_id == shop.shop_id).first()
    order_items = []
    total = 0.0
    for item in orders:
        effective_sec, pause_sec = _effective_seconds(item, db, now)
        estimated = _estimate_order_cost(item, db, cfg, math.floor(effective_sec / 60))
        details = _build_order_details(item, db, cfg, effective_sec, estimated)
        total += estimated
        order_items.append({
            "order_id": item.order_id,
            "label": item.customer_code_label or item.phone,
            "display_label": item.phone,
            "mode": item.mode,
            "mode_text": details["mode_text"],
            "start_time": _format_dt(item.start_time),
            "elapsed_sec": effective_sec,
            "elapsed_text": _format_duration(effective_sec),
            "pause_sec": pause_sec,
            "pause_text": _format_duration(pause_sec) if pause_sec else "无",
            "status": item.status,
            "is_paused": item.status == "paused",
            "is_suspended": bool(item.is_suspended),
            "estimated_cost": estimated,
            "remark": item.remark or "",
            **details,
        })

    return {
        "success": True,
        "shop": {
            "shop_code": shop.shop_code,
            "shop_name": shop.name,
        },
        "access": {
            "label": access_label,
        },
        "group_id": order.group_id,
        "orders": order_items,
        "summary": {
            "count": len(order_items),
            "estimated_total": round(total, 2),
        },
        "message": "查询成功",
    }


@customer_router.get("/by-token/{token}")
async def get_customer_order_by_token(token: str, db: Session = Depends(get_db)):
    code = db.query(CustomerAccessCode).filter(
        CustomerAccessCode.token == token,
        CustomerAccessCode.is_active == True
    ).first()
    if not code:
        return {"success": False, "code": "invalid_token", "message": "无效的顾客码"}

    shop = db.query(Shop).filter(Shop.shop_id == code.shop_id, Shop.status == 1).first()
    if not shop:
        return {"success": False, "code": "shop_disabled", "message": "门店不可用"}

    order = _active_order_query(db, shop.shop_id).filter(
        or_(
            Order.customer_code_id == code.code_id,
            Order.customer_code_label == code.label,
            Order.phone == code.label
        )
    ).order_by(Order.created_at.desc()).first()
    if not order:
        return {
            "success": False,
            "code": "no_active_order",
            "shop": {"shop_code": shop.shop_code, "shop_name": shop.name},
            "access": {"label": code.label},
            "message": "当前号牌暂无进行中的订单，请联系店员确认",
        }

    return _build_customer_payload(db, shop, code.label, order)


@customer_router.get("/by-code")
async def get_customer_order_by_code(
    shop_code: str = Query(...),
    label: str = Query(...),
    db: Session = Depends(get_db),
):
    shop = db.query(Shop).filter(Shop.shop_code == shop_code, Shop.status == 1).first()
    if not shop:
        return {"success": False, "code": "shop_not_found", "message": "未找到门店"}

    clean_label = (label or "").strip()
    if not clean_label:
        return {"success": False, "code": "empty_label", "message": "请输入号牌编号"}

    order = _find_active_order_by_label(db, shop.shop_id, clean_label)
    if not order:
        return {
            "success": False,
            "code": "no_active_order",
            "shop": {"shop_code": shop.shop_code, "shop_name": shop.name},
            "access": {"label": clean_label},
            "message": "当前号牌暂无进行中的订单，请联系店员确认",
        }

    return _build_customer_payload(db, shop, clean_label, order)


@customer_codes_router.get("")
async def list_customer_codes(
    request: Request,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db),
):
    codes = db.query(CustomerAccessCode).filter(
        CustomerAccessCode.shop_id == current_shop.shop_id
    ).order_by(CustomerAccessCode.label).all()
    base = _get_base_url(request)
    universal_url = _customer_universal_url(request, current_shop.shop_code)
    return {
        "success": True,
        "shop_code": current_shop.shop_code,
        "universal_url": universal_url,
        "codes": [
            {
                "code_id": c.code_id,
                "label": c.label,
                "token": c.token,
                "url": f"{base}/customer.html?t={c.token}",
                "is_active": c.is_active,
            }
            for c in codes
        ],
    }


@customer_codes_router.get("/export")
async def export_customer_code_qr(
    request: Request,
    scope: str = Query("all"),
    asset: str = Query("bundle"),
    include_label: bool = Query(False),
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db),
):
    try:
        import qrcode
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="缺少 qrcode 依赖，请先安装 requirements.txt") from exc

    codes = db.query(CustomerAccessCode).filter(
        CustomerAccessCode.shop_id == current_shop.shop_id,
        CustomerAccessCode.is_active == True
    ).order_by(CustomerAccessCode.label).all()

    base = _get_base_url(request)
    universal_url = _customer_universal_url(request, current_shop.shop_code)
    rows = []
    if scope in ("all", "universal"):
        rows.append(("本店通用入口", "universal", universal_url))
    if scope in ("all", "badges"):
        rows.extend([(c.label, "badge", f"{base}/customer.html?t={c.token}") for c in codes])
    if scope not in ("all", "universal", "badges") or asset not in ("bundle", "qr", "nfc"):
        raise HTTPException(status_code=400, detail="导出参数无效")
    if not rows:
        raise HTTPException(status_code=404, detail="暂无可导出的号牌")

    def item_prefix(label: str, item_type: str) -> str:
        return "00_universal" if item_type == "universal" else f"badge_{_safe_file_name(label)}"

    if asset == "qr" and len(rows) == 1:
        label, item_type, url = rows[0]
        filename = f"{item_prefix(label, item_type)}.png"
        return Response(
            content=_make_qr_png_bytes(url, label, include_label),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, item_type, url in rows:
            prefix = item_prefix(label, item_type)
            if asset in ("bundle", "qr"):
                zf.writestr(f"qrcodes/{prefix}.png", _make_qr_png_bytes(url, label, include_label))
            if asset in ("bundle", "nfc"):
                zf.writestr(f"nfc/{prefix}.txt", url.encode("utf-8"))
        zf.writestr(
            "README.txt",
            (
                "TimerPro customer export\n"
                "qrcodes/: PNG QR code images for printing.\n"
                "nfc/: one URL text file per NFC tag. Write the file content as the NFC URL.\n"
            ).encode("utf-8")
        )

    filename = f"timerpro_{_safe_file_name(current_shop.shop_code)}_{scope}_{asset}.zip"
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@customer_codes_router.post("/batch")
async def batch_create_customer_codes(
    request: Request,
    data: dict,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db),
):
    labels = data.get("labels")
    if not labels:
        start = int(data.get("start", 1))
        end = int(data.get("end", 50))
        prefix = str(data.get("prefix", ""))
        if end < start or (end - start + 1) > 500:
            return {"success": False, "message": "批量范围无效，单次最多生成 500 个"}
        labels = [f"{prefix}{i}" for i in range(start, end + 1)]

    clean_labels = []
    for label in labels:
        clean = str(label).strip()
        if clean and clean not in clean_labels:
            clean_labels.append(clean)
    if not clean_labels:
        return {"success": False, "message": "没有可生成的编号"}

    existing = {
        c.label: c
        for c in db.query(CustomerAccessCode).filter(
            CustomerAccessCode.shop_id == current_shop.shop_id,
            CustomerAccessCode.label.in_(clean_labels)
        ).all()
    }

    result = []
    for label in clean_labels:
        code = existing.get(label)
        if not code:
            code = CustomerAccessCode(
                shop_id=current_shop.shop_id,
                label=label,
                token=secrets.token_urlsafe(24),
                is_active=True,
            )
            db.add(code)
            db.flush()
        result.append(code)
    db.commit()

    base = _get_base_url(request)
    universal_url = _customer_universal_url(request, current_shop.shop_code)
    return {
        "success": True,
        "shop_code": current_shop.shop_code,
        "universal_url": universal_url,
        "codes": [
            {
                "code_id": c.code_id,
                "label": c.label,
                "token": c.token,
                "url": f"{base}/customer.html?t={c.token}",
                "is_active": c.is_active,
            }
            for c in result
        ],
    }
