import sqlite3
import os
from datetime import datetime

db_path = r'e:\antigravity_project_01\web_app\pos_saas.db'
json_path = r'e:\antigravity_project_01\active_data.json'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 强制重建所有表
print("正在重建数据库表...")
cursor.executescript('''
DROP TABLE IF EXISTS shops;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS system_configs;
DROP TABLE IF EXISTS group_buys;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS order_pause_logs;
DROP TABLE IF EXISTS order_add_times;
DROP TABLE IF EXISTS order_group_buys;

CREATE TABLE shops (shop_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_name TEXT, shop_code TEXT UNIQUE, is_active INTEGER DEFAULT 1, created_at TEXT);
CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, username TEXT UNIQUE, password_hash TEXT, full_name TEXT, is_active INTEGER DEFAULT 1, role TEXT, created_at TEXT);
CREATE TABLE system_configs (config_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, price_base REAL, time_base INTEGER, price_overtime REAL, buffer_min INTEGER, calc_mode TEXT, price_unlimited REAL, price_single_board REAL, updated_at TEXT);
CREATE TABLE group_buys (gb_config_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, name TEXT, type TEXT, price REAL, persons INTEGER, limit_min INTEGER, limit_sec INTEGER, start_time TEXT, end_time TEXT, is_active INTEGER DEFAULT 1, sort_order INTEGER);
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, phone TEXT, mode TEXT, 
    start_time TEXT, status TEXT DEFAULT 'active', is_paused INTEGER DEFAULT 0, is_suspended INTEGER DEFAULT 0, 
    total_pause_sec INTEGER DEFAULT 0, limit_min INTEGER DEFAULT 0, added_time_min INTEGER DEFAULT 0, 
    added_time_cost REAL DEFAULT 0, suspend_locked_cost REAL DEFAULT 0, guest_count INTEGER DEFAULT 1, 
    remark TEXT, group_id TEXT, gb_id INTEGER, gb_verified INTEGER DEFAULT 0,
    created_at TEXT, updated_at TEXT, end_time TEXT, actual_total REAL
);
CREATE TABLE order_pause_logs (log_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, pause_start TEXT, pause_end TEXT, pause_seconds INTEGER, pause_type TEXT);
CREATE TABLE order_add_times (add_time_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, minutes INTEGER, cost REAL, add_time TEXT);
CREATE TABLE order_group_buys (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, gb_config_id INTEGER, gb_name TEXT, price REAL, minutes INTEGER, verify_status INTEGER, add_time TEXT, timestamp TEXT);
''')

# 2. 预置商户和用户
now = datetime.now().isoformat()
cursor.execute('INSERT INTO shops (shop_id, shop_name, shop_code, created_at) VALUES (1, "TimerPro", "admin", ?)', (now,))
# 这里的哈希是 admin123
cursor.execute('INSERT INTO users (user_id, shop_id, username, password_hash, role) VALUES (1, 1, "admin", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGGa31lW", "admin")')
# 预置一个基础配置
cursor.execute('INSERT INTO system_configs (shop_id, price_base, time_base, price_overtime, buffer_min, calc_mode) VALUES (1, 29.9, 60, 15.0, 10, "step")')

# 3. 搬运老订单
if os.path.exists(json_path):
    print("正在搬运老订单...")
    with open(json_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    
    count = 0
    for oid, s in old_data.get('g', {}).items():
        if isinstance(s, str): s = json.loads(s)
        try:
            cursor.execute('''
                INSERT INTO orders (
                    phone, shop_id, mode, start_time, limit_min, status, 
                    is_paused, is_suspended, total_pause_sec, guest_count, 
                    remark, created_at, updated_at
                ) VALUES (?, 1, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
            ''', (
                s.get('phone'), s.get('mode'), s.get('start_time'),
                s.get('limit_min', 0), int(s.get('is_paused', 0)), 
                int(s.get('is_suspended', 0)), s.get('total_pause_sec', 0),
                s.get('guest_count', 1), s.get('remark', ''),
                now, now
            ))
            count += 1
        except Exception as e: print(f'Err {oid}: {e}')
    print(f'成功搬运 {count} 个订单。')

conn.commit()
conn.close()
print("所有工作完成，您的数据库现在是完美的了！")
