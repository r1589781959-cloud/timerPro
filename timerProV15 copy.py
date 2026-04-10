import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import math
import json
import csv
import os
import sys
import time
import random
import hashlib
import uuid
import base64

# ==========================================
# --- 1. 配置文件 ---
# ==========================================
# 数据文件位置：相对于脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "active_data.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "history_log.csv")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "shop_config.json")

DEFAULT_CONFIG = {
    "price_base": 29.9, "time_base": 120, "price_overtime": 10.0, "buffer_min": 10,
    "admin_pwd": "8888", "price_unlimited": 59.9, "price_single_board": 39.9,
    "price_fixed_60": 19.9, "price_fixed_120": 35.0, "price_fixed_180": 49.9,
    "calc_mode": "step", "step_n": 15, "step_y": 10.0, "step_k": 2.0, "ceil_x": 5,
    "group_buys": [
        {"name": "🎫 双人全天畅玩", "type": "unlimited", "price": 88.0, "persons": 2, "limit_min": 0, "buffer_min": 0,
         "overtime_price": 0.0, "start_time": "00:00", "end_time": "23:59"},
        {"name": "🎫 单人2小时特惠", "type": "fixed", "price": 39.9, "persons": 1, "limit_min": 120, "buffer_min": 5,
         "overtime_price": 10.0, "start_time": "00:00", "end_time": "23:59"},
        {"name": "🎫 早鸟4小时畅玩(10-14点)", "type": "time_slot", "price": 49.9, "persons": 1, "limit_min": 240,
         "buffer_min": 10, "overtime_price": 10.0, "start_time": "10:00", "end_time": "14:00"}
    ]
}


# ==========================================
# --- 2. 军工级防伪授权系统 ---
# ==========================================
class AuthManager:
    def __init__(self):
        self.machine_code = self._generate_machine_code()
        hash_a = hashlib.md5((self.machine_code + "LOC_A").encode()).hexdigest()[:8]
        hash_b = hashlib.md5((self.machine_code + "LOC_B").encode()).hexdigest()[:8]
        self.path_a = os.path.join(os.getenv('APPDATA', 'C:\\'), f"win_sys_{hash_a}.dat")
        self.path_b = os.path.join(os.getenv('LOCALAPPDATA', 'C:\\'), f"com.microsoft.cache.{hash_b}.bin")
        self.data = {"first_run": time.time(), "guests": 0, "activated": False}
        self.load_and_heal()

    def _generate_machine_code(self):
        mac = uuid.getnode()
        cname = os.environ.get('COMPUTERNAME', 'UNKNOWN')
        raw = f"{mac}_{cname}_TIMERPRO"
        h = hashlib.md5(raw.encode()).hexdigest().upper()
        return f"{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    def get_expected_key(self):
        s_part1, s_part2, s_part3 = "T!m3r", "Pr0", "V14_@uth"
        complex_raw = f"{s_part1}_{self.machine_code[::-1]}_{s_part2}_{self.machine_code}_{s_part3}"
        h = hashlib.sha256(complex_raw.encode()).hexdigest().upper()
        return f"{h[3:7]}-{h[15:19]}-{h[27:31]}-{h[50:54]}"

    def _encode_a(self, data):
        sign = hashlib.sha256((json.dumps(data, sort_keys=True) + self.machine_code).encode()).hexdigest()
        payload = {"d": data, "s": sign}
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def _decode_a(self, text):
        try:
            payload = json.loads(base64.b64decode(text).decode())
            sign = hashlib.sha256((json.dumps(payload["d"], sort_keys=True) + self.machine_code).encode()).hexdigest()
            if payload["s"] != sign: return None
            return payload["d"]
        except:
            return None

    def _encode_b(self, data):
        raw = f"{data['guests']}|{data['first_run']}|{data['activated']}|{self.machine_code}"
        return raw.encode().hex()

    def _decode_b(self, text):
        try:
            raw = bytes.fromhex(text).decode()
            parts = raw.split('|')
            if len(parts) == 4 and parts[3] == self.machine_code:
                return {"guests": int(parts[0]), "first_run": float(parts[1]), "activated": parts[2] == 'True'}
        except:
            return None

    def _spoof_timestamp(self, file_path, file_type):
        try:
            base_time = os.stat("C:\\").st_ctime
            fake_time = base_time + (123 * 24 * 3600) + 12580 if file_type == 'A' else base_time + (
                        365 * 24 * 3600) + 31500
            os.utime(file_path, (fake_time, fake_time))
        except:
            pass

    def load_and_heal(self):
        data_a, data_b = None, None
        if os.path.exists(self.path_a):
            try:
                with open(self.path_a, 'r') as f:
                    data_a = self._decode_a(f.read())
            except:
                pass
        if os.path.exists(self.path_b):
            try:
                with open(self.path_b, 'r') as f:
                    data_b = self._decode_b(f.read())
            except:
                pass

        if data_a and not data_b:
            self.data = data_a; self.save()
        elif data_b and not data_a:
            self.data = data_b; self.save()
        elif data_a and data_b:
            self.data = data_a
            if data_b["guests"] > data_a["guests"]: self.data["guests"] = data_b["guests"]
            self.save()
        else:
            self.save()

    def save(self):
        try:
            with open(self.path_a, 'w') as f:
                f.write(self._encode_a(self.data))
            self._spoof_timestamp(self.path_a, 'A')
            with open(self.path_b, 'w') as f:
                f.write(self._encode_b(self.data))
            self._spoof_timestamp(self.path_b, 'B')
        except:
            pass

    @property
    def activated(self):
        return self.data.get("activated", False)

    def activate(self, code):
        if code.strip() == self.get_expected_key():
            self.data["activated"] = True
            self.save()
            return True
        return False

    def add_guest(self, count):
        if self.activated: return True
        if self.data["guests"] + count > 20: return False
        self.data["guests"] += count
        self.save()
        return True


# ==========================================
# --- 3. 全局辅助函数与 UI组件 ---
# ==========================================
def fmt_min(minutes):
    if minutes < 60: return f"{minutes}分"
    h, m = divmod(minutes, 60)
    return f"{h}小时" if m == 0 else f"{h}小时{m}分"


def fmt_duration_str(total_seconds):
    total_seconds = int(total_seconds)
    h, r = divmod(total_seconds, 3600)
    m, s = divmod(r, 60)
    if h > 0:
        return f"{h}小时{m}分{s}秒"
    elif m > 0:
        return f"{m}分{s}秒"
    else:
        return f"{s}秒"


# 修复：补回丢失的颜色与文本解析函数
def get_mode_color(mode):
    return {"pay_later": "#3498db", "fixed": "#f39c12", "unlimited": "#9b59b6", "single_board": "#e67e22",
            "group_buy": "#1abc9c"}.get(mode, "#999999")


def get_mode_text(mode):
    return {"pay_later": "先玩后付", "fixed": "普通定额", "unlimited": "全天畅玩", "single_board": "单板不限",
            "group_buy": "团购套餐"}.get(mode, mode)


GROUP_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22", "#1abc9c", "#34495e", "#ff9ff3",
                "#feca57"]


def get_group_color(group_id):
    if not group_id: return None
    idx = int(hashlib.md5(str(group_id).encode()).hexdigest(), 16)
    return GROUP_COLORS[idx % len(GROUP_COLORS)]


class BadgeNotebook(ttk.Notebook):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)

    def set_badge(self, tab_index, show=True):
        try:
            txt = self.tab(tab_index, "text")
            if show and "🔴" not in txt: self.tab(tab_index, text=f"{txt} 🔴")
            if not show: self.tab(tab_index, text=txt.replace(" 🔴", ""))
        except:
            pass


class CardProgressBar(tk.Canvas):
    def __init__(self, master, height=6, bg="#ecf0f1"):
        super().__init__(master, height=height, bg=bg, bd=0, highlightthickness=0)
        self.rect = self.create_rectangle(0, 0, 0, height, fill="#2ecc71", width=0)

    def update_bar(self, percentage, color):
        w = self.winfo_width()
        self.coords(self.rect, 0, 0, w * min(percentage, 1.0), self.winfo_height())
        self.itemconfig(self.rect, fill=color)


# ==========================================
# --- 4. 核心系统逻辑类 ---
# ==========================================

