"""
Database Models and Connection for TimerPro SaaS System
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

# ==========================================
# Database Configuration
# ==========================================

# 同步数据库引擎（用于初始化）
SYNC_DATABASE_URL = "sqlite:///./timerpro_saas.db"
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# 导出给其他模块使用
engine = sync_engine
SessionLocal = SyncSessionLocal

# ==========================================
# Models
# ==========================================

class Shop(Base):
    """商家表"""
    __tablename__ = "shops"

    shop_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    shop_code = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, index=True)  # 主要联系邮箱
    phone = Column(String(20), index=True)  # 可选手机号
    address = Column(String(255))
    logo_url = Column(String(255))
    status = Column(Integer, default=1)  # 1:启用 0:禁用
    config_data = Column(Text)  # JSON格式配置数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    users = relationship("User", back_populates="shop", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="shop", cascade="all, delete-orphan")
    system_config = relationship("SystemConfig", back_populates="shop", uselist=False, cascade="all, delete-orphan")
    group_buys = relationship("GroupBuy", back_populates="shop", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="shop", cascade="all, delete-orphan")

class User(Base):
    """用户表"""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.shop_id"), nullable=False)
    username = Column(String(50), nullable=False)
    email = Column(String(100), index=True)  # 登录邮箱
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")  # admin/employee/staff
    real_name = Column(String(50))
    phone = Column(String(20))  # 可选手机号
    avatar_url = Column(String(255))
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    shop = relationship("Shop", back_populates="users")

    __table_args__ = (UniqueConstraint('shop_id', 'username', name='uq_shop_username'),)

class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    order_id = Column(String(36), primary_key=True)  # UUID
    shop_id = Column(Integer, ForeignKey("shops.shop_id"), nullable=False)
    phone = Column(String(20), nullable=False)
    mode = Column(String(20), nullable=False)  # fixed/group_buy/pay_later/single_board
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    limit_min = Column(Integer, default=0)
    limit_sec = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    prepaid = Column(Float, default=0.0)
    status = Column(String(20), default="active")  # active/paused/suspended/closed
    is_suspended = Column(Boolean, default=False)
    suspend_locked_cost = Column(Float, default=0.0)
    suspend_start_ts = Column(DateTime)
    group_id = Column(String(36))
    guest_count = Column(Integer, default=1)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    shop = relationship("Shop", back_populates="orders")
    pause_logs = relationship("OrderPauseLog", back_populates="order", cascade="all, delete-orphan")
    add_times = relationship("OrderAddTime", back_populates="order", cascade="all, delete-orphan")
    group_buys = relationship("OrderGroupBuy", back_populates="order", cascade="all, delete-orphan")

class OrderPauseLog(Base):
    """暂停日志表"""
    __tablename__ = "order_pause_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), ForeignKey("orders.order_id"), nullable=False)
    pause_start = Column(DateTime, nullable=False)
    pause_end = Column(DateTime)
    pause_seconds = Column(Integer, default=0)
    pause_type = Column(String(20))  # pause/cancel
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    order = relationship("Order", back_populates="pause_logs")

class OrderAddTime(Base):
    """加时记录表"""
    __tablename__ = "order_add_times"

    add_time_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), ForeignKey("orders.order_id"), nullable=False)
    minutes = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    add_time = Column(String(10), nullable=False)  # HH:mm格式
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    order = relationship("Order", back_populates="add_times")

class OrderGroupBuy(Base):
    """团购订单关联表"""
    __tablename__ = "order_group_buys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), ForeignKey("orders.order_id"), nullable=False)
    gb_config_id = Column(Integer, ForeignKey("group_buys.gb_config_id"), nullable=False)
    gb_name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    minutes = Column(Integer)
    verify_status = Column(Boolean, default=False)  # False:未核销 True:已核销
    add_time = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)

    # Relationships
    order = relationship("Order", back_populates="group_buys")

class GroupBuy(Base):
    """团购配置表"""
    __tablename__ = "group_buys"

    gb_config_id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.shop_id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # unlimited/fixed/time_slot
    price = Column(Float, nullable=False)
    persons = Column(Integer, default=1)
    limit_min = Column(Integer, default=0)
    limit_sec = Column(Integer, default=0)
    start_time = Column(String(10), default="00:00")
    end_time = Column(String(10), default="23:59")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    shop = relationship("Shop", back_populates="group_buys")
    order_group_buys = relationship("OrderGroupBuy", backref="group_buy")

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    config_id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.shop_id"), nullable=False)
    price_base = Column(Float, nullable=False)
    time_base = Column(Integer, nullable=False)
    price_overtime = Column(Float, nullable=False)
    buffer_min = Column(Integer, default=10)
    calc_mode = Column(String(20), default="step")
    step_n = Column(Integer)
    step_y = Column(Float)
    step_k = Column(Float)
    ceil_x = Column(Integer)
    price_unlimited = Column(Float)
    price_single_board = Column(Float)
    price_fixed_60 = Column(Float)
    price_fixed_120 = Column(Float)
    price_fixed_180 = Column(Float)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    shop = relationship("Shop", back_populates="system_config")

    __table_args__ = (UniqueConstraint('shop_id', name='uq_shop_config'),)

class OrderHistory(Base):
    """订单历史表"""
    __tablename__ = "order_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), ForeignKey("orders.order_id"))
    shop_id = Column(Integer, ForeignKey("shops.shop_id"), nullable=False)
    action_type = Column(String(20), nullable=False)  # checkout/pause/resume/suspend/add_time
    action_time = Column(DateTime, nullable=False)
    cost_before = Column(Float)
    cost_after = Column(Float)
    duration_before = Column(Integer)  # 持续时间（秒）
    duration_after = Column(Integer)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class APIKey(Base):
    """API密钥表"""
    __tablename__ = "api_keys"

    key_id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.shop_id"), nullable=False)
    key_name = Column(String(100), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    key_secret = Column(String(128), nullable=False)  # JWT Secret
    permissions = Column(Text)  # JSON格式
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    shop = relationship("Shop", back_populates="api_keys")

class VerifyCode(Base):
    """验证码表"""
    __tablename__ = "verify_codes"

    code_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), nullable=False, index=True)  # 接收验证码的邮箱
    code = Column(String(10), nullable=False)
    code_type = Column(String(20), nullable=False)  # register/login/reset_password
    expire_at = Column(DateTime, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    used_at = Column(DateTime)

class MerchantApplication(Base):
    """商家申请表"""
    __tablename__ = "merchant_applications"

    application_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    contact_name = Column(String(50), nullable=False)
    shop_code = Column(String(50), unique=True, nullable=False)
    address = Column(String(255))
    business_desc = Column(Text)
    password_hash = Column(String(255), nullable=False)
    apply_status = Column(String(20), default="pending")  # pending/approved/rejected
    verify_code = Column(String(10))
    verify_code_expire = Column(DateTime)
    reject_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    reviewed_at = Column(DateTime)

class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.shop_id"))
    user_id = Column(Integer)
    action = Column(String(50), nullable=False)
    request_data = Column(Text)  # JSON格式
    response_data = Column(Text)  # JSON格式
    ip_address = Column(String(45))
    user_agent = Column(Text)
    status_code = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# Database Operations
# ==========================================

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功")

def drop_tables():
    """删除所有表（谨慎使用！）"""
    Base.metadata.drop_all(bind=engine)
    print("数据库表已删除")

if __name__ == "__main__":
    create_tables()
