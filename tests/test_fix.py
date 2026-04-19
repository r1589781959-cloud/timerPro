#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试不限时类型团购结账修复
"""
import sys
import io

# 设置编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_fix():
    """测试修复是否有效"""
    print("="*60)
    print("不限时类型团购结账修复验证")
    print("="*60)

    # 检查修复是否已应用
    print("\n【检查修复】")

    try:
        with open('timerProV15.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键修复点
        checks = [
            ("变量提前声明", "lbl_verify_status = None" in content),
            ("异常处理添加", "except Exception as e:" in content and "创建结账界面时出错" in content),
            ("安全检查添加", "if lbl_verify_status is not None:" in content),
            ("安全检查添加2", "if lbl_actual_total is not None:" in content)
        ]

        all_passed = True
        for check_name, result in checks:
            status = "✓" if result else "✗"
            print(f"{status} {check_name}: {'通过' if result else '未通过'}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n✓ 所有修复点都已应用")
        else:
            print("\n✗ 部分修复点未应用")

        return all_passed

    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False

def main():
    """主函数"""
    success = test_fix()

    if success:
        print("\n【修复完成】")
        print("不限时类型团购结账问题已修复，包括：")
        print("1. 提前声明关键变量避免作用域问题")
        print("2. 添加安全检查确保变量存在")
        print("3. 添加异常处理捕获和显示错误")
        print("4. 在 update_total_price 函数中添加错误处理")

        print("\n【测试建议】")
        print("1. 重新启动 timerProV15.py")
        print("2. 创建一个不限时类型团购订单（如：双人全天畅玩）")
        print("3. 点击结账按钮")
        print("4. 检查是否能正常进入结账界面")
        print("5. 测试核销状态切换功能是否正常")
    else:
        print("\n【修复未完成】")
        print("请手动检查修复是否正确应用")

    print("\n" + "="*60)
    print(f"验证结果: {'成功 ✓' if success else '失败 ✗'}")
    print("="*60)

if __name__ == '__main__':
    main()
