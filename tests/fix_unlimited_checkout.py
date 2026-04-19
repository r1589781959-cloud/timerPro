#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
不限时类型团购结账问题修复补丁

问题分析：
在 show_single_checkout_ui 函数中，lbl_verify_status 变量的作用域可能导致
不限时类型团购在结账时无法正确访问该变量，从而导致界面创建失败。

修复方案：
1. 确保 lbl_verify_status 变量在正确的位置创建和初始化
2. 添加异常处理来捕获和显示可能的错误
3. 确保所有必需的变量在使用前都已正确初始化
"""

def generate_fix():
    """生成修复代码"""

    fix_code = '''
# 在 timerProV15.py 的 show_single_checkout_ui 函数中，找到以下代码段：

# 原始代码（第1227-1233行附近）：
            # 创建可更新的核销状态标签
            f_verify_status = tk.Frame(f_detail, bg="#f0f0f0")
            f_verify_status.pack(fill="x", pady=2)
            tk.Label(f_verify_status, text="核销状态:", bg="#f0f0f0", font=("微软雅黑", 10)).pack(side="left")
            lbl_verify_status = tk.Label(f_verify_status, text="✗ 未核销", bg="#f0f0f0", fg="#e74c3c",
                                         font=("微软雅黑", 10, "bold"))
            lbl_verify_status.pack(side="right")

# 修复方案：
# 1. 在函数开始处提前声明 lbl_verify_status 变量
# 2. 添加异常处理确保界面创建失败时能显示错误信息

# 修复后的代码结构：

    def show_single_checkout_ui(self, b):
        """显示单人结账界面"""
        try:
            # 提前声明关键变量，确保作用域正确
            lbl_verify_status = None
            lbl_actual_total = None

            win = tk.Toplevel(self.root)
            win.title("结账/挂账详情")
            win.geometry("480x950")
            win.grab_set()

            # ... 原有的界面创建代码 ...

            # 显示团购特有信息
            if b['data']['mode'] == 'group_buy':
                row("团购券价格:", f"{b['gb_voucher_price']:.2f} 元", "#8e44ad")
                if b['gb_extra_cost'] > 0:
                    row("超时费用:", f"{b['gb_extra_cost']:.2f} 元", "#e74c3c")

                # ... 其他团购信息显示 ...

                # 创建可更新的核销状态标签（确保变量在正确的作用域）
                f_verify_status = tk.Frame(f_detail, bg="#f0f0f0")
                f_verify_status.pack(fill="x", pady=2)
                tk.Label(f_verify_status, text="核销状态:", bg="#f0f0f0", font=("微软雅黑", 10)).pack(side="left")
                lbl_verify_status = tk.Label(f_verify_status, text="✗ 未核销", bg="#f0f0f0", fg="#e74c3c",
                                             font=("微软雅黑", 10, "bold"))
                lbl_verify_status.pack(side="right")

            # ... 其他界面元素 ...

            # 团购核销状态修改
            verify_var = None
            if b['data']['mode'] == 'group_buy':
                tk.Label(win, text="核销管理:", font=("微软雅黑", 10, "bold")).pack(pady=(15, 5))
                f_verify_frame = tk.Frame(win)
                f_verify_frame.pack(fill="x", padx=30, pady=5)

                verify_var = tk.StringVar(value="verified" if b['data'].get('gb_verified', False) else "unverified")
                lbl_actual_total = tk.Label(win, text="", font=("微软雅黑", 10))

                def update_total_price(*args):
                    """实时更新应收金额和核销状态显示"""
                    try:
                        is_verified = verify_var.get() == "verified"

                        # 计算中途添加的团购券的费用
                        added_gb_cost = 0.0
                        if 'added_gb' in b['data']:
                            for gb in b['data']['added_gb']:
                                if not gb['verify_status']:
                                    added_gb_cost += gb['price']

                        # 计算直接添加时间的费用
                        added_time_cost = b['data'].get('added_time_cost', 0.0)

                        if is_verified:
                            new_total = b['gb_extra_cost'] + added_gb_cost + added_time_cost
                        else:
                            new_total = b['gb_voucher_price'] + b['gb_extra_cost'] + added_gb_cost + added_time_cost
                        var_total.set(round(new_total, 2))

                        # 更新下面的标签显示
                        if is_verified:
                            lbl_actual_total.config(text=f"📌 已核销：仅需支付超时费 ¥{b['gb_extra_cost']:.2f} + 未核销添加团购 ¥{added_gb_cost:.2f} + 加时费用 ¥{added_time_cost:.2f}", fg="#27ae60")
                        else:
                            lbl_actual_total.config(text=f"📌 未核销：需支付全价 ¥{new_total:.2f}", fg="#e74c3c")

                        # 更新上面的核销状态显示（添加安全检查）
                        if lbl_verify_status is not None:
                            if is_verified:
                                lbl_verify_status.config(text="✓ 已核销", fg="#27ae60")
                            else:
                                lbl_verify_status.config(text="✗ 未核销", fg="#e74c3c")
                    except Exception as e:
                        print(f"更新价格时出错: {e}")
                        import traceback
                        traceback.print_exc()

                tk.Radiobutton(f_verify_frame, text="✓ 已核销", variable=verify_var, value="verified",
                              font=("微软雅黑", 11), bg="#f0f0f0", command=lambda: update_total_price()).pack(side="left", padx=10)
                tk.Radiobutton(f_verify_frame, text="✗ 未核销", variable=verify_var, value="unverified",
                              font=("微软雅黑", 11), bg="#f0f0f0", command=lambda: update_total_price()).pack(side="left", padx=10)

                lbl_actual_total.pack(pady=(10, 5))
                update_total_price()  # 初始化标签显示

            # ... 其余代码保持不变 ...

        except Exception as e:
            messagebox.showerror("错误", f"创建结账界面时出错: {e}")
            import traceback
            traceback.print_exc()
'''

    return fix_code

def main():
    """主函数"""
    print("="*60)
    print("不限时类型团购结账问题修复方案")
    print("="*60)

    print("\n【问题分析】")
    print("不限时类型团购计时卡片无法进入结账界面的原因可能是：")
    print("1. lbl_verify_status 变量作用域问题")
    print("2. update_total_price 函数中变量访问异常")
    print("3. 缺少异常处理导致错误被隐藏")

    print("\n【修复方案】")
    print("1. 在函数开始处提前声明关键变量")
    print("2. 添加安全检查确保变量存在")
    print("3. 添加异常处理捕获和显示错误")

    print("\n【具体修改】")
    print("需要在 timerProV15.py 的 show_single_checkout_ui 函数中进行以下修改：")

    fix_code = generate_fix()
    print(fix_code)

    print("\n【修复步骤】")
    print("1. 打开 timerProV15.py 文件")
    print("2. 找到 show_single_checkout_ui 函数（约第1165行）")
    print("3. 在函数开始处添加变量声明：lbl_verify_status = None")
    print("4. 在 update_total_price 函数中添加安全检查")
    print("5. 在整个函数外层添加 try-except 异常处理")

    print("\n【测试建议】")
    print("1. 创建一个不限时类型团购订单")
    print("2. 点击结账按钮")
    print("3. 检查是否能正常进入结账界面")
    print("4. 测试核销状态切换功能")

    print("\n" + "="*60)
    print("修复方案生成完成")
    print("="*60)

if __name__ == '__main__':
    import sys
    import io

    # 设置编码
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    main()
