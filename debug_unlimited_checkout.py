#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
不限时类型团购结账调试脚本
模拟实际的结账流程
"""
import json
import sys
import io
from datetime import datetime

# 设置编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def fmt_min(minutes):
    """格式化分钟数"""
    if minutes < 60:
        return f"{minutes}分钟"
    else:
        h = minutes // 60
        m = minutes % 60
        if m == 0:
            return f"{h}小时"
        else:
            return f"{h}小时{m}分钟"

def fmt_duration_str(seconds):
    """格式化时长字符串"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}分{int(seconds % 60)}秒"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}小时{minutes}分"

def simulate_calculate_single_bill(gid, data, end_time):
    """模拟 calculate_single_bill 函数"""
    print(f"\n=== 模拟 calculate_single_bill ===")
    print(f"GID: {gid}")
    print(f"结束时间: {end_time}")

    # 模拟时间计算
    start_time = data['start_time']
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")

    total_pause_sec = data.get('total_pause_sec', 0)
    raw_duration_sec = (end_time - start_time).total_seconds()
    effective_duration_sec = raw_duration_sec - total_pause_sec
    minutes = int(effective_duration_sec / 60)

    print(f"开始时间: {start_time}")
    print(f"总时长: {fmt_duration_str(raw_duration_sec)}")
    print(f"暂停时长: {fmt_duration_str(total_pause_sec)}")
    print(f"有效时长: {fmt_duration_str(effective_duration_sec)}")
    print(f"有效分钟数: {minutes}")

    # 初始化变量
    total_price = 0.0
    fixed_time_str = "--"
    mode_info = ""
    over_info = "正常"
    gb_voucher_price = 0.0
    gb_extra_cost = 0.0
    gb_verified = data.get('gb_verified', False)

    # 团购模式处理
    if data['mode'] == 'group_buy':
        gb = data['gb_config']
        mode_info = gb['name']
        bp = gb.get('price', 0.0)
        gb_persons = gb.get('persons', 1)

        print(f"\n--- 团购模式处理 ---")
        print(f"团购名称: {gb['name']}")
        print(f"团购类型: {gb['type']}")
        print(f"团购价格: ¥{bp}")
        print(f"包含人数: {gb_persons}")

        # 不限时类型处理
        if gb.get('type') in ['unlimited', 'single_board']:
            print(f"处理不限时类型...")
            gb_voucher_price = round(bp / gb_persons, 2)
            total_price = gb_voucher_price
            gb_extra_cost = 0.0
            over_info = "团购不限时"
            print(f"  团购券价格(每人): ¥{gb_voucher_price}")
            print(f"  总价格: ¥{total_price}")
            print(f"  超时费用: ¥{gb_extra_cost}")
        else:
            print(f"处理其他类型团购...")
            # 其他类型的团购处理逻辑...

    # 计算添加的团购券费用
    added_gb_cost = 0.0
    if 'added_gb' in data:
        for gb in data['added_gb']:
            if not gb['verify_status']:
                added_gb_cost += gb['price']
        print(f"添加的团购券费用: ¥{added_gb_cost}")

    # 计算直接添加时间的费用
    added_time_cost = 0.0
    if data['mode'] not in ['fixed', 'group_buy', 'unlimited', 'single_board']:
        added_time_cost = data.get('added_time_cost', 0.0)
        print(f"添加时间费用: ¥{added_time_cost}")

    # 调整总价格
    total_price = round(total_price + added_gb_cost + added_time_cost, 2)
    print(f"调整后总价格: ¥{total_price}")

    # 根据核销状态调整应收金额
    if data['mode'] == 'group_buy' and gb_verified:
        actual_total = gb_extra_cost + added_gb_cost
        print(f"已核销，应收金额: ¥{actual_total} (仅超时费+未核销团购券)")
    else:
        actual_total = total_price
        print(f"未核销，应收金额: ¥{actual_total}")

    actual_total = round(actual_total, 2)

    # 返回账单数据
    bill = {
        "gid": gid,
        "data": data,
        "end_time": end_time,
        "minutes": minutes,
        "total_dur_str": fmt_duration_str(raw_duration_sec),
        "play_dur_str": fmt_duration_str(effective_duration_sec),
        "pause_dur_str": fmt_duration_str(total_pause_sec),
        "total": total_price,
        "actual_total": actual_total,
        "prepaid": round(data.get('prepaid', 0.0), 2),
        "need": round(max(0, actual_total - data.get('prepaid', 0.0)), 2),
        "fixed_str": fixed_time_str,
        "mode_info": mode_info,
        "over_info": over_info,
        "pause_str": "无",
        "gb_voucher_price": gb_voucher_price,
        "gb_extra_cost": gb_extra_cost,
        "gb_verified": gb_verified
    }

    print(f"\n=== 账单数据 ===")
    for key, value in bill.items():
        if key != 'data':
            print(f"{key}: {value}")

    return bill

