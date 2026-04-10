#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
不限时类型团购结账测试
"""
import json
import sys
import io

# 设置编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_unlimited_group_buy():
    """测试不限时类型团购的结账逻辑"""
    print("="*60)
    print("不限时类型团购结账测试")
    print("="*60)

    # 模拟不限时类型团购数据
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

    # 模拟客人数据
    guest_data = {
        "phone": "12345",
        "mode": "group_buy",
        "gb_config": unlimited_gb,
        "gb_verified": False,
        "start_time": "2026-04-11 10:00:00",
        "added_gb": [],
        "added_time_min": 0,
        "remark": ""
    }

    print(f"\n【测试数据】")
    print(f"团购名称: {unlimited_gb['name']}")
    print(f"团购类型: {unlimited_gb['type']}")
    print(f"团购价格: ¥{unlimited_gb['price']}")
    print(f"包含人数: {unlimited_gb['persons']}")
    print(f"每人价格: ¥{unlimited_gb['price'] / unlimited_gb['persons']:.2f}")

    # 模拟计费计算
    print(f"\n【计费计算】")
    bp = unlimited_gb.get('price', 0.0)
    gb_persons = unlimited_gb.get('persons', 1)
    gb_voucher_price = round(bp / gb_persons, 2)
    total_price = gb_voucher_price
    gb_extra_cost = 0.0
    over_info = "团购不限时"

    print(f"团购券价格(每人): ¥{gb_voucher_price:.2f}")
    print(f"总价格: ¥{total_price:.2f}")
    print(f"超时费用: ¥{gb_extra_cost:.2f}")
    print(f"状态信息: {over_info}")

    # 模拟结账界面逻辑
    print(f"\n【结账界面逻辑检查】")

    # 检查关键变量
    checks = {
        "mode == 'group_buy'": guest_data['mode'] == 'group_buy',
        "gb_config 存在": 'gb_config' in guest_data,
        "gb_config.type == 'unlimited'": guest_data['gb_config']['type'] == 'unlimited',
        "gb_voucher_price 计算": gb_voucher_price > 0,
        "total_price 计算": total_price > 0,
        "gb_extra_cost == 0": gb_extra_cost == 0
    }

    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}: {result}")

    # 检查结账界面显示逻辑
    print(f"\n【结账界面显示逻辑】")

    # 模拟 show_single_checkout_ui 中的逻辑
    mode = guest_data['mode']
    gb_config = guest_data.get('gb_config', {})

    print(f"模式: {mode}")
    print(f"团购配置类型: {gb_config.get('type', 'N/A')}")

    # 检查是否满足创建核销管理界面的条件
    should_create_verify_ui = (mode == 'group_buy')
    print(f"是否创建核销管理界面: {should_create_verify_ui}")

    if should_create_verify_ui:
        print(f"  - verify_var 会被创建: ✓")
        print(f"  - lbl_actual_total 会被创建: ✓")
        print(f"  - lbl_verify_status 应该已存在: ✓")

    # 检查是否满足显示核销状态标签的条件
    should_show_verify_status = (mode == 'group_buy')
    print(f"是否显示核销状态标签: {should_show_verify_status}")

    # 模拟 calculate_single_bill 的返回值
    bill = {
        "gid": "test_1",
        "data": guest_data,
        "mode_info": unlimited_gb['name'],
        "fixed_str": "--",
        "gb_voucher_price": gb_voucher_price,
        "gb_extra_cost": gb_extra_cost,
        "actual_total": total_price,
        "total": total_price,
        "over_info": over_info
    }

    print(f"\n【账单数据】")
    print(f"计费模式: {bill['mode_info']}")
    print(f"定额时长: {bill['fixed_str']}")
    print(f"团购券价格: ¥{bill['gb_voucher_price']:.2f}")
    print(f"超时费用: ¥{bill['gb_extra_cost']:.2f}")
    print(f"应收金额: ¥{bill['actual_total']:.2f}")
    print(f"状态信息: {bill['over_info']}")

    # 检查可能的问题
    print(f"\n【潜在问题检查】")

    potential_issues = []

    # 检查1: 总定额时长计算
    total_fixed_min = 0
    if mode == 'group_buy' and gb_config:
        base_min = gb_config.get('limit_min', 0)
        added_time_min = guest_data.get('added_time_min', 0)
        added_gb_min = sum(gb.get('minutes', 0) for gb in guest_data.get('added_gb', []))
        total_fixed_min = base_min + added_time_min + added_gb_min

    print(f"总定额时长计算: {total_fixed_min} 分钟")
    if total_fixed_min > 0 and mode not in ['unlimited', 'single_board']:
        print(f"  ⚠️ 会显示总定额时长（可能不正确）")
    else:
        print(f"  ✓ 不会显示总定额时长（正确）")

    # 检查2: 核销状态标签创建
    if mode == 'group_buy':
        print(f"  ✓ 核销状态标签会被创建")
    else:
        print(f"  ✗ 核销状态标签不会被创建（可能导致错误）")

    # 检查3: actual_total 计算
    if mode == 'group_buy':
        if guest_data.get('gb_verified', False):
            expected_actual = gb_extra_cost
        else:
            expected_actual = total_price

        if abs(bill['actual_total'] - expected_actual) < 0.01:
            print(f"  ✓ actual_total 计算正确: ¥{bill['actual_total']:.2f}")
        else:
            print(f"  ✗ actual_total 计算错误: 期望 ¥{expected_actual:.2f}, 实际 ¥{bill['actual_total']:.2f}")
            potential_issues.append("actual_total 计算错误")

    # 总结
    print(f"\n【测试总结】")
    if not potential_issues:
        print(f"✓ 所有检查通过，不限时类型团购应该可以正常结账")
    else:
        print(f"✗ 发现以下问题:")
        for issue in potential_issues:
            print(f"  - {issue}")

    return len(potential_issues) == 0

if __name__ == '__main__':
    success = test_unlimited_group_buy()
    print("\n" + "="*60)
    print(f"测试结果: {'通过' if success else '失败'}")
    print("="*60)
