"""
验证 SaaS 计费引擎是否与示例文档完全一致
"""
from web_app.database import SessionLocal, SystemConfig
from web_app.routers.orders import get_overtime_cost_logic

db = SessionLocal()
cfg = db.query(SystemConfig).first()

print(f"=== 当前配置 ===")
print(f"price_base={cfg.price_base}, time_base={cfg.time_base}, price_overtime={cfg.price_overtime}")
print(f"calc_mode={cfg.calc_mode}, step_n={cfg.step_n}, step_y={cfg.step_y}, step_k={cfg.step_k}, ceil_x={cfg.ceil_x}")
print(f"buffer_min={cfg.buffer_min}")
print()

po = cfg.price_overtime  # 10.9
pb = cfg.price_base      # 10.9
tb = cfg.time_base        # 60
buf = cfg.buffer_min      # 10

# ==========================================
# 第一组: 纯超时费用 get_overtime_cost_logic
# ==========================================
print("=" * 70)
print("📊 纯超时 get_overtime_cost_logic(over_mins) 测试")
print("=" * 70)

overtime_cases = [
    (0, 0),
    (3, 0),    # 3 < N/K=5, 不进位
    (4, 0),
    (5, 2),    # 5 >= 5, 进1位
    (9, 2),
    (10, 2),   # 1整块
    (14, 2),   # 1块, 余4<5
    (15, 4),   # 1块 + 余5>=5 → 2块
    (20, 4),   # 2整块
    (25, 6),   # 2块 + 进位
    (30, 6),   # 3整块
    (35, 8),
    (40, 8),
    (45, 10),
    (50, 10),
    (54, 10),
    (55, 10.9),  # 抹零: 60-55=5 <= ceil_x=5
    (56, 10.9),
    (59, 10.9),
    (60, 10.9),  # 1整小时
    (65, 12.9),  # 1hr + 1块
    (70, 12.9),
    (80, 14.9),
    (115, 21.8), # 1hr + 抹零
    (120, 21.8), # 2整小时
]

all_pass = True
for mins, expected in overtime_cases:
    actual = get_overtime_cost_logic(mins, po, cfg)
    status = "✅" if abs(actual - expected) < 0.01 else "❌"
    if status == "❌": all_pass = False
    print(f"  {status} 超时{mins:>3}分 → 期望¥{expected:<6} 实际¥{actual:<6}")

print(f"\n纯超时测试: {'全部通过 ✅' if all_pass else '有失败 ❌'}\n")

# ==========================================
# 第二组: 定额模式完整案例
# ==========================================
print("=" * 70)
print("🎯 定额模式 (Fixed) 完整案例")
print("=" * 70)

def calc_fixed(limit_min, play_min):
    """模拟定额模式计费（与 orders.py 中 get_table_bill 的 fixed 分支一致）"""
    lm = limit_min
    at = 0  # 无加时
    bp = pb  # price_base
    extra = max(0, lm - tb)
    if extra > 0:
        bp += get_overtime_cost_logic(extra, po, cfg)
    bp = round(bp, 2)
    
    o = max(0, play_min - (lm + at))
    overtime_cost = get_overtime_cost_logic(o, po, cfg) if o > buf else 0.0
    
    return round(bp + overtime_cost, 2)

fixed_cases = [
    # (定额, 实际玩, 期望总价)
    (60, 45, 10.9),
    (60, 60, 10.9),
    (60, 68, 10.9),    # 超8分, 在buffer内
    (60, 72, 12.9),    # 超12分, step(12)=¥2
    (60, 85, 16.9),    # 超25分, step(25)=¥6
    (60, 120, 21.8),   # 超60分, ¥10.9
    (60, 125, 23.8),   # 超65分, ¥12.9
    (70, 70, 12.9),    # 基础: 10.9 + step(10)=2
    (80, 75, 14.9),    # 基础: 10.9 + step(20)=4, 没超
    (80, 80, 14.9),
    (80, 85, 14.9),    # 超5分, 在buffer内
    (80, 95, 18.9),    # 超15分, step(15)=4
    (90, 90, 16.9),    # 基础: 10.9 + step(30)=6
    (120, 120, 21.8),  # 基础: 10.9 + step(60)=10.9
    (120, 175, 32.7),  # 超55分, 抹零 10.9
    (60, 175, 32.7),   # 超115分, 21.8
]

all_pass2 = True
for lm, play, expected in fixed_cases:
    actual = calc_fixed(lm, play)
    over = max(0, play - lm)
    status = "✅" if abs(actual - expected) < 0.01 else "❌"
    if status == "❌": all_pass2 = False
    print(f"  {status} 定额{lm:>3}分, 玩{play:>3}分 (超{over:>3}分) → 期望¥{expected:<6} 实际¥{actual:<6}")

print(f"\n定额测试: {'全部通过 ✅' if all_pass2 else '有失败 ❌'}\n")

# ==========================================
# 第三组: 先玩后付
# ==========================================
print("=" * 70)
print("💳 先玩后付 (Pay Later) 完整案例")
print("=" * 70)

def calc_pay_later(play_min):
    if play_min <= tb:
        return pb
    o = play_min - tb
    if o > buf:
        return round(pb + get_overtime_cost_logic(o, po, cfg), 2)
    return pb

pay_later_cases = [
    (30, 10.9),
    (60, 10.9),
    (67, 10.9),    # 超7分, buffer内
    (75, 14.9),    # 超15分, step=4
    (80, 14.9),    # 超20分, step=4
    (120, 21.8),   # 超60分
    (175, 32.7),   # 超115分
]

all_pass3 = True
for play, expected in pay_later_cases:
    actual = calc_pay_later(play)
    status = "✅" if abs(actual - expected) < 0.01 else "❌"
    if status == "❌": all_pass3 = False
    print(f"  {status} 玩{play:>3}分 → 期望¥{expected:<6} 实际¥{actual:<6}")

print(f"\n先玩后付测试: {'全部通过 ✅' if all_pass3 else '有失败 ❌'}\n")

# ==========================================
# 总结
# ==========================================
print("=" * 70)
total = all_pass and all_pass2 and all_pass3
print(f"🏆 总体结果: {'✅ 全部 {0} 个案例通过!'.format(len(overtime_cases)+len(fixed_cases)+len(pay_later_cases)) if total else '❌ 有测试未通过!'}")
print("=" * 70)

db.close()
