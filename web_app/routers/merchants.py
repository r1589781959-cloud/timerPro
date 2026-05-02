"""
商家管理相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import secrets
import json

from ..database import get_db, Shop, User, Order, SystemConfig, GroupBuy, VerifyCode
from ..auth import (
    RegisterRequest, LoginRequest, SendVerifyCodeRequest,
    CheckShopCodeRequest, Token, jwt_service, password_service,
    verify_code_service, smtp_service, get_current_user, get_current_shop, require_admin
)
from typing import Optional
import random

router = APIRouter(prefix="/api/merchants", tags=["merchants"])


# =====================================================
# 验证码相关接口
# =====================================================

@router.post("/verify-code/send")
async def send_verify_code(
    request: SendVerifyCodeRequest,
    db: Session = Depends(get_db)
):
    """发送邮箱验证码"""
    # 验证邮箱格式
    if not verify_code_service.is_valid_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式不正确"
        )

    # 检查是否频繁发送（60秒内只能发送一次）
    now = datetime.now()
    recent_code = db.query(VerifyCode).filter(
        VerifyCode.email == request.email,
        VerifyCode.code_type == request.code_type,
        VerifyCode.is_used == False,
        VerifyCode.expire_at > now
    ).order_by(VerifyCode.created_at.desc()).first()

    if recent_code and (now - recent_code.created_at).seconds < 60:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="验证码发送过于频繁，请稍后再试"
        )

    # 生成验证码
    code = verify_code_service.generate_code(6)
    expire_at = now + timedelta(minutes=5)

    # 保存验证码到数据库
    new_code = VerifyCode(
        email=request.email,
        code=code,
        code_type=request.code_type,
        expire_at=expire_at
    )
    db.add(new_code)
    db.commit()

    # 通过 SMTP 发送邮件
    sent = smtp_service.send_verify_code(request.email, code, request.code_type)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码邮件发送失败，请稍后重试"
        )

    return {
        "success": True,
        "message": "验证码已发送至您的邮箱",
        "expire_seconds": 300
    }


@router.get("/check-code")
async def check_shop_code(
    code: str,
    db: Session = Depends(get_db)
):
    """检查商家编码是否可用"""
    existing_shop = db.query(Shop).filter(Shop.shop_code == code).first()

    if existing_shop:
        return {
            "available": False,
            "message": "商家编码已被使用"
        }

    return {
        "available": True,
        "message": "商家编码可用"
    }


# =====================================================
# 注册相关接口
# =====================================================

@router.post("/register", response_model=Token)
async def register_merchant(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """商家注册"""

    # 1. 验证两次密码是否一致
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次密码不一致"
        )

    # 2. 验证密码强度（6-20位）
    if len(request.password) < 6 or len(request.password) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度必须在6-20位之间"
        )

    # 3. 验证邮箱格式
    if not verify_code_service.is_valid_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式不正确"
        )

    # 4. 检查邮箱是否已注册
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已注册"
        )

    # 5. 验证邮箱验证码
    now = datetime.now()
    verify_code_record = db.query(VerifyCode).filter(
        VerifyCode.email == request.email,
        VerifyCode.code == request.verify_code,
        VerifyCode.code_type == "register",
        VerifyCode.is_used == False,
        VerifyCode.expire_at > now
    ).first()

    if not verify_code_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )

    # 6. 生成商家编码（如果未指定）
    if not request.shop_code:
        # 基于店铺名称生成拼音简写 + 随机数
        base_code = "shop"  # 简化处理，实际可以使用拼音转换库
        random_suffix = random.randint(1000, 9999)
        request.shop_code = f"{base_code}{random_suffix}"

    # 检查商家编码是否已被使用
    existing_shop = db.query(Shop).filter(Shop.shop_code == request.shop_code).first()
    if existing_shop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="商家编码已被使用，请更换"
        )

    try:
        # 7. 创建商家记录
        new_shop = Shop(
            name=request.shop_name,
            shop_code=request.shop_code,
            email=request.email,
            address=request.address,
            status=1
        )
        db.add(new_shop)
        db.flush()  # 获取shop_id

        # 8. 创建管理员用户
        new_user = User(
            shop_id=new_shop.shop_id,
            username=request.email,
            email=request.email,
            password_hash=password_service.hash_password(request.password),
            role="admin",
            real_name=request.admin_name
        )
        db.add(new_user)
        db.flush()

        # 9. 初始化系统配置（使用默认配置）
        default_config = SystemConfig(
            shop_id=new_shop.shop_id,
            price_base=10.9,
            time_base=60,
            price_overtime=10.9,
            buffer_min=10,
            calc_mode="step",
            step_n=10,
            step_y=2.0,
            step_k=2.0,
            ceil_x=5,
            price_unlimited=59.9,
            price_single_board=39.9,
            price_fixed_60=19.9,
            price_fixed_120=35.0,
            price_fixed_180=49.9
        )
        db.add(default_config)

        # 10. 添加默认团购配置
        default_group_buys = [
            GroupBuy(
                shop_id=new_shop.shop_id,
                name="🎫 双人全天畅玩",
                type="unlimited",
                price=88.0,
                persons=2,
                limit_min=0,
                start_time="00:00",
                end_time="23:59",
                sort_order=1
            ),
            GroupBuy(
                shop_id=new_shop.shop_id,
                name="🎫 单人2小时特惠",
                type="fixed",
                price=17.9,
                persons=1,
                limit_min=120,
                start_time="00:00",
                end_time="23:59",
                sort_order=2
            ),
            GroupBuy(
                shop_id=new_shop.shop_id,
                name="🎫 早鸟4小时畅玩(10-14点)",
                type="time_slot",
                price=25.0,
                persons=1,
                limit_min=240,
                start_time="10:00",
                end_time="14:00",
                sort_order=3
            ),
            GroupBuy(
                shop_id=new_shop.shop_id,
                name="🎫 双人2小时",
                type="fixed",
                price=30.0,
                persons=2,
                limit_min=120,
                start_time="00:00",
                end_time="23:59",
                sort_order=4
            )
        ]
        db.bulk_save_objects(default_group_buys)

        # 标记验证码为已使用
        verify_code_record.is_used = True
        verify_code_record.used_at = now

        db.commit()

        # 11. 生成JWT Token
        token_data = {
            "sub": request.email,
            "shop_id": new_shop.shop_id,
            "user_id": new_user.user_id,
            "role": new_user.role
        }

        access_token = jwt_service.create_access_token(token_data)
        refresh_token = jwt_service.create_refresh_token(token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            shop={
                "shop_id": new_shop.shop_id,
                "shop_code": new_shop.shop_code,
                "shop_name": new_shop.name,
                "email": new_shop.email,
                "address": new_shop.address
            },
            user={
                "user_id": new_user.user_id,
                "username": new_user.username,
                "role": new_user.role,
                "real_name": new_user.real_name,
                "email": new_user.email
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


# =====================================================
# 登录相关接口
# =====================================================

@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """商家登录"""

    # 1. 查找用户（通过邮箱）
    user = db.query(User).filter(
        or_(
            User.email == request.email,
            User.username == request.email
        )
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 2. 验证密码
    if not password_service.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 3. 检查商家状态
    shop = db.query(Shop).filter(Shop.shop_id == user.shop_id).first()
    if not shop or shop.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="商家账号已被禁用"
        )

    # 4. 更新最后登录时间
    user.last_login_at = datetime.now()
    db.commit()

    # 5. 生成JWT Token
    token_data = {
        "sub": user.username,
        "shop_id": user.shop_id,
        "user_id": user.user_id,
        "role": user.role
    }

    access_token = jwt_service.create_access_token(token_data)
    refresh_token = jwt_service.create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        shop={
            "shop_id": shop.shop_id,
            "shop_code": shop.shop_code,
            "shop_name": shop.name,
            "email": shop.email,
            "address": shop.address
        },
        user={
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "real_name": user.real_name,
            "email": user.email
        }
    )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    result = jwt_service.refresh_access_token(refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期"
        )
    return result


# =====================================================
# 商家信息接口
# =====================================================

@router.get("/info")
async def get_merchant_info(
    current_shop: Shop = Depends(get_current_shop)
):
    """获取当前商家信息"""
    return {
        "shop_id": current_shop.shop_id,
        "shop_code": current_shop.shop_code,
        "shop_name": current_shop.name,
        "email": current_shop.email,
        "phone": current_shop.phone,
        "address": current_shop.address,
        "logo_url": current_shop.logo_url,
        "status": current_shop.status,
        "created_at": current_shop.created_at.isoformat() if current_shop.created_at else None
    }


@router.put("/info")
async def update_merchant_info(
    data: dict,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """更新商家信息"""
    if "shop_name" in data:
        current_shop.name = data["shop_name"]
    if "address" in data:
        current_shop.address = data["address"]
    if "phone" in data:
        current_shop.phone = data["phone"]
    if "logo_url" in data:
        current_shop.logo_url = data["logo_url"]

    current_shop.updated_at = datetime.now()
    db.commit()

    return {
        "success": True,
        "message": "商家信息更新成功"
    }


# =====================================================
# 用户管理接口
# =====================================================

@router.get("/users")
async def get_users(
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """获取商家所有用户列表"""
    users = db.query(User).filter(User.shop_id == current_shop.shop_id).all()

    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "role": user.role,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]


@router.post("/users")
async def create_user(
    data: dict,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """创建新用户（员工）"""
    required_fields = ["username", "password", "real_name", "role"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"缺少必要字段: {field}"
            )

    # 检查用户名是否已存在
    existing_user = db.query(User).filter(
        User.shop_id == current_shop.shop_id,
        User.username == data["username"]
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    new_user = User(
        shop_id=current_shop.shop_id,
        username=data["username"],
        password_hash=password_service.hash_password(data["password"]),
        real_name=data["real_name"],
        role=data["role"],
        phone=data.get("phone")
    )
    db.add(new_user)
    db.commit()

    return {
        "success": True,
        "message": "用户创建成功",
        "user_id": new_user.user_id
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: dict,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    user = db.query(User).filter(
        User.shop_id == current_shop.shop_id,
        User.user_id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
    )

    if "real_name" in data:
        user.real_name = data["real_name"]
    if "phone" in data:
        user.phone = data["phone"]
    if "role" in data:
        user.role = data["role"]
    if "password" in data:
        user.password_hash = password_service.hash_password(data["password"])

    user.updated_at = datetime.now()
    db.commit()

    return {
        "success": True,
        "message": "用户信息更新成功"
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """删除用户"""
    user = db.query(User).filter(
        User.shop_id == current_shop.shop_id,
        User.user_id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 不能删除管理员
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除管理员账号"
        )

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "用户删除成功"
    }


# =====================================================
# 统计信息接口
# =====================================================

@router.get("/stats")
async def get_merchant_stats(
    current_shop: Shop = Depends(get_current_shop),
    db: Session = Depends(get_db)
):
    """获取商家统计信息"""
    # 活跃订单数
    active_orders = db.query(Order).filter(
        Order.shop_id == current_shop.shop_id,
        Order.status == "active"
    ).count()

    # 员工数量
    employee_count = db.query(User).filter(
        User.shop_id == current_shop.shop_id
    ).count()

    # 团购配置数
    group_buy_count = db.query(GroupBuy).filter(
        GroupBuy.shop_id == current_shop.shop_id,
        GroupBuy.is_active == True
    ).count()

    return {
        "active_orders": active_orders,
        "employee_count": employee_count,
        "group_buy_count": group_buy_count
    }
