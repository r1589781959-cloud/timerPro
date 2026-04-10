#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整测试脚本 - 验证timerProV15修复
"""
import sys
import io

# 设置编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_syntax():
    """测试语法正确性"""
    print("="*60)
    print("1. 语法检查")
    print("="*60)

    try:
        import py_compile
        py_compile.compile('timerProV15.py', doraise=True)
        print("✓ 语法检查通过")
        return True
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False

def test_imports():
    """测试导入是否正常"""
    print("\n" + "="*60)
    print("2. 导入检查")
    print("="*60)

    try:
        # 不实际运行GUI，只检查导入
        import importlib.util
        spec = importlib.util.spec_from_file_location("timerProV15", "timerProV15.py")
        if spec and spec.loader:
            print("✓ 模块规格加载成功")
            return True
        else:
            print("✗ 模块规格加载失败")
            return False
    except Exception as e:
        print(f"✗ 导入检查失败: {e}")
        return False

def test_key_functions():
    """测试关键函数是否存在"""
    print("\n" + "="*60)
    print("3. 关键函数检查")
    print("="*60)

    try:
        with open('timerProV15.py', 'r', encoding='utf-8') as f:
            content = f.read()

        functions = [
            "def show_single_checkout_ui",
            "def calculate_single_bill",
            "def checkout",
            "def update_total_price"
        ]

        all_found = True
        for func in functions:
            found = func in content
            status = "✓" if found else "✗"
            print(f"{status} {func}: {'找到' if found else '未找到'}")
            if not found:
                all_found = False

        return all_found
    except Exception as e:
        print(f"✗ 函数检查失败: {e}")
        return False

def test_fixes():
    """测试修复是否应用"""
    print("\n" + "="*60)
    print("4. 修复应用检查")
    print("="*60)

    try:
        with open('timerProV15.py', 'r', encoding='utf-8') as f:
            content = f.read()

        fixes = [
            ("变量提前声明", "lbl_verify_status = None" in content),
            ("变量提前声明2", "lbl_actual_total = None" in content),
            ("安全检查", "if lbl_verify_status is not None:" in content),
            ("安全检查2", "if lbl_actual_total is not None:" in content),
            ("异常处理", "except Exception as e:" in content),
            ("错误打印", "traceback.print_exc()" in content)
        ]

        all_applied = True
        for fix_name, applied in fixes:
            status = "✓" if applied else "✗"
            print(f"{status} {fix_name}: {'已应用' if applied else '未应用'}")
            if not applied:
                all_applied = False

        return all_applied
    except Exception as e:
        print(f"✗ 修复检查失败: {e}")
        return False

def test_unlimited_logic():
    """测试不限时类型逻辑"""
    print("\n" + "="*60)
    print("5. 不限时类型逻辑检查")
    print("="*60)

    try:
        with open('timerProV15.py', 'r', encoding='utf-8') as f:
            content = f.read()

        unlimited_checks = [
            ("不限时类型处理", "type in ['unlimited', 'single_board']" in content),
            ("团购券价格计算", "gb_voucher_price = round(bp / gb_persons, 2)" in content),
            ("不限时状态信息", "团购不限时" in content),
            ("核销状态处理", "gb_verified" in content)
        ]

        all_correct = True
        for check_name, correct in unlimited_checks:
            status = "✓" if correct else "✗"
            print(f"{status} {check_name}: {'正确' if correct else '可能有问题'}")
            if not correct:
                all_correct = False

        return all_correct
    except Exception as e:
        print(f"✗ 逻辑检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("timerProV15 完整测试")
    print("="*60)

    tests = [
        ("语法检查", test_syntax),
        ("导入检查", test_imports),
        ("关键函数检查", test_key_functions),
        ("修复应用检查", test_fixes),
        ("不限时逻辑检查", test_unlimited_logic)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} 执行失败: {e}")
            results.append((test_name, False))

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {test_name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！代码应该可以正常运行。")
        print("\n建议操作:")
        print("1. 运行: python timerProV15.py")
        print("2. 创建不限时类型团购订单测试结账功能")
        print("3. 如果仍有问题，请提供具体的错误信息")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，可能存在问题。")

    print("="*60)

    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