def simulate_show_single_checkout_ui(bill):
    """模拟 show_single_checkout_ui 函数"""
    print(f"\n=== 模拟 show_single_checkout_ui ===")

    # 检查关键数据
    required_fields = [
        'gid', 'data', 'end_time', 'total_dur_str', 'play_dur_str',
        'pause_dur_str', 'total', 'actual_total', 'fixed_str',
        'mode_info', 'over_info', 'pause_str',
        'gb_voucher_price', 'gb_extra_cost', 'gb_verified'
    ]

    print("检查必需字段:")
    all_fields_present = True
    for field in required_fields:
        present = field in bill
        status = "✓" if present else "✗"
        print(f"  {status} {field}: {present}")
        if not present:
            all_fields_present = False

    if not all_fields_present:
        print("❌ 缺少必需字段，无法创建结账界面")
        return False

    # 检查数据类型
    print("\n检查数据类型:")
    type_checks = [
        ('actual_total', float),
        ('gb_voucher_price', float),
        ('gb_extra_cost', float),
        ('gb_verified', bool)
    ]

    all_types_correct = True
    for field, expected_type in type_checks:
        actual_type = type(bill[field])
        correct = isinstance(bill[field], expected_type)
        status = "✓" if correct else "✗"
        print(f"  {status} {field}: 期望 {expected_type.__name__}, 实际 {actual_type.__name__}")
        if not correct:
            all_types_correct = False

    if not all_types_correct:
        print("❌ 数据类型错误，可能导致界面创建失败")
        return False

    # 检查结账界面显示逻辑
    print("\n检查结账界面显示逻辑:")

    mode = bill['data']['mode']
    gb_config = bill['data'].get('gb_config', {})

    print(f"模式: {mode}")
    print(f"团购配置: {gb_config}")

    # 检查是否创建核销管理界面
    if mode == 'group_buy':
        print("  ✓ 会创建核销管理界面")
        print("    - verify_var 会被创建")
        print("    - lbl_actual_total 会被创建")
        print("    - lbl_verify_status 会被创建")
    else:
        print("  ✗ 不会创建核销管理界面")

    # 检查显示逻辑
    if mode == 'group_buy':
        print(f"  ✓ 会显示团购特有信息")
        print(f"    - 团购券价格: ¥{bill['gb_voucher_price']:.2f}")
        if bill['gb_extra_cost'] > 0:
            print(f"    - 超时费用: ¥{bill['gb_extra_cost']:.2f}")
        else:
            print(f"    - 无超时费用")

        # 检查添加的团购券
        if 'added_gb' in bill['data'] and bill['data']['added_gb']:
            print(f"    - 添加团购券: {len(bill['data']['added_gb'])} 张")
        else:
            print(f"    - 无添加团购券")

    # 检查总定额时长显示
    total_fixed_min = 0
    if mode == 'group_buy' and gb_config:
        base_min = gb_config.get('limit_min', 0)
        added_time_min = bill['data'].get('added_time_min', 0)
        added_gb_min = sum(gb.get('minutes', 0) for gb in bill['data'].get('added_gb', []))
        total_fixed_min = base_min + added_time_min + added_gb_min

    print(f"\n  总定额时长计算: {total_fixed_min} 分钟")
    if total_fixed_min > 0 and mode not in ['unlimited', 'single_board']:
        print(f"  ⚠️ 会显示总定额时长（可能不正确）")
    else:
        print(f"  ✓ 不会显示总定额时长（正确）")

    print("\n✓ 结账界面应该可以正常创建")
    return True

def main():
    """主测试函数"""
    print("="*60)
    print("不限时类型团购结账流程调试")
    print("="*60)

    # 创建测试数据
    unlimited_gb = {
        "name": "🎫 双人全天畅玩",
        "type": "unlimited",
        "price": 88.0,
        "persons": 2,
        "limit_min": 0,
        "buffer_min": 0,
        "overtime_price": 0.0,
        "start_time": "00:00",
        "end_time": "23:59"
    }

    guest_data = {
        "phone": "12345",
        "mode": "group_buy",
        "gb_config": unlimited_gb,
        "gb_verified": False,
        "start_time": datetime(2026, 4, 11, 10, 0, 0),
        "added_gb": [],
        "added_time_min": 0,
        "remark": "",
        "total_pause_sec": 0,
        "prepaid": 0.0
    }

    gid = "test_001"
    end_time = datetime(2026, 4, 11, 12, 30, 0)  # 使用2.5小时

    # 模拟计费计算
    try:
        bill = simulate_calculate_single_bill(gid, guest_data, end_time)
        print("\n✓ 计费计算成功")
    except Exception as e:
        print(f"\n❌ 计费计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 模拟结账界面创建
    try:
        success = simulate_show_single_checkout_ui(bill)
        if success:
            print("\n✓ 结账界面创建应该成功")
            return True
        else:
            print("\n❌ 结账界面创建可能失败")
            return False
    except Exception as e:
        print(f"\n❌ 结账界面创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    print("\n" + "="*60)
    print(f"测试结果: {'通过 ✓' if success else '失败 ✗'}")
    print("="*60)
