"""
认证和JWT Token管理
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
import json
import bcrypt

# 配置常量
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "timerpro-saas-secret-key-2024")  # 固定密钥用于开发
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2小时
REFRESH_TOKEN_EXPIRE_DAYS = 7       # 7天

class JWTService:
    """JWT Token 服务"""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or JWT_SECRET_KEY
        self.algorithm = ALGORITHM

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[dict]:
        """解码并验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            print(f"Token解码失败: {e}")
            return None

    def verify_access_token(self, token: str) -> Optional[dict]:
        """验证访问令牌"""
        payload = self.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None

    def verify_refresh_token(self, token: str) -> Optional[dict]:
        """验证刷新令牌"""
        payload = self.decode_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None

    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """使用刷新令牌获取新的访问令牌"""
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None

        # 创建新的访问令牌
        access_token_data = {
            "sub": payload.get("sub"),
            "shop_id": payload.get("shop_id"),
            "user_id": payload.get("user_id"),
            "role": payload.get("role")
        }
        new_access_token = self.create_access_token(access_token_data)
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }


class PasswordService:
    """密码服务"""

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)


class VerifyCodeService:
    """验证码服务"""

    @staticmethod
    def generate_code(length: int = 6) -> str:
        """生成验证码"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """验证手机号格式（中国大陆）"""
        import re
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))


# 单例实例
jwt_service = JWTService()
password_service = PasswordService()
verify_code_service = VerifyCodeService()


# =====================================================
# Pydantic Models for Auth
# =====================================================

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    shop: dict
    user: dict

class TokenData(BaseModel):
    username: Optional[str] = None
    shop_id: Optional[int] = None
    user_id: Optional[int] = None
    role: Optional[str] = None

class RegisterRequest(BaseModel):
    shop_name: str
    shop_code: Optional[str] = None
    contact_phone: str
    admin_name: str
    password: str
    password_confirm: str
    verify_code: str
    address: Optional[str] = None
    description: Optional[str] = None

class LoginRequest(BaseModel):
    shop_code: Optional[str] = None  # 兼容多商家登录
    phone: str
    password: str

class SendVerifyCodeRequest(BaseModel):
    phone: str
    code_type: str = "register"  # register/login/reset_password

class CheckShopCodeRequest(BaseModel):
    code: str


# =====================================================
# Authentication Dependencies
# =====================================================

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db, User, Shop
from typing import Generator

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/merchants/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = jwt_service.verify_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_shop(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Shop:
    """获取当前用户所属的商家"""
    shop = db.query(Shop).filter(Shop.shop_id == current_user.shop_id).first()
    if shop is None:
        raise HTTPException(status_code=404, detail="商家不存在")
    return shop


def get_shop_from_header(
    shop_code: Optional[str] = Header(None, alias="X-Shop-Code"),
    db: Session = Depends(get_db)
) -> Shop:
    """从请求头获取商家信息（用于小程序等场景）"""
    if not shop_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少商家编码"
        )

    shop = db.query(Shop).filter(Shop.shop_code == shop_code).first()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商家不存在"
        )

    return shop


def require_role(*allowed_roles: str):
    """角色权限检查装饰器"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


# 预定义的权限检查器
require_admin = require_role("admin")
require_employee = require_role("admin", "employee", "staff")
