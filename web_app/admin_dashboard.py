"""
TimerPro SaaS 超级管理后台
独立运行，默认端口 5051，可通过 ADMIN_PORT 覆盖，直接读取 timerpro_saas.db
启动方式: python admin_dashboard.py
访问地址: http://localhost:5051
"""
import sqlite3
import json
import os
import base64
import hashlib
import secrets
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "timerpro_saas.db"
PORT = int(os.getenv("ADMIN_PORT", "5051"))

# ==========================================
# 管理员认证配置（请修改为你自己的账号密码）
# ==========================================
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "timerPro@2026")

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def _table_exists(db, name):
    r = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return r[0] > 0

def _safe_count(db, table, where=""):
    if not _table_exists(db, table):
        return 0
    sql = f"SELECT COUNT(*) FROM [{table}]"
    if where:
        sql += f" WHERE {where}"
    return db.execute(sql).fetchone()[0]

def query_overview():
    db = get_db()
    result = {
        "shops": _safe_count(db, "shops"),
        "users": _safe_count(db, "users"),
        "active_orders": _safe_count(db, "orders", "status='active'"),
        "paused_orders": _safe_count(db, "orders", "status='paused'"),
        "suspended_orders": _safe_count(db, "orders", "status='suspended'"),
        "total_orders": _safe_count(db, "orders"),
        "history_count": _safe_count(db, "order_history"),
    }
    db.close()
    return result

def query_shops():
    db = get_db()
    if not _table_exists(db, "shops"):
        db.close()
        return []
    has_orders = _table_exists(db, "orders")
    has_users = _table_exists(db, "users")
    has_history = _table_exists(db, "order_history")
    sub_users = f"(SELECT COUNT(*) FROM users u WHERE u.shop_id=s.shop_id)" if has_users else "0"
    sub_active = f"(SELECT COUNT(*) FROM orders o WHERE o.shop_id=s.shop_id AND o.status='active')" if has_orders else "0"
    sub_total = f"(SELECT COUNT(*) FROM orders o WHERE o.shop_id=s.shop_id)" if has_orders else "0"
    sub_hist = f"(SELECT COUNT(*) FROM order_history oh WHERE oh.shop_id=s.shop_id)" if has_history else "0"
    rows = db.execute(f"""
        SELECT s.shop_id, s.name, s.shop_code, s.email, s.phone, s.address, s.status, s.created_at,
               {sub_users} as user_count, {sub_active} as active_count,
               {sub_total} as total_orders, {sub_hist} as history_count
        FROM shops s ORDER BY s.shop_id
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]

def query_users():
    db = get_db()
    if not _table_exists(db, "users"):
        db.close()
        return []
    has_shops = _table_exists(db, "shops")
    join = "LEFT JOIN shops s ON u.shop_id=s.shop_id" if has_shops else ""
    shop_col = "s.name as shop_name" if has_shops else "'' as shop_name"
    rows = db.execute(f"""
        SELECT u.user_id, u.username, u.email, u.role, u.real_name, u.last_login_at, u.created_at,
               {shop_col}
        FROM users u {join} ORDER BY u.user_id
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]

def query_active_orders():
    db = get_db()
    if not _table_exists(db, "orders"):
        db.close()
        return []
    has_shops = _table_exists(db, "shops")
    join = "LEFT JOIN shops s ON o.shop_id=s.shop_id" if has_shops else ""
    shop_col = "s.name as shop_name" if has_shops else "'' as shop_name"
    rows = db.execute(f"""
        SELECT o.order_id, o.phone, o.mode, o.start_time, o.status, o.guest_count, o.group_id,
               o.total_cost, o.actual_cost, o.prepaid, o.is_suspended, o.remark,
               {shop_col}
        FROM orders o {join}
        ORDER BY o.start_time DESC LIMIT 100
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]

def query_history_recent():
    db = get_db()
    if not _table_exists(db, "order_history"):
        db.close()
        return []
    has_shops = _table_exists(db, "shops")
    join = "LEFT JOIN shops s ON oh.shop_id=s.shop_id" if has_shops else ""
    shop_col = "s.name as shop_name" if has_shops else "'' as shop_name"
    rows = db.execute(f"""
        SELECT oh.history_id, oh.order_id, oh.action_type, oh.action_time,
               oh.cost_before, oh.cost_after, oh.remark, {shop_col}
        FROM order_history oh {join}
        ORDER BY oh.action_time DESC LIMIT 50
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]

