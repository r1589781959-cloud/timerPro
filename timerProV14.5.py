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
# --- 配置文件 ---
# ==========================================
DATA_FILE = "active_data.json"
HISTORY_FILE = "history_log.csv"
CONFIG_FILE = "shop_config.json"

DEFAULT_CONFIG = {
    "price_base": 29.9, "time_base": 120,
    "price_overtime": 10.0, "buffer_min": 15,
    "admin_pwd": "8888",
    "price_unlimited": 59.9,
    "price_single_board": 39.9,
    "price_fixed_60": 19.9, "price_fixed_120": 35.0, "price_fixed_180": 49.9,
    "price_10min": 2.0, "buffer_10min": 5
}


# ==========================================
# --- 军工级防伪授权系统 (AuthManager V4) ---
# ==========================================
class AuthManager:
    def __init__(self):
        self.machine_code = self._generate_machine_code()

        # 千机千面：公式化隐藏文件路径
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
        # 【不可逆高强度加密算法 SHA-256 + 代码混淆】
        s_part1 = "T!m3r"
        s_part2 = "Pr0"
        s_part3 = "V14_@uth"

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
        return None

    def _spoof_timestamp(self, file_path, file_type):
        try:
            base_time = os.stat("C:\\").st_ctime
            if file_type == 'A':
                fake_time = base_time + (123 * 24 * 3600) + 12580
            else:
                fake_time = base_time + (365 * 24 * 3600) + 31500
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
            self.data = data_a
            self.save()
        elif data_b and not data_a:
            self.data = data_b
            self.save()
        elif data_a and data_b:
            self.data = data_a
            if data_b["guests"] > data_a["guests"]:
                self.data["guests"] = data_b["guests"]
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
# --- 辅助函数 ---
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


