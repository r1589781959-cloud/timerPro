import sys
"""
TimerPro Web App - FastAPI Backend
Full implementation: pause, checkout, bill calculation matching timerProV15.py logic
"""

import os
import json
import csv
import time
import math
import hashlib
import base64
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ==========================================
# --- App Configuration ---
# ==========================================

# 判定运行环境：如果是打包后的EXE，则使用EXE所在文件夹作为根目录
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent.resolve()
    # 打包环境下，静态文件被 PyInstaller 放在了 _internal/web_app/static 目录下
    STATIC_DIR = ROOT_DIR / "_internal" / "web_app" / "static"
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    # 开发环境下，静态文件在 web_app/static 目录下
    STATIC_DIR = ROOT_DIR / "web_app" / "static"

CONFIG_FILE = ROOT_DIR / "shop_config.json"
DATA_FILE = ROOT_DIR / "active_data.json"
HISTORY_FILE = ROOT_DIR / "history_log.csv"
HISTORY_DATA_FILE = ROOT_DIR / "history_data.json"

# ==========================================
# --- FastAPI App ---
# ==========================================

app = FastAPI(
    title="TimerPro API",
    description="Backend API for TimerPro Web POS System",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# --- Pydantic Models ---
# ==========================================

class HealthResponse(BaseModel):
    status: str

class AuthStatusResponse(BaseModel):
    machine_code: str
    activated: bool
    guests: int
    first_run: float

class ActivateRequest(BaseModel):
    code: str

class ActivateResponse(BaseModel):
    success: bool
    message: str

class GuestRequest(BaseModel):
    count: int

class GuestResponse(BaseModel):
    success: bool
    message: str
    total_guests: Optional[int] = None

class ActiveDataUpdate(BaseModel):
    data: Dict[str, Any]

class OpenTableRequest(BaseModel):
    phone: str
    mode: str
    configId: Optional[Any] = None
    remark: Optional[str] = ""
    count: Optional[int] = 1

class OpenTableResponse(BaseModel):
    success: bool
    message: str
    order_id: Optional[str] = None

class BillPreviewRequest(BaseModel):
    order_id: str

class SingleHistoryRecord(BaseModel):
    phone: str
    end_time: str

class DeleteHistoryRequest(BaseModel):
    records: List[SingleHistoryRecord]

class CheckoutRequest(BaseModel):
    order_id: str
    final_total: Optional[float] = None
    remark: Optional[str] = ""
    gb_verified: Optional[bool] = None

class CheckoutResponse(BaseModel):
    success: bool
    message: str
    bill: Optional[Dict[str, Any]] = None

class PauseRequest(BaseModel):
    order_id: str

class PauseResponse(BaseModel):
    success: bool
    message: str
    is_paused: bool

class ShopConfigUpdate(BaseModel):
    config: Dict[str, Any]

# ==========================================
# --- AuthManager (Ported from timerProV15.py) ---
# ==========================================

class AuthManager:
    """Machine code authorization system with dual-file backup"""

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
            fake_time = base_time + (123 * 24 * 3600) + 12580 if file_type == 'A' else base_time + (365 * 24 * 3600) + 31500
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

# Global AuthManager instance
auth_manager = AuthManager()

# ==========================================
# --- Helper Functions ---
# ==========================================

def fmt_min(minutes):
    """Format minutes into Chinese readable string"""
    if minutes < 60: return f"{minutes}分"
    h, m = divmod(int(minutes), 60)
    return f"{h}小时" if m == 0 else f"{h}小时{m}分"

def fmt_duration_str(total_seconds):
    """Format seconds into Chinese readable duration string"""
    total_seconds = int(total_seconds)
    h, r = divmod(total_seconds, 3600)
    m, s = divmod(r, 60)
    if h > 0:
        return f"{h}小时{m}分{s}秒"
    elif m > 0:
        return f"{m}分{s}秒"
    else:
        return f"{s}秒"

def get_mode_text(mode: str) -> str:
    """Get Chinese text for billing mode"""
    mode_map = {
        "pay_later": "先玩后付",
        "fixed": "普通定额",
        "unlimited": "全天畅玩",
        "single_board": "单板不限时",
        "group_buy": "团购套餐",
        "time_slot": "时段优惠"
    }
    return mode_map.get(mode, mode)

# ==========================================
# --- Data File Utilities ---
# ==========================================

def read_config() -> Dict[str, Any]:
    """Read shop_config.json from parent directory, or return defaults"""
    if not CONFIG_FILE.exists():
        # 如果不存在，返回一个默认配置，防止报错 404
        default_cfg = {
            "price_overtime": 10.0,
            "price_unlimited": 39.9,
            "price_single_board": 39.9,
            "buffer_min": 10,
            "step_config": [
                {"minutes": 60, "price": 10},
                {"minutes": 120, "price": 18},
                {"minutes": 180, "price": 25}
            ],
            "group_buys": [],
            "alert_enabled": True
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_cfg, f, ensure_ascii=False, indent=4)
        except: pass
        return default_cfg

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def read_active_data() -> Dict[str, Any]:
    """Read active_data.json from parent directory"""
    if not DATA_FILE.exists():
        return {"c": 0, "g": {}}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"c": 0, "g": {}}

