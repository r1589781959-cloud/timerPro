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
    def is_valid_email(email: str) -> bool:
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


class SMTPService:
    """邮件发送服务"""

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "465"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_name = os.getenv("SMTP_FROM_NAME", "TimerPro")

    def send_verify_code(self, to_email: str, code: str, code_type: str = "register") -> bool:
        """发送验证码邮件"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        if not self.host or not self.user or not self.password:
            # SMTP 未配置，回退到控制台输出
            print(f"[SMTP未配置 - 验证码] {to_email}: {code} (类型: {code_type})")
            return True

        type_names = {
            "register": "注册",
            "login": "登录",
            "reset_password": "重置密码"
        }
        type_text = type_names.get(code_type, "操作")

        subject = f"TimerPro {type_text}验证码: {code}"
        html_body = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; border: 1px solid #e5e7eb; border-radius: 16px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #4f46e5; margin: 0; font-size: 24px;">TimerPro</h1>
                <p style="color: #6b7280; margin: 4px 0 0; font-size: 14px;">智能计时收银系统</p>
            </div>
            <div style="background: #f8fafc; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 20px;">
                <p style="color: #374151; font-size: 14px; margin: 0 0 12px;">您的{type_text}验证码是：</p>
                <div style="font-size: 36px; font-weight: bold; color: #4f46e5; letter-spacing: 8px; font-family: monospace;">{code}</div>
            </div>
            <p style="color: #9ca3af; font-size: 12px; text-align: center; margin: 0;">验证码 5 分钟内有效，请勿泄露给他人。</p>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=10) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.user, to_email, msg.as_string())
            else:
                with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.sendmail(self.user, to_email, msg.as_string())
            print(f"[邮件已发送] {to_email} ({code_type})")
            return True
        except Exception as e:
            print(f"[邮件发送失败] {to_email}: {e}")
            return False


# 单例实例
jwt_service = JWTService()
password_service = PasswordService()
verify_code_service = VerifyCodeService()
smtp_service = SMTPService()


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
    email: str              # 注册邮箱
    admin_name: str
    password: str
    password_confirm: str
    verify_code: str
    address: Optional[str] = None
    description: Optional[str] = None

class LoginRequest(BaseModel):
    shop_code: Optional[str] = None
    email: str              # 登录邮箱
    password: str

class SendVerifyCodeRequest(BaseModel):
    email: str
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