def query_db_info():
    size = os.path.getsize(str(DB_PATH))
    mtime = datetime.fromtimestamp(os.path.getmtime(str(DB_PATH))).strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    table_info = []
    for t in tables:
        count = db.execute(f"SELECT COUNT(*) FROM [{t['name']}]").fetchone()[0]
        table_info.append({"name": t["name"], "rows": count})
    db.close()
    return {"size_kb": round(size/1024, 1), "modified": mtime, "tables": table_info}

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TimerPro 超级管理后台</title>
<link href="https://cdn.jsdelivr.net/npm/remixicon@3.5.0/fonts/remixicon.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.topbar{background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border-bottom:1px solid #334155;padding:16px 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;backdrop-filter:blur(10px)}
.topbar h1{font-size:1.25rem;background:linear-gradient(90deg,#818cf8,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:700}
.topbar .meta{font-size:.75rem;color:#64748b}
.container{max-width:1400px;margin:0 auto;padding:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155);border:1px solid #334155;border-radius:12px;padding:20px;text-align:center;transition:transform .2s,box-shadow .2s}
.stat-card:hover{transform:translateY(-4px);box-shadow:0 8px 32px rgba(99,102,241,.15)}
.stat-card .num{font-size:2.2rem;font-weight:800;margin:8px 0 4px}
.stat-card .label{font-size:.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}
.stat-card.purple .num{color:#a78bfa}
.stat-card.blue .num{color:#60a5fa}
.stat-card.green .num{color:#34d399}
.stat-card.amber .num{color:#fbbf24}
.stat-card.rose .num{color:#fb7185}
.stat-card.cyan .num{color:#22d3ee}
.stat-card.indigo .num{color:#818cf8}
.section{margin-bottom:32px}
.section h2{font-size:1.1rem;color:#c084fc;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.section h2 i{font-size:1.3rem}
.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid #334155}
table{width:100%;border-collapse:collapse;font-size:.82rem}
thead{background:#1e293b}
th{padding:12px 14px;text-align:left;color:#94a3b8;font-weight:600;white-space:nowrap;border-bottom:1px solid #334155}
td{padding:10px 14px;border-bottom:1px solid rgba(51,65,85,.5);white-space:nowrap}
tr:hover{background:rgba(99,102,241,.06)}
.badge{padding:3px 10px;border-radius:20px;font-size:.7rem;font-weight:600}
.badge.active{background:rgba(52,211,153,.15);color:#34d399}
.badge.paused{background:rgba(251,191,36,.15);color:#fbbf24}
.badge.suspended{background:rgba(167,139,250,.15);color:#a78bfa}
.badge.closed{background:rgba(100,116,139,.15);color:#94a3b8}
.badge.admin{background:rgba(96,165,250,.15);color:#60a5fa}
.badge.employee{background:rgba(251,113,133,.15);color:#fb7185}
.db-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:8px}
.db-item{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px;display:flex;justify-content:space-between;align-items:center}
.db-item .tname{color:#e2e8f0;font-weight:500;font-size:.85rem}
.db-item .tcount{color:#818cf8;font-weight:700;font-size:1rem}
.refresh-btn{background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;color:#fff;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:600;transition:opacity .2s}
.refresh-btn:hover{opacity:.85}
.tabs{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}
.tab{padding:8px 18px;border-radius:8px;border:1px solid #334155;background:#1e293b;color:#94a3b8;cursor:pointer;font-size:.82rem;transition:all .2s}
.tab.active{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border-color:transparent}
.tab:hover:not(.active){background:#334155;color:#e2e8f0}
#loading{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);font-size:1.2rem;color:#818cf8}
</style>
</head>
<body>
<div class="topbar">
  <div>
    <h1><i class="ri-shield-keyhole-line"></i> TimerPro 超级管理后台</h1>
    <div class="meta">数据库: timerpro_saas.db | 默认端口 5051，可用 ADMIN_PORT 覆盖 | 只读模式</div>
  </div>
  <button class="refresh-btn" onclick="loadAll()"><i class="ri-refresh-line"></i> 刷新数据</button>
</div>
<div class="container">
  <div class="stats" id="statsArea"></div>
  <div class="tabs">
    <div class="tab active" onclick="switchTab(this,'shopPanel')"><i class="ri-store-2-line"></i> 商家列表</div>
    <div class="tab" onclick="switchTab(this,'userPanel')"><i class="ri-user-line"></i> 用户账号</div>
    <div class="tab" onclick="switchTab(this,'orderPanel')"><i class="ri-file-list-3-line"></i> 当前订单</div>
    <div class="tab" onclick="switchTab(this,'historyPanel')"><i class="ri-history-line"></i> 操作历史</div>
    <div class="tab" onclick="switchTab(this,'dbPanel')"><i class="ri-database-2-line"></i> 数据库信息</div>
  </div>
  <div id="shopPanel" class="section"></div>
  <div id="userPanel" class="section" style="display:none"></div>
  <div id="orderPanel" class="section" style="display:none"></div>
  <div id="historyPanel" class="section" style="display:none"></div>
  <div id="dbPanel" class="section" style="display:none"></div>
</div>
<script>
const panels=['shopPanel','userPanel','orderPanel','historyPanel','dbPanel'];
function switchTab(el,id){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  panels.forEach(p=>document.getElementById(p).style.display=p===id?'block':'none');
}
async function api(path){try{const r=await fetch('/api/'+path);if(!r.ok)throw new Error(r.status);return await r.json()}catch(e){console.error('API错误:'+path,e);return null}}
function esc(v){return v==null?'-':String(v)}
function badge(v,map){const cls=map[v]||'closed';return `<span class="badge ${cls}">${esc(v)}</span>`}

async function loadAll(){
  const ov=await api('overview');
  if(!ov||ov.error){document.getElementById('statsArea').innerHTML='<div style="color:#fb7185;padding:20px">⚠️ 数据加载失败: '+(ov?ov.error:'无法连接后端API')+'</div>';return}
  document.getElementById('statsArea').innerHTML=`
    <div class="stat-card purple"><div class="num">${ov.shops}</div><div class="label">注册商家</div></div>
    <div class="stat-card blue"><div class="num">${ov.users}</div><div class="label">用户账号</div></div>
    <div class="stat-card green"><div class="num">${ov.active_orders}</div><div class="label">制作中订单</div></div>
    <div class="stat-card amber"><div class="num">${ov.paused_orders}</div><div class="label">暂离订单</div></div>
    <div class="stat-card rose"><div class="num">${ov.suspended_orders}</div><div class="label">挂账订单</div></div>
    <div class="stat-card cyan"><div class="num">${ov.total_orders}</div><div class="label">总活跃订单</div></div>
    <div class="stat-card indigo"><div class="num">${ov.history_count}</div><div class="label">历史记录</div></div>`;

  const shops=await api('shops');
  document.getElementById('shopPanel').innerHTML=`<h2><i class="ri-store-2-line"></i>商家列表 (${shops.length})</h2>
    <div class="table-wrap"><table><thead><tr><th>ID</th><th>店铺名</th><th>店铺编码</th><th>邮箱</th><th>地址</th><th>状态</th><th>员工数</th><th>活跃单</th><th>总订单</th><th>历史</th><th>注册时间</th></tr></thead>
    <tbody>${shops.map(s=>`<tr><td>${s.shop_id}</td><td><b>${esc(s.name)}</b></td><td>${esc(s.shop_code)}</td><td>${esc(s.email)}</td><td>${esc(s.address)}</td>
    <td>${badge(s.status==1?'启用':'禁用',{'启用':'active','禁用':'closed'})}</td><td>${s.user_count}</td><td>${s.active_count}</td><td>${s.total_orders}</td><td>${s.history_count}</td><td>${esc(s.created_at)}</td></tr>`).join('')}</tbody></table></div>`;

  const users=await api('users');
  document.getElementById('userPanel').innerHTML=`<h2><i class="ri-user-line"></i>用户账号 (${users.length})</h2>
    <div class="table-wrap"><table><thead><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>姓名</th><th>角色</th><th>所属店铺</th><th>最后登录</th><th>注册时间</th></tr></thead>
    <tbody>${users.map(u=>`<tr><td>${u.user_id}</td><td>${esc(u.username)}</td><td>${esc(u.email)}</td><td>${esc(u.real_name)}</td>
    <td>${badge(u.role,{admin:'admin',employee:'employee',staff:'employee'})}</td><td>${esc(u.shop_name)}</td><td>${esc(u.last_login_at)}</td><td>${esc(u.created_at)}</td></tr>`).join('')}</tbody></table></div>`;

  const orders=await api('orders');
  document.getElementById('orderPanel').innerHTML=`<h2><i class="ri-file-list-3-line"></i>当前订单 (${orders.length})</h2>
    <div class="table-wrap"><table><thead><tr><th>店铺</th><th>标识号</th><th>模式</th><th>状态</th><th>开始时间</th><th>客数</th><th>系统金额</th><th>实收</th><th>备注</th></tr></thead>
    <tbody>${orders.map(o=>`<tr><td>${esc(o.shop_name)}</td><td>${esc(o.phone)}</td><td>${esc(o.mode)}</td>
    <td>${badge(o.status,{active:'active',paused:'paused',suspended:'suspended',closed:'closed'})}</td>
    <td>${esc(o.start_time)}</td><td>${o.guest_count}</td><td>${(o.total_cost||0).toFixed(1)}</td><td>${(o.actual_cost||0).toFixed(1)}</td><td>${esc(o.remark)}</td></tr>`).join('')}</tbody></table></div>`;

  const hist=await api('history');
  document.getElementById('historyPanel').innerHTML=`<h2><i class="ri-history-line"></i>最近操作历史 (最新50条)</h2>
    <div class="table-wrap"><table><thead><tr><th>ID</th><th>店铺</th><th>订单ID</th><th>操作</th><th>时间</th><th>金额变化</th><th>备注</th></tr></thead>
    <tbody>${hist.map(h=>`<tr><td>${h.history_id}</td><td>${esc(h.shop_name)}</td><td style="font-size:.7rem">${esc(h.order_id)}</td>
    <td>${badge(h.action_type,{checkout:'active',pause:'paused',resume:'green',suspend:'suspended',add_time:'admin'})}</td>
    <td>${esc(h.action_time)}</td><td>${h.cost_before!=null?(h.cost_before+'→'+h.cost_after):'-'}</td><td>${esc(h.remark)}</td></tr>`).join('')}</tbody></table></div>`;

  const dbinfo=await api('dbinfo');
  document.getElementById('dbPanel').innerHTML=`<h2><i class="ri-database-2-line"></i>数据库信息</h2>
    <p style="margin-bottom:12px;color:#94a3b8">文件大小: <b style="color:#818cf8">${dbinfo.size_kb} KB</b> &nbsp;|&nbsp; 最后修改: <b style="color:#818cf8">${dbinfo.modified}</b></p>
    <div class="db-grid">${dbinfo.tables.map(t=>`<div class="db-item"><span class="tname">${t.name}</span><span class="tcount">${t.rows}</span></div>`).join('')}</div>`;
}
loadAll();
setInterval(loadAll,30000);
</script>
</body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def _check_auth(self):
        """验证 HTTP Basic Auth 凭据"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            return False
        try:
            decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
            user, pwd = decoded.split(':', 1)
            return user == ADMIN_USER and pwd == ADMIN_PASS
        except Exception:
            return False

    def _send_auth_required(self):
        """发送 401 要求认证"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="TimerPro Admin"')
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write('<h2 style="text-align:center;margin-top:100px;color:#666">请输入管理员账号密码</h2>'.encode('utf-8'))

    def do_GET(self):
        # 所有请求都需要认证
        if not self._check_auth():
            self._send_auth_required()
            return

        path = urlparse(self.path).path
        if path.startswith('/api/'):
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            ep = path.replace('/api/','')
            data = {}
            try:
                if ep == 'overview': data = query_overview()
                elif ep == 'shops': data = query_shops()
                elif ep == 'users': data = query_users()
                elif ep == 'orders': data = query_active_orders()
                elif ep == 'history': data = query_history_recent()
                elif ep == 'dbinfo': data = query_db_info()
            except Exception as e:
                data = {"error": str(e)}
            self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  TimerPro 超级管理后台")
    print(f"  数据库: {DB_PATH}")
    print(f"  访问地址: http://localhost:{PORT}")
    print(f"  管理员账号: {ADMIN_USER}")
    print(f"  管理员密码: {'*' * len(ADMIN_PASS)}")
    print(f"{'='*50}\n")
    server = ThreadedHTTPServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n管理后台已关闭")
        server.server_close()