def write_active_data(data: Dict[str, Any]) -> bool:
    """Write data to active_data.json in parent directory"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write active data: {str(e)}")

def write_history_csv(gid, phone, mode, start_time_str, end_time_str, total_dur, play_dur, cost, 
                      remark="", fixed_str="--", pause_info="", guest_count=1, gb_type="", gb_voucher_price=0):
    """Write a checkout record to history_log.csv, matching timerProV15.py format"""
    f_ex = os.path.exists(HISTORY_FILE)
    try:
        with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if not f_ex:
                w.writerow(["开始", "结束", "序号", "标识", "模式", "总时长", "实玩时长", "总金额", 
                           "团购类型", "团购价值", "结算金额", "备注", "定额时长", "暂停详情"])
            m_cn = {"pay_later": "先玩后付", "fixed": "定额", "unlimited": "全天畅玩", 
                    "single_board": "单板不限", "group_buy": "团购"}.get(mode, mode)
            clean_remark = str(remark).replace("\n", " ").replace("\r", "")
            try:
                gid_num = int(gid)
            except (TypeError, ValueError):
                gid_num = gid
            w.writerow([
                start_time_str, end_time_str, gid_num, phone, m_cn,
                total_dur, play_dur, round(float(cost) + float(gb_voucher_price), 2), gb_type,
                round(float(gb_voucher_price), 2), round(float(cost), 2), clean_remark, fixed_str, pause_info
            ])
    except Exception as e:
        print(f"Error writing history: {e}")

def write_history_data(record: Dict[str, Any]):
    """Append a checkout record to history_data.json"""
    history = []
    if HISTORY_DATA_FILE.exists():
        try:
            with open(HISTORY_DATA_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    history.append(record)
    try:
        with open(HISTORY_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing history data: {e}")

# ==========================================
# --- Billing Calculation (matching timerProV15.py) ---
# ==========================================

def get_overtime_cost(over_mins: int, hourly_p: float, c: Dict[str, Any]) -> float:
    """Calculate overtime cost using step pricing, matching timerProV15.py logic"""
    if over_mins <= 0:
        return 0.0
    if c.get('calc_mode', 'step') == 'exact':
        return round((over_mins / 60.0) * hourly_p, 2)
    
    n = int(c.get('step_n', 15))
    y = float(c.get('step_y', 10.0))
    k = float(c.get('step_k', 2.0))
    ceil_x = int(c.get('ceil_x', 5))
    
    hrs = int(over_mins // 60)
    rem = int(over_mins % 60)
    rem_cost = 0.0
    if rem > 0:
        if 60 - rem <= ceil_x:
            rem_cost = hourly_p
        else:
            blocks = rem // n
            if (rem % n) >= (n / k):
                blocks += 1
            rem_cost = blocks * y
            if rem_cost > hourly_p:
                rem_cost = hourly_p
    return round(hrs * hourly_p + rem_cost, 2)


def calculate_full_bill(order_id: str, order_data: Dict[str, Any], config: Dict[str, Any], 
                        end_time: datetime = None) -> Dict[str, Any]:
    """
    Full bill calculation matching timerProV15.py calculate_single_bill logic.
    Returns a comprehensive bill dict.
    """
    d = order_data
    c = config
    if end_time is None:
        end_time = datetime.now()
    
    # Parse start_time
    start_time = datetime.strptime(d['start_time'], "%Y-%m-%d %H:%M:%S")
    
    # Calculate pause duration
    current_pause = 0
    if d.get('is_paused', False) and d.get('pause_start_ts'):
        try:
            pause_start = datetime.strptime(d['pause_start_ts'], "%Y-%m-%d %H:%M:%S")
            current_pause = int((end_time - pause_start).total_seconds())
        except:
            pass
    elif d.get('is_suspended', False) and d.get('suspend_start_ts'):
        try:
            suspend_start = datetime.strptime(d['suspend_start_ts'], "%Y-%m-%d %H:%M:%S")
            current_pause = int((end_time - suspend_start).total_seconds())
        except:
            pass
    
    total_pause_sec = d.get('total_pause_sec', 0) + current_pause
    raw_duration_sec = (end_time - start_time).total_seconds()
    effective_duration_sec = raw_duration_sec - total_pause_sec
    minutes = int(effective_duration_sec / 60)
    
    total_price = 0.0
    fixed_time_str = "--"
    mode_info = ""
    over_info = "正常"
    gb_voucher_price = 0.0
    gb_extra_cost = 0.0
    gb_verified = False
    
    mode = d.get('mode', 'pay_later')
    
    if d.get('is_suspended', False):
        total_price = d.get('suspend_locked_cost', 0.0)
        over_info = "挂账锁定"
        mode_dict = {"pay_later": "先玩后付", "fixed": "普通定额", "unlimited": "全天畅玩", "single_board": "单板不限时", "time_slot": "时段优惠"}
        mode_info = d.get('gb_config', {}).get('name') if mode == 'group_buy' else mode_dict.get(mode, mode)
    else:
        if mode == 'group_buy':
            gb = d.get('gb_config', {}) or {}
            mode_info = gb.get('name', '团购套餐')
            bp = gb.get('price', 0.0)
            gb_persons = gb.get('persons', 1)
            gb_verified = d.get('gb_verified', False)
            
            is_valid = True
            if gb.get('type') == 'time_slot':
                try:
                    st = datetime.strptime(gb['start_time'], "%H:%M").time()
                    et = datetime.strptime(gb['end_time'], "%H:%M").time()
                    gst = start_time.time()
                    if not (st <= gst <= et):
                        is_valid = False
                except:
                    pass
            
            if not is_valid:
                # Non-valid time slot: charge as walk-in
                if minutes <= c.get('time_base', 120):
                    total_price = c.get('price_base', 29.9)
                else:
                    over = minutes - c.get('time_base', 120)
                    if over > c.get('buffer_min', 10):
                        total_price = c.get('price_base', 29.9) + get_overtime_cost(over, c.get('price_overtime', 10.0), c)
                    else:
                        total_price = c.get('price_base', 29.9)
                over_info = "非时段按散客计费"
            else:
                if gb.get('type') in ['unlimited', 'single_board']:
                    gb_voucher_price = round(bp / gb_persons, 2)
                    total_price = gb_voucher_price
                    gb_extra_cost = 0.0
                    over_info = "团购不限时"
                else:
                    lm = gb.get('limit_min', 60)
                    fixed_time_str = fmt_min(lm)
                    buf = gb.get('buffer_min', c.get('buffer_min', 10))
                    
                    if gb.get('type') == 'time_slot' and d.get('time_slot_end_time'):
                        try:
                            slot_end_time = datetime.strptime(d['time_slot_end_time'], "%Y-%m-%d %H:%M:%S")
                            effective_to_slot = (slot_end_time - start_time).total_seconds() / 60
                            over = max(0, minutes - effective_to_slot)
                        except:
                            added_time = d.get('added_time_min', 0)
                            over = max(0, minutes - (lm + added_time))
                    else:
                        added_time = d.get('added_time_min', 0)
                        over = max(0, minutes - (lm + added_time))
                    
                    gb_voucher_price = round(bp / gb_persons, 2)
                    
                    added_time_cost = d.get('added_time_cost', 0.0) if 'added_time_cost' in d else 0.0
                    
                    if over > buf:
                        hourly_p = gb.get('overtime_price', c.get('price_overtime', 10.0))
                        gb_extra_cost = get_overtime_cost(int(over), hourly_p, c)
                        total_price = gb_voucher_price + gb_extra_cost + added_time_cost
                        over_info = f"超时 {fmt_min(int(over))}"
                    else:
                        gb_extra_cost = 0.0
                        total_price = gb_voucher_price + added_time_cost
        
        elif mode == "pay_later":
            mode_info = "先玩后付"
            if minutes <= c.get('time_base', 120):
                total_price = c.get('price_base', 29.9)
            else:
                over = minutes - c.get('time_base', 120)
                if over > c.get('buffer_min', 10):
                    total_price = c.get('price_base', 29.9) + get_overtime_cost(over, c.get('price_overtime', 10.0), c)
                else:
                    total_price = c.get('price_base', 29.9)
            over_info = f"净时长 {fmt_min(minutes)}"
        
        elif mode == "fixed":
            mode_info = "普通定额"
            lm = d.get('limit_min', 60)
            added_time = d.get('added_time_min', 0)
            fixed_time_str = fmt_min(lm)
            bp = round(((lm + added_time) / 60.0) * c.get('price_overtime', 10.0), 2)
            over = max(0, minutes - (lm + added_time))
            if over > c.get('buffer_min', 10):
                total_price = bp + get_overtime_cost(over, c.get('price_overtime', 10.0), c)
                over_info = f"超时 {fmt_min(int(over))}"
            else:
                total_price = bp
                over_info = f"总时长 {fmt_min(lm + added_time)}"
        
        elif mode in ["unlimited", "single_board"]:
            mode_info = "全天畅玩" if mode == "unlimited" else "单板不限时"
            total_price = c.get('price_unlimited', 59.9) if mode == "unlimited" else c.get('price_single_board', 39.9)
            over_info = "不限时"
    
    # Calculate additional costs
    added_gb_cost = 0.0
    if 'added_gb' in d:
        for gb in d['added_gb']:
            if not gb.get('verify_status', False):
                added_gb_cost += gb.get('price', 0.0)
                
    added_time_cost = 0.0
    if mode not in ['unlimited', 'single_board']:
        added_time_cost = d.get('added_time_cost', 0.0)

    cost_detail_str = ""

    if d.get('is_suspended', False):
        actual_total = total_price
        cost_detail_str = f"挂账锁定待结 ¥{actual_total:.2f}"
    elif mode == "fixed":
        lm = d.get('limit_min', 60)
        added_time = d.get('added_time_min', 0)
        base_cost = round((lm / 60.0) * c.get('price_overtime', 10.0), 2)
        added_time_cost_display = round((added_time / 60.0) * c.get('price_overtime', 10.0), 2)
        
        overtime_cost = 0.0
        if over > c.get('buffer_min', 10):
            overtime_cost = get_overtime_cost(over, c.get('price_overtime', 10.0), c)
            
        gb_time_cost = 0.0
        if 'added_gb' in d and d['added_gb']:
            gb_minutes = sum(gb.get('minutes', 0) for gb in d['added_gb'])
            gb_time_cost = round((gb_minutes / 60.0) * c.get('price_overtime', 10.0), 2)
            
        total_price = round(base_cost + added_time_cost_display + overtime_cost - gb_time_cost + added_gb_cost + added_time_cost, 2)
        
        parts = [f"定额费 ¥{base_cost:.2f}"]
        if added_time > 0: parts.append(f"加时费 ¥{added_time_cost_display:.2f}")
        if added_time_cost > 0: parts.append(f"额外加时 ¥{added_time_cost:.2f}")
        if overtime_cost > 0: parts.append(f"超时费 ¥{overtime_cost:.2f}")
        if added_gb_cost > 0: parts.append(f"未核销团购 ¥{added_gb_cost:.2f}")
        if gb_time_cost > 0: parts.append(f"团购抵扣 -¥{gb_time_cost:.2f}")
        
        actual_total = round(total_price, 2)
        cost_detail_str = " + ".join(parts) + f" = ¥{actual_total:.2f}"
            
    elif mode == 'group_buy':
        total_price = round(gb_voucher_price + gb_extra_cost + added_gb_cost + added_time_cost, 2)
        parts = []
        if not gb_verified:
            parts.append(f"券价 ¥{gb_voucher_price:.2f}")
        if gb_extra_cost > 0:
            parts.append(f"超时费 ¥{gb_extra_cost:.2f}")
        if added_gb_cost > 0:
            parts.append(f"未核销添加团购 ¥{added_gb_cost:.2f}")
        if added_time_cost > 0:
            parts.append(f"加时费用 ¥{added_time_cost:.2f}")
            
        if gb_verified:
            actual_total = round(gb_extra_cost + added_gb_cost + added_time_cost, 2)
            suffix = " (券价已收)"
        else:
            actual_total = round(total_price, 2)
            suffix = ""
            
        if not parts: parts = ["¥0.00"]
        cost_detail_str = " + ".join(parts) + f" = ¥{actual_total:.2f}{suffix}"
        
    else:
        total_price = round(total_price + added_gb_cost + added_time_cost, 2)
        actual_total = round(total_price, 2)

    actual_total = round(actual_total, 2)
    
    # Build pause log
    pause_log_copy = list(d.get('pause_logs', []))
    if d.get('is_paused', False):
        pause_log_copy.append(f"结账恢复 ({fmt_duration_str(current_pause)})")
    elif d.get('is_suspended', False):
        pause_log_copy.append(f"挂账等待 ({fmt_duration_str(current_pause)})")
        
    # Calculate fully verified true voucher values (strictly following user's rule for value distribution)
    true_gb_voucher = 0.0
    if mode == 'group_buy' and gb_verified:
        true_gb_voucher += gb_voucher_price
    if 'added_gb' in d:
        for gb in d['added_gb']:
            if gb.get('verify_status', False):
                true_gb_voucher += gb.get('price', 0.0)
    
    return {
        "order_id": order_id,
        "phone": d.get('phone', ''),
        "mode": mode,
        "mode_text": mode_info,
        "start_time": d.get('start_time', ''),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "minutes": minutes,
        "total_dur_str": fmt_duration_str(raw_duration_sec),
        "play_dur_str": fmt_duration_str(effective_duration_sec),
        "pause_dur_str": fmt_duration_str(total_pause_sec),
        "total_price": round(total_price, 2),
        "actual_total": actual_total,
        "prepaid": round(d.get('prepaid', 0.0), 2),
        "need": round(max(0, actual_total - d.get('prepaid', 0.0)), 2),
        "fixed_str": fixed_time_str,
        "over_info": over_info,
        "pause_str": "; ".join(pause_log_copy) if pause_log_copy else "无",
        "gb_voucher_price": gb_voucher_price,
        "gb_extra_cost": gb_extra_cost,
        "gb_verified": gb_verified,
        "remark": d.get('remark', ''),
        "gb_config": d.get('gb_config'),
        "cost_detail_str": cost_detail_str,
        "added_gb": d.get('added_gb', []),
        "true_gb_voucher": round(true_gb_voucher, 2)
    }

# ==========================================
# --- API Endpoints ---
# ==========================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/api/auth/status", response_model=AuthStatusResponse)
async def get_auth_status():
    """Get current authorization status"""
    return {
        "machine_code": auth_manager.machine_code,
        "activated": auth_manager.activated,
        "guests": auth_manager.data.get("guests", 0),
        "first_run": auth_manager.data.get("first_run", 0)
    }

@app.post("/api/auth/activate", response_model=ActivateResponse)
async def activate_auth(request: ActivateRequest):
    """Activate with authorization code"""
    if auth_manager.activate(request.code):
        return {"success": True, "message": "Activation successful"}
    return {"success": False, "message": "Invalid activation code"}

@app.post("/api/auth/guest", response_model=GuestResponse)
async def add_guest(request: GuestRequest):
    """Add guest count (for unactivated versions)"""
    if auth_manager.add_guest(request.count):
        return {
            "success": True,
            "message": f"Added {request.count} guest(s)",
            "total_guests": auth_manager.data.get("guests", 0)
        }
    return {"success": False, "message": "Failed to add guest (limit exceeded or activated)"}

@app.get("/api/config/shop")
async def get_shop_config():
    """Read shop configuration"""
    return read_config()

@app.put("/api/config/shop")
async def update_shop_config(request: ShopConfigUpdate):
    """Write shop configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(request.config, f, ensure_ascii=False, indent=4)
        return {"success": True, "message": "Config updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")