def ask_password(parent_win, title="验证", prompt="输入管理员密码:"):
    """自定义密码输入对话框，确保窗口始终在前面"""
    dialog = tk.Toplevel(parent_win)
    dialog.title(title)
    dialog.geometry("300x150")
    dialog.grab_set()
    dialog.transient(parent_win)
    dialog.resizable(False, False)
    
    # 居中显示
    dialog.update_idletasks()
    x = parent_win.winfo_x() + (parent_win.winfo_width() - dialog.winfo_width()) // 2
    y = parent_win.winfo_y() + (parent_win.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    
    tk.Label(dialog, text=prompt, font=("微软雅黑", 11)).pack(pady=15)
    
    pwd_var = tk.StringVar()
    pwd_entry = tk.Entry(dialog, textvariable=pwd_var, font=("微软雅黑", 11), show="*", width=25)
    pwd_entry.pack(pady=5)
    pwd_entry.focus_set()
    
    result = [None]
    
    def confirm():
        result[0] = pwd_var.get()
        dialog.destroy()
    
    def cancel():
        dialog.destroy()
    
    tk.Button(dialog, text="确定", bg="#27ae60", fg="white", font=("微软雅黑", 10), width=10, command=confirm).pack(side="left", padx=10, pady=15)
    tk.Button(dialog, text="取消", bg="#e74c3c", fg="white", font=("微软雅黑", 10), width=10, command=cancel).pack(side="right", padx=10, pady=15)
    
    pwd_entry.bind("<Return>", lambda e: confirm())
    pwd_entry.bind("<Escape>", lambda e: cancel())
    
    dialog.wait_window()
    return result[0]

class PerfectTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("藤原智能收银系统 V15.0 Pro (纯血满配版)")
        self.root.geometry("1280x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_app)

        self.auth = AuthManager()
        self.config = self.load_config()
        self.upgrade_csv_format()
        self.guests = {}
        self.group_widgets = {}  # 存储常规多人大卡片
        self.team_widgets = {}    # 存储团购多人大卡片
        self.group_cards = {}     # 备用
        self.guest_counter = 0
        self.is_updating_total = False
        self.active_group_filter = None

        self.status_bar = tk.Label(root, text="系统就绪", bd=0, relief="flat", anchor="w", font=("微软雅黑", 10),
                                   bg="#ecf0f1", fg="#2c3e50", padx=10, pady=5)
        self.status_bar.pack(side="bottom", fill="x")

        top_frame = tk.Frame(root, pady=10, padx=20, bg="#ecf0f1")
        top_frame.pack(side="top", fill="x")
        tk.Button(top_frame, text="+ 新增客人", font=("微软雅黑", 12, "bold"), bg="#2980b9", fg="white", width=12,
                  command=self.open_add_dialog).pack(side="left")
        tk.Button(top_frame, text="📊 历史账单", font=("微软雅黑", 10), command=self.check_history_permission).pack(
            side="left", padx=10)
        tk.Button(top_frame, text="⚙️ 设置", font=("微软雅黑", 10), command=self.open_settings_menu).pack(
            side="left", padx=10)

        tk.Label(top_frame, text="🔍 搜索:", bg="#ecf0f1", font=("微软雅黑", 11)).pack(side="left", padx=(30, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.refresh_ui_list)
        tk.Entry(top_frame, textvariable=self.search_var, font=("微软雅黑", 11), width=15).pack(side="left")
        tk.Button(top_frame, text="🔒 一键清空", bg="#c0392b", fg="white", font=("微软雅黑", 10),
                  command=self.clear_all_guests_secure).pack(side="right")

        self.rule_frame = tk.Frame(root, bg="#f1c40f")
        self.rule_frame.pack(side="top", fill="x")
        self.rule_label = tk.Label(self.rule_frame, text="", bg="#f1c40f", fg="#333", font=("微软雅黑", 9))
        self.rule_label.pack(side="left", expand=True, fill="x")
        tk.Button(self.rule_frame, text="×", bg="#f1c40f", bd=0, fg="#555", font=("Arial", 12, "bold"),
                  command=lambda: self.rule_frame.pack_forget()).pack(side="right", padx=5)
        self.update_rule_display()

        sort_frame = tk.Frame(root, bg="#bdc3c7", pady=2)
        sort_frame.pack(side="top", fill="x")
        tk.Label(sort_frame, text="排序:", bg="#bdc3c7", font=("微软雅黑", 9)).pack(side="left", padx=10)
        btn_style = {"font": ("微软雅黑", 9), "bg": "white", "relief": "flat", "padx": 5}
        tk.Button(sort_frame, text="按 序号", command=lambda: self.sort_list("id"), **btn_style).pack(side="left",
                                                                                                      padx=2)
        tk.Button(sort_frame, text="按 开始时间", command=lambda: self.sort_list("start"), **btn_style).pack(
            side="left", padx=2)
        tk.Button(sort_frame, text="按 剩余时长", command=lambda: self.sort_list("remain"), **btn_style).pack(
            side="left", padx=2)
        self.current_sort_key = "id"
        self.current_sort_rev = False

        self.notebook = BadgeNotebook(root)
        self.notebook.pack(side="top", fill="x", padx=10, pady=(10, 0))
        self.tabs = ["全部订单", "团队订单", "先玩后付", "无限模式", "定额/倒计时", "限时段", "团购", "超时监控"]
        for t in self.tabs: self.notebook.add(tk.Frame(self.notebook), text=t)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        main_content_frame = tk.Frame(root, bg="#ecf0f1")
        main_content_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas = tk.Canvas(main_content_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_content_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if event.widget.winfo_toplevel() == self.root:
                try:
                    if self.scrollable_frame.winfo_height() > self.canvas.winfo_height():
                        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except:
                    pass

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.load_from_disk()
        self.update_timers()

    def load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg.update(json.load(f))
            except:
                pass
        return cfg

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.update_rule_display()
            messagebox.showinfo("成功", "配置已更新")
        except Exception as e:
            messagebox.showerror("错误", f"{e}")

    def update_rule_display(self):
        c = self.config
        txt = f"基础: {c['price_base']}元/{fmt_min(c['time_base'])} | 超时: {c['price_overtime']}元/时 | 定额: {c['price_fixed_60']}元/1h..."
        self.rule_label.config(text=txt)

    def show_activation_window(self, reason_text="感谢体验！", force=False):
        if hasattr(self, 'act_win') and self.act_win.winfo_exists():
            self.act_win.focus();
            return
        win = tk.Toplevel(self.root)
        self.act_win = win
        win.title("系统激活 - 藤原智能门店")
        win.geometry("500x400")
        win.grab_set()
        win.attributes('-topmost', True)

        def on_close():
            if force:
                if messagebox.askyesno("警告",
                                       "试用名额已耗尽，必须输入激活码解锁！是否直接退出程序？"): self.root.destroy()
            else:
                win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(win, text="🔒 商业授权认证", font=("微软雅黑", 22, "bold"), fg="#c0392b").pack(pady=(20, 10))
        tk.Label(win, text=reason_text, font=("微软雅黑", 11), fg="#e67e22").pack(pady=5)

        f_mc = tk.Frame(win, bg="#ecf0f1", pady=10, padx=10);
        f_mc.pack(fill="x", padx=40, pady=10)
        tk.Label(f_mc, text="您的专属机器码：", font=("微软雅黑", 12), bg="#ecf0f1").pack()
        e_mc = tk.Entry(f_mc, font=("Consolas", 16, "bold"), justify="center", width=25, fg="#2980b9")
        e_mc.insert(0, self.auth.machine_code)
        e_mc.config(state="readonly");
        e_mc.pack(pady=5)

        tk.Label(win, text="请将机器码发送给客服，获取永久激活码：", font=("微软雅黑", 10)).pack(pady=(10, 5))
        var_code = tk.StringVar()
        e_code = tk.Entry(win, textvariable=var_code, font=("Consolas", 18, "bold"), justify="center", width=22);
        e_code.pack(pady=5)

        def attempt_activate():
            if self.auth.activate(var_code.get().strip()):
                messagebox.showinfo("激活成功", "恭喜！商业授权验证成功，永久解锁所有功能！\n请重启软件以加载完全版界面。")
                win.destroy()
            else:
                messagebox.showerror("错误", "激活码无效，请核对后重新输入！")

        tk.Button(win, text="验证并永久激活", bg="#27ae60", fg="white", font=("微软雅黑", 14, "bold"), width=20,
                  command=attempt_activate).pack(pady=20)

    def upgrade_csv_format(self):
        if not os.path.exists(HISTORY_FILE): return
        try:
            rows = []
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                rows = list(csv.reader(f))
            if not rows: return
            header = rows[0]
            if len(header) < 12:
                new_header = ["开始", "结束", "序号", "手机", "模式", "客流量", "总时长", "实玩时长", "总金额", "备注",
                              "定额时长", "暂停详情"]
                new_rows = [new_header]
                for r in rows[1:]:
                    new_r = r[:5] + ["1"] + r[5:]
                    if len(new_r) < 12: new_r += ["--"] * (12 - len(new_r))
                    new_rows.append(new_r)
                with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(new_rows)
        except:
            pass

    def get_overtime_cost(self, over_mins, hourly_p, c):
        if over_mins <= 0: return 0.0
        if c.get('calc_mode', 'step') == 'exact': return round((over_mins / 60.0) * hourly_p, 2)
        n, y, k, ceil_x = int(c.get('step_n', 15)), float(c.get('step_y', 10.0)), float(c.get('step_k', 2.0)), int(
            c.get('ceil_x', 5))
        hrs, rem = int(over_mins // 60), int(over_mins % 60)
        rem_cost = 0.0
        if rem > 0:
            if 60 - rem <= ceil_x:
                rem_cost = hourly_p
            else:
                blocks = rem // n
                if (rem % n) >= (n / k): blocks += 1
                rem_cost = blocks * y
                if rem_cost > hourly_p: rem_cost = hourly_p
        return round(hrs * hourly_p + rem_cost, 2)

    def toggle_pause(self, gid):
        data = self.guests[gid]
        if data.get('is_suspended', False): return
        now = datetime.now()
        if data.get('is_paused', False):
            duration = int((now - data['pause_start_ts']).total_seconds())
            data['total_pause_sec'] += duration
            data['is_paused'] = False
            data['pause_logs'].append(
                f"{len(data['pause_logs']) + 1}. {data['pause_start_ts'].strftime('%H:%M')}-{now.strftime('%H:%M')} ({fmt_duration_str(duration)})")
            data['widgets']['btn_pause'].config(text="⏸ 暂停", bg="#f39c12")
            data['widgets']['lbl_time'].config(fg="#2c3e50")
        else:
            data['is_paused'] = True;
            data['pause_start_ts'] = now
            data['widgets']['btn_pause'].config(text="▶ 继续", bg="#27ae60")
        self.save_to_disk();
        self.refresh_ui_list()

    def toggle_suspend(self, gid):
        data = self.guests[gid]
        now = datetime.now()
        if data.get('is_suspended', False):
            data['is_suspended'] = False
            susp_duration = (now - data['suspend_start_ts']).total_seconds()
            data['total_pause_sec'] += int(susp_duration)
            data['pause_logs'].append(
                f"{len(data['pause_logs']) + 1}. 挂账等候 {data['suspend_start_ts'].strftime('%H:%M')}-{now.strftime('%H:%M')} ({fmt_duration_str(susp_duration)})")
            data['widgets']['btn_suspend'].config(text="挂账", bg="#8e44ad")
            data['widgets']['btn_pause'].config(state=tk.NORMAL)
            data['widgets']['lbl_time'].config(fg="#2c3e50")
            self.save_to_disk();
            self.refresh_ui_list()
        else:
            bill = self.calculate_single_bill(gid, now)
            win = tk.Toplevel(self.root)
            win.title("确认挂账")
            win.geometry("380x380")
            win.grab_set()
            tk.Label(win, text=f"顾客 #{gid} 挂账锁定", font=("微软雅黑", 14, "bold")).pack(pady=10)
            f_info = tk.Frame(win, bg="#f9f9f9", padx=10, pady=10);
            f_info.pack(fill="x", padx=20, pady=5)

            def row(k, v, color="black"):
                f = tk.Frame(f_info, bg="#f9f9f9");
                f.pack(fill="x", pady=2)
                tk.Label(f, text=k, bg="#f9f9f9", font=("微软雅黑", 10)).pack(side="left")
                tk.Label(f, text=v, bg="#f9f9f9", fg=color, font=("微软雅黑", 10, "bold")).pack(side="right")

            row("总时长:", bill['total_dur_str'])
            row("暂停时长:", bill['pause_dur_str'], "#e67e22" if bill['pause_str'] != "无" else "black")
            row("计费时长:", bill['play_dur_str'], "#2ecc71")
            tk.Label(win, text="请确认挂账待付金额:", font=("微软雅黑", 11)).pack(pady=(15, 5))
            var_amount = tk.DoubleVar(value=round(bill['total'], 2))
            e_amount = tk.Entry(win, textvariable=var_amount, font=("Arial", 22, "bold"), fg="#8e44ad",
                                justify="center", bg="#f4ecf7", width=10);
            e_amount.pack(pady=5)

            def confirm():
                try:
                    locked_cost = round(var_amount.get(), 2)
                except:
                    messagebox.showerror("错误", "金额无效"); return
                if data.get('is_paused', False): self.toggle_pause(gid)
                data['is_suspended'] = True;
                data['suspend_start_ts'] = now;
                data['suspend_locked_cost'] = locked_cost
                data['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
                data['widgets']['btn_pause'].config(state=tk.DISABLED)
                self.save_to_disk();
                self.refresh_ui_list();
                win.destroy()

            tk.Button(win, text="确认挂账", bg="#8e44ad", fg="white", font=("微软雅黑", 12, "bold"), width=15,
                      command=confirm).pack(pady=10)

    def change_guest_mode(self, gid):
        data = self.guests[gid]
        if data['mode'] == 'group_buy': return messagebox.showinfo("提示", "团购订单不可直接修改模式，请结账后重新开台。")
        dialog = tk.Toplevel(self.root)
        dialog.title(f"修改 #{gid} 常规模式")
        dialog.geometry("400x350")
        dialog.grab_set()
        tk.Label(dialog, text=f"当前手机: {data['phone']}", font=("微软雅黑", 12, "bold")).pack(pady=10)
        mode_var = tk.StringVar(value=data['mode'])
        tk.Radiobutton(dialog, text=f"🕒 先玩后付", variable=mode_var, value="pay_later", font=("微软雅黑", 11)).pack(
            anchor="w", padx=80)
        tk.Radiobutton(dialog, text=f"♾️ 全天畅玩", variable=mode_var, value="unlimited", font=("微软雅黑", 11)).pack(
            anchor="w", padx=80)
        tk.Radiobutton(dialog, text=f"🎨 单板不限时", variable=mode_var, value="single_board",
                       font=("微软雅黑", 11)).pack(anchor="w", padx=80)
        tk.Radiobutton(dialog, text="🎫 普通定额", variable=mode_var, value="fixed", font=("微软雅黑", 11)).pack(
            anchor="w", padx=80)
        f_min = tk.Frame(dialog);
        f_min.pack(pady=10)
        tk.Label(f_min, text="定额时长(分):").pack(side="left")
        min_entry = tk.Entry(f_min, width=6)
        min_entry.insert(0, str(data['limit_min']) if data['mode'] == 'fixed' else "60")
        min_entry.pack(side="left", padx=5)
        min_entry.bind("<Button-1>", lambda e: mode_var.set("fixed"))

        def confirm():
            new_m = mode_var.get()
            new_l = 0
            if new_m == "fixed":
                try:
                    new_l = int(min_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "请输入有效定额时长"); return
            if new_m == data['mode'] and (new_m != "fixed" or new_l == data['limit_min']): dialog.destroy(); return
            m_txt = get_mode_text(new_m)
            if new_m == 'fixed': m_txt = f"定额({new_l}分)"
            now_str = datetime.now().strftime("%H:%M")
            data['remark'] = (data.get('remark', '') + f"[{now_str} 改为{m_txt}]").strip()
            data['mode'] = new_m;
            data['limit_min'] = new_l
            if data.get('is_suspended', False):
                bill = self.calculate_single_bill(gid, data['suspend_start_ts'])
                data['suspend_locked_cost'] = round(bill['total'], 2)
            data['widgets']['lbl_mode'].config(text=m_txt, bg=get_mode_color(new_m))
            remark_txt = f"备注: {data['remark'].replace(chr(10), ' ')[:15]}..." if data['remark'] else "备注: (点击添加)"
            data['widgets']['lbl_remark'].config(text=remark_txt)
            self.save_to_disk();
            self.refresh_ui_list();
            dialog.destroy()

        tk.Button(dialog, text="确认修改", bg="#27ae60", fg="white", font=("微软雅黑", 12), width=15,
                  command=confirm).pack(pady=20)

    # ==========================
    # --- 结账核心算法 ---
    # ==========================
    def calculate_single_bill(self, gid, end_time):
        d = self.guests[gid]
        c = self.config
        current_pause = 0

        if d.get('is_paused', False):
            current_pause = int((end_time - d['pause_start_ts']).total_seconds())
        elif d.get('is_suspended', False):
            current_pause = int((end_time - d['suspend_start_ts']).total_seconds())

        total_pause_sec = d.get('total_pause_sec', 0) + current_pause
        raw_duration_sec = (end_time - d['start_time']).total_seconds()
        effective_duration_sec = raw_duration_sec - total_pause_sec
        minutes = int(effective_duration_sec / 60)

        total_price = 0.0
        fixed_time_str = "--"
        mode_info = ""
        over_info = "正常"
        gb_voucher_price = 0.0  # 团购券价格
        gb_extra_cost = 0.0     # 额外费用（超时等）
        gb_verified = False     # 是否已核销

        if d.get('is_suspended', False):
            total_price = d.get('suspend_locked_cost', 0.0)
            over_info = "挂账锁定"
            mode_info = d.get('gb_config', {}).get('name') if d['mode'] == 'group_buy' else get_mode_text(d['mode'])
        else:
            if d['mode'] == 'group_buy':
                gb = d['gb_config']
                mode_info = gb['name']
                bp = gb.get('price', 0.0)
                gb_persons = gb.get('persons', 1)
                gb_verified = d.get('gb_verified', False)

                is_valid = True
                if gb.get('type') == 'time_slot':
                    try:
                        st = datetime.strptime(gb['start_time'], "%H:%M").time()
                        et = datetime.strptime(gb['end_time'], "%H:%M").time()
                        gst = d['start_time'].time()
                        if not (st <= gst <= et): is_valid = False
                    except:
                        pass

                if not is_valid:
                    if minutes <= c['time_base']:
                        total_price = c['price_base']
                    else:
                        over = minutes - c['time_base']
                        if over > c['buffer_min']:
                            total_price = c['price_base'] + self.get_overtime_cost(over, c['price_overtime'], c)
                        else:
                            total_price = c['price_base']
                    over_info = "非时段按散客计费"
                else:
                    if gb.get('type') in ['unlimited', 'single_board']:
                        # 多人团购的券价格分摊
                        gb_voucher_price = round(bp / gb_persons, 2)
                        total_price = gb_voucher_price
                        gb_extra_cost = 0.0
                        over_info = "团购不限时"
                    else:
                        lm = gb.get('limit_min', 60)
                        fixed_time_str = fmt_min(lm)
                        buf = gb.get('buffer_min', c['buffer_min'])
                        
                        # time_slot模式特殊处理：看是否超出了时段
                        if gb.get('type') == 'time_slot' and d.get('time_slot_end_time'):
                            # 计算到time_slot_end_time的时长
                            slot_end_time = d['time_slot_end_time']
                            effective_to_slot = (slot_end_time - d['start_time']).total_seconds() / 60
                            # 实际超时是从start_time开始超过time_slot_end_time的部分
                            over = max(0, minutes - effective_to_slot)
                        else:
                            # 固定定额模式：比较minutes和limit_min + 已添加时间
                            added_time = d.get('added_time_min', 0)
                            over = max(0, minutes - (lm + added_time))
                    
                    # 多人团购的券价格分摊
                    gb_voucher_price = round(bp / gb_persons, 2)
                    
                    # 计算直接添加时间的费用（如果是通过直接添加时间的方式）
                    added_time_cost = 0.0
                    if 'added_time_cost' in d:
                        added_time_cost = d['added_time_cost']
                    
                    if over > buf:
                        hourly_p = gb.get('overtime_price', c['price_overtime'])
                        gb_extra_cost = self.get_overtime_cost(over, hourly_p, c)
                        total_price = gb_voucher_price + gb_extra_cost + added_time_cost
                        over_info = f"超时 {fmt_min(over)}"
                    else:
                        gb_extra_cost = 0.0
                        total_price = gb_voucher_price + added_time_cost

            elif d['mode'] == "pay_later":
                mode_info = "先玩后付"
                if minutes <= c['time_base']:
                    total_price = c['price_base']
                else:
                    over = minutes - c['time_base']
                    if over > c['buffer_min']:
                        total_price = c['price_base'] + self.get_overtime_cost(over, c['price_overtime'], c)
                    else:
                        total_price = c['price_base']
                over_info = f"净时长 {fmt_min(minutes)}"

            elif d['mode'] == "fixed":
                mode_info = "普通定额"
                lm = d['limit_min']
                added_time = d.get('added_time_min', 0)
                fixed_time_str = fmt_min(lm + added_time)
                bp = round(((lm + added_time) / 60.0) * c['price_overtime'], 2)
                over = max(0, minutes - (lm + added_time))
                if over > c['buffer_min']:
                    total_price = bp + self.get_overtime_cost(over, c['price_overtime'], c)
                    over_info = f"超时 {fmt_min(over)}"
                else:
                    total_price = bp
                    over_info = f"总时长 {fmt_min(lm + added_time)}"

            elif d['mode'] in ["unlimited", "single_board"]:
                mode_info = "全天畅玩" if d['mode'] == "unlimited" else "单板不限"
                total_price = c['price_unlimited'] if d['mode'] == "unlimited" else c.get('price_single_board', 39.9)
                over_info = "不限时"

        # 计算中途添加的团购券的费用
        added_gb_cost = 0.0
        if 'added_gb' in d:
            for gb in d['added_gb']:
                # 未核销的团购券需要计入费用
                if not gb['verify_status']:
                    added_gb_cost += gb['price']
        
        # 计算直接添加时间的费用（仅在不是通过基础价格计算的模式中添加）
        added_time_cost = 0.0
        if d['mode'] not in ['fixed', 'group_buy']:
            added_time_cost = d.get('added_time_cost', 0.0)
        
        # 对于普通定额模式，需要调整费用计算
        # 因为团购券的时长已经被计入了added_time_min，所以需要从基础价格中扣除这部分时长的费用
        if d['mode'] == 'fixed' and 'added_gb' in d:
            # 计算团购券包含的时长
            gb_minutes = sum(gb['minutes'] for gb in d['added_gb'])
            # 从基础价格中扣除团购券时长的费用
            gb_time_cost = round((gb_minutes / 60.0) * c['price_overtime'], 2)
            total_price = round(total_price - gb_time_cost + added_gb_cost + added_time_cost, 2)
        else:
            total_price = round(total_price + added_gb_cost + added_time_cost, 2)
        
        # 根据核销状态调整应收金额
        if d['mode'] == 'group_buy' and gb_verified:
            # 已核销：只需支付额外费用和未核销的添加团购券费用
            actual_total = gb_extra_cost + added_gb_cost
        else:
            # 未核销或非团购：正常收费
            actual_total = total_price
        
        actual_total = round(actual_total, 2)
        
        pause_log_copy = list(d.get('pause_logs', []))
        if d.get('is_paused', False):
            pause_log_copy.append(f"结账恢复 ({fmt_duration_str(current_pause)})")
        elif d.get('is_suspended', False):
            pause_log_copy.append(f"挂账等待 ({fmt_duration_str(current_pause)})")

        return {
            "gid": gid, "data": d, "end_time": end_time,
            "minutes": minutes, "total_dur_str": fmt_duration_str(raw_duration_sec),
            "play_dur_str": fmt_duration_str(effective_duration_sec),
            "pause_dur_str": fmt_duration_str(total_pause_sec),
            "total": total_price, "actual_total": actual_total, "prepaid": round(d.get('prepaid', 0.0), 2),
            "need": round(max(0, actual_total - d.get('prepaid', 0.0)), 2),
            "fixed_str": fixed_time_str,
            "mode_info": mode_info, "over_info": over_info,
            "pause_str": "; ".join(pause_log_copy) if pause_log_copy else "无",
            "gb_voucher_price": gb_voucher_price, "gb_extra_cost": gb_extra_cost, "gb_verified": gb_verified
        }

    def checkout_group(self, group_id):
        """多人订单合并结账"""
        group_members = [k for k, v in self.guests.items() if v.get('group_id') == group_id]
        if not group_members:
            messagebox.showwarning("警告", "该组已无成员")
            return
        bills = [self.calculate_single_bill(gid, datetime.now()) for gid in group_members]
        self.show_group_checkout_ui(bills, sum([b['total'] for b in bills]))

    def toggle_gb_verified(self, gid):
        """弹窗修改团购核销状态"""
        if gid not in self.guests:
            return
        data = self.guests[gid]
        if data.get('mode') != 'group_buy':
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("修改核销状态")
        dialog.geometry("320x260")
        dialog.grab_set()
        
        tk.Label(dialog, text=f"顾客: {data['phone']}", font=("微软雅黑", 12, "bold")).pack(pady=10)
        tk.Label(dialog, text="选择核销状态:", font=("微软雅黑", 11)).pack(pady=8)
        
        verify_var = tk.StringVar(value="verified" if data.get('gb_verified', False) else "unverified")
        
        tk.Radiobutton(dialog, text="✓ 已核销", variable=verify_var, value="verified", 
                      font=("微软雅黑", 11), fg="#27ae60").pack(anchor="w", padx=50, pady=5)
        tk.Radiobutton(dialog, text="✗ 未核销", variable=verify_var, value="unverified", 
                      font=("微软雅黑", 11), fg="#e74c3c").pack(anchor="w", padx=50, pady=5)
        
        def confirm():
            new_status = verify_var.get() == "verified"
            data['gb_verified'] = new_status
            
            # 联动修改同group_id的其他客人
            group_id = data.get('group_id')
            if group_id:
                for other_gid, other_data in self.guests.items():
                    if other_data.get('group_id') == group_id and other_gid != gid:
                        other_data['gb_verified'] = new_status
                        # 更新其他成员卡片上的标签
                        if other_data.get('mode') == 'group_buy' and other_data['widgets'].get('lbl_verify'):
                            verify_text = "✓ 已核销" if new_status else "✗ 未核销"
                            verify_color = "#27ae60" if new_status else "#e74c3c"
                            other_data['widgets']['lbl_verify'].config(text=verify_text, fg=verify_color)
            
            # 更新当前成员卡片上的标签
            if data['widgets'].get('lbl_verify'):
                verify_text = "✓ 已核销" if new_status else "✗ 未核销"
                verify_color = "#27ae60" if new_status else "#e74c3c"
                data['widgets']['lbl_verify'].config(text=verify_text, fg=verify_color)
            
            self.save_to_disk()
            dialog.destroy()
            status_text = "已核销" if new_status else "未核销"
            messagebox.showinfo("成功", f"已更新为: {status_text}")
        
        tk.Button(dialog, text="确认修改", bg="#27ae60", fg="white", font=("微软雅黑", 12, "bold"),
                 command=confirm).pack(pady=15)
        
        # 添加管理添加团购券的按钮
        if 'added_gb' in data and data['added_gb']:
            tk.Button(dialog, text="管理添加的团购券", bg="#3498db", fg="white", font=("微软雅黑", 10),
                     command=lambda: [dialog.destroy(), self.manage_added_gb_verification(gid)]).pack(pady=5)
    
    def manage_added_gb_verification(self, gid):
        """管理中途添加的团购券的核销状态"""
        data = self.guests[gid]
        
        if 'added_gb' not in data or not data['added_gb']:
            messagebox.showinfo("提示", "没有中途添加的团购券")
            return
        
        # 弹出对话框
        win = tk.Toplevel(self.root)
        win.title("管理添加的团购券")
        win.geometry("400x300")
        win.grab_set()
        
        # 创建列表框
        listbox = tk.Listbox(win, width=40, height=10)
        listbox.pack(pady=10)
        
        # 填充列表
        for i, gb in enumerate(data['added_gb']):
            status = "已核销" if gb['verify_status'] else "未核销"
            listbox.insert(tk.END, f"{i+1}. {gb['name']} - {status}")
        
        # 核销按钮
        def verify_selected():
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("提示", "请选择要核销的团购券")
                return
            
            index = selected[0]
            data['added_gb'][index]['verify_status'] = True
            
            # 更新列表
            listbox.delete(0, tk.END)
            for i, gb in enumerate(data['added_gb']):
                status = "已核销" if gb['verify_status'] else "未核销"
                listbox.insert(tk.END, f"{i+1}. {gb['name']} - {status}")
            
            # 更新备注
            # 重新生成备注
            current_remark = ""
            if 'added_gb' in data:
                for gb in data['added_gb']:
                    status_text = "已核销" if gb['verify_status'] else "未核销"
                    current_remark += f"\n【加团购】{gb['add_time']} {gb['name']} ({status_text})"
            data['remark'] = current_remark.strip()
            
            # 更新备注显示
            if 'lbl_remark' in data['widgets']:
                display_remark = data['remark'].strip().replace("\n", " ")
                if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
                data['widgets']['lbl_remark'].config(text=f"备注: {display_remark}")
            
            self.save_to_disk()
            messagebox.showinfo("成功", "团购券已核销")
        
        # 取消核销按钮
        def unverify_selected():
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("提示", "请选择要取消核销的团购券")
                return
            
            index = selected[0]
            data['added_gb'][index]['verify_status'] = False
            
            # 更新列表
            listbox.delete(0, tk.END)
            for i, gb in enumerate(data['added_gb']):
                status = "已核销" if gb['verify_status'] else "未核销"
                listbox.insert(tk.END, f"{i+1}. {gb['name']} - {status}")
            
            # 更新备注
            # 重新生成备注
            current_remark = ""
            if 'added_gb' in data:
                for gb in data['added_gb']:
                    status_text = "已核销" if gb['verify_status'] else "未核销"
                    current_remark += f"\n【加团购】{gb['add_time']} {gb['name']} ({status_text})"
            data['remark'] = current_remark.strip()
            
            # 更新备注显示
            if 'lbl_remark' in data['widgets']:
                display_remark = data['remark'].strip().replace("\n", " ")
                if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
                data['widgets']['lbl_remark'].config(text=f"备注: {display_remark}")
            
            self.save_to_disk()
            messagebox.showinfo("成功", "团购券已取消核销")
        
        button_frame = tk.Frame(win)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="核销选中的团购券", bg="#27ae60", fg="white", command=verify_selected).pack(side="left", padx=10)
        tk.Button(button_frame, text="取消核销选中的团购券", bg="#e74c3c", fg="white", command=unverify_selected).pack(side="left", padx=10)
        tk.Button(win, text="关闭", bg="#95a5a6", fg="white", command=win.destroy).pack(pady=10)
        
    def add_time(self, gid):
        """为定额或团购倒计时类型卡片添加时间"""
        data = self.guests[gid]
        
        # 弹出对话框让用户选择添加方式
        win = tk.Toplevel(self.root)
        win.title("添加时间")
        win.geometry("400x350")
        win.grab_set()
        
        # 添加方式选择
        add_mode = tk.StringVar(value="direct")
        
        tk.Label(win, text="选择添加方式:", font=("微软雅黑", 12, "bold")).pack(pady=(10, 5))
        
        frame_mode = tk.Frame(win)
        frame_mode.pack(pady=5)
        
        tk.Radiobutton(frame_mode, text="直接添加时间", variable=add_mode, value="direct", font=("微软雅黑", 11)).pack(anchor="w")
        tk.Radiobutton(frame_mode, text="添加团购券", variable=add_mode, value="group_buy", font=("微软雅黑", 11)).pack(anchor="w")
        
        # 直接添加时间的选项
        frame_direct = tk.Frame(win)
        
        tk.Label(frame_direct, text="请输入要添加的时间（分钟）:", font=("微软雅黑", 12)).pack(pady=5)
        
        var_min = tk.StringVar()
        var_min.set("60")  # 默认添加60分钟
        entry_min = tk.Entry(frame_direct, textvariable=var_min, font=("微软雅黑", 14), width=10)
        entry_min.pack(pady=5)
        
        # 添加团购券的选项
        frame_gb = tk.Frame(win)
        
        tk.Label(frame_gb, text="选择团购券模板:", font=("微软雅黑", 12)).pack(pady=5)
        
        # 过滤出倒计时类型的团购券
        countdown_gbs = [gb for gb in self.config.get('group_buys', []) if gb.get('type') in ['fixed', 'time_slot']]
        gb_names = [gb['name'] for gb in countdown_gbs]
        
        var_gb = tk.StringVar()
        cb_gb = ttk.Combobox(frame_gb, textvariable=var_gb, values=gb_names, state="readonly", width=30)
        if gb_names: cb_gb.current(0)
        cb_gb.pack(pady=5)
        
        # 核销状态选择
        tk.Label(frame_gb, text="核销状态:", font=("微软雅黑", 12)).pack(pady=5)
        
        var_verify = tk.StringVar(value="unverified")
        frame_verify = tk.Frame(frame_gb)
        frame_verify.pack()
        
        tk.Radiobutton(frame_verify, text="✓ 已核销", variable=var_verify, value="verified", font=("微软雅黑", 10)).pack(side="left", padx=10)
        tk.Radiobutton(frame_verify, text="✗ 未核销", variable=var_verify, value="unverified", font=("微软雅黑", 10)).pack(side="left", padx=10)
        
        # 根据选择显示不同的选项
        def update_ui():
            mode = add_mode.get()
            if mode == "direct":
                frame_gb.pack_forget()
                frame_direct.pack(pady=10)
            else:
                frame_direct.pack_forget()
                frame_gb.pack(pady=10)
        
        add_mode.trace("w", lambda *args: update_ui())
        update_ui()  # 初始化显示
        
        def confirm():
            try:
                mode = add_mode.get()
                if mode == "direct":
                    # 直接添加时间
                    add_min = int(var_min.get())
                    if add_min <= 0:
                        messagebox.showerror("错误", "请输入正整数")
                        return
                    
                    # 计算添加时间的价格
                    add_price = 0.0
                    if data['mode'] == "fixed":
                        # 常规定额模式：按价格配置计算
                        add_price = round((add_min / 60.0) * self.config['price_overtime'], 2)
                    elif data['mode'] == "group_buy" and data['gb_config']:
                        # 团购模式：按团购的超时价格计算
                        gb = data['gb_config']
                        hourly_p = gb.get('overtime_price', self.config['price_overtime'])
                        add_price = round((add_min / 60.0) * hourly_p, 2)
                    
                    # 更新卡片数据
                    data['added_time_min'] = data.get('added_time_min', 0) + add_min
                    
                    # 保存直接添加时间的费用
                    # 对于团购模式，直接添加时间的费用需要单独保存
                    # 对于固定定额模式，费用已经在基础价格中计算
                    if data['mode'] != 'fixed':
                        if 'added_time_cost' not in data:
                            data['added_time_cost'] = 0.0
                        data['added_time_cost'] += add_price
                    
                    # 更新time_slot_end_time（如果是时段团购）
                    if data.get('time_slot_end_time'):
                        from datetime import timedelta
                        data['time_slot_end_time'] += timedelta(minutes=add_min)
                    
                    # 自动添加加时备注
                    now = datetime.now()
                    add_time_str = now.strftime("%H:%M")
                    current_remark = data.get('remark', '').strip()
                    new_remark = f"{current_remark}\n【加时】{add_time_str} +{add_min}分钟" if current_remark else f"【加时】{add_time_str} +{add_min}分钟"
                    data['remark'] = new_remark.strip()
                    
                    # 显示添加成功信息
                    messagebox.showinfo("成功", f"已添加 {add_min} 分钟\n需支付额外费用: ¥{add_price:.2f}")
                else:
                    # 添加团购券
                    gb_name = var_gb.get()
                    if not gb_name:
                        messagebox.showerror("错误", "请选择团购券模板")
                        return
                    
                    # 找到选中的团购券配置
                    selected_gb = next((gb for gb in countdown_gbs if gb['name'] == gb_name), None)
                    if not selected_gb:
                        messagebox.showerror("错误", "未找到选中的团购券配置")
                        return
                    
                    # 计算团购券的时间和价格
                    add_min = selected_gb.get('limit_min', 60)
                    add_price = selected_gb.get('price', 0.0)
                    
                    # 更新卡片数据
                    data['added_time_min'] = data.get('added_time_min', 0) + add_min
                    
                    # 更新time_slot_end_time（如果是时段团购）
                    if data.get('time_slot_end_time'):
                        from datetime import timedelta
                        data['time_slot_end_time'] += timedelta(minutes=add_min)
                    
                    # 保存中途添加的团购券信息
                    if 'added_gb' not in data:
                        data['added_gb'] = []
                    
                    # 添加团购券信息
                    now = datetime.now()
                    add_time_str = now.strftime("%H:%M")
                    verify_status = var_verify.get() == "verified"
                    
                    added_gb_info = {
                        'id': len(data['added_gb']) + 1,
                        'name': selected_gb['name'],
                        'price': add_price,
                        'minutes': add_min,
                        'verify_status': verify_status,
                        'add_time': add_time_str,
                        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    data['added_gb'].append(added_gb_info)
                    
                    # 自动添加加团购备注
                    verify_status_text = "已核销" if verify_status else "未核销"
                    current_remark = data.get('remark', '').strip()
                    new_remark = f"{current_remark}\n【加团购】{add_time_str} {selected_gb['name']} ({verify_status_text})" if current_remark else f"【加团购】{add_time_str} {selected_gb['name']} ({verify_status_text})"
                    data['remark'] = new_remark.strip()
                    
                    # 显示添加成功信息
                    messagebox.showinfo("成功", f"已添加团购券: {selected_gb['name']}\n时间: {add_min}分钟\n价格: ¥{add_price:.2f}\n核销状态: {verify_status}")
                
                # 更新备注显示
                if 'lbl_remark' in data['widgets']:
                    display_remark = data['remark'].strip().replace("\n", " ")
                    if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
                    data['widgets']['lbl_remark'].config(text=f"备注: {display_remark}")
                
                # 保存数据
                self.save_to_disk()
                
                win.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效数字")
        
        tk.Button(win, text="确认", bg="#27ae60", fg="white", font=("微软雅黑", 12), command=confirm).pack(pady=10)
        tk.Button(win, text="取消", bg="#95a5a6", fg="white", font=("微软雅黑", 12), command=win.destroy).pack()

    def checkout(self, gid, is_auto=False):
        current_group_id = self.guests[gid].get('group_id')
        group_members = [k for k, v in self.guests.items() if
                         v.get('group_id') == current_group_id] if current_group_id else []

        target_gids = [gid]
        if not is_auto and len(group_members) > 1:
            choice = messagebox.askyesnocancel("同组结算", f"该组还有 {len(group_members)} 人，是否合并进入团队收银台？")
            if choice is None: return
            if choice: target_gids = group_members

        bills = [self.calculate_single_bill(tid, datetime.now()) for tid in target_gids]

        if is_auto:
            for b in bills:
                rmk = f"{b['data'].get('remark', '')}[强制]"
                gb_type = ""
                gb_voucher = 0
                if b['data']['mode'] == 'group_buy' and b['data'].get('gb_config'):
                    gb_type = b['data']['gb_config'].get('name', '')
                    gb_voucher = b.get('gb_voucher_price', 0)
                self.write_history(b['gid'], b['data']['phone'], b['data']['mode'], b['data']['start_time'],
                                   b['end_time'], b['total_dur_str'], b['play_dur_str'], b['actual_total'], rmk,
                                   b['fixed_str'], b['pause_str'], b['data'].get('guest_count', 1), gb_type, gb_voucher)
                self.guests[b['gid']]['widgets']['container'].destroy()
                del self.guests[b['gid']]
            self.save_to_disk()
            self.refresh_ui_list()
            return

        if len(bills) == 1:
            self.show_single_checkout_ui(bills[0])
        else:
            total_actual = sum([b['actual_total'] for b in bills])
            self.show_group_checkout_ui(bills, total_actual)

    def show_single_checkout_ui(self, b):
        win = tk.Toplevel(self.root)
        win.title("结账/挂账详情")
        win.geometry("480x950")
        win.grab_set()
        tk.Label(win, text=f"顾客: {b['data']['phone']} [👥 {b['data'].get('guest_count', 1)}人]",
                 font=("微软雅黑", 18, "bold")).pack(pady=15)

        f_detail = tk.Frame(win, bg="#f0f0f0", padx=10, pady=10)
        f_detail.pack(fill="x", padx=20)

        def row(k, v, color="black"):
            f = tk.Frame(f_detail, bg="#f0f0f0")
            f.pack(fill="x", pady=2)
            tk.Label(f, text=k, bg="#f0f0f0", font=("微软雅黑", 10)).pack(side="left")
            tk.Label(f, text=v, bg="#f0f0f0", fg=color, font=("微软雅黑", 10, "bold")).pack(side="right")

        row("计费模式:", b['mode_info'])
        if b['fixed_str'] != "--": row("定额时长:", b['fixed_str'])
        row("总时长:", b['total_dur_str'])
        row("暂停时长:", b['pause_dur_str'], "#e67e22" if b['pause_str'] != "无" else "black")
        row("计费时长:", b['play_dur_str'], "#2ecc71")
        row("状态:", b['over_info'], "red" if "超时" in b['over_info'] else "green")
        
        # 显示团购特有信息
        if b['data']['mode'] == 'group_buy':
            row("团购券价格:", f"{b['gb_voucher_price']:.2f} 元", "#8e44ad")
            if b['gb_extra_cost'] > 0:
                row("超时费用:", f"{b['gb_extra_cost']:.2f} 元", "#e74c3c")
            
            # 显示中途添加的团购券信息
            if 'added_gb' in b['data'] and b['data']['added_gb']:
                row("添加团购券:", f"{len(b['data']['added_gb'])} 张")
                for i, gb in enumerate(b['data']['added_gb']):
                    status = "已核销" if gb['verify_status'] else "未核销"
                    color = "#27ae60" if gb['verify_status'] else "#e74c3c"
                    row(f"  {i+1}. {gb['name']}:", f"¥{gb['price']:.2f} ({status})", color)
            
            # 创建可更新的核销状态标签
            f_verify_status = tk.Frame(f_detail, bg="#f0f0f0")
            f_verify_status.pack(fill="x", pady=2)
            tk.Label(f_verify_status, text="核销状态:", bg="#f0f0f0", font=("微软雅黑", 10)).pack(side="left")
            lbl_verify_status = tk.Label(f_verify_status, text="✗ 未核销", bg="#f0f0f0", fg="#e74c3c", 
                                         font=("微软雅黑", 10, "bold"))
            lbl_verify_status.pack(side="right")
        
        # 显示常规定额卡片的信息
        elif b['data']['mode'] == 'fixed':
            # 显示中途添加的团购券信息
            if 'added_gb' in b['data'] and b['data']['added_gb']:
                row("添加团购券:", f"{len(b['data']['added_gb'])} 张")
                for i, gb in enumerate(b['data']['added_gb']):
                    status = "已核销" if gb['verify_status'] else "未核销"
                    color = "#27ae60" if gb['verify_status'] else "#e74c3c"
                    row(f"  {i+1}. {gb['name']}:", f"¥{gb['price']:.2f} ({status})", color)
        
        # 显示其他模式的加时费用
        else:
            added_time_cost = b['data'].get('added_time_cost', 0.0)
            if added_time_cost > 0:
                row("加时费用:", f"¥{added_time_cost:.2f} 元", "#3498db")
            
            # 显示中途添加的团购券信息
            if 'added_gb' in b['data'] and b['data']['added_gb']:
                row("添加团购券:", f"{len(b['data']['added_gb'])} 张")
                for i, gb in enumerate(b['data']['added_gb']):
                    status = "已核销" if gb['verify_status'] else "未核销"
                    color = "#27ae60" if gb['verify_status'] else "#e74c3c"
                    row(f"  {i+1}. {gb['name']}:", f"¥{gb['price']:.2f} ({status})", color)

        tk.Frame(f_detail, height=2, bg="#ccc").pack(fill="x", pady=8)
        if b['prepaid'] > 0:
            row("预付金额:", f"{b['prepaid']:.2f} 元", "#3498db")
            row("还需补交:", f"{b['need']:.2f} 元", "#e74c3c")

        tk.Label(win, text="订单备注:", font=("微软雅黑", 10)).pack(pady=(10, 0))
        entry_remark = tk.Text(win, font=("微软雅黑", 10), height=3, width=30, bd=1, relief="solid")
        entry_remark.pack(fill="x", padx=30, pady=5)
        entry_remark.insert("1.0", b['data'].get('remark', ''))

        # 先定义金额变量，供后续回调函数使用
        var_total = tk.DoubleVar(value=round(b['actual_total'], 2))
        
        # 团购核销状态修改（必须在金额定义之后）
        verify_var = None
        if b['data']['mode'] == 'group_buy':
            tk.Label(win, text="核销管理:", font=("微软雅黑", 10, "bold")).pack(pady=(15, 5))
            f_verify_frame = tk.Frame(win)
            f_verify_frame.pack(fill="x", padx=30, pady=5)
            
            verify_var = tk.StringVar(value="verified" if b['data'].get('gb_verified', False) else "unverified")
            lbl_actual_total = tk.Label(win, text="", font=("微软雅黑", 10))
            
            def update_total_price(*args):
                """实时更新应收金额和核销状态显示"""
                is_verified = verify_var.get() == "verified"
                
                # 计算中途添加的团购券的费用
                added_gb_cost = 0.0
                if 'added_gb' in b['data']:
                    for gb in b['data']['added_gb']:
                        # 未核销的团购券需要计入费用
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
                
                # 更新上面的核销状态显示
                if is_verified:
                    lbl_verify_status.config(text="✓ 已核销", fg="#27ae60")
                else:
                    lbl_verify_status.config(text="✗ 未核销", fg="#e74c3c")
            
            tk.Radiobutton(f_verify_frame, text="✓ 已核销", variable=verify_var, value="verified", 
                          font=("微软雅黑", 11), bg="#f0f0f0", command=lambda: update_total_price()).pack(side="left", padx=10)
            tk.Radiobutton(f_verify_frame, text="✗ 未核销", variable=verify_var, value="unverified", 
                          font=("微软雅黑", 11), bg="#f0f0f0", command=lambda: update_total_price()).pack(side="left", padx=10)
            
            lbl_actual_total.pack(pady=(10, 5))
            update_total_price()  # 初始化标签显示

        f_money = tk.Frame(win)
        f_money.pack(fill="x", padx=20, pady=10)

        if b['data']['mode'] == 'group_buy' and b['gb_verified']:
            tk.Label(f_money, text="应收金额 (已核销，券价已收):", font=("微软雅黑", 12, "bold")).pack()
        else:
            tk.Label(f_money, text="结算总金额:", font=("微软雅黑", 14, "bold")).pack()
        
        e_total = tk.Entry(f_money, textvariable=var_total, font=("Arial", 24, "bold"), fg="#2980b9", justify="center",
                           bg="#fff3cd")
        e_total.pack(pady=5)

        def suspend_action():
            try:
                final_total = round(var_total.get(), 2)
            except:
                messagebox.showerror("错误", "金额无效"); return
            data = self.guests[b['gid']]
            now = datetime.now()
            if not data.get('is_suspended', False):
                if data.get('is_paused', False): self.toggle_pause(b['gid'])
                data['is_suspended'] = True
                data['suspend_start_ts'] = now
            data['suspend_locked_cost'] = final_total
            
            # 保存团购核销状态 - 包含联动修改
            if b['data']['mode'] == 'group_buy' and verify_var is not None:
                verify_status = (verify_var.get() == "verified")
                data['gb_verified'] = verify_status
                # 联动修改同group_id的其他客人
                group_id = data.get('group_id')
                if group_id:
                    for gid, other_data in self.guests.items():
                        if other_data.get('group_id') == group_id and gid != b['gid']:
                            other_data['gb_verified'] = verify_status
            
            data['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
            data['widgets']['btn_pause'].config(state=tk.DISABLED)

            final_rmk = entry_remark.get("1.0", "end-1c")
            data['remark'] = final_rmk
            remark_txt = f"备注: {final_rmk.strip().replace(chr(10), ' ')[:15]}..." if final_rmk else "备注: (点击添加)"
            data['widgets']['lbl_remark'].config(text=remark_txt)

            self.save_to_disk()
            self.refresh_ui_list()
            win.destroy()
            messagebox.showinfo("挂账完成", f"顾客 #{b['gid']} 已成功挂账！\n系统已冻结金额: {final_total}元")

        def confirm():
            try:
                final_total = round(var_total.get(), 2)
            except:
                messagebox.showerror("错误", "金额无效"); return
            final_rmk = entry_remark.get("1.0", "end-1c")
            
            # 保存团购核销状态 - 包含联动修改
            if b['data']['mode'] == 'group_buy' and verify_var is not None:
                verify_status = (verify_var.get() == "verified")
                self.guests[b['gid']]['gb_verified'] = verify_status
                # 联动修改同group_id的其他客人
                data = self.guests[b['gid']]
                group_id = data.get('group_id')
                if group_id:
                    for gid, other_data in self.guests.items():
                        if other_data.get('group_id') == group_id and gid != b['gid']:
                            other_data['gb_verified'] = verify_status
            
            gb_type = ""
            gb_voucher = 0
            if b['data']['mode'] == 'group_buy' and b['data'].get('gb_config'):
                gb_type = b['data']['gb_config'].get('name', '')
                gb_voucher = b.get('gb_voucher_price', 0)
            self.write_history(b['gid'], b['data']['phone'], b['data']['mode'], b['data']['start_time'], b['end_time'],
                               b['total_dur_str'], b['play_dur_str'], final_total, final_rmk,
                               b['fixed_str'], b['pause_str'], b['data'].get('guest_count', 1), gb_type, gb_voucher)
            self.guests[b['gid']]['widgets']['container'].destroy()
            del self.guests[b['gid']]
            self.save_to_disk()
            self.refresh_ui_list()
            win.destroy()
            messagebox.showinfo("完成", f"结账成功\n入账金额: {final_total}元")

        f_btns = tk.Frame(win)
        f_btns.pack(pady=20)
        tk.Button(f_btns, text="挂账等候", bg="#8e44ad", fg="white", font=("微软雅黑", 14), width=10,
                  command=suspend_action).pack(side="left", padx=10)
        tk.Button(f_btns, text="确认结账", bg="#27ae60", fg="white", font=("微软雅黑", 14), width=10,
                  command=confirm).pack(side="left", padx=10)

    def show_group_checkout_ui(self, bills, total_sum):
        win = tk.Toplevel(self.root)
        win.title(f"团队收银台 ({len(bills)}单)")
        win.geometry("950x800")
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy)

        f_scroll = tk.Frame(win)
        f_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        cv = tk.Canvas(f_scroll, bg="#f2f2f2")
        sb = tk.Scrollbar(f_scroll, orient="vertical", command=cv.yview)
        scroll_f = tk.Frame(cv, bg="#f2f2f2")

        scroll_f.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv_win = cv.create_window((0, 0), window=scroll_f, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfig(cv_win, width=e.width))
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        ui_data_list = []
        verify_var_list = []  # 存储团购核销状态变量

        def update_total(*args):
            if self.is_updating_total: return
            self.is_updating_total = True
            try:
                s = sum(item['var_price'].get() for item in ui_data_list if item['var_check'].get())
                var_total_all.set(round(s, 2))
            except:
                pass
            self.is_updating_total = False

        def update_items(*args):
            if self.is_updating_total: return
            self.is_updating_total = True
            try:
                new_total = round(var_total_all.get(), 2)
                selected_items = [item for item in ui_data_list if item['var_check'].get()]
                if selected_items:
                    curr_others = sum(item['var_price'].get() for item in selected_items[1:])
                    selected_items[0]['var_price'].set(round(new_total - curr_others, 2))
            except:
                pass
            self.is_updating_total = False

        for b in bills:
            var_check = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(scroll_f,
                                 text=f" 手机号: {b['data']['phone']} [👥 {b['data'].get('guest_count', 1)}人]",
                                 variable=var_check, bg="white", font=("微软雅黑", 11, "bold"), command=update_total)
            card = tk.LabelFrame(scroll_f, labelwidget=chk, bg="white", padx=10, pady=8)
            card.pack(fill="x", padx=10, pady=5)

            f_r1 = tk.Frame(card, bg="white")
            f_r1.pack(fill="x", pady=2)
            tk.Label(f_r1, text=f"模式: {b['mode_info']}", width=25, anchor="w", bg="white").pack(side="left")
            if b['fixed_str'] != "--":
                tk.Label(f_r1, text=f"定额时长: {b['fixed_str']}", width=20, anchor="w", bg="white").pack(side="left")
            status_color = "red" if "超时" in b['over_info'] else "green"
            tk.Label(f_r1, text=f"状态: {b['over_info']}", width=20, anchor="w", bg="white", fg=status_color,
                     font=("微软雅黑", 9, "bold")).pack(side="left")

            f_r2 = tk.Frame(card, bg="white")
            f_r2.pack(fill="x", pady=2)
            tk.Label(f_r2, text=f"总时长: {b['total_dur_str']}", width=25, anchor="w", bg="white").pack(side="left")
            pause_color = "#e67e22" if b['pause_str'] != "无" else "black"
            tk.Label(f_r2, text=f"暂停时长: {b['pause_dur_str']}", width=20, anchor="w", bg="white",
                     fg=pause_color).pack(side="left")
            tk.Label(f_r2, text=f"计费时长: {b['play_dur_str']}", width=20, anchor="w", bg="white", fg="#2ecc71",
                     font=("微软雅黑", 9, "bold")).pack(side="left")

            if b['prepaid'] > 0:
                f_r_pre = tk.Frame(card, bg="white")
                f_r_pre.pack(fill="x", pady=2)
                tk.Label(f_r_pre, text=f"预付金额: {round(b['prepaid'], 2)} 元", width=20, anchor="w", bg="white",
                         fg="#3498db").pack(side="left")
                tk.Label(f_r_pre, text=f"还需补交: {round(b['need'], 2)} 元", width=20, anchor="w", bg="white",
                         fg="#e74c3c", font=("微软雅黑", 9, "bold")).pack(side="left")

            f_r3 = tk.Frame(card, bg="white")
            f_r3.pack(fill="x", pady=5)
            tk.Label(f_r3, text="订单备注:", bg="white").pack(side="left")
            e_rmk = tk.Entry(f_r3, bg="#f9f9f9")
            e_rmk.pack(side="left", fill="x", expand=True, padx=(5, 10))
            e_rmk.insert(0, b['data'].get('remark', ''))

            f_r4 = tk.Frame(card, bg="white")
            f_r4.pack(fill="x", pady=(5, 5))
            # 团购的话显示分离的价格，非团购显示total
            if b['data']['mode'] == 'group_buy':
                tk.Label(f_r4, text="团购券:", bg="white", font=("微软雅黑", 9, "bold")).pack(side="left", padx=(0, 5))
                tk.Label(f_r4, text=f"{b['gb_voucher_price']:.2f}元", bg="white", fg="#8e44ad").pack(side="left", padx=5)
                if b['gb_extra_cost'] > 0:
                    tk.Label(f_r4, text="超时费:", bg="white", font=("微软雅黑", 9, "bold")).pack(side="left", padx=(10, 5))
                    tk.Label(f_r4, text=f"{b['gb_extra_cost']:.2f}元", bg="white", fg="#e74c3c").pack(side="left", padx=5)
            tk.Label(f_r4, text="应收:", bg="white", font=("微软雅黑", 10, "bold")).pack(side="left", padx=(20, 5))
            v_price = tk.DoubleVar(value=round(b['actual_total'], 2))
            e_price = tk.Entry(f_r4, textvariable=v_price, width=12, bg="#fff3cd", fg="#e74c3c",
                               font=("Arial", 12, "bold"), justify="center")
            e_price.pack(side="left", padx=5)
            
            # 初始化verify_var为None，只在团购时赋值
            verify_var = None
            
            # 团购核销状态调整
            if b['data']['mode'] == 'group_buy':
                f_verify = tk.Frame(card, bg="white")
                f_verify.pack(fill="x", pady=5)
                tk.Label(f_verify, text="核销:", bg="white", font=("微软雅黑", 10, "bold")).pack(side="left", padx=5)
                verify_var = tk.StringVar(value="verified" if b['gb_verified'] else "unverified")
                
                def make_verify_update(bill_idx):
                    def on_verify_change(*args):
                        idx = bill_idx
                        is_verified = verify_var_list[idx].get() == "verified"
                        # 更新应收金额
                        bill = ui_data_list[idx]['bill']
                        new_actual = bill['gb_extra_cost'] if is_verified else (bill['gb_voucher_price'] + bill['gb_extra_cost'])
                        ui_data_list[idx]['var_price'].set(round(new_actual, 2))
                        update_total()  # 重新计算总额
                    return on_verify_change
                
                verify_var_list.append(verify_var)
                verify_var.trace("w", make_verify_update(len(verify_var_list) - 1))
                
                tk.Radiobutton(f_verify, text="✓已核销", variable=verify_var, value="verified", 
                              font=("微软雅黑", 9), bg="white").pack(side="left", padx=5)
                tk.Radiobutton(f_verify, text="✗未核销", variable=verify_var, value="unverified", 
                              font=("微软雅黑", 9), bg="white").pack(side="left", padx=5)

            ui_data_list.append({'var_price': v_price, 'entry_rmk': e_rmk, 'bill': b, 'var_check': var_check, 'verify_var': verify_var})

        def _bind_to_mousewheel(event):
            try:
                if scroll_f.winfo_height() > cv.winfo_height():
                    cv.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass

        def _recursive_bind(widget):
            widget.bind("<MouseWheel>", _bind_to_mousewheel)
            for child in widget.winfo_children(): _recursive_bind(child)

        _recursive_bind(scroll_f)
        cv.bind("<MouseWheel>", _bind_to_mousewheel)
        win.bind("<MouseWheel>", _bind_to_mousewheel)

        f_bottom = tk.Frame(win, bg="#ecf0f1", pady=15)
        f_bottom.pack(fill="x")

        is_all_selected = tk.BooleanVar(value=True)

        def toggle_select_all():
            new_state = not is_all_selected.get()
            is_all_selected.set(new_state)
            for item in ui_data_list: item['var_check'].set(new_state)
            update_total()

        tk.Button(f_bottom, text="全选 / 反选", command=toggle_select_all, bg="#bdc3c7", font=("微软雅黑", 10)).pack(
            side="left", padx=15)
        tk.Label(f_bottom, text="选中项营收:", bg="#ecf0f1", font=("微软雅黑", 14)).pack(side="left", padx=(10, 5))
        var_total_all = tk.DoubleVar(value=round(total_sum, 2))
        e_ta = tk.Entry(f_bottom, textvariable=var_total_all, width=10, font=("Arial", 22, "bold"), fg="#2980b9",
                        justify="center", bg="white")
        e_ta.pack(side="left")

        for item in ui_data_list: item['var_price'].trace_add("write", update_total)
        var_total_all.trace_add("write", update_items)

        def suspend_group():
            selected_items = [item for item in ui_data_list if item['var_check'].get()]
            if not selected_items: return messagebox.showwarning("提示", "未勾选任何顾客！")

            try:
                final_chk = round(var_total_all.get(), 2)
                now = datetime.now()
                for item in selected_items:
                    b = item['bill']
                    f_price = round(item['var_price'].get(), 2)
                    f_rmk = item['entry_rmk'].get()
                    gid = b['gid']
                    data = self.guests[gid]

                    if not data.get('is_suspended', False):
                        if data.get('is_paused', False): self.toggle_pause(gid)
                        data['is_suspended'] = True
                        data['suspend_start_ts'] = now

                    data['suspend_locked_cost'] = f_price
                    data['remark'] = f_rmk
                    data['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
                    data['widgets']['btn_pause'].config(state=tk.DISABLED)
                    remark_txt = f"备注: {f_rmk.strip().replace(chr(10), ' ')[:15]}..." if f_rmk else "备注: (点击添加)"
                    data['widgets']['lbl_remark'].config(text=remark_txt)

                self.save_to_disk()
                self.refresh_ui_list()
                win.destroy()
                messagebox.showinfo("分组挂账完成",
                                    f"已勾选的 {len(selected_items)} 人成功挂账！\n系统已冻结总金额: {final_chk}元")
            except Exception as e:
                messagebox.showerror("错误", f"数据错误: {e}")

        def confirm():
            selected_items = [item for item in ui_data_list if item['var_check'].get()]
            if not selected_items: return messagebox.showwarning("提示", "未勾选任何顾客！")

            try:
                final_chk = round(var_total_all.get(), 2)
                for item in selected_items:
                    b = item['bill']
                    f_price = round(item['var_price'].get(), 2)
                    f_rmk = item['entry_rmk'].get()
                    gid = b['gid']
                    
                    # 保存团购核销状态的改变
                    if b['data']['mode'] == 'group_buy' and item['verify_var']:
                        verify_status = (item['verify_var'].get() == "verified")
                        self.guests[gid]['gb_verified'] = verify_status
                        # 联动修改同group_id的其他客人
                        data = self.guests[gid]
                        group_id = data.get('group_id')
                        if group_id:
                            for other_gid, other_data in self.guests.items():
                                if other_data.get('group_id') == group_id and other_gid != gid:
                                    other_data['gb_verified'] = verify_status
                    
                    gb_type = ""
                    gb_voucher = 0
                    if b['data']['mode'] == 'group_buy' and b['data'].get('gb_config'):
                        gb_type = b['data']['gb_config'].get('name', '')
                        gb_voucher = b.get('gb_voucher_price', 0)
                    self.write_history(gid, b['data']['phone'], b['data']['mode'], b['data']['start_time'],
                                       b['end_time'], b['total_dur_str'], b['play_dur_str'], f_price, f_rmk,
                                       b['fixed_str'], b['pause_str'], b['data'].get('guest_count', 1), gb_type, gb_voucher)
                    self.guests[gid]['widgets']['container'].destroy()
                    del self.guests[gid]

                self.save_to_disk()
                self.refresh_ui_list()
                win.destroy()
                messagebox.showinfo("完成", f"已勾选的 {len(selected_items)} 人结账成功！\n总入账: {final_chk}元")
            except Exception as e:
                messagebox.showerror("错误", f"数据错误: {e}")

        # 检查是否有团购项目，如果有则添加"总开关"
        has_group_buy = any(b['data']['mode'] == 'group_buy' for b in bills)
        if has_group_buy:
            f_verify_switch = tk.Frame(f_bottom, bg="#ecf0f1")
            f_verify_switch.pack(side="left", padx=10)
            tk.Label(f_verify_switch, text="总开关:", font=("微软雅黑", 10, "bold"), bg="#ecf0f1").pack(side="left", padx=3)
            
            def toggle_all_verified(status):
                """批量改变所有团购项目的核销状态"""
                for item in ui_data_list:
                    if item['verify_var'] and item['bill']['data']['mode'] == 'group_buy':
                        item['verify_var'].set("verified" if status else "unverified")
            
            tk.Button(f_verify_switch, text="✓核", bg="#27ae60", fg="white", font=("微软雅黑", 9),
                     command=lambda: toggle_all_verified(True)).pack(side="left", padx=1)
            tk.Button(f_verify_switch, text="✗未", bg="#e74c3c", fg="white", font=("微软雅黑", 9),
                     command=lambda: toggle_all_verified(False)).pack(side="left", padx=1)
        
        f_btns = tk.Frame(f_bottom, bg="#ecf0f1")
        f_btns.pack(side="right", padx=10)
        tk.Button(f_btns, text="选中项挂账", bg="#8e44ad", fg="white", font=("微软雅黑", 14, "bold"), width=10,
                  command=suspend_group).pack(side="left", padx=10)
        tk.Button(f_btns, text="选中项结账", bg="#27ae60", fg="white", font=("微软雅黑", 14, "bold"), width=10,
                  command=confirm).pack(side="left", padx=10)

    # ==========================
    # --- 后台设置核心 ---
    # ==========================
    def write_history(self, gid, phone, mode, start, end, total_dur, play_dur, cost, remark="", fixed_str="--", pause_info="", guest_count=1, gb_type="", gb_voucher_price=0):
        """写入历史账单记录"""
        f_ex = os.path.exists(HISTORY_FILE)
        with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if not f_ex:
                w.writerow(["开始", "结束", "序号", "标识", "模式", "总时长", "实玩时长", "总金额", "团购类型", "团购价值", "结算金额", "备注", "定额时长", "暂停详情"])
            m_cn = {"pay_later": "先玩后付", "fixed": "定额", "unlimited": "全天畅玩", "single_board": "单板不限", "group_buy": "团购"}.get(mode, mode)
            clean_remark = remark.replace("\n", " ").replace("\r", "")
            w.writerow([
                start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M"), gid, phone, m_cn,
                total_dur, play_dur, round(cost + gb_voucher_price, 2), gb_type, round(gb_voucher_price, 2), round(cost, 2), clean_remark, fixed_str, pause_info
            ])

    def open_gb_pricing_dialog(self, parent_win, gb_data):
        """团购专用计费算法设置窗口"""
        win = tk.Toplevel(parent_win)
        win.title("⚙️ 团购专用计费算法设置")
        win.geometry("550x650")
        win.grab_set()

        canvas = tk.Canvas(win, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_win, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scrollable_frame, text="🔧 专用计费算法参数", font=("微软雅黑", 14, "bold"), fg="#e74c3c", bg="white").pack(pady=15, padx=20)

        entries = {}
        fields = [
            ("【分阶参数】计费周期 (分钟)", "gb_step_n", "int"),
            ("【分阶参数】周期收费 (元)", "gb_step_y", "float"),
            ("【分阶参数】容差比例 (如2为N/2触发进位)", "gb_step_k", "float"),
            ("【分阶参数】靠拢线 (差X分收满1小时)", "gb_ceil_x", "int"),
            ("【通用】免单缓冲宽限期 (分钟)", "gb_buffer_min", "int"),
            ("【基础】小时单价 (元/时)", "gb_price_overtime", "float"),
        ]

        for txt, k, typ in fields:
            f = tk.Frame(scrollable_frame, bg="white")
            f.pack(fill="x", padx=40, pady=6)
            tk.Label(f, text=txt, font=("微软雅黑", 9), bg="white", width=30, anchor="w").pack(side="left")
            e = tk.Entry(f, width=15, font=("微软雅黑", 10))
            # 尝试从 gb_data 中读取，否则使用系统默认值
            default_val = gb_data.get(k, self.config.get(k.replace("gb_", ""), DEFAULT_CONFIG.get(k.replace("gb_", ""), 0)))
            e.insert(0, str(default_val))
            e.pack(side="left", fill="x", expand=True)
            entries[k] = (e, typ)

        def save():
            try:
                for k, (e, typ) in entries.items():
                    val = e.get()
                    if typ == "int":
                        gb_data[k] = int(float(val))
                    else:
                        gb_data[k] = float(val)
                messagebox.showinfo("成功", "专用计费参数已保存")
                win.destroy()
            except Exception as ex:
                messagebox.showerror("错误", f"输入格式错误：{ex}")

        tk.Button(scrollable_frame, text="💾 保存参数", bg="#27ae60", fg="white", font=("微软雅黑", 12, "bold"), command=save).pack(pady=20)

    def open_gb_settings_dialog(self):
        pwd = ask_password(self.root, "验证", "输入管理员密码:")
        if pwd is None: return
        if pwd != self.config["admin_pwd"]: return messagebox.showerror("错误", "密码错误")

        win = tk.Toplevel(self.root)
        win.title("🎫 团购券/模板管理中心")
        win.geometry("1080x680")
        win.grab_set()

        # 左侧：现有团购列表
        left_f = tk.Frame(win, width=350, bg="#ecf0f1", padx=10, pady=10)
        left_f.pack(side="left", fill="both")
        left_f.pack_propagate(False)

        tk.Label(left_f, text="现有团购模板列表", font=("微软雅黑", 12, "bold"), bg="#ecf0f1").pack(pady=5)
        
        f_listbox = tk.Frame(left_f, bg="white", bd=1, relief="solid")
        f_listbox.pack(fill="both", expand=True, pady=5)
        
        sb = tk.Scrollbar(f_listbox)
        sb.pack(side="right", fill="y")
        
        lb = tk.Listbox(f_listbox, yscrollcommand=sb.set, font=("微软雅黑", 10), bg="white")
        lb.pack(fill="both", expand=True)
        sb.config(command=lb.yview)

        def refresh_listbox():
            lb.delete(0, "end")
            for idx, gb in enumerate(self.config.get("group_buys", [])):
                t_str = {"unlimited": "不限时", "fixed": "倒计时", "time_slot": "限时段"}.get(gb['type'], gb['type'])
                lb.insert("end", f"[{t_str}] {gb['name'].replace('🎫 ', '')}")
            if not self.config.get("group_buys", []):
                lb.insert("end", "暂无团购模板")

        def on_select(event):
            sel = lb.curselection()
            if not sel: return
            idx = sel[0]
            gbs = self.config.get("group_buys", [])
            if idx < len(gbs):
                gb = gbs[idx]
                load_gb_form(gb, idx)

        lb.bind("<<ListboxSelect>>", on_select)
        refresh_listbox()

        # 右侧：编辑表单
        right_f = tk.Frame(win, padx=20, pady=10)
        right_f.pack(side="left", fill="both", expand=True)

        tk.Label(right_f, text="📝 团购模板编辑器", font=("微软雅黑", 14, "bold"), fg="#8E44AD").pack(pady=(0, 15))

        def row_entry(txt, width=20):
            f = tk.Frame(right_f)
            f.pack(fill="x", pady=5)
            tk.Label(f, text=txt, width=22, anchor="w", font=("微软雅黑", 10)).pack(side="left")
            e = tk.Entry(f, width=width, font=("微软雅黑", 10))
            e.pack(side="left", fill="x", expand=True)
            return e

        e_name = row_entry("团购名称 (必填):")
        
        # 计费类型选择
        f_type = tk.Frame(right_f)
        f_type.pack(fill="x", pady=5)
        tk.Label(f_type, text="计费类型:", width=22, anchor="w", font=("微软雅黑", 10)).pack(side="left")
        v_type = tk.StringVar(value="fixed")
        cb_type = ttk.Combobox(f_type, textvariable=v_type, values=["fixed (倒计时)", "unlimited (不限时)", "time_slot (限时段)"], 
                               state="readonly", width=23, font=("微软雅黑", 10))
        cb_type.pack(side="left", fill="x", expand=True)

        e_price = row_entry("套餐一口价 (元):")
        e_persons = row_entry("包含人数:")
        
        # 时长相关 - 倒计时和限时段都需要
        f_limit_label = tk.Frame(right_f)
        lbl_limit = tk.Label(f_limit_label, text="包含时长 (分钟):", width=22, anchor="w", font=("微软雅黑", 10))
        lbl_limit.pack(side="left")
        e_limit = tk.Entry(f_limit_label, width=20, font=("微软雅黑", 10))
        e_limit.pack(side="left", fill="x", expand=True)
        
        # 时间段相关 - 仅限时段需要
        f_time_start = tk.Frame(right_f)
        tk.Label(f_time_start, text="限时段开始 (HH:MM):", width=22, anchor="w", font=("微软雅黑", 10)).pack(side="left")
        e_start = tk.Entry(f_time_start, width=20, font=("微软雅黑", 10))
        e_start.pack(side="left", fill="x", expand=True)
        
        f_time_end = tk.Frame(right_f)
        tk.Label(f_time_end, text="限时段结束 (HH:MM):", width=22, anchor="w", font=("微软雅黑", 10)).pack(side="left")
        e_end = tk.Entry(f_time_end, width=20, font=("微软雅黑", 10))
        e_end.pack(side="left", fill="x", expand=True)
        
        # 计费算法选择
        f_algo = tk.Frame(right_f)
        f_algo.pack(fill="x", pady=5)
        tk.Label(f_algo, text="超时计费算法:", width=22, anchor="w", font=("微软雅黑", 10)).pack(side="left")
        v_algo = tk.StringVar(value="common")
        ttk.Combobox(f_algo, textvariable=v_algo, values=["通用计费算法", "专用计费算法"], state="readonly", width=20, font=("微软雅黑", 10)).pack(side="left", fill="x", expand=True)
        
        # 专用计费设置按钮
        btn_pricing = tk.Button(f_algo, text="⚙️ 计费设置", bg="#f39c12", fg="white", font=("微软雅黑", 10, "bold"), state="disabled")
        btn_pricing.pack(side="left", padx=5)

        # 当前编辑的索引
        current_gb_idx = [None]
        current_gb_data = [{}]  # 保存当前的团购数据

        def update_btn_pricing(*args):
            if v_algo.get() == "专用计费算法":
                btn_pricing.config(state="normal")
            else:
                btn_pricing.config(state="disabled")

        def on_pricing_click():
            self.open_gb_pricing_dialog(win, current_gb_data[0])

        v_algo.trace("w", update_btn_pricing)
        btn_pricing.config(command=on_pricing_click)

        def update_form_visibility(*args):
            mode = v_type.get()
            # 倒计时模式：显示时长，隐藏时间段
            if "倒计时" in mode:
                f_limit_label.pack(fill="x", pady=5)
                f_time_start.pack_forget()
                f_time_end.pack_forget()
            # 限时段模式：显示时长和时间段
            elif "限时段" in mode:
                f_limit_label.pack(fill="x", pady=5)
                f_time_start.pack(fill="x", pady=5)
                f_time_end.pack(fill="x", pady=5)
            # 不限时模式：隐藏时长和时间段
            else:
                f_limit_label.pack_forget()
                f_time_start.pack_forget()
                f_time_end.pack_forget()

        v_type.trace("w", update_form_visibility)

        def load_gb_form(gb, idx):
            current_gb_idx[0] = idx
            current_gb_data[0] = gb.copy()
            
            e_name.delete(0, "end")
            e_name.insert(0, gb['name'].replace("🎫 ", ""))
            
            type_map = {"fixed": "fixed (倒计时)", "unlimited": "unlimited (不限时)", "time_slot": "time_slot (限时段)"}
            v_type.set(type_map.get(gb['type'], gb['type']))
            
            e_price.delete(0, "end")
            e_price.insert(0, str(gb.get('price', 0)))
            
            e_persons.delete(0, "end")
            e_persons.insert(0, str(gb.get('persons', 1)))
            
            e_limit.delete(0, "end")
            e_limit.insert(0, str(gb.get('limit_min', 0)))
            
            e_start.delete(0, "end")
            e_start.insert(0, gb.get('start_time', '00:00'))
            
            e_end.delete(0, "end")
            e_end.insert(0, gb.get('end_time', '23:59'))
            
            # 判断是否使用专用计费
            if any(k in gb for k in ['gb_step_n', 'gb_step_y', 'gb_step_k', 'gb_ceil_x', 'gb_buffer_min', 'gb_price_overtime']):
                v_algo.set("专用计费算法")
            else:
                v_algo.set("通用计费算法")
            
            update_form_visibility()

        def save_gb():
            name = e_name.get().strip()
            if not name: return messagebox.showerror("错误", "请填写团购名称")
            
            try:
                type_val = v_type.get().split()[0]
                gb_obj = {
                    "name": f"🎫 {name}",
                    "type": type_val,
                    "price": float(e_price.get() or 0),
                    "persons": int(e_persons.get() or 1),
                    "limit_min": int(e_limit.get() or 0),
                    "start_time": e_start.get() or "00:00",
                    "end_time": e_end.get() or "23:59",
                }
                
                # 添加专用计费参数（如果选择了专用算法）
                if v_algo.get() == "专用计费算法":
                    for k in ['gb_step_n', 'gb_step_y', 'gb_step_k', 'gb_ceil_x', 'gb_buffer_min', 'gb_price_overtime']:
                        if k in current_gb_data[0]:
                            gb_obj[k] = current_gb_data[0][k]
                
                if current_gb_idx[0] is not None:
                    self.config["group_buys"][current_gb_idx[0]] = gb_obj
                    messagebox.showinfo("成功", "团购模板已更新")
                else:
                    if "group_buys" not in self.config:
                        self.config["group_buys"] = []
                    self.config["group_buys"].append(gb_obj)
                    messagebox.showinfo("成功", "团购模板已添加")
                
                self.save_config()
                refresh_listbox()
                current_gb_idx[0] = None
                clear_form()
            except Exception as e:
                messagebox.showerror("错误", f"数据格式错误: {e}")

        def clear_form():
            current_gb_idx[0] = None
            current_gb_data[0] = {}
            e_name.delete(0, "end")
            v_type.set("fixed (倒计时)")
            e_price.delete(0, "end")
            e_price.insert(0, "39.9")
            e_persons.delete(0, "end")
            e_persons.insert(0, "1")
            e_limit.delete(0, "end")
            e_start.delete(0, "end")
            e_end.delete(0, "end")
            v_algo.set("通用计费算法")
            update_form_visibility()

        def delete_gb():
            if current_gb_idx[0] is None: return messagebox.showwarning("提示", "请先选择要删除的模板")
            name = self.config["group_buys"][current_gb_idx[0]]['name']
            if messagebox.askyesno("确认删除", f"确定删除 {name} 吗？"):
                del self.config["group_buys"][current_gb_idx[0]]
                self.save_config()
                refresh_listbox()
                clear_form()

        # 按钮
        f_btns = tk.Frame(right_f)
        f_btns.pack(fill="x", pady=20)
        tk.Button(f_btns, text="💾 保存", bg="#27ae60", fg="white", font=("微软雅黑", 11, "bold"), 
                  command=save_gb).pack(side="left", padx=5)
        tk.Button(f_btns, text="🗑️ 删除", bg="#e74c3c", fg="white", font=("微软雅黑", 11, "bold"),
                  command=delete_gb).pack(side="left", padx=5)
        tk.Button(f_btns, text="✨ 新建", bg="#3498db", fg="white", font=("微软雅黑", 11, "bold"),
                  command=clear_form).pack(side="left", padx=5)

    def open_settings_dialog(self):
        pwd = ask_password(self.root, "验证", "输入管理员密码:")
        if pwd is None: return
        if pwd != self.config["admin_pwd"]: return messagebox.showerror("错误", "密码错误")

        win = tk.Toplevel(self.root)
        win.title("⚙️ 计费引擎核心设置")
        win.geometry("750x850")
        win.grab_set()

        canvas = tk.Canvas(win, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_win, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scrollable_frame, text="⚙️ 通用计费引擎参数", font=("微软雅黑", 14, "bold"), fg="#e74c3c",
                 bg="white").pack(pady=15, padx=20)

        # 超时计费模式
        f_mode = tk.Frame(scrollable_frame, bg="white")
        f_mode.pack(fill="x", padx=40, pady=10)
        tk.Label(f_mode, text="【超时核算引擎】", font=("微软雅黑", 11, "bold"), bg="white").pack(side="left")
        v_mode = tk.StringVar(value=self.config.get("calc_mode", "step"))
        cb_mode = ttk.Combobox(f_mode, textvariable=v_mode, values=["exact (精确计费)", "step (分阶计费)"], state="readonly", width=20)
        cb_mode.pack(side="right", padx=10)
        
        tk.Label(scrollable_frame, text="※ exact: 按分钟精确折算 | step: 高级分阶靠拢计费", 
                 fg="#7f8c8d", font=("微软雅黑", 9), bg="white").pack(padx=40, anchor="w")

        # 分阶参数（仅在step模式时显示）
        step_fields = [
            ("【分阶参数】计费周期 (分钟)", "step_n", "int"),
            ("【分阶参数】周期收费 (元)", "step_y", "float"),
            ("【分阶参数】容差比例 (如2为N/2触发进位)", "step_k", "float"),
            ("【分阶参数】靠拢线 (差X分收满1小时)", "ceil_x", "int"),
        ]
        
        # 通用/基础参数（总是显示）
        base_fields = [
            ("【通用】免单缓冲宽限期 (分钟)", "buffer_min", "int"),
            ("【基础】超时单价 (元/时)", "price_overtime", "float"),
            ("【基础】先玩后付起步价 (元)", "price_base", "float"),
            ("【基础】先玩后付起步时长 (分钟)", "time_base", "int"),
            ("【无限】全天畅玩一口价 (元)", "price_unlimited", "float"),
            ("【无限】单板不限时一口价 (元)", "price_single_board", "float"),
            ("【系统】管理员密码", "admin_pwd", "str")
        ]
        
        entries = {}
        step_frames = {}
        
        # 创建分阶参数框
        for txt, k, typ in step_fields:
            f = tk.Frame(scrollable_frame, bg="white")
            f.pack(fill="x", padx=40, pady=6)
            step_frames[k] = f
            tk.Label(f, text=txt, font=("微软雅黑", 9), bg="white", width=30, anchor="w").pack(side="left")
            e = tk.Entry(f, font=("微软雅黑", 10))
            e.insert(0, str(self.config.get(k, DEFAULT_CONFIG.get(k, 0))))
            e.pack(side="right", padx=10, fill="x", expand=False)
            entries[k] = (e, typ)
        
        # 创建基础参数框
        for txt, k, typ in base_fields:
            f = tk.Frame(scrollable_frame, bg="white")
            f.pack(fill="x", padx=40, pady=6)
            tk.Label(f, text=txt, font=("微软雅黑", 9), bg="white", width=30, anchor="w").pack(side="left")
            e = tk.Entry(f, font=("微软雅黑", 10))
            e.insert(0, str(self.config.get(k, DEFAULT_CONFIG.get(k, 0))))
            e.pack(side="right", padx=10, fill="x", expand=False)
            entries[k] = (e, typ)
        
        # 根据模式显示/隐藏分阶参数
        def update_fields_visibility(*args):
            mode = v_mode.get()
            if "精确" in mode:
                # 精确模式：隐藏分阶参数
                for f in step_frames.values():
                    f.pack_forget()
            else:
                # 分阶模式：显示分阶参数
                for idx, (k, f) in enumerate(step_frames.items()):
                    f.pack(fill="x", padx=40, pady=6)
        
        v_mode.trace("w", update_fields_visibility)
        update_fields_visibility()  # 初始化显示

        def save():
            try:
                mode_val = v_mode.get().split()[0]
                self.config["calc_mode"] = mode_val
                for k, (e, typ) in entries.items():
                    val = e.get()
                    if typ == "str":
                        self.config[k] = val
                    elif typ == "int":
                        self.config[k] = int(float(val))
                    else:
                        self.config[k] = float(val)
                self.save_config()
                win.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"输入格式错误：{e}")

        tk.Button(scrollable_frame, text="💾 保存并重启引擎", bg="#27ae60", fg="white", font=("微软雅黑", 12, "bold"),
                  command=save).pack(pady=20)

    def open_settings_menu(self):
        """打开统一的设置菜单"""
        win = tk.Toplevel(self.root)
        win.title("⚙️ 系统设置")
        win.geometry("400x450")
        win.grab_set()
        
        tk.Label(win, text="🔧 系统设置菜单", font=("微软雅黑", 16, "bold"), fg="#2c3e50").pack(pady=20)
        
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="⚙️ 计费引擎设置", font=("微软雅黑", 12, "bold"), bg="#3498db", fg="white",
                  width=20, height=2, command=lambda: [win.destroy(), self.open_settings_dialog()]).pack(pady=10)
        
        tk.Button(btn_frame, text="🎫 团购券管理", font=("微软雅黑", 12, "bold"), bg="#9b59b6", fg="white",
                  width=20, height=2, command=lambda: [win.destroy(), self.open_gb_settings_dialog()]).pack(pady=10)
        
        if not self.auth.activated:
            tk.Button(btn_frame, text="💎 激活商业版", font=("微软雅黑", 12, "bold"), bg="#f39c12", fg="white",
                      width=20, height=2, command=lambda: [win.destroy(), self.show_activation_window(force=False)]).pack(pady=10)
        else:
            tk.Label(btn_frame, text="✅ 已激活商业版", font=("微软雅黑", 12), fg="#27ae60").pack(pady=10)

    # ==========================
    # --- 核心 UI 机制 ---
    # ==========================
    def open_add_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("极速开单")
        dialog.geometry("500x550")
        dialog.grab_set()

        tk.Label(dialog, text="标识:", font=("微软雅黑", 12)).pack(pady=(15, 0))
        phone_entry = tk.Entry(dialog, font=("微软雅黑", 16), width=20, justify="center")
        phone_entry.pack(pady=5);
        phone_entry.focus_set()

        f_cnt = tk.Frame(dialog);
        f_cnt.pack(pady=5)
        tk.Label(f_cnt, text="开台数量/桌数:", font=("微软雅黑", 12)).pack(side="left")
        spin_count = tk.Spinbox(f_cnt, from_=1, to=50, width=5, font=("微软雅黑", 12))
        spin_count.pack(side="left", padx=5)

        tk.Label(dialog, text="选择计费模式:", font=("微软雅黑", 12, "bold"), fg="#2980b9").pack(pady=(15, 5))
        mode_var = tk.StringVar(value="pay_later")

        f_modes = tk.Frame(dialog);
        f_modes.pack()
        tk.Radiobutton(f_modes, text="🕒 先玩后付", variable=mode_var, value="pay_later", font=("微软雅黑", 11)).grid(
            row=0, column=0, sticky="w", padx=20)
        tk.Radiobutton(f_modes, text="♾️ 全天畅玩", variable=mode_var, value="unlimited", font=("微软雅黑", 11)).grid(
            row=0, column=1, sticky="w", padx=20)
        tk.Radiobutton(f_modes, text="🎨 单板不限", variable=mode_var, value="single_board", font=("微软雅黑", 11)).grid(
            row=1, column=0, sticky="w", padx=20)
        tk.Radiobutton(f_modes, text="⏳ 常规定额", variable=mode_var, value="fixed", font=("微软雅黑", 11)).grid(row=1,
                                                                                                                 column=1,
                                                                                                                 sticky="w",
                                                                                                                 padx=20)
        tk.Radiobutton(f_modes, text="🎫 团购核销", variable=mode_var, value="group_buy", font=("微软雅黑", 11, "bold"),
                       fg="#8E44AD").grid(row=2, column=0, columnspan=2, pady=10)

        f_fixed = tk.Frame(dialog)
        tk.Label(f_fixed, text="常规定额时长(分):").pack(side="left")
        min_entry = tk.Entry(f_fixed, width=8);
        min_entry.insert(0, "60")
        min_entry.pack(side="left", padx=5)

        f_gb = tk.Frame(dialog)
        tk.Label(f_gb, text="选择团购券模板:").pack(side="left")
        cb_gb = ttk.Combobox(f_gb, state="readonly", width=25)
        cb_gb.pack(side="left", padx=5)

        f_gb_verify = tk.Frame(dialog)
        tk.Label(f_gb_verify, text="核销状态:").pack(side="left", padx=5)
        verify_var = tk.StringVar(value="unverified")
        tk.Radiobutton(f_gb_verify, text="✓ 已核销", variable=verify_var, value="verified", font=("微软雅黑", 10)).pack(side="left", padx=5)
        tk.Radiobutton(f_gb_verify, text="✗ 未核销", variable=verify_var, value="unverified", font=("微软雅黑", 10)).pack(side="left", padx=5)

        def update_dynamic_ui(*args):
            m = mode_var.get()
            if m == "fixed":
                f_gb.pack_forget(); f_gb_verify.pack_forget()
                f_fixed.pack(pady=5)
            elif m == "group_buy":
                f_fixed.pack_forget()
                f_gb.pack(pady=5)
                f_gb_verify.pack(pady=5)
                cb_gb['values'] = [gb['name'] for gb in self.config.get('group_buys', [])]
                if cb_gb['values']: cb_gb.current(0)
            else:
                f_fixed.pack_forget(); f_gb.pack_forget(); f_gb_verify.pack_forget()

        mode_var.trace("w", update_dynamic_ui)

        tk.Label(dialog, text="初始备注:", font=("微软雅黑", 10)).pack(pady=(10, 0))
        remark_entry = tk.Text(dialog, font=("微软雅黑", 10), height=2, width=35, bd=1, relief="solid")
        remark_entry.pack()

        def confirm():
            p = phone_entry.get().strip()
            m = mode_var.get()
            l = 0;
            gb_cfg = None;
            g_count = 1
            if not p: return

            if m == "fixed":
                try:
                    l = int(min_entry.get())
                except:
                    return
            elif m == "group_buy":
                sel_name = cb_gb.get()
                gb_cfg = next((x for x in self.config.get('group_buys', []) if x['name'] == sel_name), None)
                if not gb_cfg: return messagebox.showerror("错误", "请先在后台配置团购模板！")
                g_count = gb_cfg.get('persons', 1)
                
                # 检查时间段团购的时段限制
                if gb_cfg.get('type') == 'time_slot':
                    start_time_str = gb_cfg.get('start_time', '00:00')
                    end_time_str = gb_cfg.get('end_time', '23:59')
                    try:
                        start_h, start_m = map(int, start_time_str.split(':'))
                        end_h, end_m = map(int, end_time_str.split(':'))
                        now = datetime.now()
                        now_h, now_m = now.hour, now.minute
                        now_minutes = now_h * 60 + now_m
                        start_minutes = start_h * 60 + start_m
                        end_minutes = end_h * 60 + end_m
                        
                        # 处理跨越午夜的时段
                        if start_minutes <= end_minutes:
                            in_time = start_minutes <= now_minutes <= end_minutes
                        else:
                            in_time = now_minutes >= start_minutes or now_minutes <= end_minutes
                        
                        if not in_time:
                            messagebox.showwarning("时段限制", f"此团购只在 {start_time_str} 到 {end_time_str} 开放！\n请在允许时段内开单。")
                            return
                    except:
                        pass

            count = int(spin_count.get())
            if not self.auth.activated and (self.auth.data['guests'] + count > 20):
                self.show_activation_window("试用版最多仅支持开 20 单，体验名额已用尽！\n请购买正版授权以继续使用。",
                                            force=True)
                dialog.destroy();
                return

            # 团购处理：无论什么类型，多人都生成group_id
            if m == "group_buy":
                # 确定该团购对应的总卡片数
                total_cards = count * g_count
                # 如果多人，生成group_id用于大卡片关联
                group_id = int(time.time()) if (g_count > 1 and total_cards > 1) else None
                
                for i in range(total_cards):
                    self.guest_counter += 1
                    p_final = f"{p}({i + 1})" if total_cards > 1 else p
                    self.create_guest_ui(self.guest_counter, p_final, m, datetime.now(), l,
                                         remark_entry.get("1.0", "end-1c"), False, group_id, 0.0, guest_count=1,
                                         gb_config=gb_cfg, gb_verified=(verify_var.get() == "verified"))
            else:
                # 常规订单处理
                total_cards = count
                group_id = int(time.time()) if total_cards > 1 else None
                for i in range(total_cards):
                    self.guest_counter += 1
                    p_final = f"{p}({i + 1})" if total_cards > 1 else p
                    self.create_guest_ui(self.guest_counter, p_final, m, datetime.now(), l,
                                         remark_entry.get("1.0", "end-1c"), False, group_id, 0.0, guest_count=1,
                                         gb_config=gb_cfg if m == "group_buy" else None, 
                                         gb_verified=(verify_var.get() == "verified") if m == "group_buy" else False)

            self.auth.add_guest(count)
            self.save_to_disk()
            dialog.destroy()

        tk.Button(dialog, text="立即开台", bg="#27ae60", fg="white", font=("微软雅黑", 14, "bold"), width=20,
                  command=confirm).pack(pady=20)

    def create_guest_ui(self, gid, phone, mode, start_time, limit_min, remark="", is_paused=False, group_id=None,
                        prepaid=0.0, guest_count=1, gb_config=None, gb_verified=False):
        container = tk.Frame(self.scrollable_frame, bg="#bdc3c7", bd=1)
        bg_frame = tk.Frame(container, bg="#ffffff", padx=10, pady=5)
        bg_frame.pack(fill="x", padx=1, pady=1)

        tk.Button(bg_frame, text="结账", bg="#e74c3c", fg="white", font=("微软雅黑", 12, "bold"),
                  command=lambda: self.checkout(gid), width=6).pack(side="right")
        btn_suspend = tk.Button(bg_frame, text="挂账", bg="#8e44ad", fg="white", font=("微软雅黑", 10),
                                command=lambda: self.toggle_suspend(gid), width=7)
        btn_suspend.pack(side="right", padx=(5, 5))
        btn_pause = tk.Button(bg_frame, text="⏸ 暂停" if not is_paused else "▶ 继续",
                              bg="#f39c12" if not is_paused else "#27ae60", fg="white", font=("微软雅黑", 10),
                              command=lambda: self.toggle_pause(gid), width=6)
        btn_pause.pack(side="right", padx=(5, 0))
        
        # 添加加时间按钮（只对定额和团购倒计时类型显示）
        btn_add_time = None
        if mode == "fixed" or (mode == "group_buy" and gb_config and gb_config.get('type') in ['fixed', 'time_slot']):
            btn_add_time = tk.Button(bg_frame, text="➕ 加时间", bg="#27ae60", fg="white", font=("微软雅黑", 10),
                                    command=lambda: self.add_time(gid), width=7)
            btn_add_time.pack(side="right", padx=(5, 0))

        info_frame = tk.Frame(bg_frame, bg="#ffffff", width=220, height=80)
        info_frame.pack_propagate(False)
        info_frame.pack(side="right", padx=10)
        inner_frame = tk.Frame(info_frame, bg="#ffffff")
        inner_frame.place(relx=1.0, rely=0.5, anchor="e")

        tk.Label(inner_frame, text=f"开始: {start_time.strftime('%H:%M')}", font=("Arial", 9), fg="#95a5a6",
                 bg="#ffffff", anchor="e").pack(fill="x")

        display_limit = "--"
        if mode == "fixed":
            display_limit = fmt_min(limit_min)
        elif mode == "group_buy" and gb_config and gb_config.get('type') == 'fixed':
            display_limit = fmt_min(gb_config.get('limit_min', 60))
        elif mode == "group_buy" and gb_config and gb_config.get('type') == 'time_slot':
            display_limit = fmt_min(gb_config.get('limit_min', 60))
        if display_limit != "--":
            tk.Label(inner_frame, text=f"定额: {display_limit}", font=("微软雅黑", 9), fg="#f39c12", bg="#ffffff",
                     anchor="e").pack(fill="x")
        
        # 显示团购核销状态
        lbl_verify = None
        if mode == "group_buy":
            verify_text = "✓ 已核销" if gb_verified else "✗ 未核销"
            verify_color = "#27ae60" if gb_verified else "#e74c3c"
            lbl_verify = tk.Label(inner_frame, text=verify_text, font=("微软雅黑", 9, "bold"), fg=verify_color, bg="#ffffff",
                     anchor="e", cursor="hand2")
            lbl_verify.pack(fill="x")
            lbl_verify.bind("<Button-1>", lambda e: self.toggle_gb_verified(gid))

        display_remark = remark.strip().replace("\n", " ")
        if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
        remark_txt = f"备注: {display_remark}" if display_remark else "备注: (点击添加)"
        lbl_remark = tk.Label(inner_frame, text=remark_txt, font=("微软雅黑", 9), fg="#7f8c8d", bg="#ffffff",
                              cursor="hand2", anchor="e")
        lbl_remark.pack(fill="x")
        lbl_remark.bind("<Button-1>", lambda e: self.edit_remark(gid))

        left_frame = tk.Frame(bg_frame, bg="#ffffff")
        left_frame.pack(side="left")

        if group_id:
            col = get_group_color(group_id)
            tk.Frame(left_frame, bg=col, width=5, height=40).pack(side="left", padx=(0, 5), fill="y")
            tk.Label(left_frame, text="👥", font=("Arial", 12), fg=col, bg="#ffffff").pack(side="left", padx=(0, 5))

        center_frame = tk.Frame(bg_frame, bg="#ffffff")
        center_frame.pack(side="left", expand=True, fill="x")

        tk.Label(left_frame, text=f"#{gid}", font=("Arial", 16, "bold"), fg="#bdc3c7", bg="#ffffff", width=3).pack(
            side="left")

        phone_txt = f"{phone}[👥 {guest_count}人]" if guest_count > 1 else phone
        tk.Label(left_frame, text=phone_txt, font=("微软雅黑", 14, "bold"), fg="#2c3e50", bg="#ffffff", width=16,
                 anchor="w").pack(side="left", padx=5)

        m_txt = gb_config['name'] if mode == 'group_buy' else get_mode_text(mode)
        m_bg = get_mode_color(mode)

        lbl_mode = tk.Label(left_frame, text=m_txt, font=("微软雅黑", 9, "bold"), fg="white", bg=m_bg, width=18, pady=2,
                            cursor="hand2")
        lbl_mode.pack(side="left", padx=5)
        lbl_mode.bind("<Button-1>", lambda e, g=gid: self.change_guest_mode(g))

        lbl_time = tk.Label(center_frame, text="00:00:00", font=("Consolas", 26, "bold"), fg="#2c3e50", bg="#ffffff")
        lbl_time.pack(anchor="center")

        bar = CardProgressBar(container, height=6)
        bar.pack(side="bottom", fill="x")

        # 决定是否为群组主卡片（用于显示方式）
        is_group_master = False
        if group_id:
            # 检查是否为该group_id的first member
            group_members = [k for k, v in self.guests.items() if v.get('group_id') == group_id]
            is_group_master = (len(group_members) == 0)  # 如果没有其他member，就是master
        
        # 计算time_slot类型的限制时间
        time_slot_end_time = None
        if mode == "group_buy" and gb_config and gb_config.get('type') == 'time_slot':
            end_time_str = gb_config.get('end_time', '23:59')
            try:
                end_h, end_m = map(int, end_time_str.split(':'))
                now = datetime.now()
                end_time_today = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
                
                # 如果end_time已经过了，用明天的end_time
                if now > end_time_today:
                    end_time_today = end_time_today + timedelta(days=1)
                
                # time_slot_end_time是时段结束时间
                time_slot_end_time = end_time_today
            except:
                pass
        
        # 构建widgets字典
        widgets = {'container': container, 'bg_frame': bg_frame, 'lbl_time': lbl_time, 'bar': bar,
                   'lbl_remark': lbl_remark, 'btn_pause': btn_pause, 'lbl_mode': lbl_mode,
                   'btn_suspend': btn_suspend, 'lbl_verify': lbl_verify}
        
        # 添加加时间按钮到widgets字典
        if btn_add_time:
            widgets['btn_add_time'] = btn_add_time
        
        self.guests[gid] = {
            'phone': phone, 'mode': mode, 'start_time': start_time, 'limit_min': limit_min,
            'remark': remark, 'is_paused': is_paused, 'total_pause_sec': 0, 'pause_start_ts': None, 'pause_logs': [],
            'is_suspended': False, 'suspend_start_ts': None, 'suspend_locked_cost': 0.0,
            'group_id': group_id, 'prepaid': prepaid, 'guest_count': guest_count, 'gb_config': gb_config,
            'gb_verified': gb_verified if mode == 'group_buy' else None, 
            'gb_verified_group_id': group_id if mode == 'group_buy' and group_id else None,
            'is_group_master': is_group_master,
            'time_slot_end_time': time_slot_end_time,
            'added_time_min': 0,  # 记录已添加的时间（分钟）
            'widgets': widgets
        }
        self.refresh_ui_list()

    def create_group_card(self, grp, is_team=False):
        """创建团队订单大卡片"""
        container = tk.Frame(self.scrollable_frame, bg="#bdc3c7", bd=1)
        bg_frame = tk.Frame(container, bg="#ffffff", padx=10, pady=10)
        bg_frame.pack(fill="x", padx=2, pady=2)

        col = get_group_color(grp) if not is_team else "#8B4513"
        left_band = tk.Frame(bg_frame, bg=col, width=8)
        left_band.pack(side="left", fill="y", padx=(0, 15))

        right_content = tk.Frame(bg_frame, bg="#ffffff")
        right_content.pack(side="left", fill="both", expand=True)

        top_row = tk.Frame(right_content, bg="#ffffff")
        top_row.pack(fill="x")

        lbl_title = tk.Label(top_row, text="Loading...", font=("微软雅黑", 16, "bold"), fg=col, bg="#ffffff")
        lbl_title.pack(side="left")

        lbl_count = tk.Label(top_row, text="成员数: 0 人", font=("微软雅黑", 11), bg="#ffffff", fg="#7f8c8d")
        lbl_count.pack(side="left", padx=15)

        # 只在常规多人（非团购）时显示"新增组员"按钮
        if not is_team:
            tk.Button(top_row, text="+ 新增组员", bg="#2980b9", fg="white", font=("微软雅黑", 10, "bold"), width=12,
                      command=lambda g=grp: self.add_to_group(g)).pack(side="right", padx=5)
        tk.Button(top_row, text="📋 独立查看/结账", bg="#e67e22", fg="white", font=("微软雅黑", 10, "bold"), width=15,
                  command=lambda g=grp: self.view_group_details(g)).pack(side="right", padx=5)

        mid_row = tk.Frame(right_content, bg="#ffffff")
        mid_row.pack(fill="x", pady=15)
        lbl_time = tk.Label(mid_row, text="00:00:00", font=("Consolas", 36, "bold"), fg="#2c3e50", bg="#ffffff")
        lbl_time.pack(anchor="center")

        bot_row = tk.Frame(right_content, bg="#f9f9f9", padx=10, pady=10)
        bot_row.pack(fill="x")
        lbl_members = tk.Label(bot_row, text="", font=("微软雅黑", 10), bg="#f9f9f9", fg="#34495e", justify="left",
                               wraplength=1050)
        lbl_members.pack(fill="x", anchor="w")

        widget_dict = {
            'container': container,
            'lbl_title': lbl_title,
            'lbl_time': lbl_time,
            'lbl_count': lbl_count,
            'lbl_members': lbl_members
        }
        
        if is_team:
            self.team_widgets[grp] = widget_dict
        else:
            self.group_widgets[grp] = widget_dict

    def render_group_cards(self):
        """渲染所有大卡片（常规多人 + 团购多人）"""
        # ========== 常规多人订单 ==========
        current_groups = {}
        for gid, d in self.guests.items():
            grp = d.get('group_id')
            if grp and d.get('mode') != 'group_buy':  # 只处理常规多人订单
                if grp not in current_groups: current_groups[grp] = []
                current_groups[grp].append(gid)

        # 删除不存在的group卡片
        for grp, widget_data in list(self.group_widgets.items()):
            if grp not in current_groups:
                widget_data['container'].destroy()
                del self.group_widgets[grp]

        # 创建新的group卡片
        for grp, gids in current_groups.items():
            if grp not in self.group_widgets:
                self.create_group_card(grp)

            # 更新大卡片信息
            rep_phone = self.guests[sorted(gids)[0]]['phone'].split('(')[0]
            self.group_widgets[grp]['lbl_title'].config(text=f"👥 {rep_phone} (团队)")

            data_list = []
            for gid in sorted(gids):
                d = self.guests[gid]
                status = "计时中"
                if d.get('is_suspended'):
                    status = f"挂账(¥{d.get('suspend_locked_cost', 0):.1f})"
                elif d.get('is_paused'):
                    status = "已暂停"

                m_map = {"pay_later": "后付", "fixed": f"定额{d['limit_min']}分", "unlimited": "畅玩",
                         "single_board": "单板"}
                m_txt = m_map.get(d['mode'], d['mode'])
                data_list.append(f"{d['phone']} {m_txt} - {status}")

            txt = "   |   ".join(data_list)
            self.group_widgets[grp]['lbl_members'].config(text=txt)
            self.group_widgets[grp]['lbl_count'].config(text=f"成员数: {len(gids)} 人")

            # 显示/隐藏大卡片
            if self.tabs[self.notebook.index(self.notebook.select())] == "团队订单":
                kw = self.search_var.get().lower()
                show = False
                if not kw:
                    show = True
                else:
                    for gid in gids:
                        if kw in self.guests[gid]['phone'].lower(): show = True; break
                if show:
                    self.group_widgets[grp]['container'].pack(fill="x", pady=8, padx=10)
            else:
                self.group_widgets[grp]['container'].pack_forget()

        # ========== 团购多人订单 ==========
        # 按first member分组团购多人
        gb_groups = {}
        for gid, d in self.guests.items():
            if d.get('mode') == 'group_buy' and d.get('gb_config', {}).get('persons', 1) > 1:
                grp = d.get('group_id')
                if grp:  # 团购多人应该有group_id
                    if grp not in gb_groups: gb_groups[grp] = []
                    gb_groups[grp].append(gid)

        # 删除不存在的team卡片
        for grp, widget_data in list(self.team_widgets.items()):
            if grp not in gb_groups:
                widget_data['container'].destroy()
                del self.team_widgets[grp]

        # 创建新的team卡片
        for grp, gids in gb_groups.items():
            if grp not in self.team_widgets:
                self.create_group_card(grp, is_team=True)

            # 更新大卡片信息
            first_guest = self.guests[sorted(gids)[0]]
            gb_name = first_guest.get('gb_config', {}).get('name', '团购')
            self.team_widgets[grp]['lbl_title'].config(text=f"🎫 {gb_name}")

            data_list = []
            for gid in sorted(gids):
                d = self.guests[gid]
                status = "计时中"
                if d.get('is_suspended'):
                    status = f"挂账(¥{d.get('suspend_locked_cost', 0):.1f})"
                elif d.get('is_paused'):
                    status = "已暂停"
                verify_text = "✓已核销" if d.get('gb_verified') else "✗未核销"
                data_list.append(f"{d['phone']} {verify_text} - {status}")

            txt = "   |   ".join(data_list)
            self.team_widgets[grp]['lbl_members'].config(text=txt)
            self.team_widgets[grp]['lbl_count'].config(text=f"成员数: {len(gids)} 人")

            # 显示/隐藏大卡片
            if self.tabs[self.notebook.index(self.notebook.select())] == "团队订单":
                kw = self.search_var.get().lower()
                show = False
                if not kw:
                    show = True
                else:
                    for gid in gids:
                        if kw in self.guests[gid]['phone'].lower(): show = True; break
                if show:
                    self.team_widgets[grp]['container'].pack(fill="x", pady=8, padx=10)
            else:
                self.team_widgets[grp]['container'].pack_forget()

    def view_group_details(self, grp):
        """查看团队详情 - 切换到全部订单视图并过滤该团队"""
        self.active_group_filter = grp
        self.notebook.select(0)
        if self.search_var.get() != "":
            self.search_var.set("")
        else:
            self.refresh_ui_list()

    def add_to_group(self, grp):
        """向现有团队添加成员"""
        gids = [gid for gid, d in self.guests.items() if d.get('group_id') == grp]
        if not gids: return

        phones = [self.guests[g]['phone'] for g in gids]
        base_phone = phones[0].split('(')[0]
        
        # 检查是常规多人还是团购多人
        first_member = self.guests[gids[0]]
        is_group_buy = first_member.get('mode') == 'group_buy'
        gb_config = first_member.get('gb_config') if is_group_buy else None
        gb_verified = first_member.get('gb_verified', False) if is_group_buy else False

        import re
        max_seq = 0
        for p in phones:
            m = re.search(r'\((\d+)\)$', p)
            if m:
                max_seq = max(max_seq, int(m.group(1)))
        if max_seq == 0:
            max_seq = len(phones)

        dialog = tk.Toplevel(self.root)
        dialog.title("向团队添加新成员")
        dialog.geometry("450x550")
        dialog.grab_set()

        tk.Label(dialog, text=f"团队手机号: {base_phone}", font=("微软雅黑", 16, "bold"), fg="#2980b9").pack(
            pady=(15, 5))

        f_cnt = tk.Frame(dialog)
        f_cnt.pack(pady=10)
        tk.Label(f_cnt, text="新增人数:", font=("微软雅黑", 12)).pack(side="left")
        spin_count = tk.Spinbox(f_cnt, from_=1, to=20, width=5, font=("微软雅黑", 12))
        spin_count.pack(side="left", padx=5)

        # 如果是常规多人，显示计费模式选择；如果是团购多人，显示团购信息（不可修改）
        if not is_group_buy:
            tk.Label(dialog, text="计费模式:", font=("微软雅黑", 12)).pack(pady=(15, 5))
            mode_var = tk.StringVar(value="pay_later")
            tk.Radiobutton(dialog, text=f"🕒 先玩后付", variable=mode_var, value="pay_later", font=("微软雅黑", 11)).pack(
                anchor="w", padx=60)
            tk.Radiobutton(dialog, text=f"♾️ 全天畅玩", variable=mode_var, value="unlimited", font=("微软雅黑", 11)).pack(
                anchor="w", padx=60)
            tk.Radiobutton(dialog, text=f"🎨 单板不限时", variable=mode_var, value="single_board",
                           font=("微软雅黑", 11)).pack(anchor="w", padx=60)
            tk.Radiobutton(dialog, text="🎫 普通定额", variable=mode_var, value="fixed", font=("微软雅黑", 11)).pack(
                anchor="w", padx=60)

            frame_btns = tk.Frame(dialog)
            frame_btns.pack(pady=5)
            tk.Label(frame_btns, text="定额时长(分):").pack(side="left")
            min_entry = tk.Entry(frame_btns, width=6)
            min_entry.insert(0, "60")
            min_entry.pack(side="left", padx=5)

            def set_m(v):
                min_entry.delete(0, "end")
                min_entry.insert(0, str(v))
                mode_var.set("fixed")

            for v in [60, 120, 180]: tk.Button(frame_btns, text=f"{v // 60}h", command=lambda x=v: set_m(x),
                                               bg="white").pack(side="left", padx=2)
        else:
            # 团购多人：显示团购信息（不可修改）
            tk.Label(dialog, text="团购模式:", font=("微软雅黑", 12)).pack(pady=(15, 5))
            tk.Label(dialog, text=f"🎫 {gb_config['name']}", font=("微软雅黑", 14, "bold"), 
                    fg="#8e44ad", bg="#f9f9f9").pack(pady=10, padx=40, fill="x")
            
            tk.Label(dialog, text="核销状态:", font=("微软雅黑", 12)).pack(pady=(10, 5))
            verify_var = tk.StringVar(value="verified" if gb_verified else "unverified")
            tk.Radiobutton(dialog, text="✓ 已核销", variable=verify_var, value="verified", font=("微软雅黑", 11)).pack(
                anchor="w", padx=60)
            tk.Radiobutton(dialog, text="✗ 未核销", variable=verify_var, value="unverified", font=("微软雅黑", 11)).pack(
                anchor="w", padx=60)
            
            mode_var = tk.StringVar(value="group_buy")

        def confirm():
            m = mode_var.get()
            l = 0
            count = int(spin_count.get())
            
            if not is_group_buy and m == "fixed":
                try:
                    l = int(min_entry.get())
                except:
                    return

            if not self.auth.activated and (self.auth.data['guests'] + count > 20):
                self.show_activation_window("试用版最多仅支持开 20 单，您的体验名额已用尽！\n请购买正版授权以继续使用。",
                                            force=True)
                dialog.destroy()
                return

            for i in range(count):
                self.guest_counter += 1
                curr_seq = max_seq + i + 1
                p_final = f"{base_phone}({curr_seq})"
                if is_group_buy:
                    # 团购多人：传入gb_config和核销状态
                    verify_status = (verify_var.get() == "verified") if is_group_buy else False
                    self.create_guest_ui(self.guest_counter, p_final, m, datetime.now(), l, "", False, grp, 0.0, 
                                       guest_count=1, gb_config=gb_config, gb_verified=verify_status)
                else:
                    # 常规多人
                    self.create_guest_ui(self.guest_counter, p_final, m, datetime.now(), l, "", False, grp, 0.0)

            self.auth.add_guest(count)
            self.save_to_disk()
            self.refresh_ui_list()
            dialog.destroy()

        tk.Button(dialog, text="确认添加", bg="#27ae60", fg="white", font=("微软雅黑", 14), width=20,
                  command=confirm).pack(pady=30)

    def on_tab_change(self, event):
        cur_tab = self.tabs[self.notebook.index(self.notebook.select())]
        if cur_tab == "超时监控": self.notebook.set_badge(7, False)
        if cur_tab != "全部订单":
            self.active_group_filter = None
        self.refresh_ui_list()

    def sort_list(self, key):
        self.current_sort_key = key;
        self.current_sort_rev = not self.current_sort_rev
        self.refresh_ui_list()

    def refresh_ui_list(self, *args):
        cur_tab = self.tabs[self.notebook.index(self.notebook.select())]
        kw = self.search_var.get().lower()
        if kw and self.active_group_filter: self.active_group_filter = None

        # 渲染团队订单的大卡片
        self.render_group_cards()

        lst = [(gid, d) for gid, d in self.guests.items()]

        def sort_val(item):
            gid, d = item
            if self.current_sort_key == "id": return gid
            if self.current_sort_key == "start": return d['start_time'].timestamp()
            if self.current_sort_key == "remain":
                if d['mode'] == 'fixed': return d['limit_min'] - (datetime.now() - d['start_time']).total_seconds() / 60
                return 99999
            return gid

        lst.sort(key=sort_val, reverse=self.current_sort_rev)

        for gid, data in self.guests.items(): data['widgets']['container'].pack_forget()
        
        # 团队订单Tab只显示大卡片，不显示individual卡片
        if cur_tab == "团队订单":
            return

        for gid, data in lst:
            is_ot = False
            now = datetime.now()
            pause_sec = data.get('total_pause_sec', 0)
            if data.get('is_paused', False):
                pause_sec += (now - data['pause_start_ts']).total_seconds()
            elif data.get('is_suspended', False):
                pause_sec += (now - data['suspend_start_ts']).total_seconds()

            effective_min = (now - data['start_time']).total_seconds() - pause_sec

            if data['mode'] == 'fixed' and (effective_min / 60) > data['limit_min']:
                is_ot = True
            elif data['mode'] == 'group_buy' and data.get('gb_config', {}).get('type') in ['fixed', 'time_slot'] and (
                    effective_min / 60) > data.get('gb_config', {}).get('limit_min', 0):
                is_ot = True

            show = False
            if self.active_group_filter:
                if data.get('group_id') == self.active_group_filter: show = True
            else:
                if cur_tab == "全部订单":
                    # 全部订单显示所有individual卡片（无论是否有group_id）
                    show = True
                elif cur_tab == "先玩后付":
                    if data['mode'] == "pay_later": show = True
                elif cur_tab == "无限模式":
                    # 全天畅玩、单板不限、团购无限
                    if data['mode'] in ["unlimited", "single_board"]: show = True
                    elif data['mode'] == "group_buy" and data.get('gb_config', {}).get('type') == 'unlimited': show = True
                elif cur_tab == "定额/倒计时":
                    # 常规定额 + 倒计时团购
                    if data['mode'] == "fixed": show = True
                    elif data['mode'] == "group_buy" and data.get('gb_config', {}).get('type') == 'fixed': show = True
                elif cur_tab == "限时段":
                    # 限时段团购
                    if data['mode'] == "group_buy" and data.get('gb_config', {}).get('type') == 'time_slot': show = True
                elif cur_tab == "团购":
                    # 所有团购
                    if data['mode'] == "group_buy": show = True
                elif cur_tab == "超时监控":
                    # 超时监控
                    if is_ot: show = True

            if kw and kw not in data['phone'].lower() and kw not in str(data.get('remark', '')).lower() and kw != str(
                gid): show = False
            if show: data['widgets']['container'].pack(fill="x", pady=4, padx=5)

    def update_timers(self):
        now = datetime.now()
        ot_cnt = 0

        if self.auth.activated:
            self.status_bar.config(text="✓ 系统就绪 (永久授权商业版) - 欢迎使用藤原智能门店管理系统", fg="#27ae60")
        else:
            rem_guests = max(0, 20 - self.auth.data['guests'])
            self.status_bar.config(text=f"【试用版】剩余体验开单名额: {rem_guests}单 | 请尽快激活商业版以免影响营业",
                                   fg="#e74c3c")

        for gid, data in self.guests.items():
            total_pause = data.get('total_pause_sec', 0)
            active_sec = (now - data['start_time']).total_seconds() - total_pause
            if data.get('is_paused', False):
                active_sec -= (now - data['pause_start_ts']).total_seconds()
            elif data.get('is_suspended', False):
                active_sec -= (now - data['suspend_start_ts']).total_seconds()

            active_sec = max(0, int(active_sec))
            frozen_time_str = fmt_duration_str(active_sec)

            if data.get('is_suspended', False):
                locked_cost = data.get('suspend_locked_cost', 0.0)
                time_text = f"已挂账 {frozen_time_str} (待付: ¥{locked_cost:.2f})"
                data['widgets']['lbl_time'].config(text=time_text, fg="#8e44ad", font=("微软雅黑", 16, "bold"))
                data['widgets']['bar'].update_bar(1.0, "#bdc3c7")
                continue

            if data.get('is_paused', False):
                current_pause_dur = (now - data['pause_start_ts']).total_seconds()
                total_pause_display = total_pause + current_pause_dur
                time_text = f"已暂停 {frozen_time_str} (已停 {fmt_duration_str(total_pause_display)})"
                data['widgets']['lbl_time'].config(text=time_text, fg="#95a5a6", font=("微软雅黑", 16, "bold"))
                bar_pct = 0
                if data['mode'] == 'fixed':
                    limit = data['limit_min']
                    if limit > 0: bar_pct = min(1.0, (active_sec / 60) / limit)
                else:
                    if data['mode'] in ["unlimited", "single_board", "group_buy"]: bar_pct = 1.0
                data['widgets']['bar'].update_bar(bar_pct, "#ecf0f1")
                continue

            h, r = divmod(int(active_sec), 3600)
            m, s = divmod(r, 60)
            time_text = f"{h:02d}:{m:02d}:{s:02d}"
            data['widgets']['lbl_time'].config(text=time_text, font=("Consolas", 26, "bold"))

            tm = int(active_sec / 60)
            bar_pct = 0;
            bar_color = "#ecf0f1"

            is_fixed_mode = False
            lm = 60
            if data['mode'] == "fixed":
                is_fixed_mode = True; lm = data['limit_min']
            elif data['mode'] == "group_buy" and data['gb_config']['type'] in ['fixed', 'time_slot']:
                is_fixed_mode = True
                if data['gb_config']['type'] == 'time_slot':
                    # time_slot模式：用time_slot_end_time计算
                    lm = data['gb_config'].get('limit_min', 60)
                else:
                    # fixed模式：用limit_min计算
                    lm = data['gb_config'].get('limit_min', 60)

            if is_fixed_mode:
                if data.get('time_slot_end_time'):
                    # time_slot模式：计算到time_slot_end_time还有多久
                    remain_sec = (data['time_slot_end_time'] - now).total_seconds()
                    # 计算总可用时间（从开始到时段结束）
                    total_available_sec = (data['time_slot_end_time'] - data['start_time']).total_seconds()
                    if total_available_sec > 0: bar_pct = min(1.0, active_sec / total_available_sec)
                else:
                    # 普通定额模式：计算到limit_min + 已添加时间还有多久
                    added_time = data.get('added_time_min', 0)
                    remain_sec = (lm + added_time) * 60 - active_sec
                    if (lm + added_time) > 0: bar_pct = min(1.0, tm / (lm + added_time))
                
                if remain_sec < 0:
                    ot_h, ot_r = divmod(int(abs(remain_sec)), 3600)
                    ot_m, ot_s = divmod(ot_r, 60)
                    time_text = f"超时 {ot_h:02d}:{ot_m:02d}:{ot_s:02d}"
                    data['widgets']['lbl_time'].config(text=time_text, fg="#c0392b", font=("微软雅黑", 22, "bold"))
                    bar_color = "#e74c3c"
                else:
                    # 显示剩余时间
                    rem_h, rem_r = divmod(int(remain_sec), 3600)
                    rem_m, rem_s = divmod(rem_r, 60)
                    time_text = f"剩余 {rem_h:02d}:{rem_m:02d}:{rem_s:02d}"
                    data['widgets']['lbl_time'].config(text=time_text, fg="#27ae60", font=("Consolas", 26, "bold"))
                    bar_color = "#2ecc71"
                    ot_cnt += 1
            else:
                data['widgets']['lbl_time'].config(fg="#2c3e50")
                if data['mode'] in ["unlimited", "single_board", "group_buy"]: bar_color = get_mode_color(
                    data['mode']); bar_pct = 1.0

            data['widgets']['lbl_time'].config(text=time_text)
            data['widgets']['bar'].update_bar(bar_pct, bar_color)

        if ot_cnt > 0 and self.tabs[self.notebook.index(self.notebook.select())] != "超时监控":
            self.notebook.set_badge(6, True)
        else:
            self.notebook.set_badge(6, False)
        self.root.after(1000, self.update_timers)

    def edit_remark(self, gid):
        current = self.guests[gid].get('remark', '')
        win = tk.Toplevel(self.root)
        win.title("修改备注")
        win.geometry("400x300")
        win.grab_set()
        tk.Label(win, text="修改备注:", font=("微软雅黑", 12)).pack(pady=10)
        txt = tk.Text(win, font=("微软雅黑", 10), height=5, width=40, bd=1, relief="solid")
        txt.pack(pady=5, padx=20)
        txt.insert("1.0", current)

        def save():
            new_r = txt.get("1.0", "end-1c")
            self.guests[gid]['remark'] = new_r
            display_remark = new_r.strip().replace("\n", " ")
            if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
            remark_txt = f"备注: {display_remark}" if display_remark else "备注: (点击添加)"
            self.guests[gid]['widgets']['lbl_remark'].config(text=remark_txt)
            self.save_to_disk()
            win.destroy()

        tk.Button(win, text="保存", bg="#2980b9", fg="white", command=save, font=("微软雅黑", 10), width=10).pack(
            pady=20)

    def open_history_window(self):
        win = tk.Toplevel(self.root)
        win.title("历史账单分析")
        win.geometry("1250x700")
        filter_frame = tk.LabelFrame(win, text="筛选", pady=5, padx=5)
        filter_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(filter_frame, text="关键词:").pack(side="left")
        search_var = tk.StringVar()
        tk.Entry(filter_frame, textvariable=search_var).pack(side="left", padx=5)
        tk.Button(filter_frame, text="🗑️ 批量删除选中", bg="#e74c3c", fg="white",
                  command=lambda: self.delete_history_items(tree)).pack(side="right")
        stats_frame = tk.Frame(win, bg="#ecf0f1", pady=10)
        stats_frame.pack(fill="x", padx=10)
        lbl_count = tk.Label(stats_frame, text="资流总数: 0 人", font=("微软雅黑", 12, "bold"), fg="#2980b9",
                             bg="#ecf0f1")
        lbl_count.pack(side="left", padx=20)
        lbl_gb_total = tk.Label(stats_frame, text="团购价值: ¥0.00", font=("微软雅黑", 12, "bold"), fg="#8e44ad", bg="#ecf0f1")
        lbl_gb_total.pack(side="left", padx=20)
        lbl_settle = tk.Label(stats_frame, text="结算金额: ¥0.00", font=("微软雅黑", 12, "bold"), fg="#e67e22", bg="#ecf0f1")
        lbl_settle.pack(side="left", padx=20)
        lbl_income = tk.Label(stats_frame, text="核算总金额: ¥0.00", font=("微软雅黑", 12, "bold"), fg="#27ae60", bg="#ecf0f1")
        lbl_income.pack(side="right", padx=20)
        cols = (
        "start", "end", "id", "phone", "mode", "tot_dur", "play_dur", "cost", "gb_type", "gb_val", "settle", "remark", "fixed", "pause")
        tree = ttk.Treeview(win, columns=cols, show='headings', selectmode='extended')
        headers = ["开始", "结束", "序号", "标识", "模式", "总时长", "实玩时长", "总金额", "团购类型", "团购价值", "结算金额", "备注", "定额",
                   "暂停"]
        for c, h in zip(cols, headers): 
            tree.heading(c, text=h, command=lambda _c=c: self.treeview_sort_column(tree, _c, False))
            tree.column(c, width=80 if c not in ["start", "end", "pause", "remark"] else 120)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        all_rows = []

        def load_data():
            all_rows.clear()
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                        r = csv.reader(f)
                        next(r, None)
                        all_rows.extend(list(r))
                except:
                    pass
            filter_data()

        def filter_data(*args):
            kw = search_var.get().lower()
            for i in tree.get_children(): tree.delete(i)
            filtered = []
            total_rev = 0.0
            total_gb_value = 0.0
            total_settle = 0.0
            for row in reversed(all_rows):
                if kw in " ".join(row).lower():
                    if len(row) == 12:
                        new_row = [row[0], row[1], row[2], row[3], row[4], row[6], row[7], row[8], "", "0", row[8], row[9], row[10], row[11]]
                        row = new_row
                    elif len(row) < 14: 
                        row += ["--"] * (14 - len(row))
                    tree.insert("", "end", values=row[:14])
                    filtered.append(row)
                    try:
                        total_rev += float(row[7])
                    except:
                        pass
                    try:
                        total_gb_value += float(row[9])
                    except:
                        pass
                    try:
                        total_settle += float(row[10])
                    except:
                        pass
            lbl_count.config(text=f"资流总数: {len(filtered)} 人")
            lbl_gb_total.config(text=f"团购价值: ¥{total_gb_value:.2f}")
            lbl_settle.config(text=f"结算金额: ¥{total_settle:.2f}")
            lbl_income.config(text=f"核算总金额: ¥{total_rev:.2f}")

        search_var.trace("w", filter_data)
        load_data()

    def check_history_permission(self):
        pwd = ask_password(self.root, "验证", "输入密码:")
        if pwd == self.config["admin_pwd"]: self.open_history_window()

    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except:
            l.sort(key=lambda t: t[0], reverse=reverse)
        for index, (val, k) in enumerate(l): tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def delete_history_items(self, tree):
        selected = tree.selection()
        if not selected: return
        if messagebox.askyesno("删除", f"删除选中的 {len(selected)} 条记录？"):
            to_del = [[str(x) for x in tree.item(i)['values']] for i in selected]
            new_rows = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    r = csv.reader(f)
                    h = next(r, None)
                    new_rows.append(h)
                    for row in r:
                        match = False
                        for d in to_del:
                            if len(row) > 3 and row[0] == d[0] and row[2] == d[2] and row[3] == d[
                                3]: match = True; break
                        if not match: new_rows.append(row)
            with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows(new_rows)
            for i in selected: tree.delete(i)

    def clear_all_guests_secure(self):
        if not self.guests: return
        pwd = ask_password(self.root, "警报", "输入密码强制清空:")
        if pwd == self.config["admin_pwd"]:
            for gid in list(self.guests.keys()): self.checkout(gid, True)

    def on_close_app(self):
        pwd = ask_password(self.root, "退出", "输入密码退出:")
        if pwd == self.config["admin_pwd"]:
            self.save_to_disk();
            self.root.destroy()

    def save_to_disk(self):
        s = {}
        for gid, d in self.guests.items():
            s[gid] = {
                'phone': d['phone'], 'mode': d['mode'], 'start_time': d['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                'limit_min': d['limit_min'], 'remark': d.get('remark', ''),
                'is_paused': d.get('is_paused', False), 'total_pause_sec': d.get('total_pause_sec', 0),
                'pause_logs': d.get('pause_logs', []),
                'pause_start_ts': d.get('pause_start_ts').strftime("%Y-%m-%d %H:%M:%S") if d.get(
                    'pause_start_ts') else None,
                'is_suspended': d.get('is_suspended', False), 'suspend_locked_cost': d.get('suspend_locked_cost', 0.0),
                'suspend_start_ts': d.get('suspend_start_ts').strftime("%Y-%m-%d %H:%M:%S") if d.get(
                    'suspend_start_ts') else None,
                'group_id': d.get('group_id'), 'prepaid': d.get('prepaid', 0.0), 'guest_count': d.get('guest_count', 1),
                'gb_config': d.get('gb_config'),
                'gb_verified': d.get('gb_verified', False),
                'added_time_min': d.get('added_time_min', 0),
                'added_time_cost': d.get('added_time_cost', 0.0),
                'time_slot_end_time': d.get('time_slot_end_time').strftime("%Y-%m-%d %H:%M:%S") if d.get('time_slot_end_time') else None,
                'added_gb': d.get('added_gb', [])
            }
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump({'c': self.guest_counter, 'g': s}, f)
        except:
            pass

    def load_from_disk(self):
        if not os.path.exists(DATA_FILE): return
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                self.guest_counter = data.get('c', 0)
                for gid, v in data.get('g', {}).items():
                    self.create_guest_ui(int(gid), v['phone'], v['mode'],
                                         datetime.strptime(v['start_time'], "%Y-%m-%d %H:%M:%S"), v['limit_min'],
                                         v.get('remark', ''), group_id=v.get('group_id'), prepaid=v.get('prepaid', 0.0),
                                         guest_count=v.get('guest_count', 1), gb_config=v.get('gb_config'))
                    g = self.guests[int(gid)]
                    g['is_paused'] = v.get('is_paused', False)
                    g['total_pause_sec'] = v.get('total_pause_sec', 0)
                    g['pause_logs'] = v.get('pause_logs', [])
                    if v.get('pause_start_ts'): g['pause_start_ts'] = datetime.strptime(v['pause_start_ts'],
                                                                                        "%Y-%m-%d %H:%M:%S")
                    g['is_suspended'] = v.get('is_suspended', False)
                    g['suspend_locked_cost'] = round(v.get('suspend_locked_cost', 0.0), 2)
                    if v.get('suspend_start_ts'): g['suspend_start_ts'] = datetime.strptime(v['suspend_start_ts'],
                                                                                            "%Y-%m-%d %H:%M:%S")
                    g['gb_verified'] = v.get('gb_verified', False)
                    g['added_time_min'] = v.get('added_time_min', 0)
                    g['added_time_cost'] = v.get('added_time_cost', 0.0)
                    if v.get('time_slot_end_time'): g['time_slot_end_time'] = datetime.strptime(v['time_slot_end_time'],
                                                                                                "%Y-%m-%d %H:%M:%S")
                    g['added_gb'] = v.get('added_gb', [])
                    if g['is_suspended']:
                        g['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
                        g['widgets']['btn_pause'].config(state=tk.DISABLED)
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = PerfectTimerApp(root)
    root.mainloop()