GROUP_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6",
    "#e67e22", "#1abc9c", "#34495e", "#ff9ff3", "#feca57",
    "#ff6b6b", "#48dbfb", "#1dd1a1", "#00d2d3", "#5f27cd"
]


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
# --- 核心逻辑类 ---
# ==========================================
class PerfectTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("timerPro V14.5 (试用版)")
        self.root.geometry("1250x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_app)

        self.auth = AuthManager()

        self.config = self.load_config()
        self.upgrade_csv_format()
        self.guests = {}
        self.group_widgets = {}
        self.guest_counter = 0
        self.is_updating_total = False
        self.active_group_filter = None

        # ================== 核心布局重构 ==================
        self.status_bar = tk.Label(root, text="系统就绪", bd=0, relief="flat", anchor="w",
                                   font=("微软雅黑", 10), bg="#ecf0f1", fg="#2c3e50", padx=10, pady=5)
        self.status_bar.pack(side="bottom", fill="x")

        top_frame = tk.Frame(root, pady=10, padx=20, bg="#ecf0f1")
        top_frame.pack(side="top", fill="x")

        tk.Button(top_frame, text="+ 新增客人", font=("微软雅黑", 12, "bold"), bg="#2980b9", fg="white", width=12,
                  command=self.open_add_dialog).pack(side="left")
        tk.Button(top_frame, text="📊 历史账单", font=("微软雅黑", 10), command=self.check_history_permission).pack(
            side="left", padx=10)
        tk.Button(top_frame, text="⚙️ 价格设置", font=("微软雅黑", 10), command=self.open_settings_dialog).pack(
            side="left", padx=10)

        # 💎 商业版激活入口
        if not self.auth.activated:
            tk.Button(top_frame, text="💎 激活商业版", font=("微软雅黑", 10, "bold"), bg="#f39c12", fg="white",
                      command=lambda: self.show_activation_window(force=False)).pack(side="left", padx=10)

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
        self.tabs = ["全部订单", "团队订单", "先玩后付", "团购/定额", "无限模式", "超时监控"]
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
        # =================================================

        # 启动安检 (彻底移除了时间限制)
        self.load_from_disk()
        self.update_timers()

    # ==========================
    # --- 商业级弹窗与清理机制 ---
    # ==========================
    def show_activation_window(self, reason_text="感谢体验！", force=False):
        if hasattr(self, 'act_win') and self.act_win.winfo_exists():
            self.act_win.focus()
            return

        win = tk.Toplevel(self.root)
        self.act_win = win
        win.title("系统激活 - timerPro")
        win.geometry("500x400")
        win.grab_set()
        win.attributes('-topmost', True)

        def on_close():
            if force:
                if messagebox.askyesno("警告", "试用名额已耗尽，必须输入激活码解锁！是否直接退出程序？"):
                    self.root.destroy()
            else:
                win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(win, text="🔒 商业授权认证", font=("微软雅黑", 22, "bold"), fg="#c0392b").pack(pady=(20, 10))
        tk.Label(win, text=reason_text, font=("微软雅黑", 11), fg="#e67e22").pack(pady=5)

        f_mc = tk.Frame(win, bg="#ecf0f1", pady=10, padx=10)
        f_mc.pack(fill="x", padx=40, pady=10)
        tk.Label(f_mc, text="您的专属机器码：", font=("微软雅黑", 12), bg="#ecf0f1").pack()
        e_mc = tk.Entry(f_mc, font=("Consolas", 16, "bold"), justify="center", width=25, fg="#2980b9")
        e_mc.insert(0, self.auth.machine_code)
        e_mc.config(state="readonly")
        e_mc.pack(pady=5)

        tk.Label(win, text="请将机器码发送给客服（微信:r799469），获取永久激活码：", font=("微软雅黑", 10)).pack(pady=(10, 5))
        var_code = tk.StringVar()
        e_code = tk.Entry(win, textvariable=var_code, font=("Consolas", 18, "bold"), justify="center", width=22)
        e_code.pack(pady=5)

        def attempt_activate():
            c = var_code.get().strip()
            if self.auth.activate(c):
                messagebox.showinfo("激活成功", "恭喜！商业授权验证成功，永久解锁所有功能！\n请重启软件以加载完全版界面。")
                win.destroy()
            else:
                messagebox.showerror("错误", "激活码无效，请核对后重新输入！")

        tk.Button(win, text="验证并永久激活", bg="#27ae60", fg="white", font=("微软雅黑", 14, "bold"), width=20,
                  command=attempt_activate).pack(pady=20)

    # ==========================
    # --- 自动升级CSV ---
    # ==========================
    def upgrade_csv_format(self):
        if not os.path.exists(HISTORY_FILE): return
        try:
            rows = []
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                r = csv.reader(f)
                rows = list(r)
            if not rows: return
            header = rows[0]
            if len(header) < 11:
                new_header = ["开始", "结束", "序号", "手机", "模式", "总时长", "实玩时长", "订单总价值", "备注",
                              "定额时长", "暂停详情"]
                new_rows = [new_header]
                for r in rows[1:]:
                    diff = 11 - len(r)
                    new_r = r + ["--"] * diff
                    new_rows.append(new_r)
                with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(new_rows)
        except:
            pass

    # ==========================
    # --- 核心计费算法 ---
    # ==========================
    def calc_pay_later_cost(self, minutes):
        c = self.config
        if minutes <= c['time_base']: return c['price_base']
        extra_min = minutes - c['time_base']
        return c['price_base'] + self.calc_overtime_cost(extra_min)

    def calc_overtime_cost(self, extra_minutes):
        c = self.config
        if extra_minutes <= 0: return 0
        if extra_minutes <= c['buffer_min']: return 0
        hours = int(extra_minutes / 60)
        rem_min = extra_minutes % 60
        blocks = rem_min // 10
        leftover = rem_min % 10
        if leftover > c.get('buffer_10min', 5): blocks += 1
        if blocks >= 6: hours += 1; blocks = 0
        return hours * c['price_overtime'] + blocks * c.get('price_10min', 2.0)

    def calc_fixed_total(self, minutes, limit_min):
        c = self.config
        base_price = 0
        if limit_min == 60:
            base_price = c['price_fixed_60']
        elif limit_min == 120:
            base_price = c['price_fixed_120']
        elif limit_min == 180:
            base_price = c['price_fixed_180']
        else:
            base_price = self.calc_pay_later_cost(limit_min)

        over = max(0, minutes - limit_min)
        over_price = self.calc_overtime_cost(over)
        return base_price + over_price

    # ==========================
    # --- 暂停与修改模式 ---
    # ==========================
    def toggle_pause(self, gid):
        data = self.guests[gid]
        if data.get('is_suspended', False):
            return

        now = datetime.now()
        if data.get('is_paused', False):
            start = data['pause_start_ts']
            duration = int((now - start).total_seconds())
            data['total_pause_sec'] += duration
            data['is_paused'] = False

            start_str = start.strftime("%H:%M")
            end_str = now.strftime("%H:%M")
            dur_str = fmt_duration_str(duration)
            log = f"{len(data['pause_logs']) + 1}. {start_str}-{end_str} ({dur_str})"
            data['pause_logs'].append(log)

            data['widgets']['btn_pause'].config(text="⏸ 暂停", bg="#f39c12")
            data['widgets']['lbl_time'].config(fg="#2c3e50")
        else:
            data['is_paused'] = True
            data['pause_start_ts'] = now
            data['widgets']['btn_pause'].config(text="▶ 继续", bg="#27ae60")

        self.save_to_disk()
        self.refresh_ui_list()

    def toggle_suspend(self, gid):
        data = self.guests[gid]
        now = datetime.now()

        if data.get('is_suspended', False):
            data['is_suspended'] = False
            susp_duration = (now - data['suspend_start_ts']).total_seconds()
            data['total_pause_sec'] += int(susp_duration)

            start_str = data['suspend_start_ts'].strftime("%H:%M")
            end_str = now.strftime("%H:%M")
            dur_str = fmt_duration_str(susp_duration)
            log = f"{len(data['pause_logs']) + 1}. 挂账等候 {start_str}-{end_str} ({dur_str})"
            data['pause_logs'].append(log)

            data['widgets']['btn_suspend'].config(text="挂账", bg="#8e44ad")
            data['widgets']['btn_pause'].config(state=tk.NORMAL)
            data['widgets']['lbl_time'].config(fg="#2c3e50")

            self.save_to_disk()
            self.refresh_ui_list()
        else:
            bill = self.calculate_single_bill(gid, now)

            win = tk.Toplevel(self.root)
            win.title("确认挂账")
            win.geometry("380x380")
            win.grab_set()

            tk.Label(win, text=f"顾客 #{gid} 挂账锁定", font=("微软雅黑", 14, "bold")).pack(pady=10)

            f_info = tk.Frame(win, bg="#f9f9f9", padx=10, pady=10)
            f_info.pack(fill="x", padx=20, pady=5)

            def row(k, v, color="black"):
                f = tk.Frame(f_info, bg="#f9f9f9")
                f.pack(fill="x", pady=2)
                tk.Label(f, text=k, bg="#f9f9f9", font=("微软雅黑", 10)).pack(side="left")
                tk.Label(f, text=v, bg="#f9f9f9", fg=color, font=("微软雅黑", 10, "bold")).pack(side="right")

            row("总时长:", bill['total_dur_str'])
            row("暂停时长:", bill['pause_dur_str'], "#e67e22" if bill['pause_str'] != "无" else "black")
            row("计费时长:", bill['play_dur_str'], "#2ecc71")

            tk.Label(win, text="请确认挂账待付金额:", font=("微软雅黑", 11)).pack(pady=(15, 5))

            var_amount = tk.DoubleVar(value=round(bill['total'], 2))
            e_amount = tk.Entry(win, textvariable=var_amount, font=("Arial", 22, "bold"), fg="#8e44ad",
                                justify="center", bg="#f4ecf7", width=10)
            e_amount.pack(pady=5)

            def confirm():
                try:
                    locked_cost = round(var_amount.get(), 2)
                except:
                    messagebox.showerror("错误", "金额无效")
                    return

                if data.get('is_paused', False):
                    self.toggle_pause(gid)

                data['is_suspended'] = True
                data['suspend_start_ts'] = now
                data['suspend_locked_cost'] = locked_cost

                data['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
                data['widgets']['btn_pause'].config(state=tk.DISABLED)

                self.save_to_disk()
                self.refresh_ui_list()
                win.destroy()

            tk.Button(win, text="确认挂账", bg="#8e44ad", fg="white", font=("微软雅黑", 12, "bold"), width=15,
                      command=confirm).pack(pady=10)

    def change_guest_mode(self, gid):
        data = self.guests[gid]
        dialog = tk.Toplevel(self.root)
        dialog.title(f"修改 #{gid} 计费模式")
        dialog.geometry("400x420")
        dialog.grab_set()

        tk.Label(dialog, text=f"当前手机: {data['phone']}", font=("微软雅黑", 12, "bold")).pack(pady=10)

        mode_var = tk.StringVar(value=data['mode'])
        c = self.config

        tk.Radiobutton(dialog, text=f"🕒 先玩后付", variable=mode_var, value="pay_later", font=("微软雅黑", 11)).pack(
            anchor="w", padx=80)
        tk.Radiobutton(dialog, text=f"♾️ 全天畅玩", variable=mode_var, value="unlimited", font=("微软雅黑", 11)).pack(
            anchor="w", padx=80)
        tk.Radiobutton(dialog, text=f"🎨 单板不限时", variable=mode_var, value="single_board",
                       font=("微软雅黑", 11)).pack(anchor="w", padx=80)
        tk.Radiobutton(dialog, text="🎫 团购/定额", variable=mode_var, value="fixed", font=("微软雅黑", 11)).pack(
            anchor="w", padx=80)

        f_min = tk.Frame(dialog)
        f_min.pack(pady=10)
        tk.Label(f_min, text="定额时长(分):").pack(side="left")
        min_entry = tk.Entry(f_min, width=6)
        if data['mode'] == 'fixed':
            min_entry.insert(0, str(data['limit_min']))
        else:
            min_entry.insert(0, "60")
        min_entry.pack(side="left", padx=5)

        min_entry.bind("<Button-1>", lambda e: mode_var.set("fixed"))

        frame_btns = tk.Frame(dialog)
        frame_btns.pack(pady=5)
        tk.Label(frame_btns, text="快捷:").pack(side="left")

        def set_m(v):
            min_entry.delete(0, "end");
            min_entry.insert(0, str(v));
            mode_var.set("fixed")

        for v in [60, 120, 180]:
            tk.Button(frame_btns, text=f"{v // 60}h", command=lambda x=v: set_m(x), bg="white").pack(side="left",
                                                                                                     padx=2)

        def confirm():
            new_m = mode_var.get()
            new_l = 0
            if new_m == "fixed":
                try:
                    new_l = int(min_entry.get())
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的定额时长(分钟)！")
                    return

            old_m = data['mode']
            old_l = data['limit_min']

            if new_m == old_m and (new_m != "fixed" or new_l == old_l):
                dialog.destroy()
                return

            m_map = {"pay_later": "先玩后付", "fixed": "定额/团购", "unlimited": "全天畅玩", "single_board": "单板不限"}
            m_bg = {"pay_later": "#3498db", "fixed": "#f39c12", "unlimited": "#9b59b6", "single_board": "#8e44ad"}

            new_m_txt = m_map.get(new_m, new_m)
            if new_m == 'fixed':
                new_m_txt += f"({new_l}分)"

            now_str = datetime.now().strftime("%H:%M")
            change_log = f"[{now_str} 改为{new_m_txt}]"
            data['remark'] = (data.get('remark', '') + " " + change_log).strip()

            data['mode'] = new_m
            data['limit_min'] = new_l

            if data.get('is_suspended', False):
                bill = self.calculate_single_bill(gid, data['suspend_start_ts'])
                data['suspend_locked_cost'] = round(bill['total'], 2)

            lbl_mode = data['widgets']['lbl_mode']
            lbl_mode.config(text=m_map.get(new_m, new_m), bg=m_bg.get(new_m, "#999"))

            display_remark = data['remark'].replace("\n", " ")
            if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
            remark_txt = f"备注: {display_remark}" if display_remark else "备注: (点击添加)"
            data['widgets']['lbl_remark'].config(text=remark_txt)

            self.save_to_disk()
            self.refresh_ui_list()
            dialog.destroy()

        tk.Button(dialog, text="确认修改", bg="#27ae60", fg="white", font=("微软雅黑", 12), width=15,
                  command=confirm).pack(pady=20)

    # ==========================
    # --- 结账逻辑 ---
    # ==========================
    def calculate_single_bill(self, gid, end_time):
        data = self.guests[gid]
        current_pause = 0

        if data.get('is_paused', False):
            current_pause = int((end_time - data['pause_start_ts']).total_seconds())
        elif data.get('is_suspended', False):
            current_pause = int((end_time - data['suspend_start_ts']).total_seconds())

        total_pause_sec = data.get('total_pause_sec', 0) + current_pause
        raw_duration_sec = (end_time - data['start_time']).total_seconds()
        effective_duration_sec = raw_duration_sec - total_pause_sec
        minutes = int(effective_duration_sec / 60)

        c = self.config
        total_price = 0.0
        fixed_time_str = "--"
        mode_info = ""
        over_info = "正常"

        if data.get('is_suspended', False):
            total_price = data.get('suspend_locked_cost', 0.0)
            if data['mode'] == "pay_later":
                mode_info = "先玩后付"
                over_info = f"净时长 {fmt_min(minutes)}"
            elif data['mode'] == "unlimited":
                mode_info = "全天畅玩"
                over_info = "不限时"
            elif data['mode'] == "single_board":
                mode_info = "单板不限"
                over_info = "不限时"
            elif data['mode'] == "fixed":
                mode_info = "定额/团购"
                lm = data['limit_min']
                fixed_time_str = fmt_min(lm)
                over = max(0, minutes - lm)
                if over > c['buffer_min']:
                    over_info = f"超时 {fmt_min(over)}"
                else:
                    over_info = "未超时"
        else:
            if data['mode'] == "pay_later":
                mode_info = "先玩后付"
                total_price = self.calc_pay_later_cost(minutes)
                over_info = f"净时长 {fmt_min(minutes)}"
            elif data['mode'] == "unlimited":
                mode_info = "全天畅玩"
                total_price = c['price_unlimited']
                over_info = "不限时"
            elif data['mode'] == "single_board":
                mode_info = "单板不限"
                total_price = c.get('price_single_board', 39.9)
                over_info = "不限时"
            elif data['mode'] == "fixed":
                mode_info = "定额/团购"
                lm = data['limit_min']
                fixed_time_str = fmt_min(lm)
                total_price = self.calc_fixed_total(minutes, lm)
                over = max(0, minutes - lm)
                if over > c['buffer_min']:
                    over_info = f"超时 {fmt_min(over)}"
                else:
                    over_info = "未超时"

        total_price = round(total_price, 2)

        pause_log_copy = list(data.get('pause_logs', []))
        if data.get('is_paused', False):
            dur_str = fmt_duration_str(current_pause)
            pause_log_copy.append(f"结账恢复 ({dur_str})")
        elif data.get('is_suspended', False):
            dur_str = fmt_duration_str(current_pause)
            pause_log_copy.append(f"挂账等待 ({dur_str})")

        pause_str = "; ".join(pause_log_copy) if pause_log_copy else "无"
        prepaid = round(data.get('prepaid', 0.0), 2)

        return {
            "gid": gid, "data": data, "end_time": end_time,
            "minutes": minutes, "total_dur_str": fmt_duration_str(raw_duration_sec),
            "play_dur_str": fmt_duration_str(effective_duration_sec),
            "pause_dur_str": fmt_duration_str(total_pause_sec),
            "total": total_price, "prepaid": prepaid,
            "need": round(max(0, total_price - prepaid), 2),
            "fixed_str": fixed_time_str,
            "mode_info": mode_info, "over_info": over_info, "pause_str": pause_str
        }

    def checkout(self, gid, is_auto=False):
        current_group_id = self.guests[gid].get('group_id')
        group_members = []
        if current_group_id:
            group_members = [k for k, v in self.guests.items() if v.get('group_id') == current_group_id]

        target_gids = [gid]
        if not is_auto and len(group_members) > 1:
            choice = messagebox.askyesnocancel("同组结算", f"该组还有 {len(group_members)} 人，是否合并进入团队收银台？")
            if choice is None: return
            if choice: target_gids = group_members

        bills = []
        sum_total_price = 0
        end_time = datetime.now()

        for tid in target_gids:
            bill = self.calculate_single_bill(tid, end_time)
            bills.append(bill)
            sum_total_price += bill['total']

        if is_auto:
            for b in bills:
                rmk = f"{b['data'].get('remark', '')} [强制]"
                self.write_history(b['gid'], b['data']['phone'], b['data']['mode'], b['data']['start_time'],
                                   b['end_time'],
                                   b['total_dur_str'], b['play_dur_str'], b['total'], rmk,
                                   b['fixed_str'], b['pause_str'])
                data = self.guests[b['gid']]
                data['widgets']['container'].destroy()
                del self.guests[b['gid']]
            self.save_to_disk()
            self.refresh_ui_list()
            return

        if len(bills) == 1:
            self.show_single_checkout_ui(bills[0])
        else:
            self.show_group_checkout_ui(bills, sum_total_price)

    def show_single_checkout_ui(self, b):
        win = tk.Toplevel(self.root)
        win.title("结账/挂账详情")
        win.geometry("480x680")
        win.grab_set()
        tk.Label(win, text=f"顾客: {b['data']['phone']}", font=("微软雅黑", 18, "bold")).pack(pady=15)

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

        tk.Frame(f_detail, height=2, bg="#ccc").pack(fill="x", pady=8)
        if b['prepaid'] > 0:
            row("预付金额:", f"{b['prepaid']:.2f} 元", "#3498db")
            row("还需补交:", f"{b['need']:.2f} 元", "#e74c3c")

        tk.Label(win, text="订单备注:", font=("微软雅黑", 10)).pack(pady=(10, 0))
        entry_remark = tk.Text(win, font=("微软雅黑", 10), height=3, width=30, bd=1, relief="solid")
        entry_remark.pack(fill="x", padx=30, pady=5)
        entry_remark.insert("1.0", b['data'].get('remark', ''))

        f_money = tk.Frame(win)
        f_money.pack(fill="x", padx=20, pady=10)

        tk.Label(f_money, text="结算总金额:", font=("微软雅黑", 14, "bold")).pack()
        var_total = tk.DoubleVar(value=round(b['total'], 2))
        e_total = tk.Entry(f_money, textvariable=var_total, font=("Arial", 24, "bold"), fg="#2980b9", justify="center",
                           bg="#fff3cd")
        e_total.pack(pady=5)

        def suspend_action():
            try:
                final_total = round(var_total.get(), 2)
            except:
                messagebox.showerror("错误", "金额无效");
                return

            data = self.guests[b['gid']]
            now = datetime.now()

            if not data.get('is_suspended', False):
                if data.get('is_paused', False):
                    self.toggle_pause(b['gid'])
                data['is_suspended'] = True
                data['suspend_start_ts'] = now

            data['suspend_locked_cost'] = final_total

            data['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
            data['widgets']['btn_pause'].config(state=tk.DISABLED)

            final_rmk = entry_remark.get("1.0", "end-1c")
            data['remark'] = final_rmk
            display_remark = final_rmk.strip().replace("\n", " ")
            if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
            remark_txt = f"备注: {display_remark}" if display_remark else "备注: (点击添加)"
            data['widgets']['lbl_remark'].config(text=remark_txt)

            self.save_to_disk()
            self.refresh_ui_list()
            win.destroy()
            messagebox.showinfo("挂账完成", f"顾客 #{b['gid']} 已成功挂账！\n系统已冻结金额: {final_total}元")

        def confirm():
            try:
                final_total = round(var_total.get(), 2)
            except:
                messagebox.showerror("错误", "金额无效");
                return

            final_rmk = entry_remark.get("1.0", "end-1c")

            self.write_history(b['gid'], b['data']['phone'], b['data']['mode'], b['data']['start_time'], b['end_time'],
                               b['total_dur_str'], b['play_dur_str'], final_total, final_rmk,
                               b['fixed_str'], b['pause_str'])

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
        win.geometry("950x700")
        win.grab_set()

        def _close():
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close)

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

            chk = tk.Checkbutton(scroll_f, text=f" 手机号: {b['data']['phone']}",
                                 variable=var_check, bg="white", font=("微软雅黑", 11, "bold"),
                                 command=update_total)
            card = tk.LabelFrame(scroll_f, labelwidget=chk, bg="white", padx=10, pady=8)
            card.pack(fill="x", padx=10, pady=5)

            f_r1 = tk.Frame(card, bg="white")
            f_r1.pack(fill="x", pady=2)
            tk.Label(f_r1, text=f"模式: {b['mode_info']}", width=20, anchor="w", bg="white").pack(side="left")
            if b['fixed_str'] != "--":
                tk.Label(f_r1, text=f"定额时长: {b['fixed_str']}", width=20, anchor="w", bg="white").pack(side="left")
            status_color = "red" if "超时" in b['over_info'] else "green"
            tk.Label(f_r1, text=f"状态: {b['over_info']}", width=20, anchor="w", bg="white", fg=status_color,
                     font=("微软雅黑", 9, "bold")).pack(side="left")

            f_r2 = tk.Frame(card, bg="white")
            f_r2.pack(fill="x", pady=2)
            tk.Label(f_r2, text=f"总时长: {b['total_dur_str']}", width=20, anchor="w", bg="white").pack(side="left")
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
            tk.Label(f_r4, text="本单总价:", bg="white", font=("微软雅黑", 10, "bold")).pack(side="left")
            v_price = tk.DoubleVar(value=round(b['total'], 2))
            e_price = tk.Entry(f_r4, textvariable=v_price, width=12, bg="#fff3cd", fg="#e74c3c",
                               font=("Arial", 12, "bold"), justify="center")
            e_price.pack(side="left", padx=5)

            ui_data_list.append({'var_price': v_price, 'entry_rmk': e_rmk, 'bill': b, 'var_check': var_check})

        def _bind_to_mousewheel(event):
            try:
                if scroll_f.winfo_height() > cv.winfo_height():
                    cv.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass

        def _recursive_bind(widget):
            widget.bind("<MouseWheel>", _bind_to_mousewheel)
            for child in widget.winfo_children():
                _recursive_bind(child)

        _recursive_bind(scroll_f)
        cv.bind("<MouseWheel>", _bind_to_mousewheel)
        win.bind("<MouseWheel>", _bind_to_mousewheel)

        f_bottom = tk.Frame(win, bg="#ecf0f1", pady=15)
        f_bottom.pack(fill="x")

        is_all_selected = tk.BooleanVar(value=True)

        def toggle_select_all():
            new_state = not is_all_selected.get()
            is_all_selected.set(new_state)
            for item in ui_data_list:
                item['var_check'].set(new_state)
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
            if not selected_items:
                messagebox.showwarning("提示", "未勾选任何顾客！")
                return

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
                        if data.get('is_paused', False):
                            self.toggle_pause(gid)
                        data['is_suspended'] = True
                        data['suspend_start_ts'] = now

                    data['suspend_locked_cost'] = f_price
                    data['remark'] = f_rmk

                    data['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
                    data['widgets']['btn_pause'].config(state=tk.DISABLED)

                    display_remark = f_rmk.strip().replace("\n", " ")
                    if len(display_remark) > 15: display_remark = display_remark[:15] + "..."
                    remark_txt = f"备注: {display_remark}" if display_remark else "备注: (点击添加)"
                    data['widgets']['lbl_remark'].config(text=remark_txt)

                self.save_to_disk()
                self.refresh_ui_list()
                _close()
                messagebox.showinfo("分组挂账完成",
                                    f"已勾选的 {len(selected_items)} 人成功挂账！\n系统已冻结总金额: {final_chk}元")
            except Exception as e:
                messagebox.showerror("错误", f"数据错误: {e}")

        def confirm():
            selected_items = [item for item in ui_data_list if item['var_check'].get()]
            if not selected_items:
                messagebox.showwarning("提示", "未勾选任何顾客！")
                return

            try:
                final_chk = round(var_total_all.get(), 2)
                for item in selected_items:
                    b = item['bill']
                    f_price = round(item['var_price'].get(), 2)
                    f_rmk = item['entry_rmk'].get()

                    self.write_history(b['gid'], b['data']['phone'], b['data']['mode'], b['data']['start_time'],
                                       b['end_time'], b['total_dur_str'], b['play_dur_str'], f_price, f_rmk,
                                       b['fixed_str'], b['pause_str'])

                    self.guests[b['gid']]['widgets']['container'].destroy()
                    del self.guests[b['gid']]

                self.save_to_disk()
                self.refresh_ui_list()
                _close()
                messagebox.showinfo("完成", f"已勾选的 {len(selected_items)} 人结账成功！\n总入账: {final_chk}元")
            except Exception as e:
                messagebox.showerror("错误", f"数据错误: {e}")

        f_btns = tk.Frame(f_bottom, bg="#ecf0f1")
        f_btns.pack(side="right", padx=10)

        tk.Button(f_btns, text="选中项挂账", bg="#8e44ad", fg="white", font=("微软雅黑", 14, "bold"), width=10,
                  command=suspend_group).pack(side="left", padx=10)
        tk.Button(f_btns, text="选中项结账", bg="#27ae60", fg="white", font=("微软雅黑", 14, "bold"), width=10,
                  command=confirm).pack(side="left", padx=10)

    # ==========================
    # --- 通用功能 ---
    # ==========================
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
        txt = (f"基础: {c['price_base']}元/{fmt_min(c['time_base'])} | "
               f"超时: {c['price_overtime']}元/时, {c.get('price_10min', 2)}元/10分 | "
               f"定额: {c['price_fixed_60']}元/1h...")
        self.rule_label.config(text=txt)

    def open_settings_dialog(self):
        pwd = simpledialog.askstring("验证", "输入管理员密码:", show="*")

        if pwd is None: return
        if pwd != self.config["admin_pwd"]:
            messagebox.showerror("错误", "密码错误")
            return

        win = tk.Toplevel(self.root)
        win.title("价格设置")
        win.geometry("500x750")
        win.grab_set()
        fields = [
            ("【基础】先玩后付 价格", "price_base"), ("【基础】先玩后付 时长", "time_base"),
            ("【通用】超时费率 (元/小时)", "price_overtime"),
            ("【通用】阶梯费率 (元/10分)", "price_10min"),
            ("【通用】阶梯缓冲 (分)", "buffer_10min"),
            ("【通用】总免单缓冲 (分)", "buffer_min"),
            ("【无限】全天畅玩一口价", "price_unlimited"),
            ("【无限】单板不限时一口价", "price_single_board"),
            ("【定额】1小时 价格", "price_fixed_60"), ("【定额】2小时 价格", "price_fixed_120"),
            ("【定额】3小时 价格", "price_fixed_180"),
            ("【系统】管理员密码", "admin_pwd")
        ]
        entries = {}
        for txt, k in fields:
            f = tk.Frame(win)
            f.pack(fill="x", padx=40, pady=5)
            tk.Label(f, text=txt).pack(side="left")
            e = tk.Entry(f, width=10)
            e.insert(0, str(self.config.get(k, DEFAULT_CONFIG.get(k, 0))))
            e.pack(side="right")
            entries[k] = e

        def save():
            try:
                for k, e in entries.items():
                    val = e.get()
                    if k == "admin_pwd":
                        self.config[k] = val
                    elif k in ["time_base", "buffer_min", "buffer_10min"]:
                        self.config[k] = int(float(val))
                    else:
                        self.config[k] = float(val)
                self.save_config()
                win.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"输入格式错误：{e}")

        tk.Button(win, text="保存修改", bg="#27ae60", fg="white", command=save).pack(pady=20)

    # ==========================
    # --- 团队看板 核心逻辑 ---
    # ==========================
    def view_group_details(self, grp):
        self.active_group_filter = grp
        self.notebook.select(0)
        if self.search_var.get() != "":
            self.search_var.set("")
        else:
            self.refresh_ui_list()

    def add_to_group(self, grp):
        gids = [gid for gid, d in self.guests.items() if d.get('group_id') == grp]
        if not gids: return

        phones = [self.guests[g]['phone'] for g in gids]
        base_phone = phones[0].split('(')[0]

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

        tk.Label(dialog, text="计费模式:", font=("微软雅黑", 12)).pack(pady=(15, 5))
        mode_var = tk.StringVar(value="pay_later")
        c = self.config
        tk.Radiobutton(dialog, text=f"🕒 先玩后付", variable=mode_var, value="pay_later", font=("微软雅黑", 11)).pack(
            anchor="w", padx=60)
        tk.Radiobutton(dialog, text=f"♾️ 全天畅玩", variable=mode_var, value="unlimited", font=("微软雅黑", 11)).pack(
            anchor="w", padx=60)
        tk.Radiobutton(dialog, text=f"🎨 单板不限时", variable=mode_var, value="single_board",
                       font=("微软雅黑", 11)).pack(anchor="w", padx=60)
        tk.Radiobutton(dialog, text="🎫 团购/定额", variable=mode_var, value="fixed", font=("微软雅黑", 11)).pack(
            anchor="w", padx=60)

        frame_btns = tk.Frame(dialog)
        frame_btns.pack(pady=5)
        tk.Label(frame_btns, text="定额时长(分):").pack(side="left")
        min_entry = tk.Entry(frame_btns, width=6)
        min_entry.insert(0, "60")
        min_entry.pack(side="left", padx=5)

        def set_m(v):
            min_entry.delete(0, "end");
            min_entry.insert(0, str(v));
            mode_var.set("fixed")

        for v in [60, 120, 180]: tk.Button(frame_btns, text=f"{v // 60}h", command=lambda x=v: set_m(x),
                                           bg="white").pack(side="left", padx=2)

        def confirm():
            m = mode_var.get()
            l = 0
            count = int(spin_count.get())
            if m == "fixed":
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
                self.create_guest_ui(self.guest_counter, p_final, m, datetime.now(), l, "", False, grp, 0.0)

            self.auth.add_guest(count)
            self.save_to_disk()
            self.refresh_ui_list()
            dialog.destroy()

        tk.Button(dialog, text="确认添加", bg="#27ae60", fg="white", font=("微软雅黑", 14), width=20,
                  command=confirm).pack(pady=30)

    def create_group_card(self, grp):
        container = tk.Frame(self.scrollable_frame, bg="#bdc3c7", bd=1)
        bg_frame = tk.Frame(container, bg="#ffffff", padx=10, pady=10)
        bg_frame.pack(fill="x", padx=2, pady=2)

        col = get_group_color(grp)
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

        self.group_widgets[grp] = {
            'container': container,
            'lbl_title': lbl_title,
            'lbl_time': lbl_time,
            'lbl_count': lbl_count,
            'lbl_members': lbl_members
        }

    def render_group_cards(self):
        current_groups = {}
        for gid, d in self.guests.items():
            grp = d.get('group_id')
            if grp:
                if grp not in current_groups: current_groups[grp] = []
                current_groups[grp].append(gid)

        for grp, widget_data in list(self.group_widgets.items()):
            if grp not in current_groups:
                widget_data['container'].destroy()
                del self.group_widgets[grp]

        for grp, gids in current_groups.items():
            if grp not in self.group_widgets:
                self.create_group_card(grp)

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

    # ==========================
    # --- 核心UI刷新机制 ---
    # ==========================
    def on_tab_change(self, event):
        cur_tab = self.tabs[self.notebook.index(self.notebook.select())]
        if cur_tab == "超时监控": self.notebook.set_badge(5, False)
        if cur_tab != "全部订单":
            self.active_group_filter = None
        self.refresh_ui_list()

    def sort_list(self, key):
        self.current_sort_key = key
        self.current_sort_rev = not self.current_sort_rev
        self.refresh_ui_list()

    def refresh_ui_list(self, *args):
        cur_tab = self.tabs[self.notebook.index(self.notebook.select())]
        kw = self.search_var.get().lower()
        if kw and self.active_group_filter:
            self.active_group_filter = None

        self.render_group_cards()

        lst = []
        for gid, d in self.guests.items(): lst.append((gid, d))

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
            if data['mode'] == 'fixed':
                if (effective_min / 60) > data['limit_min']: is_ot = True

            show = False

            if self.active_group_filter:
                if data.get('group_id') == self.active_group_filter:
                    show = True
            else:
                if cur_tab == "全部订单":
                    show = True
                elif cur_tab == "先玩后付" and data['mode'] == "pay_later":
                    show = True
                elif cur_tab == "团购/定额" and data['mode'] == "fixed":
                    show = True
                elif cur_tab == "无限模式" and (data['mode'] == "unlimited" or data['mode'] == "single_board"):
                    show = True
                elif cur_tab == "超时监控" and is_ot:
                    show = True

                if kw and kw not in data['phone'].lower() and kw not in str(
                        data.get('remark', '')).lower() and kw != str(gid):
                    show = False

            if show: data['widgets']['container'].pack(fill="x", pady=4, padx=5)

    def update_timers(self):
        now = datetime.now()
        ot_cnt = 0

        if self.auth.activated:
            self.status_bar.config(text="✓ 系统就绪 - 欢迎使用timerPro智能门店管理系统", fg="#27ae60")
        else:
            rem_guests = max(0, 20 - self.auth.data['guests'])
            self.status_bar.config(text=f"【试用版】剩余体验开单名额: {rem_guests}单 | 请尽快激活商业版以免影响营业",
                                   fg="#e74c3c")

        def fmt_hhmmss(seconds):
            h, r = divmod(int(max(0, seconds)), 3600)
            m, s = divmod(r, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"

        for grp, widget_data in self.group_widgets.items():
            gids = [gid for gid, d in self.guests.items() if d.get('group_id') == grp]
            if not gids: continue

            max_active_sec = 0
            all_paused_or_suspended = True

            for gid in gids:
                d = self.guests[gid]
                if not (d.get('is_paused', False) or d.get('is_suspended', False)):
                    all_paused_or_suspended = False

                total_pause = d.get('total_pause_sec', 0)
                active_sec = (now - d['start_time']).total_seconds() - total_pause
                if d.get('is_paused', False):
                    active_sec -= (now - d['pause_start_ts']).total_seconds()
                elif d.get('is_suspended', False):
                    active_sec -= (now - d['suspend_start_ts']).total_seconds()
                max_active_sec = max(max_active_sec, max(0, int(active_sec)))

            time_text = fmt_hhmmss(max_active_sec)
            if all_paused_or_suspended:
                widget_data['lbl_time'].config(text=f"全员挂账/暂停 {time_text}", fg="#95a5a6",
                                               font=("微软雅黑", 22, "bold"))
            else:
                widget_data['lbl_time'].config(text=time_text, fg="#2c3e50", font=("Consolas", 36, "bold"))

        for gid, data in self.guests.items():
            total_pause = data.get('total_pause_sec', 0)

            active_sec = (now - data['start_time']).total_seconds() - total_pause
            if data.get('is_paused', False):
                active_sec -= (now - data['pause_start_ts']).total_seconds()
            elif data.get('is_suspended', False):
                active_sec -= (now - data['suspend_start_ts']).total_seconds()

            active_sec = max(0, int(active_sec))
            frozen_time_str = fmt_hhmmss(active_sec)

            if data.get('is_suspended', False):
                locked_cost = data.get('suspend_locked_cost', 0.0)
                time_text = f"已挂账 {frozen_time_str} (待付: ¥{locked_cost:.2f})"
                data['widgets']['lbl_time'].config(text=time_text, fg="#8e44ad", font=("微软雅黑", 16, "bold"))
                data['widgets']['bar'].update_bar(1.0, "#bdc3c7")
                continue

            if data.get('is_paused', False):
                current_pause_dur = (now - data['pause_start_ts']).total_seconds()
                total_pause_display = total_pause + current_pause_dur
                dur_str = fmt_duration_str(total_pause_display)
                time_text = f"已暂停 {frozen_time_str} (已停 {dur_str})"
                data['widgets']['lbl_time'].config(text=time_text, fg="#95a5a6", font=("微软雅黑", 16, "bold"))

                bar_pct = 0
                if data['mode'] == 'fixed':
                    limit = data['limit_min']
                    if limit > 0: bar_pct = min(1.0, (active_sec / 60) / limit)
                else:
                    if data['mode'] in ["unlimited", "single_board"]: bar_pct = 1.0
                data['widgets']['bar'].update_bar(bar_pct, "#ecf0f1")
                continue

            time_text = fmt_hhmmss(active_sec)
            data['widgets']['lbl_time'].config(text=time_text, font=("Consolas", 26, "bold"))

            tm = int(active_sec / 60)
            bar_pct = 0
            bar_color = "#ecf0f1"

            if data['mode'] == "fixed":
                limit = data['limit_min']
                remain_sec = limit * 60 - active_sec
                if limit > 0: bar_pct = min(1.0, tm / limit)

                if remain_sec < 0:
                    over_sec = int(abs(remain_sec))
                    time_text = f"超时 {fmt_hhmmss(over_sec)}"
                    data['widgets']['lbl_time'].config(text=time_text, fg="#c0392b", font=("微软雅黑", 22, "bold"))
                    bar_color = "#e74c3c"
                    ot_cnt += 1
                else:
                    time_text = fmt_hhmmss(remain_sec)
                    data['widgets']['lbl_time'].config(text=time_text, fg="#2c3e50")
                    if remain_sec <= self.config['buffer_min'] * 60:
                        bar_color = "#f39c12"
                    else:
                        bar_color = "#2ecc71"
            else:
                data['widgets']['lbl_time'].config(fg="#2c3e50")
                if data['mode'] in ["unlimited", "single_board"]:
                    bar_color = "#9b59b6"
                    bar_pct = 1.0

            data['widgets']['lbl_time'].config(text=time_text)
            data['widgets']['bar'].update_bar(bar_pct, bar_color)

        if ot_cnt > 0 and self.tabs[self.notebook.index(self.notebook.select())] != "超时监控":
            self.notebook.set_badge(5, True)
        else:
            self.notebook.set_badge(5, False)
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

    def open_add_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("新增客人")
        dialog.geometry("500x600")
        dialog.grab_set()
        tk.Label(dialog, text="手机号 / 备注:", font=("微软雅黑", 14)).pack(pady=(15, 5))
        phone_entry = tk.Entry(dialog, font=("微软雅黑", 16), width=20)
        phone_entry.pack(pady=5)
        phone_entry.focus_set()

        f_cnt = tk.Frame(dialog)
        f_cnt.pack(pady=5)
        tk.Label(f_cnt, text="人数(批量):", font=("微软雅黑", 12)).pack(side="left")
        spin_count = tk.Spinbox(f_cnt, from_=1, to=50, width=5, font=("微软雅黑", 12))
        spin_count.pack(side="left", padx=5)

        tk.Label(dialog, text="初始备注 (可选):", font=("微软雅黑", 12)).pack(pady=(10, 0))
        remark_entry = tk.Text(dialog, font=("微软雅黑", 10), height=3, width=35, bd=1, relief="solid")
        remark_entry.pack(pady=5, padx=20)

        tk.Label(dialog, text="计费模式:", font=("微软雅黑", 12)).pack(pady=(15, 5))
        mode_var = tk.StringVar(value="pay_later")
        c = self.config
        tk.Radiobutton(dialog, text=f"🕒 先玩后付 ({c['price_base']}元/{fmt_min(c['time_base'])})", variable=mode_var,
                       value="pay_later", font=("微软雅黑", 11)).pack(anchor="w", padx=60)
        tk.Radiobutton(dialog, text=f"♾️ 全天畅玩 ({c['price_unlimited']}元)", variable=mode_var, value="unlimited",
                       font=("微软雅黑", 11)).pack(anchor="w", padx=60)
        tk.Radiobutton(dialog, text=f"🎨 单板不限时 ({c.get('price_single_board', 39.9)}元)", variable=mode_var,
                       value="single_board", font=("微软雅黑", 11)).pack(anchor="w", padx=60)
        tk.Radiobutton(dialog, text="🎫 团购/定额 (倒计时)", variable=mode_var, value="fixed",
                       font=("微软雅黑", 11)).pack(anchor="w", padx=60)
        frame_btns = tk.Frame(dialog)
        frame_btns.pack(pady=5)
        tk.Label(frame_btns, text="时长(分):").pack(side="left")
        min_entry = tk.Entry(frame_btns, width=6)
        min_entry.insert(0, "60")
        min_entry.pack(side="left", padx=5)

        def set_m(v):
            min_entry.delete(0, "end");
            min_entry.insert(0, str(v));
            mode_var.set("fixed")

        for v in [60, 120, 180]: tk.Button(frame_btns, text=f"{v // 60}h", command=lambda x=v: set_m(x),
                                           bg="white").pack(side="left")

        def confirm():
            p = phone_entry.get()
            m = mode_var.get()
            l = 0
            rmk = remark_entry.get("1.0", "end-1c")
            count = int(spin_count.get())
            if not p: return
            if m == "fixed":
                try:
                    l = int(min_entry.get())
                except:
                    return

            if not self.auth.activated and (self.auth.data['guests'] + count > 20):
                self.show_activation_window("试用版最多仅支持开 20 单，您的体验名额已用尽！\n请购买正版授权以继续使用。",
                                            force=True)
                dialog.destroy()
                return

            group_id = int(time.time()) if count > 1 else None
            for i in range(count):
                self.guest_counter += 1
                p_final = f"{p}({i + 1})" if count > 1 else p
                self.create_guest_ui(self.guest_counter, p_final, m, datetime.now(), l, rmk, False, group_id, 0.0)

            self.auth.add_guest(count)
            self.save_to_disk()
            dialog.destroy()

        tk.Button(dialog, text="确定下单", bg="#27ae60", fg="white", font=("微软雅黑", 14), width=20,
                  command=confirm).pack(pady=30)

    def create_guest_ui(self, gid, phone, mode, start_time, limit_min, remark="", is_paused=False, group_id=None,
                        prepaid=0.0):
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

        info_frame = tk.Frame(bg_frame, bg="#ffffff", width=220, height=80)
        info_frame.pack_propagate(False)
        info_frame.pack(side="right", padx=10)
        inner_frame = tk.Frame(info_frame, bg="#ffffff")
        inner_frame.place(relx=1.0, rely=0.5, anchor="e")

        tk.Label(inner_frame, text=f"开始: {start_time.strftime('%H:%M')}", font=("Arial", 9), fg="#95a5a6",
                 bg="#ffffff", anchor="e").pack(fill="x")
        if mode == "fixed": tk.Label(inner_frame, text=f"定额: {fmt_min(limit_min)}", font=("微软雅黑", 9),
                                     fg="#f39c12", bg="#ffffff", anchor="e").pack(fill="x")

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
        tk.Label(left_frame, text=phone, font=("微软雅黑", 14, "bold"), fg="#2c3e50", bg="#ffffff", width=12,
                 anchor="w").pack(side="left", padx=5)

        m_map = {"pay_later": "先玩后付", "fixed": "定额/团购", "unlimited": "全天畅玩", "single_board": "单板不限"}
        m_txt = m_map.get(mode, mode)
        m_bg = {"pay_later": "#3498db", "fixed": "#f39c12", "unlimited": "#9b59b6", "single_board": "#8e44ad"}.get(mode,
                                                                                                                   "#999")

        lbl_mode = tk.Label(left_frame, text=m_txt, font=("微软雅黑", 9), fg="white", bg=m_bg, width=8, pady=2,
                            cursor="hand2")
        lbl_mode.pack(side="left", padx=5)
        lbl_mode.bind("<Button-1>", lambda e, g=gid: self.change_guest_mode(g))

        lbl_time = tk.Label(center_frame, text="00:00:00", font=("Consolas", 26, "bold"), fg="#2c3e50", bg="#ffffff")
        lbl_time.pack(anchor="center")

        bar = CardProgressBar(container, height=6)
        bar.pack(side="bottom", fill="x")

        self.guests[gid] = {'phone': phone, 'mode': mode, 'start_time': start_time, 'limit_min': limit_min,
                            'remark': remark,
                            'is_paused': is_paused, 'total_pause_sec': 0, 'pause_start_ts': None, 'pause_logs': [],
                            'is_suspended': False, 'suspend_start_ts': None, 'suspend_locked_cost': 0.0,
                            'group_id': group_id, 'prepaid': prepaid,
                            'widgets': {'container': container, 'bg_frame': bg_frame, 'lbl_time': lbl_time, 'bar': bar,
                                        'lbl_remark': lbl_remark, 'btn_pause': btn_pause, 'lbl_mode': lbl_mode,
                                        'btn_suspend': btn_suspend}}
        self.refresh_ui_list()

    def write_history(self, gid, phone, mode, start, end, total_dur, play_dur, cost, remark="", paid_val=0, need_pay=0,
                      fixed_str="--", pause_info=""):
        f_ex = os.path.exists(HISTORY_FILE)
        with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if not f_ex: w.writerow(
                ["开始", "结束", "序号", "手机", "模式", "总时长(含暂停)", "实际时长(纯玩)", "总金额", "备注",
                 "已付(套餐)", "补交(需付)", "定额时长", "暂停详情"])
            m_cn = {"pay_later": "先玩后付", "fixed": "定额", "unlimited": "全天畅玩", "single_board": "单板不限"}.get(
                mode, mode)
            clean_remark = remark.replace("\n", " ").replace("\r", "")
            w.writerow([
                start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M"), gid, phone, m_cn,
                total_dur, play_dur,
                round(cost, 2), clean_remark, fixed_str, pause_info
            ])

    def check_history_permission(self):
        if simpledialog.askstring("验证", "输入密码:", show="*") == self.config["admin_pwd"]: self.open_history_window()

    def open_history_window(self):
        win = tk.Toplevel(self.root)
        win.title("历史账单分析")
        win.geometry("1200x700")
        filter_frame = tk.LabelFrame(win, text="筛选", pady=5, padx=5)
        filter_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(filter_frame, text="关键词:").pack(side="left")
        search_var = tk.StringVar()
        tk.Entry(filter_frame, textvariable=search_var).pack(side="left", padx=5)
        tk.Button(filter_frame, text="🗑️ 批量删除选中", bg="#e74c3c", fg="white",
                  command=lambda: self.delete_history_items(tree)).pack(side="right")
        stats_frame = tk.Frame(win, bg="#ecf0f1", pady=10)
        stats_frame.pack(fill="x", padx=10)
        lbl_count = tk.Label(stats_frame, text="客流: 0", font=("微软雅黑", 12), bg="#ecf0f1")
        lbl_count.pack(side="left", padx=20)
        lbl_income = tk.Label(stats_frame, text="营收: 0", font=("微软雅黑", 14, "bold"), fg="#e67e22", bg="#ecf0f1")
        lbl_income.pack(side="right", padx=20)
        cols = ("start", "end", "id", "phone", "mode", "tot_dur", "play_dur", "cost", "remark", "fixed", "pause")
        tree = ttk.Treeview(win, columns=cols, show='headings', selectmode='extended')
        headers = ["开始", "结束", "序号", "手机", "模式", "总时长", "实玩时长", "总金额", "备注", "定额", "暂停"]
        for c, h in zip(cols, headers): tree.heading(c, text=h, command=lambda _c=c: self.treeview_sort_column(tree, _c,
                                                                                                               False)); tree.column(
            c, width=80 if c not in ["start", "end", "pause"] else 120)
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
            tm = 0
            for i in tree.get_children(): tree.delete(i)
            filtered = []
            total_rev = 0
            total_cash = 0
            for row in reversed(all_rows):
                if kw in " ".join(row).lower():
                    if len(row) < 11: row += ["--"] * (11 - len(row))
                    if len(row) >= 13:
                        display_row = row[:9] + [row[11], row[12]]
                    else:
                        display_row = row[:11]
                    tree.insert("", "end", values=display_row)
                    filtered.append(display_row)
                    try:
                        total_rev += float(display_row[7])
                    except:
                        pass
            lbl_count.config(text=f"客流: {len(filtered)}")
            lbl_income.config(text=f"历史总价值: {total_rev:.2f}元")

        search_var.trace("w", filter_data)
        load_data()

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
        if simpledialog.askstring("警报", "输入密码强制清空:", show="*") == self.config["admin_pwd"]:
            for gid in list(self.guests.keys()): self.checkout(gid, True)

    def on_close_app(self):
        if simpledialog.askstring("退出", "输入密码退出:", show="*") == self.config["admin_pwd"]:
            self.save_to_disk()
            self.root.destroy()

    def save_to_disk(self):
        s = {}
        for gid, d in self.guests.items():
            s[gid] = {
                'phone': d['phone'], 'mode': d['mode'],
                'start_time': d['start_time'].strftime("%Y-%m-%d %H:%M:%S"),
                'limit_min': d['limit_min'], 'remark': d.get('remark', ''),

                'is_paused': d.get('is_paused', False),
                'total_pause_sec': d.get('total_pause_sec', 0),
                'pause_logs': d.get('pause_logs', []),
                'pause_start_ts': d.get('pause_start_ts').strftime("%Y-%m-%d %H:%M:%S") if d.get(
                    'pause_start_ts') else None,

                'is_suspended': d.get('is_suspended', False),
                'suspend_locked_cost': d.get('suspend_locked_cost', 0.0),
                'suspend_start_ts': d.get('suspend_start_ts').strftime("%Y-%m-%d %H:%M:%S") if d.get(
                    'suspend_start_ts') else None,

                'group_id': d.get('group_id'), 'prepaid': d.get('prepaid', 0.0),
                'fixed_end_time': d.get('fixed_end_time').strftime("%Y-%m-%d %H:%M:%S") if d.get(
                    'fixed_end_time') else None,
                'status': d.get('status', 0)
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
                                         v.get('remark', ''), group_id=v.get('group_id'), prepaid=v.get('prepaid', 0.0))
                    g = self.guests[int(gid)]

                    g['is_paused'] = v.get('is_paused', False)
                    g['total_pause_sec'] = v.get('total_pause_sec', 0)
                    g['pause_logs'] = v.get('pause_logs', [])
                    if v.get('pause_start_ts'):
                        g['pause_start_ts'] = datetime.strptime(v['pause_start_ts'], "%Y-%m-%d %H:%M:%S")

                    g['is_suspended'] = v.get('is_suspended', False)
                    g['suspend_locked_cost'] = round(v.get('suspend_locked_cost', 0.0), 2)
                    if v.get('suspend_start_ts'):
                        g['suspend_start_ts'] = datetime.strptime(v['suspend_start_ts'], "%Y-%m-%d %H:%M:%S")

                    if g['is_suspended']:
                        g['widgets']['btn_suspend'].config(text="取消挂账", bg="#d35400")
                        g['widgets']['btn_pause'].config(state=tk.DISABLED)

                    g['status'] = v.get('status', 0)
                    if v.get('fixed_end_time'): g['fixed_end_time'] = datetime.strptime(v['fixed_end_time'],
                                                                                        "%Y-%m-%d %H:%M:%S")
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = PerfectTimerApp(root)
    root.mainloop()