@app.get("/api/history")
async def get_history(start: Optional[str] = None, end: Optional[str] = None):
    """Get checkout history"""
    history = []
    if HISTORY_DATA_FILE.exists():
        try:
            with open(HISTORY_DATA_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            pass
            
    if start:
        history = [h for h in history if h.get('end_time', '') >= start]
    if end:
        end_dt = end + " 23:59:59"
        history = [h for h in history if h.get('end_time', '') <= end_dt]
        
    history.sort(key=lambda x: x.get('end_time', ''), reverse=True)
    return {"success": True, "history": history}

@app.get("/api/data/active")
async def get_active_data():
    """Read active session data"""
    return read_active_data()

@app.post("/api/data/active")
async def update_active_data(request: ActiveDataUpdate):
    """Update active session data"""
    current_data = read_active_data()
    current_data.update(request.data)
    write_active_data(current_data)
    return {"success": True, "message": "Active data updated"}

@app.post("/api/tables/open", response_model=OpenTableResponse)
async def open_table(request: OpenTableRequest):
    """Create a new table/order and save to active_data.json"""
    current_data = read_active_data()

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    count = max(1, request.count or 1)
    
    # Detect multi-person group buy override
    if request.mode == "group_buy" and isinstance(request.configId, dict):
        gb_persons = int(request.configId.get('persons', 1))
        if gb_persons > count:
            count = gb_persons

    group_id = now.strftime("%Y%m%d%H%M%S%f") if count > 1 else None

    first_order_id = None

    for i in range(count):
        current_data['c'] = current_data.get('c', 0) + 1
        order_id = str(current_data['c'])
        if i == 0:
            first_order_id = order_id

        phone_val = request.phone if count == 1 else f"{request.phone}-{i+1}"

        # Build order data matching timerProV15.py save_to_disk field list exactly
        order_data = {
            "phone": phone_val,
            "mode": request.mode,
            "start_time": now_str,
            "limit_min": 0,
            "remark": request.remark or "",
            "is_paused": False,
            "total_pause_sec": 0,
            "pause_logs": [],
            "pause_start_ts": None,
            "is_suspended": False,
            "suspend_locked_cost": 0.0,
            "suspend_start_ts": None,
            "group_id": group_id,
            "prepaid": 0.0,
            "guest_count": 1,
            "gb_config": None,
            "gb_verified": False,
            "added_time_min": 0,
            "added_time_cost": 0.0,
            "time_slot_end_time": None,
            "added_gb": []
        }

        # Handle mode-specific settings
        if request.mode == "fixed" and request.configId:
            order_data["limit_min"] = int(request.configId)

        elif request.mode == "group_buy" and request.configId:
            order_data["gb_config"] = request.configId
            order_data["mode"] = "group_buy"
            if isinstance(request.configId, dict):
                if request.configId.get('type') == 'time_slot':
                    # Calculate the actual end time for time_slot
                    try:
                        end_time_str = request.configId.get('end_time', '23:59')
                        today = now.date()
                        slot_end = datetime.combine(today, datetime.strptime(end_time_str, "%H:%M").time())
                        order_data["time_slot_end_time"] = slot_end.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        order_data["time_slot_end_time"] = None
                if request.configId.get('limit_min'):
                    order_data["limit_min"] = request.configId.get('limit_min', 0)

        elif request.mode == "time_slot" and request.configId:
            order_data["gb_config"] = request.configId
            order_data["mode"] = "group_buy"
            if isinstance(request.configId, dict):
                order_data["limit_min"] = request.configId.get('limit_min', 0)
                try:
                    end_time_str = request.configId.get('end_time', '23:59')
                    today = now.date()
                    slot_end = datetime.combine(today, datetime.strptime(end_time_str, "%H:%M").time())
                    order_data["time_slot_end_time"] = slot_end.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    order_data["time_slot_end_time"] = None

        current_data['g'][order_id] = order_data

    write_active_data(current_data)

    return {
        "success": True,
        "message": f"开台成功 (共 {count} 台)",
        "order_id": first_order_id
    }

@app.post("/api/tables/bill")
async def preview_bill(request: BillPreviewRequest):
    """账单预览：返回完整费用明细，不修改数据"""
    current_data = read_active_data()
    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")
    order_data = current_data['g'][request.order_id]
    config = read_config()
    bill = calculate_full_bill(request.order_id, order_data, config, datetime.now())
    return {"success": True, "bill": bill}


@app.post("/api/tables/checkout", response_model=CheckoutResponse)
async def checkout_table(request: CheckoutRequest):
    """结账：计算账单、写历史、移除订单。支持自定义金额和核销状态。"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")

    order_data = current_data['g'][request.order_id]
    config = read_config()
    
    # 如果前端传了核销状态，先更新
    if request.gb_verified is not None and order_data.get('mode') == 'group_buy':
        order_data['gb_verified'] = request.gb_verified
        group_id = order_data.get('group_id')
        if group_id:
            for oid, odata in current_data['g'].items():
                if oid != request.order_id and odata.get('group_id') == group_id:
                    odata['gb_verified'] = request.gb_verified
    
    # 如果前端传了备注，先更新
    if request.remark is not None and request.remark != "":
        order_data['remark'] = request.remark
    
    end_time = datetime.now()
    bill = calculate_full_bill(request.order_id, order_data, config, end_time)
    
    # 如果前端指定了最终金额，使用自定义金额
    final_cost = request.final_total if request.final_total is not None else bill['actual_total']
    final_cost = round(final_cost, 2)
    
    # Write to history_log.csv
    start_time = datetime.strptime(order_data['start_time'], "%Y-%m-%d %H:%M:%S")
    gb_type = ""
    gb_voucher = bill.get('true_gb_voucher', 0)
    if order_data.get('mode') == 'group_buy' and order_data.get('gb_config'):
        gb_type = order_data['gb_config'].get('name', '')
    
    write_history_csv(
        gid=request.order_id,
        phone=order_data.get('phone', ''),
        mode=order_data.get('mode', ''),
        start_time_str=start_time.strftime("%Y-%m-%d %H:%M"),
        end_time_str=end_time.strftime("%Y-%m-%d %H:%M"),
        total_dur=bill['total_dur_str'],
        play_dur=bill['play_dur_str'],
        cost=final_cost,
        remark=order_data.get('remark', ''),
        fixed_str=bill['fixed_str'],
        pause_info=bill['pause_str'],
        guest_count=order_data.get('guest_count', 1),
        gb_type=gb_type,
        gb_voucher_price=gb_voucher
    )
    
    # Write to history_data.json
    write_history_data({
        "order_id": request.order_id,
        "phone": order_data.get('phone', ''),
        "mode": order_data.get('mode', ''),
        "mode_text": bill['mode_text'],
        "start_time": order_data.get('start_time', ''),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_dur": bill['total_dur_str'],
        "play_dur": bill['play_dur_str'],
        "total_price": bill['total_price'],
        "actual_total": final_cost,
        "remark": order_data.get('remark', ''),
        "fixed_str": bill['fixed_str'],
        "pause_str": bill['pause_str'],
        "gb_type": gb_type,
        "gb_voucher": gb_voucher,
        "checkout_time": end_time.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Remove from active data
    del current_data['g'][request.order_id]
    write_active_data(current_data)

    bill['actual_total'] = final_cost
    return {
        "success": True,
        "message": "结账成功",
        "bill": bill
    }

@app.delete("/api/tables/{order_id}")
async def cancel_order(order_id: str):
    """强制作废活跃订单（不记录历史）"""
    current_data = read_active_data()
    if 'g' in current_data and order_id in current_data['g']:
        del current_data['g'][order_id]
        write_active_data(current_data)
        return {"success": True, "message": "订单已强制作废并移除"}
    raise HTTPException(status_code=404, detail="订单不存在")

@app.delete("/api/history")
async def delete_history_record(req: DeleteHistoryRequest):
    """删除单条历史记录并重写JSON存储文件"""
    history = []
    if HISTORY_DATA_FILE.exists():
        try:
            with open(HISTORY_DATA_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail="解析历史文件失败")
            
    targets = {(r.phone, r.end_time) for r in req.records}
    filtered = []
    removed_count = 0
    for h in history:
        if (h.get('phone'), h.get('end_time')) in targets:
            removed_count += 1
        else:
            filtered.append(h)
            
    if removed_count == 0:
        raise HTTPException(status_code=404, detail="找不到指定的历史记录")
        
    try:
        with open(HISTORY_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail="覆盖历史文件失败")
        
    return {"success": True, "message": f"成功批量删除了 {removed_count} 条流水记录"}


@app.post("/api/tables/pause", response_model=PauseResponse)
async def toggle_pause(request: PauseRequest):
    """Toggle pause/resume state for an order"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="Order not found")

    order_data = current_data['g'][request.order_id]

    if order_data.get('is_suspended', False):
        raise HTTPException(status_code=400, detail="Cannot pause suspended order")

    now = datetime.now()

    if order_data.get('is_paused', False):
        # Resume: Calculate pause duration and add to total_pause_sec
        pause_start_str = order_data.get('pause_start_ts')
        duration_sec = 0
        if pause_start_str:
            try:
                pause_start = datetime.strptime(pause_start_str, "%Y-%m-%d %H:%M:%S")
                duration_sec = int((now - pause_start).total_seconds())
            except:
                pass
        
        order_data['total_pause_sec'] = order_data.get('total_pause_sec', 0) + duration_sec
        order_data['is_paused'] = False
        
        # Add pause log entry matching timerProV15 format
        pause_logs = order_data.get('pause_logs', [])
        if pause_start_str:
            try:
                pause_start = datetime.strptime(pause_start_str, "%Y-%m-%d %H:%M:%S")
                log_entry = f"{len(pause_logs) + 1}. {pause_start.strftime('%H:%M')}-{now.strftime('%H:%M')} ({fmt_duration_str(duration_sec)})"
                pause_logs.append(log_entry)
            except:
                pass
        order_data['pause_logs'] = pause_logs
        order_data['pause_start_ts'] = None
        message = "已恢复"
    else:
        # Pause: Record pause start time
        order_data['is_paused'] = True
        order_data['pause_start_ts'] = now.strftime("%Y-%m-%d %H:%M:%S")
        message = "已暂停"

    write_active_data(current_data)

    return {
        "success": True,
        "message": message,
        "is_paused": order_data['is_paused']
    }

# ==========================================
# --- Phase 1: 挂账 / 加时间 / 修改备注 / 核销 ---
# ==========================================

class SuspendRequest(BaseModel):
    order_id: str
    locked_cost: float

class SuspendResponse(BaseModel):
    success: bool
    message: str

class AddTimeRequest(BaseModel):
    order_id: str
    mode: str  # "direct" or "group_buy"
    minutes: Optional[int] = 0
    gb_name: Optional[str] = None
    gb_verified: Optional[bool] = False

class AddTimeResponse(BaseModel):
    success: bool
    message: str

class RemarkRequest(BaseModel):
    order_id: str
    remark: str

class RemarkResponse(BaseModel):
    success: bool
    message: str

class VerifyRequest(BaseModel):
    order_id: str
    verified: bool
    added_gb_index: Optional[int] = None

class VerifyResponse(BaseModel):
    success: bool
    message: str


@app.post("/api/tables/suspend", response_model=SuspendResponse)
async def suspend_table(request: SuspendRequest):
    """挂账等候：冻结金额，暂停计时，保留订单"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")

    order_data = current_data['g'][request.order_id]
    now = datetime.now()

    # 如果当前在暂停中，先恢复暂停（累加暂停时间）
    if order_data.get('is_paused', False) and order_data.get('pause_start_ts'):
        try:
            pause_start = datetime.strptime(order_data['pause_start_ts'], "%Y-%m-%d %H:%M:%S")
            duration_sec = int((now - pause_start).total_seconds())
            order_data['total_pause_sec'] = order_data.get('total_pause_sec', 0) + duration_sec
            pause_logs = order_data.get('pause_logs', [])
            log_entry = f"{len(pause_logs) + 1}. {pause_start.strftime('%H:%M')}-{now.strftime('%H:%M')} ({fmt_duration_str(duration_sec)})"
            pause_logs.append(log_entry)
            order_data['pause_logs'] = pause_logs
        except:
            pass
        order_data['is_paused'] = False
        order_data['pause_start_ts'] = None

    # 设置挂账状态
    order_data['is_suspended'] = True
    order_data['suspend_start_ts'] = now.strftime("%Y-%m-%d %H:%M:%S")
    order_data['suspend_locked_cost'] = round(request.locked_cost, 2)

    write_active_data(current_data)

    return {
        "success": True,
        "message": f"已挂账，冻结金额 ¥{request.locked_cost:.2f}"
    }

class CancelSuspendRequest(BaseModel):
    order_id: str

@app.post("/api/tables/cancel-suspend")
async def cancel_suspend(request: CancelSuspendRequest):
    """取消挂账状态：恢复计费时间和金额"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")

    order_data = current_data['g'][request.order_id]
    
    if not order_data.get('is_suspended', False):
        raise HTTPException(status_code=400, detail="该订单未挂账")

    now = datetime.now()
    suspend_start_str = order_data.get('suspend_start_ts')
    
    # 累加挂账时的等待时间到暂停时间池子
    if suspend_start_str:
        try:
            suspend_start = datetime.strptime(suspend_start_str, "%Y-%m-%d %H:%M:%S")
            duration_sec = int((now - suspend_start).total_seconds())
            order_data['total_pause_sec'] = order_data.get('total_pause_sec', 0) + duration_sec
            pause_logs = order_data.get('pause_logs', [])
            log_entry = f"{len(pause_logs) + 1}. {suspend_start.strftime('%H:%M')}-{now.strftime('%H:%M')} 挂账取消 ({fmt_duration_str(duration_sec)})"
            pause_logs.append(log_entry)
            order_data['pause_logs'] = pause_logs
        except:
            pass

    order_data['is_suspended'] = False
    order_data['suspend_start_ts'] = None
    order_data['suspend_locked_cost'] = 0.0

    write_active_data(current_data)

    return {
        "success": True,
        "message": "已取消挂账并恢复计费"
    }


