"""
数据库初始化和迁移脚本
"""
from sqlalchemy.orm import Session
import json
from pathlib import Path

try:
    from .database import SessionLocal, create_tables, Shop, User, SystemConfig, GroupBuy
except ImportError:
    from database import SessionLocal, create_tables, Shop, User, SystemConfig, GroupBuy

DEFAULT_ADMIN_PASSWORD = "admin123"

def init_default_data():
    """初始化默认数据（如果不存在）"""
    db = SessionLocal()

    try:
        # 检查是否已经有商家数据
        existing_shops = db.query(Shop).count()
        if existing_shops > 0:
            print(f"数据库已包含 {existing_shops} 个商家，跳过初始化")
            return

        print("开始初始化默认数据...")

        # 1. 创建测试商家
        test_shop = Shop(
            name="星空桌球俱乐部",
            shop_code="starbilliards",
            phone="13800138000",
            address="北京市朝阳区星空大厦1楼",
            status=1
        )
        db.add(test_shop)
        db.flush()  # 获取shop_id

        # 2. 创建测试用户（管理员）
        import bcrypt

        # 生成密码哈希
        password_bytes = DEFAULT_ADMIN_PASSWORD.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

        test_user = User(
            shop_id=test_shop.shop_id,
            username="admin",
            email="admin@timerpro.local",
            password_hash=password_hash,
            role="admin",
            real_name="系统管理员",
            phone="13800138000"
        )
        db.add(test_user)

        # 3. 初始化系统配置（从现有的shop_config.json读取）
        config_file = Path(__file__).parent.parent / "shop_config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                shop_config = json.load(f)
        else:
            # 默认配置
            shop_config = {
                "price_base": 10.9,
                "time_base": 60,
                "price_overtime": 10.9,
                "buffer_min": 10,
                "calc_mode": "step",
                "step_n": 10,
                "step_y": 2.0,
                "step_k": 2.0,
                "ceil_x": 5,
                "price_unlimited": 59.9,
                "price_single_board": 39.9,
                "price_fixed_60": 19.9,
                "price_fixed_120": 35.0,
                "price_fixed_180": 49.9
            }

        system_config = SystemConfig(
            shop_id=test_shop.shop_id,
            price_base=shop_config.get("price_base", 10.9),
            time_base=shop_config.get("time_base", 60),
            price_overtime=shop_config.get("price_overtime", 10.9),
            buffer_min=shop_config.get("buffer_min", 10),
            calc_mode=shop_config.get("calc_mode", "step"),
            step_n=shop_config.get("step_n"),
            step_y=shop_config.get("step_y"),
            step_k=shop_config.get("step_k"),
            ceil_x=shop_config.get("ceil_x"),
            price_unlimited=shop_config.get("price_unlimited"),
            price_single_board=shop_config.get("price_single_board"),
            price_fixed_60=shop_config.get("price_fixed_60"),
            price_fixed_120=shop_config.get("price_fixed_120"),
            price_fixed_180=shop_config.get("price_fixed_180")
        )
        db.add(system_config)

        # 4. 初始化团购配置
        default_group_buys = [
            GroupBuy(
                shop_id=test_shop.shop_id,
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
                shop_id=test_shop.shop_id,
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
                shop_id=test_shop.shop_id,
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
                shop_id=test_shop.shop_id,
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

        db.commit()

        print("=" * 50)
        print("数据库初始化完成！")
        print("=" * 50)
        print(f"测试商家:")
        print(f"  - 商家名称: {test_shop.name}")
        print(f"  - 商家编码: {test_shop.shop_code}")
        print(f"  - 联系电话: {test_shop.phone}")
        print(f"\n管理员账号:")
        print(f"  - 用户名: {test_user.username}")
        print(f"  - 邮箱: {test_user.email}")
        print(f"  - 密码: {DEFAULT_ADMIN_PASSWORD}")
        print(f"  - 角色: {test_user.role}")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        db.close()

def migrate_from_files():
    """从现有JSON文件迁移数据到数据库"""
    db = SessionLocal()

    try:
        # 1. 迁移shop_config.json
        print("正在迁移shop_config.json...")
        config_file = Path(__file__).parent.parent / "shop_config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                shop_config = json.load(f)
            # 这里可以将配置迁移到对应的商家
            # 需要先确定要迁移到哪个商家
            print("shop_config.json 读取成功，但需要指定迁移目标商家")

        # 2. 迁移active_data.json
        print("正在迁移active_data.json...")
        data_file = Path(__file__).parent.parent / "active_data.json"
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8-sig") as f:
                active_data = json.load(f)
            # 这里需要解析active_data中的订单数据
            # 并转换为数据库记录
            print("active_data.json 读取成功，但需要指定迁移目标商家")

        # 3. 迁移history_data.json
        print("正在迁移history_data.json...")
        history_file = Path(__file__).parent.parent / "history_data.json"
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8-sig") as f:
                history_data = json.load(f)
            print("history_data.json 读取成功")

        print("\n数据迁移需要指定目标商家ID，请在代码中完善迁移逻辑")

    except Exception as e:
        print(f"迁移失败: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # 创建表结构
    create_tables()

    # 初始化默认数据
    init_default_data()

    # 如需迁移现有数据，取消下面注释
    # migrate_from_files()
