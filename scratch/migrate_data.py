import json
import sqlite3
import os
from datetime import datetime

# 路径配置
json_path = r'e:\antigravity_project_01\web_app\active_data.json'
db_path = r'e:\antigravity_project_01\web_app\pos_saas.db'

if not os.path.exists(json_path):
    print("找不到 active_data.json，跳过迁移。")
    exit()

with open(json_path, 'r', encoding='utf-8') as f:
    old_data = json.load(f)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 假设主商家的 shop_id 是 1 (默认 admin 绑定的商家)
shop_id = 1

count = 0
for order_id, s in old_data.get('g', {}).items():
    if isinstance(s, str):
        s = json.loads(s)
        
    # 插入到 orders 表
    # 根据 database.py，Order 字段有: 
    # order_id, shop_id, phone, mode, start_time, limit_min, status ...
    try:
        cursor.execute("""
            INSERT INTO orders (
                order_id, shop_id, phone, mode, start_time, 
                limit_min, status, is_paused, is_suspended, 
                total_pause_sec, guest_count, remark, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(order_id), shop_id, s.get('phone'), s.get('mode'), 
            s.get('start_time'), s.get('limit_min', 0), 
            'active', int(s.get('is_paused', 0)), int(s.get('is_suspended', 0)),
            s.get('total_pause_sec', 0), s.get('guest_count', 1),
            s.get('remark', ''), datetime.now()
        ))
        count += 1
    except Exception as e:
        print(f"订单 {order_id} 迁移失败: {e}")

conn.commit()
conn.close()
print(f"成功从 JSON 迁移了 {count} 个活跃订单到 SaaS 数据库！")