@app.post("/api/tables/add-time", response_model=AddTimeResponse)
async def add_time(request: AddTimeRequest):
    """加时间或加团购券"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")

    order_data = current_data['g'][request.order_id]
    config = read_config()
    now = datetime.now()
    add_time_str = now.strftime("%H:%M")

    if request.mode == "direct":
        # 直接添加时间（分钟）
        add_min = request.minutes or 0
        if add_min <= 0:
            raise HTTPException(status_code=400, detail="请输入正整数分钟")

        # 计算加时费用
        add_price = 0.0
        order_mode = order_data.get('mode', '')
        if order_mode == "fixed":
            add_price = round((add_min / 60.0) * config.get('price_overtime', 10.0), 2)
        elif order_mode == "group_buy" and order_data.get('gb_config'):
            gb = order_data['gb_config']
            hourly_p = gb.get('overtime_price', config.get('price_overtime', 10.0))
            add_price = round((add_min / 60.0) * hourly_p, 2)

        # 更新数据
        order_data['added_time_min'] = order_data.get('added_time_min', 0) + add_min

        # 非fixed模式保存费用
        if order_mode != 'fixed':
            order_data['added_time_cost'] = order_data.get('added_time_cost', 0.0) + add_price

        # 更新time_slot_end_time
        if order_data.get('time_slot_end_time'):
            try:
                slot_end = datetime.strptime(order_data['time_slot_end_time'], "%Y-%m-%d %H:%M:%S")
                slot_end += timedelta(minutes=add_min)
                order_data['time_slot_end_time'] = slot_end.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        # 追加备注
        current_remark = order_data.get('remark', '').strip()
        new_note = f"【加时】{add_time_str} +{add_min}分钟 ¥{add_price:.2f}"
        order_data['remark'] = f"{current_remark}\n{new_note}".strip() if current_remark else new_note

        write_active_data(current_data)
        return {
            "success": True,
            "message": f"已添加 {add_min} 分钟，额外费用 ¥{add_price:.2f}"
        }

    elif request.mode == "group_buy":
        # 添加团购券
        gb_name = request.gb_name
        if not gb_name:
            raise HTTPException(status_code=400, detail="请选择团购券")

        # 从配置中查找团购券
        group_buys = config.get('group_buys', [])
        selected_gb = next((gb for gb in group_buys if gb['name'] == gb_name), None)
        if not selected_gb:
            raise HTTPException(status_code=404, detail="未找到该团购券配置")

        add_min = selected_gb.get('limit_min', 60)
        add_price = selected_gb.get('price', 0.0)

        # 更新数据
        order_data['added_time_min'] = order_data.get('added_time_min', 0) + add_min

        # 更新time_slot_end_time
        if order_data.get('time_slot_end_time'):
            try:
                slot_end = datetime.strptime(order_data['time_slot_end_time'], "%Y-%m-%d %H:%M:%S")
                slot_end += timedelta(minutes=add_min)
                order_data['time_slot_end_time'] = slot_end.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        # 添加到 added_gb 列表
        if 'added_gb' not in order_data:
            order_data['added_gb'] = []

        added_gb_info = {
            'id': len(order_data['added_gb']) + 1,
            'name': selected_gb['name'],
            'price': add_price,
            'minutes': add_min,
            'verify_status': request.gb_verified or False,
            'add_time': add_time_str,
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S")
        }
        order_data['added_gb'].append(added_gb_info)

        # 追加备注
        verify_text = "已核销" if request.gb_verified else "未核销"
        current_remark = order_data.get('remark', '').strip()
        new_note = f"【加团购】{add_time_str} {selected_gb['name']} ({verify_text}) ¥{add_price:.2f}"
        order_data['remark'] = f"{current_remark}\n{new_note}".strip() if current_remark else new_note

        write_active_data(current_data)
        return {
            "success": True,
            "message": f"已添加团购券: {selected_gb['name']}，时间 {add_min}分钟，价格 ¥{add_price:.2f}"
        }

    else:
        raise HTTPException(status_code=400, detail="无效的 mode，应为 'direct' 或 'group_buy'")


@app.post("/api/tables/remark", response_model=RemarkResponse)
async def update_remark(request: RemarkRequest):
    """修改订单备注"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")

    current_data['g'][request.order_id]['remark'] = request.remark
    write_active_data(current_data)

    return {
        "success": True,
        "message": "备注已更新"
    }


