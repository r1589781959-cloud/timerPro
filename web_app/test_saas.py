"""
TimerPro SaaS 系统测试脚本
用于测试多商家注册、登录和API功能
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health():
    """测试健康检查"""
    print_section("健康检查")
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    print(f"状态: {data['status']}")
    print(f"版本: {data['version']}")
    print(f"SaaS模式: {data.get('saas_mode', False)}")


def test_register():
    """测试商家注册"""
    print_section("商家注册")

    # 1. 检查商家编码是否可用
    shop_code = "testshop001"
    response = requests.get(f"{BASE_URL}/api/merchants/check-code?code={shop_code}")
    print(f"商家编码 '{shop_code}' 可用性: {response.json()['message']}")

    # 2. 发送验证码
    print("\n发送验证码...")
    response = requests.post(
        f"{BASE_URL}/api/merchants/verify-code/send",
        json={
            "phone": "13800138000",
            "code_type": "register"
        }
    )
    if response.ok:
        print("✓ 验证码已发送（请查看控制台）")
        verify_code = input("请输入验证码: ").strip()
    else:
        print("✗ 验证码发送失败")
        verify_code = "123456"  # 测试时使用

    # 3. 注册商家
    print("\n注册商家...")
    response = requests.post(
        f"{BASE_URL}/api/merchants/register",
        json={
            "shop_name": "测试商家",
            "shop_code": shop_code,
            "contact_phone": "13800138000",
            "admin_name": "测试管理员",
            "password": "test123456",
            "password_confirm": "test123456",
            "verify_code": verify_code,
            "address": "测试地址",
            "description": "这是一个测试商家"
        }
    )

    if response.ok:
        data = response.json()
        print("✓ 注册成功!")
        print(f"  商家编码: {data['shop']['shop_code']}")
        print(f"  商家名称: {data['shop']['shop_name']}")
        print(f"  用户ID: {data['user']['user_id']}")
        print(f"  角色: {data['user']['role']}")
        return data['access_token'], data['shop']['shop_id']
    else:
        print(f"✗ 注册失败: {response.json()['detail']}")
        return None, None


def test_login(token=None):
    """测试登录"""
    print_section("商家登录")

    response = requests.post(
        f"{BASE_URL}/api/merchants/login",
        json={
            "shop_code": "starbilliards",
            "phone": "13800138000",
            "password": "admin888"
        }
    )

    if response.ok:
        data = response.json()
        print("✓ 登录成功!")
        print(f"  商家名称: {data['shop']['shop_name']}")
        print(f"  用户角色: {data['user']['role']}")
        return data['access_token']
    else:
        print(f"✗ 登录失败: {response.json()['detail']}")
        return None


def test_merchant_info(token):
    """测试获取商家信息"""
    print_section("获取商家信息")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/merchants/info", headers=headers)

    if response.ok:
        data = response.json()
        print("✓ 获取成功!")
        print(f"  商家ID: {data['shop_id']}")
        print(f"  商家编码: {data['shop_code']}")
        print(f"  商家名称: {data['shop_name']}")
        print(f"  手机号: {data['phone']}")
        print(f"  状态: {data['status']}")
    else:
        print(f"✗ 获取失败: {response.json()['detail']}")


def test_shop_config(token):
    """测试获取店铺配置"""
    print_section("获取店铺配置")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/config/shop", headers=headers)

    if response.ok:
        data = response.json()
        print("✓ 获取成功!")
        print(f"  基础价格: ¥{data['price_base']}")
        print(f"  基础时间: {data['time_base']} 分钟")
        print(f"  计算模式: {data['calc_mode']}")
        print(f"  团购数量: {data.get('group_buy_count', 0)}")
    else:
        print(f"✗ 获取失败: {response.json()['detail']}")


def test_group_buys(token):
    """测试获取团购配置"""
    print_section("获取团购配置")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/config/group-buys", headers=headers)

    if response.ok:
        data = response.json()
        print(f"✓ 获取成功! 共 {len(data)} 个团购配置")
        for gb in data:
            print(f"\n  - {gb['name']}")
            print(f"    类型: {gb['type']}, 价格: ¥{gb['price']}")
            print(f"    人数: {gb['persons']}, 限时: {gb['limit_min']} 分钟")
    else:
        print(f"✗ 获取失败: {response.json()['detail']}")


def test_active_data(token):
    """测试获取活跃订单"""
    print_section("获取活跃订单")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/data/active", headers=headers)

    if response.ok:
        data = response.json()
        print(f"✓ 获取成功! 活跃订单数: {data['c']}")
        if data['g']:
            for order_id, order_data in data['g'].items():
                print(f"\n  订单 {order_id}:")
                print(f"    手机号: {order_data['phone']}")
                print(f"    模式: {order_data['mode']}")
                print(f"    开始时间: {order_data['start_time']}")
        else:
            print("  当前没有活跃订单")
    else:
        print(f"✗ 获取失败: {response.json()['detail']}")


def test_history(token):
    """测试获取历史记录"""
    print_section("获取历史记录")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/history", headers=headers)

    if response.ok:
        data = response.json()
        print(f"✓ 获取成功! 历史订单数: {len(data['history'])}")
        if data['history']:
            print("\n  最近5条记录:")
            for h in data['history'][:5]:
                print(f"    {h['phone']} - {h['mode']} - ¥{h['actual_cost']}")
        else:
            print("  暂无历史记录")
    else:
        print(f"✗ 获取失败: {response.json()['detail']}")


def test_merchant_stats(token):
    """测试获取商家统计"""
    print_section("获取商家统计")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/merchants/stats", headers=headers)

    if response.ok:
        data = response.json()
        print("✓ 获取成功!")
        print(f"  活跃订单: {data['active_orders']}")
        print(f"  员工数量: {data['employee_count']}")
        print(f"  团购配置: {data['group_buy_count']}")
    else:
        print(f"✗ 获取失败: {response.json()['detail']}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  TimerPro SaaS 系统测试")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 健康检查
    test_health()

    # 2. 测试注册（可选）
    print("\n是否测试商家注册? (y/n): ", end="")
    if input().strip().lower() == 'y':
        register_token, shop_id = test_register()
        if register_token:
            # 使用新注册的token测试其他功能
            test_merchant_info(register_token)
            test_shop_config(register_token)
            test_group_buys(register_token)
            test_active_data(register_token)
            test_history(register_token)
            test_merchant_stats(register_token)
        return

    # 3. 测试登录（使用默认测试账号）
    login_token = test_login()
    if not login_token:
        print("\n提示: 请先运行 'cd web_app && python init_db.py' 初始化数据库")
        print("      默认测试账号: shop_code=starbilliards, phone=13800138000, password=admin888")
        return

    # 4. 测试其他API
    test_merchant_info(login_token)
    test_shop_config(login_token)
    test_group_buys(login_token)
    test_active_data(login_token)
    test_history(login_token)
    test_merchant_stats(login_token)

    print("\n" + "=" * 60)
    print("  测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n错误: 无法连接到服务器")
        print("请确保服务器正在运行: cd web_app && python main_saas.py")
    except KeyboardInterrupt:
        print("\n\n测试已中断")