@app.post("/api/tables/verify", response_model=VerifyResponse)
async def toggle_verify(request: VerifyRequest):
    """切换团购核销状态（包括主团购和附加团购券）"""
    current_data = read_active_data()

    if request.order_id not in current_data.get('g', {}):
        raise HTTPException(status_code=404, detail="订单不存在")

    order_data = current_data['g'][request.order_id]
    status_text = "已核销" if request.verified else "未核销"

    if request.added_gb_index is not None:
        idx = request.added_gb_index
        added_gb = order_data.get('added_gb', [])
        if idx < 0 or idx >= len(added_gb):
            raise HTTPException(status_code=400, detail="找不到指定的团购券")
        
        added_gb[idx]['verify_status'] = request.verified
        
        # 更新备注
        old_remark = order_data.get('remark', '')
        preserved_lines = [ln for ln in old_remark.splitlines() if not ln.strip().startswith("【加团购】")]
        preserved = "\n".join(preserved_lines).strip()
        added_lines = []
        for gb in added_gb:
            st = "已核销" if gb.get('verify_status') else "未核销"
            atime = gb.get('add_time', '')
            nm = gb.get('name', '')
            pr = float(gb.get('price', 0.0) or 0.0)
            added_lines.append(f"【加团购】{atime} {nm} ({st}) ¥{pr:.2f}".strip())
        
        order_data['remark'] = ("\n".join([preserved] + added_lines)).strip() if preserved else ("\n".join(added_lines)).strip()
        
    else:
        if order_data.get('mode') != 'group_buy':
            raise HTTPException(status_code=400, detail="仅团购订单可操作主团购核销")

        # 更新当前订单的核销状态
        order_data['gb_verified'] = request.verified

        # 联动同 group_id 的其他成员
        group_id = order_data.get('group_id')
        if group_id:
            for oid, odata in current_data['g'].items():
                if oid != request.order_id and odata.get('group_id') == group_id:
                    odata['gb_verified'] = request.verified

    write_active_data(current_data)

    return {
        "success": True,
        "message": f"核销状态已更新为: {status_text}"
    }


# ==========================================
# --- Static Files ---
# ==========================================

# Mount static files directory (must be AFTER all API routes)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # 启动服务器，端口 8000
    print(f"\n🚀 TimerPro Web POS 系统正在启动...")
    print(f"👉 本地访问: http://localhost:8000")
    print(f"👉 静态资源目录: {STATIC_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)