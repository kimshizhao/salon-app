import streamlit as st
import pandas as pd
import io
import calendar as _cal
import hashlib
from datetime import date as dt_date

# Try to import DB layer (only available when Supabase secrets are configured)
try:
    from db import (
        db_login, db_load_branches_and_accounts, db_load_salon,
        db_add_booking, db_save_all_bookings, db_update_booking, db_get_bookings,
        db_add_walkin, db_delete_walkin, db_save_all_inventory,
        db_add_member, db_update_member, db_add_member_history, db_delete_member,
        db_set_stylists, db_add_account, db_delete_account, db_update_password,
        db_add_salon, db_delete_salon,
        db_confirm_booking, db_cancel_booking,
        db_update_salon_subscription, db_activate_trial,
        db_update_salon_contact, db_get_salon_info,
        db_save_commissions, db_get_commissions,
        db_update_salon_profile,
    )
    _USE_DB = "SUPABASE_URL" in st.secrets and st.secrets["SUPABASE_URL"] != "https://YOUR_PROJECT_ID.supabase.co"
except Exception:
    _USE_DB = False

try:
    from notify import (
        send_booking_confirmed, whatsapp_link,
        wa_booking_confirmed_msg, wa_booking_reminder_msg, email_configured,
    )
    _NOTIFY = True
except Exception:
    _NOTIFY = False

# ── Auth helpers ──────────────────────────────────────────────────────────────
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# Default accounts — owner should change passwords after first login
# Structure: { username: {hash, role, branch, display_name} }
# Roles: "owner" | "manager" | "staff"
# Branch: branch_id string or "all" for owner
_DEFAULT_ACCOUNTS = {
    "iqsalon": {"hash": _hash("iqadmin888"), "role": "admin",   "branch": "all", "name": "IQSALON Admin"},
    "admin":   {"hash": _hash("admin123"),   "role": "owner",   "branch": "all", "name": "Admin"},
    "kim":     {"hash": _hash("kim123"),     "role": "manager", "branch": "B001","name": "Kim"},
    "lily":    {"hash": _hash("lily123"),    "role": "staff",   "branch": "B001","name": "Lily"},
    "jason":   {"hash": _hash("jason123"),   "role": "staff",   "branch": "B001","name": "Jason"},
}

_DEFAULT_BRANCHES = {
    "B001": "Signature Kim — KL",
}

# Role hierarchy: admin > owner > manager > staff
ROLE_HIERARCHY = {"admin": 4, "owner": 3, "manager": 2, "staff": 1}

def _can(action: str) -> bool:
    """Check if current user has permission for an action."""
    role = st.session_state.get("role", "staff")
    perms = {
        "admin":   {"settlement","member_delete","inventory_edit","super_admin","admin",
                    "view_all","payment","booking","analytics","manage_owners"},
        "owner":   {"settlement","member_delete","inventory_edit","admin",
                    "view_all","payment","booking","analytics"},
        "manager": {"settlement","member_delete","inventory_edit","payment","booking","analytics"},
        "staff":   {"payment","booking"},
    }
    return action in perms.get(role, set())

st.set_page_config(
    page_title="IQSALON",
    page_icon="✂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Auto-refresh every 60s to pick up new online bookings
try:
    from streamlit_autorefresh import st_autorefresh
    _auto_refresh_count = st_autorefresh(interval=60_000, limit=None, key="auto_refresh")
except Exception:
    _auto_refresh_count = 0

# Inject viewport meta for proper mobile scaling
st.markdown(
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">',
    unsafe_allow_html=True,
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Raleway:wght@300;400;600&display=swap');
  html, body, [class*="css"] { font-family:'Raleway',sans-serif; background:#0a0a0a; color:#f0ece0; }
  .stApp { background-color:#0a0a0a; }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:1.5rem 2rem 2rem; max-width:960px !important; width:100% !important; }

  .hero { text-align:center; padding:2.2rem 1rem 1.2rem; border-bottom:1px solid #c9a84c44; margin-bottom:1.6rem; }
  .hero-title { font-family:'Playfair Display',serif; font-size:2.8rem; font-weight:700; letter-spacing:8px;
    background:linear-gradient(135deg,#c9a84c,#f5e19a,#c9a84c);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; margin:0; }
  .hero-sub { font-size:0.78rem; letter-spacing:4px; color:#888; margin-top:0.3rem; text-transform:uppercase; }

  .stTabs [data-baseweb="tab-list"] { gap:4px; background:#111; border-radius:8px; padding:6px; border:1px solid #c9a84c33; }
  .stTabs [data-baseweb="tab"] { font-family:'Raleway',sans-serif; font-weight:600; letter-spacing:2px; font-size:0.76rem;
    text-transform:uppercase; color:#888 !important; background:transparent; border:none; border-radius:6px;
    padding:9px 18px; transition:all .25s; }
  .stTabs [aria-selected="true"] { background:linear-gradient(135deg,#c9a84c,#a07830) !important; color:#0a0a0a !important; }
  .stTabs [data-baseweb="tab-highlight"] { background:transparent !important; }
  .stTabs [data-baseweb="tab-border"] { display:none; }

  .card { background:#111; border:1px solid #c9a84c33; border-radius:12px; padding:1.5rem 1.8rem; margin-bottom:1.2rem; }
  .card-title { font-family:'Playfair Display',serif; font-size:1.15rem; color:#c9a84c; margin-bottom:0.8rem; letter-spacing:1px; }

  .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div,
  .stDateInput>div>div>input, .stNumberInput>div>div>input {
    background-color:#1a1a1a !important; border:1px solid #c9a84c55 !important;
    border-radius:8px !important; color:#f0ece0 !important; font-family:'Raleway',sans-serif !important; }
  .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
    border-color:#c9a84c !important; box-shadow:0 0 0 2px #c9a84c22 !important; }
  label, .stMarkdown p { color:#ccb97a !important; font-size:0.85rem; letter-spacing:1px; }

  .stButton>button { background:linear-gradient(135deg,#c9a84c,#a07830); color:#0a0a0a;
    font-family:'Raleway',sans-serif; font-weight:700; font-size:0.82rem; letter-spacing:2px;
    text-transform:uppercase; border:none; border-radius:8px; padding:0.65rem 2rem;
    transition:all .25s; width:100%; }
  .stButton>button:hover { background:linear-gradient(135deg,#f5e19a,#c9a84c); transform:translateY(-1px);
    box-shadow:0 4px 20px #c9a84c44; }

  .alert-warn { background:#2b1a0d; border-left:4px solid #e67e22; border-radius:8px;
    padding:0.9rem 1.2rem; margin-bottom:1rem; color:#f5c88a; }
  .alert-safe { background:#0d2b1a; border-left:4px solid #2ecc71; border-radius:8px;
    padding:0.9rem 1.2rem; margin-bottom:1rem; color:#a8f5c8; }

  /* Stat boxes */
  .stat-box { background:#111; border:1px solid #c9a84c33; border-radius:12px;
    padding:1rem 1.2rem; text-align:center; }
  .stat-val { font-family:'Playfair Display',serif; font-size:1.6rem; color:#c9a84c; font-weight:700; }
  .stat-lbl { font-size:0.68rem; letter-spacing:2px; color:#666; text-transform:uppercase; margin-top:2px; }

  /* Checkout */
  .checkout-box { background:linear-gradient(135deg,#1a1500,#0f0f0f); border:1px solid #c9a84c55;
    border-radius:14px; padding:1.4rem 1.6rem; }
  .checkout-price { font-family:'Playfair Display',serif; font-size:2.8rem; color:#c9a84c;
    font-weight:700; text-align:center; margin:0.5rem 0; }
  .checkout-customer { font-size:1.05rem; color:#f0ece0; text-align:center; letter-spacing:2px; }
  .checkout-svc { font-size:0.78rem; color:#888; text-align:center; margin-top:2px; letter-spacing:1px; }

  /* Stylist schedule card */
  .sched-card { background:#111; border:1px solid #c9a84c33; border-radius:12px;
    padding:1.2rem 1.4rem; margin-bottom:0.8rem; }
  .sched-avatar { width:44px; height:44px; border-radius:50%; display:flex; align-items:center;
    justify-content:center; font-size:1.1rem; font-weight:700; flex-shrink:0; }
  .sched-name { font-family:'Playfair Display',serif; font-size:1rem; color:#c9a84c; letter-spacing:1px; }
  .sched-count { font-size:0.72rem; color:#888; letter-spacing:1px; }
  .sched-slot { background:#1a1a1a; border-left:3px solid; border-radius:0 8px 8px 0;
    padding:7px 12px; margin-bottom:5px; }
  .sched-slot-time { font-size:0.75rem; color:#888; letter-spacing:1px; }
  .sched-slot-client { font-size:0.9rem; color:#f0ece0; }
  .sched-slot-svc { font-size:0.72rem; color:#aaa; }

  /* Stylist roster pill */
  .stylist-pill { display:inline-flex; align-items:center; gap:8px; background:#1a1a1a;
    border:1px solid #c9a84c33; border-radius:30px; padding:5px 14px 5px 8px;
    margin:4px; font-size:0.82rem; color:#f0ece0; }

  /* Inventory */
  .inv-card { background:#111; border:1px solid #c9a84c33; border-radius:12px; padding:1.1rem;
    text-align:center; transition:all .2s; margin-bottom:4px; }
  .inv-card:hover { border-color:#c9a84c99; transform:translateY(-2px); }
  .inv-name { font-family:'Playfair Display',serif; font-size:0.88rem; color:#c9a84c; min-height:2.2rem; }
  .inv-qty { font-size:2rem; font-weight:700; color:#f0ece0; margin:0.2rem 0; }
  .inv-unit { font-size:0.7rem; letter-spacing:2px; color:#666; text-transform:uppercase; }
  .inv-bar { height:4px; border-radius:2px; margin-top:0.6rem; background:#222; overflow:hidden; }
  .inv-fill { height:100%; border-radius:2px; }

  .stRadio>div { gap:8px !important; }
  .stRadio label { color:#ccc !important; font-size:0.85rem !important; }
  hr { border:none; border-top:1px solid #c9a84c22; margin:1.4rem 0; }
  [data-testid="stDataEditor"] { border:1px solid #c9a84c33 !important; border-radius:10px !important; }
  .stSelectbox [data-baseweb="select"]>div { background:#1a1a1a !important; border-color:#c9a84c55 !important; }
  .stSelectbox svg { fill:#c9a84c !important; }

  /* ── Mobile & iPad Responsive ─────────────────────────────────────────── */
  /* iPad (portrait & landscape) */
  @media (max-width: 1024px) {
    .block-container { padding:1rem 1.2rem 1.5rem !important; max-width:100% !important; }
    .hero-title { font-size:2.2rem !important; letter-spacing:5px !important; }
    .stTabs [data-baseweb="tab"] { padding:8px 14px !important; font-size:0.72rem !important; }
    .checkout-price { font-size:2.2rem !important; }
  }

  /* Mobile phones */
  @media (max-width: 768px) {
    .block-container { padding:0.6rem 0.6rem 1rem !important; }
    .hero { padding:1.4rem 0.5rem 0.9rem !important; margin-bottom:1rem !important; }
    .hero-title { font-size:1.7rem !important; letter-spacing:4px !important; }
    .hero-sub { font-size:0.68rem !important; letter-spacing:2px !important; }

    /* Tabs: horizontal scroll on mobile */
    .stTabs [data-baseweb="tab-list"] {
      overflow-x:auto !important; flex-wrap:nowrap !important;
      -webkit-overflow-scrolling:touch !important; scrollbar-width:none !important;
      padding:4px !important; gap:2px !important;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display:none !important; }
    .stTabs [data-baseweb="tab"] {
      padding:7px 10px !important; font-size:0.65rem !important;
      white-space:nowrap !important; letter-spacing:1px !important;
    }

    /* Cards */
    .card { padding:1rem 1rem !important; }
    .card-title { font-size:1rem !important; }

    /* Larger touch targets for buttons */
    .stButton>button { padding:0.85rem 1rem !important; font-size:0.82rem !important;
      min-height:48px !important; }

    /* Stat boxes */
    .stat-val { font-size:1.3rem !important; }
    .stat-lbl { font-size:0.62rem !important; }
    .stat-box { padding:0.8rem 0.6rem !important; }

    /* Checkout */
    .checkout-box { padding:1rem 1rem !important; }
    .checkout-price { font-size:2rem !important; }
    .checkout-customer { font-size:0.9rem !important; }

    /* Inventory cards */
    .inv-qty { font-size:1.5rem !important; }

    /* Stylist cards */
    .sched-card { padding:0.9rem 1rem !important; }

    /* Inputs: bigger for touch */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div,
    .stDateInput>div>div>input,
    .stNumberInput>div>div>input {
      font-size:16px !important; /* prevents iOS auto-zoom */
      min-height:44px !important;
    }

    /* Fix number input spinner buttons on mobile */
    .stNumberInput [data-testid="stNumberInputContainer"] button {
      min-width:44px !important; min-height:44px !important;
    }

    /* Radio buttons: bigger tap area */
    .stRadio>div { gap:12px !important; }
    .stRadio label { font-size:0.9rem !important; padding:6px 0 !important; }

    /* Data editor: allow horizontal scroll */
    [data-testid="stDataEditor"] { overflow-x:auto !important; }

    hr { margin:1rem 0 !important; }
  }

  /* Small phones */
  @media (max-width: 400px) {
    .hero-title { font-size:1.35rem !important; letter-spacing:3px !important; }
    .stTabs [data-baseweb="tab"] { padding:6px 8px !important; font-size:0.6rem !important; }
    .checkout-price { font-size:1.7rem !important; }
  }
</style>
""", unsafe_allow_html=True)

# ── Language & Reference Data ─────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "zh"

SERVICES = {
    "zh": {"剪髮": 50, "染髮": 180, "頭皮護理": 120, "燙髮": 250, "角蛋白護理": 350, "頭皮SPA": 100},
    "en": {"Haircut": 50, "Hair Coloring": 180, "Scalp Treatment": 120,
           "Perm": 250, "Keratin Treatment": 350, "Scalp SPA": 100},
}
# Canonical service names (ZH <-> EN mapping)
SVC_ZH_EN = {"剪髮":"Haircut","染髮":"Hair Coloring","頭皮護理":"Scalp Treatment",
              "燙髮":"Perm","角蛋白護理":"Keratin Treatment","頭皮SPA":"Scalp SPA"}
SVC_EN_ZH = {v: k for k, v in SVC_ZH_EN.items()}
SVC_ALL_ZH = list(SVC_ZH_EN.keys())  # canonical service name list

def _canonical_svc(svc: str) -> str:
    """Normalise a service name to ZH canonical form."""
    if svc in SVC_ZH_EN:
        return svc
    return SVC_EN_ZH.get(svc, svc)
CATS  = {"zh": ["造型品","定型噴霧","染髮劑","護髮品","漂髮","頭皮護理"],
         "en": ["Styling","Setting Spray","Hair Color","Hair Care","Bleach","Scalp Care"]}
UNITS = {"zh": ["瓶","管","盒","罐","組"], "en": ["bottle","tube","box","can","set"]}

PAY_METHODS = {
    "Cash":        ("Cash 現金",    "💵", "#2ecc71"),
    "Visa/Card":   ("Visa / Card",  "💳", "#3498db"),
    "Touch 'n Go": ("Touch 'n Go", "📱", "#e74c3c"),
    "DuitNow QR":  ("DuitNow QR",  "📲", "#9b59b6"),
}

# Avatar colours cycling for stylists
STYLIST_COLORS = ["#c9a84c","#3498db","#e74c3c","#2ecc71","#9b59b6","#e67e22","#1abc9c","#e91e8c"]

UI = {
    "zh": {
        "subtitle":      "髮廊智能管理系統 · Malaysia",
        "lang_btn":      "🌐 English",
        "tab1":          "  ✂  預約管理  ",
        "tab2":          "  💇  髮型師  ",
        "tab3":          "  💳  收費  ",
        "tab4":          "  📦  庫存  ",
        "tab5":          "  📊  結算  ",
        # Booking
        "new_booking":   "＋ 新增預約",
        "client_name":   "客戶姓名",
        "name_ph":       "請輸入全名",
        "book_date":     "預約日期",
        "book_time":     "預約時間",
        "stylist":       "髮型師",
        "service":       "服務項目",
        "note":          "備註（選填）",
        "note_ph":       "例如：過敏史、頭髮狀況…",
        "confirm_btn":   "確認預約 →",
        "name_warn":     "請輸入客戶姓名",
        "online_pending": "待確認網上預約",
        "any_stylist":    "不指定髮型師",
        "cancel":         "拒絕",
        "book_list":     "📅 預約名單",
        "save_bookings": "儲存更改",
        "bookings_saved":"✦ 預約已更新",
        "no_bookings":   "尚無預約記錄",
        "col_name":      "姓名",
        "col_date":      "日期",
        "col_time":      "時間",
        "col_stylist":   "髮型師",
        "col_service":   "服務",
        "col_note":      "備註",
        # Stylist
        "sty_title":     "💇 髮型師管理",
        "sty_roster":    "髮型師名單",
        "sty_add":       "新增髮型師",
        "sty_name_lbl":  "名稱",
        "sty_name_ph":   "例如：Kim",
        "sty_add_btn":   "新增 →",
        "sty_name_warn": "請輸入髮型師名稱",
        "sty_added":     "✦ 已新增 **{}**",
        "sty_removed":   "✦ 已移除 **{}**",
        "sty_schedule":  "今日排班",
        "sty_filter":    "篩選髮型師",
        "sty_all":       "全部",
        "sty_no_bk":     "今日無預約",
        "sty_clients":   "位客戶",
        "sty_remove":    "移除",
        "sty_view_sched":"📅 排班",
        "sty_view_perf": "📊 業績",
        "sty_view_comm": "💰 抽成設定",
        "perf_title":    "📊 業績排行",
        "perf_today_rev":"今日業績",
        "perf_total_rev":"累計業績",
        "perf_clients":  "接待人次",
        "perf_top_svc":  "最多服務",
        "perf_avg":      "平均客單價",
        "perf_rank":     "排行",
        "perf_no_data":  "尚無業績記錄（未有結帳數據）",
        "comm_title":    "💰 抽成比例設定",
        "comm_desc":     "為每位髮型師的每種服務設定抽成百分比（%）",
        "comm_save":     "儲存抽成設定",
        "comm_saved":    "✦ 抽成設定已儲存",
        "comm_svc":      "服務",
        "comm_rate":     "比例 (%)",
        "comm_no_sty":   "請先在左側新增髮型師",
        "comm_report_title": "💰 抽成報表",
        "comm_stylist":  "髮型師",
        "comm_service":  "服務",
        "comm_revenue":  "業績收入",
        "comm_rate_col": "抽成 %",
        "comm_amount":   "抽成金額",
        "comm_subtotal": "小計",
        "comm_grand":    "合計",
        "comm_period":   "報表期間",
        "comm_export":   "匯出抽成報表 (Excel)",
        "comm_no_data":  "所選期間沒有已結帳記錄",
        # Payment
        "pay_title":     "💳 今日收費",
        "stat_paid":     "已收款",
        "stat_pending":  "待收款",
        "stat_total":    "今日總計",
        "stat_count":    "今日客數",
        "pending_list":  "⏳ 待付款",
        "no_pending":    "✦ 今日所有預約已結清",
        "checkout_title":"結帳",
        "select_booking":"選擇預約",
        "pay_method":    "付款方式",
        "confirm_pay":   "確認收款 →",
        "pay_success":   "✦ 已收款 RM {:.2f}（{}）",
        "history_title": "📋 今日收款記錄",
        "breakdown_title":"付款方式分佈",
        "disc_label":    "折扣 Discount (%)",
        "extra_label":   "額外收費 Extra (RM)",
        "walkin_title":  "即場客收費",
        "wi_svc_ph":     "剪髮 / 染髮 / 護理…",
        "wi_amt_label":  "金額 (RM)",
        "wi_confirm":    "收款 →",
        "mode_booked":   "預約客戶",
        "mode_walkin":   "即場客 Walk-in",
        # Inventory
        "inv_title":     "📦 產品庫存",
        "add_product":   "＋ 新增產品",
        "p_name":        "產品名稱",
        "p_name_ph":     "例如：OSiS+ Dust It",
        "p_cat":         "分類",
        "p_qty":         "數量",
        "p_max":         "最大庫存",
        "p_unit":        "單位",
        "add_btn":       "新增產品 →",
        "name_req":      "請輸入產品名稱",
        "add_success":   "✦ 已新增 **{}**",
        "low_warn":      "⚠ 庫存不足警告：{}",
        "filter":        "分類篩選",
        "search":        "搜尋產品",
        "search_ph":     "輸入產品名稱…",
        "all_cat":       "全部",
        "edit_section":  "✏  編輯 / 刪除庫存",
        "save_inv":      "儲存庫存更改",
        "inv_saved":     "✦ 庫存已更新",
        "remain":        "剩餘",
        "col_pname":     "產品名稱",
        "col_pcat":      "分類",
        "col_pqty":      "數量",
        "col_pmax":      "最大庫存",
        "col_punit":     "單位",
        # Settlement
        "settle_title":   "📊 結算報告",
        "settle_mode_day":  "📅 每日結算",
        "settle_mode_mth":  "📆 每月結算",
        "settle_mode_comm": "💰 抽成報表",
        "settle_date":    "選擇結算日期",
        "settle_month":   "選擇月份",
        "settle_mth_title":"📆 每月結算報告",
        "settle_clients": "總客數",
        "settle_daily_bk":"每日收款明細",
        "col_s_date":     "日期",
        "col_s_clients":  "客數",
        "settle_total":   "結算總額",
        "settle_paid":    "已收款",
        "settle_pending": "待收款",
        "settle_walkin":  "即場客",
        "settle_detail":  "收款明細",
        "settle_sty":     "髮型師業績",
        "settle_svc":     "服務統計",
        "settle_method":  "付款方式統計",
        "settle_no_data": "所選日期無收款記錄",
        "settle_export":  "📥 匯出 Excel",
        "settle_exporting":"正在生成…",
        "col_s_name":     "客戶姓名",
        "col_s_stylist":  "髮型師",
        "col_s_svc":      "服務",
        "col_s_method":   "付款方式",
        "col_s_amt":      "金額 (RM)",
        "col_s_type":     "類型",
        "col_s_count":    "人次",
        "col_s_rev":      "業績 (RM)",
        "col_s_avg":      "平均 (RM)",
        # Members
        "tab6":           "  👥  會員  ",
        "mem_title":      "👥 會員管理",
        "mem_add":        "＋ 新增會員",
        "mem_name":       "姓名",
        "mem_name_ph":    "例如：Siti Aminah",
        "mem_phone":      "電話號碼",
        "mem_phone_ph":   "例如：012-3456789",
        "mem_bday":       "生日（選填）",
        "mem_notes":      "備注（頭髮狀況、過敏等）",
        "mem_notes_ph":   "例如：對氨水過敏，頭髮細軟…",
        "mem_add_btn":    "新增會員 →",
        "mem_name_warn":  "請輸入會員姓名",
        "mem_added":      "✦ 已新增會員 **{}**",
        "mem_search":     "搜尋會員",
        "mem_search_ph":  "輸入姓名或電話…",
        "mem_no_result":  "找不到符合的會員",
        "mem_no_members": "尚無會員資料",
        "mem_select":     "點選會員查看詳情",
        "mem_detail":     "會員詳情",
        "mem_tier":       "等級",
        "mem_points":     "積分",
        "mem_spent":      "累計消費 (RM)",
        "mem_visits":     "到訪次數",
        "mem_joined":     "加入日期",
        "mem_edit_notes": "更新備注",
        "mem_save_notes": "儲存備注",
        "mem_notes_saved":"✦ 備注已儲存",
        "mem_delete":     "刪除會員",
        "mem_deleted":    "✦ 已刪除會員 **{}**",
        "mem_history":    "消費記錄",
        "mem_no_history": "尚無消費記錄",
        "mem_stats":      "會員總覽",
        "mem_total":      "總會員數",
        "mem_vip_count":  "VIP 會員",
        "mem_pts_issued": "已發積分",
        "mem_tier_up":    "✦ {} 已升級至 {}！",
        "mem_disc_hint":  "會員折扣 {}%",
        "mem_lookup":     "會員查詢（選填）",
        "mem_pts_added":  "已為 {} 累加 {} 積分",
        # Receipt
        "rcpt_btn":       "🧾 收據",
        "rcpt_title":     "收據",
        "rcpt_print":     "🖨️ 列印收據",
        "rcpt_email":     "📧 Email 收據",
        "rcpt_email_to":  "收件人 Email",
        "rcpt_email_ph":  "例如：client@email.com",
        "rcpt_send":      "發送 →",
        "rcpt_sent":      "✦ 郵件已開啟，請在郵件 App 確認發送",
        "rcpt_close":     "關閉",
        "rcpt_service":   "服務",
        "rcpt_stylist":   "髮型師",
        "rcpt_subtotal":  "小計",
        "rcpt_discount":  "折扣",
        "rcpt_total":     "總計",
        "rcpt_method":    "付款方式",
        "rcpt_member":    "會員",
        "rcpt_pts":       "本次積分",
        "rcpt_thanks":    "感謝您的光臨，期待再次為您服務！",
        "rcpt_no_sel":    "請先從收款記錄中選擇一筆收據",
    },
    "en": {
        "subtitle":      "Salon Management System · Malaysia",
        "lang_btn":      "🌐 中文",
        "tab1":          "  ✂  Bookings  ",
        "tab2":          "  💇  Stylists  ",
        "tab3":          "  💳  Payment  ",
        "tab4":          "  📦  Inventory  ",
        "tab5":          "  📊  Report  ",
        "new_booking":   "＋ New Booking",
        "client_name":   "Client Name",
        "name_ph":       "Enter full name",
        "book_date":     "Date",
        "book_time":     "Time",
        "stylist":       "Stylist",
        "service":       "Service",
        "note":          "Notes (optional)",
        "note_ph":       "e.g. allergies, hair condition…",
        "confirm_btn":   "Confirm Booking →",
        "name_warn":     "Please enter client name",
        "online_pending": "Online Booking Requests",
        "any_stylist":    "No preference",
        "cancel":         "Decline",
        "book_list":     "📅 Booking List",
        "save_bookings": "Save Changes",
        "bookings_saved":"✦ Bookings updated",
        "no_bookings":   "No bookings yet",
        "col_name":      "Name",
        "col_date":      "Date",
        "col_time":      "Time",
        "col_stylist":   "Stylist",
        "col_service":   "Service",
        "col_note":      "Notes",
        "sty_title":     "💇 Stylist Management",
        "sty_roster":    "Stylist Roster",
        "sty_add":       "Add Stylist",
        "sty_name_lbl":  "Name",
        "sty_name_ph":   "e.g. Kim",
        "sty_add_btn":   "Add →",
        "sty_name_warn": "Please enter stylist name",
        "sty_added":     "✦ Added **{}**",
        "sty_removed":   "✦ Removed **{}**",
        "sty_schedule":  "Today's Schedule",
        "sty_filter":    "Filter Stylist",
        "sty_all":       "All",
        "sty_no_bk":     "No bookings today",
        "sty_clients":   "client(s)",
        "sty_remove":    "Remove",
        "sty_view_sched":"📅 Schedule",
        "sty_view_perf": "📊 Performance",
        "sty_view_comm": "💰 Commission Rates",
        "perf_title":    "📊 Performance Ranking",
        "perf_today_rev":"Today's Revenue",
        "perf_total_rev":"Total Revenue",
        "perf_clients":  "Clients Served",
        "perf_top_svc":  "Top Service",
        "perf_avg":      "Avg. Per Client",
        "perf_rank":     "Rank",
        "perf_no_data":  "No performance data yet (no completed payments)",
        "comm_title":    "💰 Commission Rate Settings",
        "comm_desc":     "Set the commission percentage (%) for each stylist per service",
        "comm_save":     "Save Commission Rates",
        "comm_saved":    "✦ Commission rates saved",
        "comm_svc":      "Service",
        "comm_rate":     "Rate (%)",
        "comm_no_sty":   "Please add stylists on the left first",
        "comm_report_title": "💰 Commission Report",
        "comm_stylist":  "Stylist",
        "comm_service":  "Service",
        "comm_revenue":  "Revenue",
        "comm_rate_col": "Commission %",
        "comm_amount":   "Commission",
        "comm_subtotal": "Subtotal",
        "comm_grand":    "Grand Total",
        "comm_period":   "Report Period",
        "comm_export":   "Export Commission Report (Excel)",
        "comm_no_data":  "No completed payments in selected period",
        "pay_title":     "💳 Payment",
        "stat_paid":     "Collected",
        "stat_pending":  "Pending",
        "stat_total":    "Total Today",
        "stat_count":    "Clients Today",
        "pending_list":  "⏳ Pending",
        "no_pending":    "✦ All payments collected",
        "checkout_title":"Checkout",
        "select_booking":"Select Booking",
        "pay_method":    "Payment Method",
        "confirm_pay":   "Confirm Payment →",
        "pay_success":   "✦ Received RM {:.2f} ({})",
        "history_title": "📋 Payment History Today",
        "breakdown_title":"Payment Breakdown",
        "disc_label":    "Discount (%)",
        "extra_label":   "Extra Charge (RM)",
        "walkin_title":  "Walk-in Payment",
        "wi_svc_ph":     "Haircut / Colour / Treatment…",
        "wi_amt_label":  "Amount (RM)",
        "wi_confirm":    "Collect →",
        "mode_booked":   "Booked Client",
        "mode_walkin":   "Walk-in Client",
        "inv_title":     "📦 Product Inventory",
        "add_product":   "＋ Add Product",
        "p_name":        "Product Name",
        "p_name_ph":     "e.g. OSiS+ Dust It",
        "p_cat":         "Category",
        "p_qty":         "Quantity",
        "p_max":         "Max Stock",
        "p_unit":        "Unit",
        "add_btn":       "Add Product →",
        "name_req":      "Please enter product name",
        "add_success":   "✦ Added **{}**",
        "low_warn":      "⚠ Low Stock: {}",
        "filter":        "Filter",
        "search":        "Search",
        "search_ph":     "Enter product name…",
        "all_cat":       "All",
        "edit_section":  "✏  Edit / Delete Inventory",
        "save_inv":      "Save Changes",
        "inv_saved":     "✦ Inventory updated",
        "remain":        "remaining",
        "col_pname":     "Product",
        "col_pcat":      "Category",
        "col_pqty":      "Qty",
        "col_pmax":      "Max",
        "col_punit":     "Unit",
        # Settlement
        "settle_title":   "📊 Settlement Report",
        "settle_mode_day":  "📅 Daily",
        "settle_mode_mth":  "📆 Monthly",
        "settle_mode_comm": "💰 Commission",
        "settle_date":    "Select Date",
        "settle_month":   "Select Month",
        "settle_mth_title":"📆 Monthly Settlement Report",
        "settle_clients": "Total Clients",
        "settle_daily_bk":"Daily Breakdown",
        "col_s_date":     "Date",
        "col_s_clients":  "Clients",
        "settle_total":   "Total Revenue",
        "settle_paid":    "Collected",
        "settle_pending": "Pending",
        "settle_walkin":  "Walk-ins",
        "settle_detail":  "Payment Details",
        "settle_sty":     "Stylist Performance",
        "settle_svc":     "Service Summary",
        "settle_method":  "Payment Methods",
        "settle_no_data": "No payment records for this date",
        "settle_export":  "📥 Export Excel",
        "settle_exporting":"Generating…",
        "col_s_name":     "Client",
        "col_s_stylist":  "Stylist",
        "col_s_svc":      "Service",
        "col_s_method":   "Method",
        "col_s_amt":      "Amount (RM)",
        "col_s_type":     "Type",
        "col_s_count":    "Count",
        "col_s_rev":      "Revenue (RM)",
        "col_s_avg":      "Average (RM)",
        # Members
        "tab6":           "  👥  Members  ",
        "mem_title":      "👥 Member Management",
        "mem_add":        "＋ Add Member",
        "mem_name":       "Name",
        "mem_name_ph":    "e.g. Siti Aminah",
        "mem_phone":      "Phone",
        "mem_phone_ph":   "e.g. 012-3456789",
        "mem_bday":       "Birthday (optional)",
        "mem_notes":      "Notes (hair condition, allergies, etc.)",
        "mem_notes_ph":   "e.g. Sensitive to ammonia, fine hair…",
        "mem_add_btn":    "Add Member →",
        "mem_name_warn":  "Please enter member name",
        "mem_added":      "✦ Member **{}** added",
        "mem_search":     "Search Members",
        "mem_search_ph":  "Enter name or phone…",
        "mem_no_result":  "No matching members",
        "mem_no_members": "No members yet",
        "mem_select":     "Select a member to view details",
        "mem_detail":     "Member Profile",
        "mem_tier":       "Tier",
        "mem_points":     "Points",
        "mem_spent":      "Total Spent (RM)",
        "mem_visits":     "Visit Count",
        "mem_joined":     "Member Since",
        "mem_edit_notes": "Update Notes",
        "mem_save_notes": "Save Notes",
        "mem_notes_saved":"✦ Notes saved",
        "mem_delete":     "Delete Member",
        "mem_deleted":    "✦ Member **{}** deleted",
        "mem_history":    "Spending History",
        "mem_no_history": "No spending history yet",
        "mem_stats":      "Member Overview",
        "mem_total":      "Total Members",
        "mem_vip_count":  "VIP Members",
        "mem_pts_issued": "Points Issued",
        "mem_tier_up":    "✦ {} upgraded to {}!",
        "mem_disc_hint":  "{}% member discount",
        "mem_lookup":     "Member Lookup (optional)",
        "mem_pts_added":  "Added {} pts to {}",
        # Receipt
        "rcpt_btn":       "🧾 Receipt",
        "rcpt_title":     "Receipt",
        "rcpt_print":     "🖨️ Print Receipt",
        "rcpt_email":     "📧 Email Receipt",
        "rcpt_email_to":  "Recipient Email",
        "rcpt_email_ph":  "e.g. client@email.com",
        "rcpt_send":      "Send →",
        "rcpt_sent":      "✦ Email app opened — confirm to send",
        "rcpt_close":     "Close",
        "rcpt_service":   "Service",
        "rcpt_stylist":   "Stylist",
        "rcpt_subtotal":  "Subtotal",
        "rcpt_discount":  "Discount",
        "rcpt_total":     "Total",
        "rcpt_method":    "Payment",
        "rcpt_member":    "Member",
        "rcpt_pts":       "Points Earned",
        "rcpt_thanks":    "Thank you for visiting — we look forward to seeing you again!",
        "rcpt_no_sel":    "Select a receipt from the payment history",
    },
}

def u(key):    return UI[st.session_state.lang][key]
def svc_map(): return SERVICES[st.session_state.lang]
def bar_color(r): return "#2ecc71" if r > 0.6 else ("#e67e22" if r > 0.3 else "#e74c3c")

# ── Member tier system ────────────────────────────────────────────────────────
TIERS = [
    {"key": "普通",  "en": "Regular", "min_pts": 0,    "disc": 0,    "color": "#888888", "badge": "⚪"},
    {"key": "銀卡",  "en": "Silver",  "min_pts": 500,  "disc": 5,    "color": "#adb5bd", "badge": "🥈"},
    {"key": "金卡",  "en": "Gold",    "min_pts": 1500, "disc": 10,   "color": "#c9a84c", "badge": "🥇"},
    {"key": "VIP",   "en": "VIP",     "min_pts": 3000, "disc": 15,   "color": "#e74c3c", "badge": "💎"},
]

def tier_for_points(pts):
    t = TIERS[0]
    for tier in TIERS:
        if pts >= tier["min_pts"]:
            t = tier
    return t

def tier_label(tier_dict):
    return tier_dict["en"] if st.session_state.lang == "en" else tier_dict["key"]

# ── Cookie manager for persistent login ──────────────────────────────────────
try:
    from streamlit_cookies_controller import CookieController as _CookieController
    _cookie_mgr = _CookieController()
    _COOKIES_OK = True
except Exception:
    _cookie_mgr = None
    _COOKIES_OK = False

def _save_login_cookie(username: str):
    if _COOKIES_OK and _cookie_mgr:
        try:
            from datetime import datetime, timedelta
            _cookie_mgr.set("sk_user", username,
                            expires=datetime.now() + timedelta(days=7))
        except Exception:
            pass

def _clear_login_cookie():
    if _COOKIES_OK and _cookie_mgr:
        try:
            _cookie_mgr.remove("sk_user")
        except Exception:
            pass

def _get_cookie_user() -> str:
    if _COOKIES_OK and _cookie_mgr:
        try:
            return _cookie_mgr.get("sk_user") or ""
        except Exception:
            pass
    return ""

# ── Auth session state ────────────────────────────────────────────────────────
if "logged_in"  not in st.session_state: st.session_state.logged_in  = False
if "username"   not in st.session_state: st.session_state.username   = ""
if "role"       not in st.session_state: st.session_state.role       = ""
if "user_name"  not in st.session_state: st.session_state.user_name  = ""
if "cur_branch" not in st.session_state: st.session_state.cur_branch = ""
if "accounts"   not in st.session_state: st.session_state.accounts   = dict(_DEFAULT_ACCOUNTS)
if "branches"   not in st.session_state: st.session_state.branches   = dict(_DEFAULT_BRANCHES)

# ── Auto-login from cookie ────────────────────────────────────────────────────
if not st.session_state.logged_in:
    _cookie_user = _get_cookie_user()
    if _cookie_user:
        if _USE_DB:
            try: db_load_branches_and_accounts()
            except Exception: pass
        acct = st.session_state.accounts.get(_cookie_user)
        if acct:
            st.session_state.logged_in = True
            st.session_state.username  = _cookie_user
            st.session_state.role      = acct["role"]
            st.session_state.user_name = acct["name"]
            branch = acct["branch"]
            if branch == "all":
                branch = next(iter(st.session_state.branches), "B001")
            st.session_state.cur_branch = branch
            _init_branch(branch)
            if _USE_DB:
                try:
                    data = db_load_salon(branch)
                    st.session_state.branch_data[branch] = data
                except Exception:
                    pass

# ── Branch-scoped data: keyed by branch_id ────────────────────────────────────
def _init_branch(bid: str):
    bd = st.session_state.setdefault("branch_data", {})
    if bid not in bd:
        bd[bid] = {
            "stylists":    ["Kim", "Lily", "Jason"],
            "bookings":    [],
            "walkins":     [],
            "members":     [],
            "commissions": {},
            "inventory": [
                {"name":"OSiS+ Dust It",        "category":"造型品",   "qty":14,"max":30,"unit":"瓶"},
                {"name":"OSiS+ Freeze",          "category":"定型噴霧","qty":7, "max":24,"unit":"瓶"},
                {"name":"Schwarzkopf IGORA",     "category":"染髮劑",  "qty":22,"max":50,"unit":"管"},
                {"name":"Fibre Clinix 蛋白護理", "category":"護髮品",  "qty":5, "max":20,"unit":"瓶"},
                {"name":"BLONDME 漂髮粉",        "category":"漂髮",    "qty":9, "max":25,"unit":"盒"},
                {"name":"OSiS+ Session Label",   "category":"造型品",  "qty":18,"max":30,"unit":"瓶"},
                {"name":"Chroma ID 酸性染",      "category":"染髮劑",  "qty":31,"max":60,"unit":"管"},
                {"name":"Scalp Clinix 頭皮精華", "category":"頭皮護理","qty":3, "max":15,"unit":"瓶"},
            ],
        }

def _bd():
    """Return current branch data dict."""
    _init_branch(st.session_state.cur_branch)
    return st.session_state.branch_data[st.session_state.cur_branch]

# Backwards-compat shims so existing code using st.session_state.bookings works:
# We'll keep them as properties pointing into branch_data.
def _sync_ss():
    """Sync top-level session state aliases to current branch."""
    bd = _bd()
    st.session_state.stylists    = bd["stylists"]
    st.session_state.bookings    = bd["bookings"]
    st.session_state.walkins     = bd["walkins"]
    st.session_state.members     = bd["members"]
    st.session_state.inventory   = bd["inventory"]
    st.session_state.commissions = bd.setdefault("commissions", {})

if "sel_member_id" not in st.session_state: st.session_state.sel_member_id = None
if "sel_receipt"   not in st.session_state: st.session_state.sel_receipt   = None

TIME_SLOTS     = [f"{h:02d}:{m:02d}" for h in range(9, 20) for m in (0, 30)]
HIDDEN_BK_COLS = ["price", "paid", "method", "final"]

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.markdown(f"""
    <div style="max-width:420px;margin:6vh auto;padding:2.5rem 2.8rem;
    background:#111;border:1px solid #c9a84c44;border-radius:16px;text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;
      letter-spacing:6px;background:linear-gradient(135deg,#c9a84c,#f5e19a,#c9a84c);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
        IQ SALON</div>
      <div style="font-size:0.7rem;letter-spacing:3px;color:#555;margin:4px 0 24px;
      text-transform:uppercase;">Salon Management System</div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        col = st.columns([1, 2, 1])[1]
        with col:
            lg_user = st.text_input("👤 Username / 用戶名", key="lg_user", placeholder="username")
            lg_pass = st.text_input("🔑 Password / 密碼",   key="lg_pass", placeholder="password", type="password")
            if st.button("Login / 登入", key="login_btn", use_container_width=True):
                uname = lg_user.strip()
                ph    = _hash(lg_pass)
                acct  = None

                if _USE_DB:
                    # Load branches + accounts from DB first
                    try:
                        db_load_branches_and_accounts()
                    except Exception as e:
                        st.error(f"Database error: {e}")
                        st.stop()

                acct = st.session_state.accounts.get(uname)
                if acct and acct["hash"] == ph:
                    st.session_state.logged_in  = True
                    st.session_state.username   = uname
                    st.session_state.role       = acct["role"]
                    st.session_state.user_name  = acct["name"]
                    branch = acct["branch"]
                    if branch == "all":
                        branch = next(iter(st.session_state.branches), "B001")
                    st.session_state.cur_branch = branch
                    _init_branch(branch)

                    if _USE_DB:
                        # Load real data from Supabase
                        try:
                            data = db_load_salon(branch)
                            st.session_state.branch_data[branch] = data
                        except Exception as e:
                            st.warning(f"Could not load data: {e}")

                    _save_login_cookie(uname)
                    _sync_ss()
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤 / Wrong username or password")
    st.stop()

# ── Logged in — sync data aliases ────────────────────────────────────────────
_sync_ss()

# ── Subscription status check (skip for owner — they manage the system) ───────
import datetime as _sub_dt

def _get_sub_status(salon_id: str) -> dict:
    """Return subscription status for current branch."""
    info = st.session_state.get("salon_info", {}).get(salon_id, {})
    plan       = info.get("plan", "trial")
    trial_ends = info.get("trial_ends")
    plan_ends  = info.get("plan_ends")
    today      = _sub_dt.date.today()

    if plan == "active":
        if plan_ends:
            end = _sub_dt.date.fromisoformat(str(plan_ends))
            days_left = (end - today).days
            return {"ok": True, "plan": "active", "days_left": days_left, "ends": end}
        return {"ok": True, "plan": "active", "days_left": 999, "ends": None}

    if plan == "trial" or not plan:
        if trial_ends:
            end = _sub_dt.date.fromisoformat(str(trial_ends))
            days_left = (end - today).days
            if days_left >= 0:
                return {"ok": True, "plan": "trial", "days_left": days_left, "ends": end}
        return {"ok": False, "plan": "expired", "days_left": 0, "ends": None}

    return {"ok": False, "plan": "expired", "days_left": 0, "ends": None}

_sub = _get_sub_status(st.session_state.cur_branch) if st.session_state.role != "owner" else {"ok": True, "plan": "owner", "days_left": 999, "ends": None}

# ── Subscription expired page ─────────────────────────────────────────────────
if not _sub["ok"] and st.session_state.role != "owner":
    stripe_link = st.session_state.get("salon_info", {}).get(
        st.session_state.cur_branch, {}).get("stripe_link", "")
    is_zh = st.session_state.lang == "zh"
    st.markdown(f"""
    <div style="max-width:480px;margin:8vh auto;background:#111;border:1px solid #e74c3c55;
      border-radius:16px;padding:2.5rem 2.8rem;text-align:center;">
      <div style="font-size:3rem;margin-bottom:1rem">🔒</div>
      <div style="font-family:'Playfair Display',serif;font-size:1.5rem;color:#e74c3c;
        letter-spacing:3px;margin-bottom:0.8rem">
        {"訂閱已到期" if is_zh else "Subscription Expired"}
      </div>
      <div style="color:#888;font-size:0.88rem;line-height:1.8;margin-bottom:1.5rem">
        {"您的試用期已結束，請訂閱以繼續使用所有功能。" if is_zh else
         "Your trial has ended. Please subscribe to continue using all features."}
      </div>
      {'<a href="' + stripe_link + '" target="_blank" style="display:inline-block;' +
       'background:linear-gradient(135deg,#c9a84c,#a07830);color:#0a0a0a;font-weight:700;' +
       'font-size:0.9rem;letter-spacing:2px;text-transform:uppercase;padding:1rem 2.5rem;' +
       'border-radius:8px;text-decoration:none;margin-bottom:1rem">💳 ' +
       ("立即訂閱" if is_zh else "Subscribe Now") + '</a>'
       if stripe_link else
       '<div style="background:#1a1a1a;border:1px solid #c9a84c33;border-radius:8px;' +
       'padding:1rem;color:#888;font-size:0.82rem">' +
       ("請聯絡管理員啟用訂閱。" if is_zh else "Please contact admin to activate your subscription.") +
       '</div>'}
      <div style="margin-top:1.5rem;color:#555;font-size:0.75rem">
        {"或聯絡 Signature Kim 支援" if is_zh else "Or contact Signature Kim support"}
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚪 " + ("登出" if is_zh else "Logout"), key="exp_logout"):
        _clear_login_cookie()
        for k in ["logged_in","username","role","user_name","cur_branch"]:
            if k in st.session_state: del st.session_state[k]
        st.rerun()
    st.stop()

# ── Auto-refresh: reload bookings from Supabase on each refresh cycle ─────────
if _USE_DB and _auto_refresh_count > 0:
    try:
        branch = st.session_state.cur_branch
        fresh_bookings = db_get_bookings(branch) if branch else []
        if fresh_bookings is not None:
            st.session_state.branch_data[branch]["bookings"] = fresh_bookings
            _sync_ss()
    except Exception:
        pass

# ── Header ────────────────────────────────────────────────────────────────────
hdr_l, hdr_m, hdr_r = st.columns([2, 3, 2])
with hdr_l:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    # Branch selector (owner sees all branches)
    if _can("view_all") and len(st.session_state.branches) > 1:
        branch_opts  = list(st.session_state.branches.keys())
        branch_names = [st.session_state.branches[b] for b in branch_opts]
        cur_idx      = branch_opts.index(st.session_state.cur_branch) if st.session_state.cur_branch in branch_opts else 0
        chosen_name  = st.selectbox("🏠 分店", branch_names, index=cur_idx, key="branch_sel", label_visibility="collapsed")
        chosen_bid   = branch_opts[branch_names.index(chosen_name)]
        if chosen_bid != st.session_state.cur_branch:
            st.session_state.cur_branch = chosen_bid
            _init_branch(chosen_bid)
            _sync_ss()
            st.rerun()
    else:
        branch_name = st.session_state.branches.get(st.session_state.cur_branch, st.session_state.cur_branch)
        st.markdown(f"<div style='padding-top:8px;font-size:0.8rem;color:#c9a84c;letter-spacing:1px;'>🏠 {branch_name}</div>", unsafe_allow_html=True)

with hdr_r:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    role_icon = {"admin":"🔴","owner":"👑","manager":"💼","staff":"✂️"}.get(st.session_state.role,"👤")
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button(u("lang_btn"), key="lang_toggle"):
            st.session_state.lang = "en" if st.session_state.lang == "zh" else "zh"
            st.rerun()
    with rc2:
        if st.button(f"{role_icon} 登出", key="logout_btn"):
            _clear_login_cookie()
            for k in ["logged_in","username","role","user_name","cur_branch"]:
                del st.session_state[k]
            st.rerun()

# Build subscription badge for header
_sub_badge = ""
if _sub["plan"] == "trial" and _sub["days_left"] <= 7:
    _sub_badge = f'<span style="background:#e67e22;color:#fff;font-size:0.65rem;padding:3px 10px;border-radius:20px;letter-spacing:1px;margin-left:8px">⏳ {"試用期剩" if st.session_state.lang=="zh" else "Trial"} {_sub["days_left"]} {"天" if st.session_state.lang=="zh" else "days"}</span>'
elif _sub["plan"] == "trial":
    _sub_badge = f'<span style="background:#2ecc71;color:#0a0a0a;font-size:0.65rem;padding:3px 10px;border-radius:20px;letter-spacing:1px;margin-left:8px">✓ {"試用中" if st.session_state.lang=="zh" else "Trial"} {_sub["days_left"]}{"天" if st.session_state.lang=="zh" else "d"}</span>'
elif _sub["plan"] == "active":
    _sub_badge = f'<span style="background:#c9a84c;color:#0a0a0a;font-size:0.65rem;padding:3px 10px;border-radius:20px;letter-spacing:1px;margin-left:8px">✦ {"已訂閱" if st.session_state.lang=="zh" else "Subscribed"}</span>'

_salon_display = st.session_state.branches.get(st.session_state.cur_branch, "IQSALON")
st.markdown(f"""
<div class="hero">
  <p class="hero-title">✦ {_salon_display.upper()} ✦</p>
  <p class="hero-sub">{u('subtitle')} &nbsp;·&nbsp; {st.session_state.user_name} {role_icon}{_sub_badge}</p>
</div>
""", unsafe_allow_html=True)

# ── Receipt builder (Malaysian format) ───────────────────────────────────────
def build_receipt_html(r: dict, lang: str) -> str:
    """Return a printable Malaysian-format HTML receipt."""
    import datetime as _dt
    is_zh    = (lang == "zh")
    subtotal = float(r.get("subtotal", r.get("final", 0)) or 0)
    disc     = float(r.get("disc_pct", 0) or 0)
    extra    = float(r.get("extra", 0) or 0)
    final    = float(r.get("final", 0) or 0)
    member   = r.get("member", "")
    pts      = r.get("pts", 0)
    method   = r.get("method", "Cash")
    stylist  = r.get("stylist", "")
    date_iso = r.get("date", str(_dt.date.today()))
    time_str = r.get("time", "")
    name     = r.get("name", "")
    service  = r.get("service", "")
    salon    = r.get("salon", "IQSALON")

    # Malaysian date format: DD/MM/YYYY
    try:
        d = _dt.date.fromisoformat(date_iso)
        date_my = d.strftime("%d/%m/%Y")
    except Exception:
        date_my = date_iso

    # Receipt number: RCP-YYYYMMDD-XXXX
    receipt_no = f"RCP-{date_iso.replace('-','')}-{abs(hash(name + time_str)) % 10000:04d}"

    # Salon info from session state (if available)
    salon_info = {}
    try:
        sid = st.session_state.get("cur_branch", "")
        salon_info = st.session_state.get("salon_info", {}).get(sid, {})
    except Exception:
        pass
    salon_phone   = salon_info.get("contact_phone", "")
    salon_email   = salon_info.get("contact_email", "")
    salon_address = ", ".join(filter(None, [
        salon_info.get("address",""),
        salon_info.get("city",""),
        salon_info.get("postcode",""),
    ]))
    salon_ssm     = salon_info.get("ssm_no", "")
    salon_hours   = salon_info.get("operating_hours", "")
    salon_web     = salon_info.get("website", "")

    # Build item rows
    disc_amt  = round(subtotal * disc / 100, 2) if disc else 0
    rows_html = f"""
      <tr>
        <td class="desc">{service}</td>
        <td class="qty">1</td>
        <td class="price">RM {subtotal:.2f}</td>
        <td class="amt">RM {subtotal:.2f}</td>
      </tr>"""
    if extra:
        extra_lbl = "Caj Tambahan" if not is_zh else "加收費用"
        rows_html += f"""
      <tr>
        <td class="desc">{extra_lbl}</td>
        <td class="qty">1</td>
        <td class="price">RM {extra:.2f}</td>
        <td class="amt">RM {extra:.2f}</td>
      </tr>"""

    disc_row_html = ""
    if disc:
        disc_lbl = f"Diskaun {disc:.0f}%" if not is_zh else f"折扣 {disc:.0f}%"
        disc_row_html = f"""
      <tr class="disc-row">
        <td colspan="3">{disc_lbl}</td>
        <td class="amt" style="color:#c0392b;">- RM {disc_amt:.2f}</td>
      </tr>"""

    member_rows = ""
    if member:
        pts_lbl = f"Mata Ganjaran / 積分" if not is_zh else "積分"
        member_rows = f"""
      <tr class="info-row">
        <td colspan="2">{'Ahli / 會員' if not is_zh else '會員'}</td>
        <td colspan="2" style="text-align:right;">{member}</td>
      </tr>"""
        if pts:
            member_rows += f"""
      <tr class="info-row">
        <td colspan="2">{pts_lbl}</td>
        <td colspan="2" style="text-align:right;color:#2980b9;">+{pts} pts</td>
      </tr>"""

    stylist_row = ""
    if stylist:
        sty_lbl = "Penata Rambut / 髮型師" if not is_zh else "髮型師"
        stylist_row = f"""
      <tr class="info-row">
        <td colspan="2">{sty_lbl}</td>
        <td colspan="2" style="text-align:right;">{stylist}</td>
      </tr>"""

    pay_lbl   = "Kaedah Pembayaran" if not is_zh else "付款方式"
    total_lbl = "JUMLAH / TOTAL" if not is_zh else "總計"
    sst_note  = "Harga adalah termasuk SST / Harga tidak termasuk SST (Dikecualikan)" \
                if not is_zh else "價格已含/免收 SST（服務稅）"
    thanks_my = "Terima Kasih Kerana Sudi Hadir" if not is_zh else "感謝您的光臨"
    thanks_en = "We look forward to serving you again!" if not is_zh else "期待再次為您服務！"

    contact_parts = []
    if salon_address: contact_parts.append(f"📍 {salon_address}")
    if salon_phone:   contact_parts.append(f"📞 {salon_phone}")
    if salon_email:   contact_parts.append(f"✉ {salon_email}")
    if salon_web:     contact_parts.append(f"🌐 {salon_web}")
    contact_line = ("".join(f"<div class='contact'>{p}</div>" for p in contact_parts)
                    if contact_parts else "")

    footer_meta_parts = []
    if salon_ssm:   footer_meta_parts.append(f"SSM No: {salon_ssm}")
    if salon_hours: footer_meta_parts.append(f"{'Waktu Operasi' if not is_zh else '營業時間'}: {salon_hours}")
    footer_meta = ("<div class='footer-meta'>" + " &nbsp;·&nbsp; ".join(footer_meta_parts) + "</div>"
                   if footer_meta_parts else "")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Resit / Receipt — {salon}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Raleway:wght@300;400;600;700&display=swap');
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ font-family:'Raleway',sans-serif; background:#f5f5f5; color:#111;
        display:flex; justify-content:center; padding:24px 10px; }}
  .receipt{{ width:400px; background:#fff; box-shadow:0 2px 16px rgba(0,0,0,.12);
             border-radius:4px; overflow:hidden; }}
  /* Header */
  .header{{ background:#111; color:#fff; text-align:center; padding:22px 20px 16px; }}
  .salon-name{{ font-family:'Playfair Display',serif; font-size:1.6rem; font-weight:700;
                letter-spacing:4px; color:#c9a84c; }}
  .salon-sub{{ font-size:0.6rem; letter-spacing:3px; color:#aaa; margin-top:4px;
               text-transform:uppercase; }}
  .contact{{ font-size:0.72rem; color:#999; margin-top:6px; }}
  /* Metadata strip */
  .meta-strip{{ background:#1a1a1a; padding:10px 20px;
                display:flex; justify-content:space-between; align-items:center; }}
  .rcpt-no{{ color:#c9a84c; font-size:0.72rem; font-weight:700; letter-spacing:1px; }}
  .rcpt-date{{ color:#999; font-size:0.72rem; }}
  /* Body */
  .body{{ padding:18px 20px; }}
  /* Customer */
  .customer-box{{ background:#f9f9f9; border-left:3px solid #c9a84c;
                  padding:10px 12px; margin-bottom:14px; border-radius:0 4px 4px 0; }}
  .customer-label{{ font-size:0.65rem; color:#888; letter-spacing:2px; text-transform:uppercase;
                    margin-bottom:3px; }}
  .customer-name{{ font-size:1rem; font-weight:700; color:#111; }}
  .customer-time{{ font-size:0.72rem; color:#888; margin-top:2px; }}
  /* Items table */
  table{{ width:100%; border-collapse:collapse; margin-bottom:10px; }}
  thead tr{{ background:#f0f0f0; }}
  thead td{{ font-size:0.65rem; font-weight:700; letter-spacing:1px; text-transform:uppercase;
             color:#666; padding:7px 6px; }}
  tbody td{{ padding:8px 6px; font-size:0.82rem; border-bottom:1px solid #f0f0f0;
             vertical-align:top; }}
  td.desc{{ color:#111; }}
  td.qty{{ text-align:center; color:#888; width:30px; }}
  td.price{{ text-align:right; color:#888; width:80px; }}
  td.amt{{ text-align:right; font-weight:600; color:#111; width:80px; }}
  tr.disc-row td{{ font-size:0.78rem; color:#c0392b; border-bottom:1px solid #f0f0f0; padding:6px 6px; }}
  tr.info-row td{{ font-size:0.78rem; color:#666; border-bottom:1px dashed #f0f0f0; padding:5px 6px; }}
  /* Totals */
  .totals{{ background:#111; color:#fff; padding:12px 16px; border-radius:4px; margin:10px 0; }}
  .totals-row{{ display:flex; justify-content:space-between; align-items:center; }}
  .totals-label{{ font-size:0.72rem; letter-spacing:2px; color:#aaa; }}
  .totals-amount{{ font-family:'Playfair Display',serif; font-size:1.5rem; font-weight:700;
                   color:#c9a84c; }}
  /* Payment */
  .payment-row{{ display:flex; justify-content:space-between; padding:8px 0;
                 border-bottom:1px solid #eee; font-size:0.82rem; }}
  .payment-label{{ color:#888; }}
  .payment-val{{ font-weight:700; color:#111; }}
  /* SST */
  .sst-note{{ font-size:0.65rem; color:#bbb; text-align:center; margin:10px 0 6px;
              line-height:1.5; }}
  /* Footer */
  .footer{{ background:#111; text-align:center; padding:16px 20px; }}
  .thanks-main{{ font-family:'Playfair Display',serif; font-size:1rem; color:#c9a84c;
                 letter-spacing:2px; }}
  .thanks-sub{{ font-size:0.7rem; color:#888; margin-top:4px; }}
  .rcpt-stamp{{ font-size:0.6rem; color:#555; margin-top:8px; letter-spacing:1px; }}
  .footer-meta{{ font-size:0.65rem; color:#777; margin-top:6px; line-height:1.7; }}
  /* Print button */
  .print-btn{{ display:block; width:calc(100% - 40px); margin:16px 20px; padding:11px;
               background:#c9a84c; color:#fff; border:none; border-radius:4px;
               font-size:0.82rem; font-weight:700; letter-spacing:2px; cursor:pointer;
               font-family:'Raleway',sans-serif; text-transform:uppercase; }}
  .print-btn:hover{{ background:#a07830; }}
  @media print{{
    body{{ background:#fff; padding:0; }}
    .receipt{{ box-shadow:none; width:100%; border-radius:0; }}
    .print-btn{{ display:none; }}
  }}
</style>
</head><body>
<div class="receipt">

  <!-- HEADER -->
  <div class="header">
    <div class="salon-name">{salon.upper()}</div>
    <div class="salon-sub">Professional Hair Salon · Malaysia</div>
    {contact_line}
  </div>

  <!-- META STRIP -->
  <div class="meta-strip">
    <div class="rcpt-no">No. {receipt_no}</div>
    <div class="rcpt-date">{date_my} {time_str}</div>
  </div>

  <div class="body">

    <!-- CUSTOMER -->
    <div class="customer-box">
      <div class="customer-label">{'Pelanggan / 客戶' if not is_zh else '客戶'}</div>
      <div class="customer-name">{name}</div>
      {'<div class="customer-time">' + ('Temujanji / 預約時間: ' if not is_zh else '預約時間: ') + time_str + '</div>' if time_str else ''}
    </div>

    <!-- ITEMS TABLE -->
    <table>
      <thead>
        <tr>
          <td class="desc">{'Perkhidmatan / 服務' if not is_zh else '服務項目'}</td>
          <td class="qty">Qty</td>
          <td class="price">{'Harga' if not is_zh else '單價'}</td>
          <td class="amt">{'Jumlah' if not is_zh else '金額'}</td>
        </tr>
      </thead>
      <tbody>
        {rows_html}
        {disc_row_html}
        {stylist_row}
        {member_rows}
      </tbody>
    </table>

    <!-- TOTAL BOX -->
    <div class="totals">
      <div class="totals-row">
        <div class="totals-label">{total_lbl}</div>
        <div class="totals-amount">RM {final:.2f}</div>
      </div>
    </div>

    <!-- PAYMENT METHOD -->
    <div class="payment-row">
      <span class="payment-label">{pay_lbl}</span>
      <span class="payment-val">{method}</span>
    </div>

    <!-- SST NOTE -->
    <div class="sst-note">* SST Exempted · Perkhidmatan Salun Rambut<br>{sst_note}</div>

  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="thanks-main">{thanks_my}</div>
    <div class="thanks-sub">{thanks_en}</div>
    <div class="rcpt-stamp">Resit ini adalah sah tanpa tandatangan · This receipt is valid without signature</div>
    {footer_meta}
  </div>

  <button class="print-btn" onclick="window.print()">
    {'🖨️  Cetak Resit / 列印收據' if not is_zh else '🖨️  列印收據'}
  </button>

</div>
</body></html>"""


# ── Shared settlement helpers ─────────────────────────────────────────────────
def _settle_build_panels(paid_list, walkin_list, total_coll, label_suffix=""):
    """Return (df_detail, df_sty, df_svc, df_mth) for given paid + walkin lists."""
    detail_rows = [
        {u("col_s_name"):    b.get("name",""),  u("col_s_stylist"): b.get("stylist",""),
         u("col_s_svc"):     b.get("service",""), u("col_s_method"):  b.get("method",""),
         u("col_s_amt"):     b.get("final", b.get("price",0)),
         u("col_s_type"):    ("預約" if st.session_state.lang=="zh" else "Booking")}
        for b in paid_list
    ] + [
        {u("col_s_name"):    w.get("name",""),  u("col_s_stylist"): "—",
         u("col_s_svc"):     w.get("service",""), u("col_s_method"):  w.get("method",""),
         u("col_s_amt"):     w.get("final",0),
         u("col_s_type"):    ("即場客" if st.session_state.lang=="zh" else "Walk-in")}
        for w in walkin_list
    ]
    df_detail = pd.DataFrame(detail_rows) if detail_rows else pd.DataFrame()

    sty_rows = []
    for sty in sorted({b.get("stylist","") for b in paid_list} - {"","—"}):
        items = [b for b in paid_list if b.get("stylist")==sty]
        rev = sum(b.get("final",b.get("price",0)) for b in items)
        cnt = len(items)
        sty_rows.append({u("col_s_stylist"):sty, u("col_s_count"):cnt,
                         u("col_s_rev"):round(rev,2), u("col_s_avg"):round(rev/cnt,2) if cnt else 0})
    df_sty = pd.DataFrame(sty_rows) if sty_rows else pd.DataFrame()

    svc_agg = {}
    for row in detail_rows:
        s = row[u("col_s_svc")]
        if s not in svc_agg: svc_agg[s] = {"cnt":0,"rev":0}
        svc_agg[s]["cnt"] += 1; svc_agg[s]["rev"] += row[u("col_s_amt")]
    df_svc = pd.DataFrame([
        {u("col_s_svc"):s, u("col_s_count"):v["cnt"],
         u("col_s_rev"):round(v["rev"],2), u("col_s_avg"):round(v["rev"]/v["cnt"],2) if v["cnt"] else 0}
        for s,v in svc_agg.items()
    ]).sort_values(u("col_s_rev"),ascending=False).reset_index(drop=True) if svc_agg else pd.DataFrame()

    mth_agg = {}
    for row in detail_rows:
        m = row[u("col_s_method")] or "Cash"
        if m not in mth_agg: mth_agg[m] = {"cnt":0,"rev":0}
        mth_agg[m]["cnt"] += 1; mth_agg[m]["rev"] += row[u("col_s_amt")]
    df_mth = pd.DataFrame([
        {u("col_s_method"):m, u("col_s_count"):v["cnt"], u("col_s_rev"):round(v["rev"],2)}
        for m,v in mth_agg.items()
    ]).sort_values(u("col_s_rev"),ascending=False).reset_index(drop=True) if mth_agg else pd.DataFrame()

    return df_detail, df_sty, df_svc, df_mth


def _render_right_panels(df_svc, df_mth, total_coll):
    """Render service + method breakdown cards (right column)."""
    if not df_svc.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("settle_svc")}</p>', unsafe_allow_html=True)
        for _, row in df_svc.iterrows():
            pct = int(row[u("col_s_rev")] / total_coll * 100) if total_coll else 0
            st.markdown(
                f"<div style='margin-bottom:10px;'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
                f"<span style='color:#ccc;font-size:0.83rem;'>{row[u('col_s_svc')]}</span>"
                f"<span style='color:#c9a84c;font-weight:700;'>RM {row[u('col_s_rev')]:.2f}"
                f" <span style='color:#666;font-size:0.72rem;'>×{int(row[u('col_s_count')])}</span></span></div>"
                f"<div style='height:4px;background:#222;border-radius:2px;overflow:hidden;'>"
                f"<div style='width:{pct}%;height:100%;background:#c9a84c;border-radius:2px;'></div>"
                f"</div></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if not df_mth.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("settle_method")}</p>', unsafe_allow_html=True)
        for _, row in df_mth.iterrows():
            m = row[u("col_s_method")]
            ic = PAY_METHODS.get(m,("","💰","#888"))[1]
            cl = PAY_METHODS.get(m,("","💰","#888"))[2]
            pct = int(row[u("col_s_rev")] / total_coll * 100) if total_coll else 0
            st.markdown(
                f"<div style='margin-bottom:10px;'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
                f"<span style='color:#ccc;font-size:0.83rem;'>{ic} {m}</span>"
                f"<span style='color:{cl};font-weight:700;'>RM {row[u('col_s_rev')]:.2f}"
                f" <span style='color:#666;font-size:0.72rem;'>×{int(row[u('col_s_count')])}</span></span></div>"
                f"<div style='height:4px;background:#222;border-radius:2px;overflow:hidden;'>"
                f"<div style='width:{pct}%;height:100%;background:{cl};border-radius:2px;'></div>"
                f"</div></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def _render_sty_panel(df_sty):
    if df_sty.empty: return
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<p class="card-title">{u("settle_sty")}</p>', unsafe_allow_html=True)
    for _, row in df_sty.iterrows():
        sn = row[u("col_s_stylist")]
        idx = st.session_state.stylists.index(sn) if sn in st.session_state.stylists else 0
        cl = STYLIST_COLORS[idx % len(STYLIST_COLORS)]
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:9px 0;border-bottom:1px solid #1a1a1a;'>"
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<div class='sched-avatar' style='background:{cl}22;color:{cl};"
            f"width:34px;height:34px;font-size:0.85rem;'>{sn[:2].upper()}</div>"
            f"<span style='color:#f0ece0;'>{sn}</span>"
            f"<span style='color:#666;font-size:0.78rem;'>· {int(row[u('col_s_count')])} {u('sty_clients')}</span></div>"
            f"<div style='text-align:right;'>"
            f"<span style='color:{cl};font-weight:700;font-size:1rem;'>RM {row[u('col_s_rev')]:.2f}</span>"
            f"<span style='display:block;color:#666;font-size:0.72rem;'>avg RM {row[u('col_s_avg')]:.2f}</span>"
            f"</div></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# Build tab list
_tabs_labels = [u("tab1"), u("tab2"), u("tab3"), u("tab4"), u("tab5"), u("tab6")]
if _can("analytics"):
    _tabs_labels.append("  📊  " + ("業績" if st.session_state.lang=="zh" else "Analytics") + "  ")
if _can("admin"):
    _tabs_labels.append("  ⚙️  " + ("管理" if st.session_state.lang=="zh" else "Admin") + "  ")

_tabs = st.tabs(_tabs_labels)
tab1, tab2, tab3, tab4, tab5, tab6 = _tabs[:6]
_tab_offset = 6
if _can("analytics"):
    tab_analytics = _tabs[_tab_offset]; _tab_offset += 1
if _can("admin"):
    tab_admin = _tabs[_tab_offset]

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — BOOKINGS  (no pricing shown)
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Manual refresh + last updated ────────────────────────────────────────
    import datetime as _dt
    _ref_col, _time_col = st.columns([1, 3])
    with _ref_col:
        if st.button("🔄 " + ("刷新" if st.session_state.lang=="zh" else "Refresh"), key="manual_refresh_bk"):
            if _USE_DB:
                try:
                    branch = st.session_state.cur_branch
                    fresh = db_get_bookings(branch)
                    st.session_state.branch_data[branch]["bookings"] = fresh
                    _sync_ss()
                except Exception:
                    pass
            st.rerun()
    with _time_col:
        _now_str = _dt.datetime.now().strftime("%H:%M:%S")
        st.markdown(
            f'<p style="color:#555;font-size:0.75rem;margin-top:0.6rem;letter-spacing:1px;">'
            f'⏱ {"上次更新" if st.session_state.lang=="zh" else "Last updated"}: {_now_str} '
            f'· {"每60秒自動刷新" if st.session_state.lang=="zh" else "Auto-refresh every 60s"}</p>',
            unsafe_allow_html=True
        )

    # ── Online Booking Requests panel ─────────────────────────────────────────
    pending_online = [
        b for b in st.session_state.bookings
        if b.get("source") == "online" and b.get("status") == "pending"
    ]
    if pending_online:
        n = len(pending_online)
        st.markdown(f"""
        <div style="background:#1a0d00;border:1px solid #e67e22;border-radius:12px;
          padding:1rem 1.3rem;margin-bottom:1.2rem;">
          <div style="font-family:'Playfair Display',serif;color:#e67e22;font-size:1rem;
            letter-spacing:2px;margin-bottom:0.7rem;">
            🌐 {u('online_pending')} ({n})
          </div>
        """, unsafe_allow_html=True)
        for bk in pending_online:
            bk_id = bk.get("id", "")
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                phone_str = f" · 📞 {bk.get('phone','')}" if bk.get('phone') else ""
                st.markdown(
                    f"**{bk.get('name','')}**{phone_str}  \n"
                    f"🗓 {bk.get('date','')} {bk.get('time','')} · "
                    f"✂️ {bk.get('service','')} · 👤 {bk.get('stylist','') or u('any_stylist')}",
                    help=bk.get("note", "")
                )
            with c2:
                if st.button("✅ " + u("confirm_btn"), key=f"ok_{bk_id}"):
                    bk["status"] = "confirmed"
                    if _USE_DB and bk_id:
                        try: db_confirm_booking(bk_id)
                        except Exception: pass
                    _bd()["bookings"] = st.session_state.bookings
                    # Send confirmation email to customer
                    if _NOTIFY:
                        cust_email = bk.get("email", "")
                        if cust_email:
                            salon_name_str = st.session_state.branches.get(
                                st.session_state.cur_branch, "Signature Kim")
                            try:
                                ok = send_booking_confirmed(
                                    to_email=cust_email,
                                    customer_name=bk.get("name",""),
                                    service=bk.get("service",""),
                                    stylist=bk.get("stylist",""),
                                    date=bk.get("date",""),
                                    time=bk.get("time",""),
                                    price=bk.get("price",0),
                                    salon_name=salon_name_str,
                                    salon_phone=st.secrets.get("SALON_PHONE","") if hasattr(st,"secrets") else "",
                                )
                                if ok:
                                    st.toast(f"✉️ 確認郵件已發送至 {cust_email}", icon="✅")
                                else:
                                    st.toast("⚠️ 郵件發送失敗，請檢查 Gmail 設定", icon="⚠️")
                            except Exception as e:
                                st.toast(f"郵件錯誤: {e}", icon="❌")
                    st.rerun()
            with c3:
                if st.button("❌ " + u("cancel"), key=f"cx_{bk_id}"):
                    bk["status"] = "cancelled"
                    if _USE_DB and bk_id:
                        try: db_cancel_booking(bk_id)
                        except Exception: pass
                    _bd()["bookings"] = st.session_state.bookings
                    st.rerun()
            # WhatsApp quick-send button
            if bk.get("phone"):
                wa_msg = wa_booking_confirmed_msg(
                    bk.get("name",""), bk.get("service",""),
                    bk.get("stylist",""), bk.get("date",""),
                    bk.get("time",""),
                    st.session_state.branches.get(st.session_state.cur_branch,"Signature Kim")
                ) if _NOTIFY else ""
                if wa_msg:
                    wa_url = whatsapp_link(bk["phone"], wa_msg)
                    st.markdown(
                        f'<a href="{wa_url}" target="_blank" style="display:inline-block;'
                        f'background:#25D366;color:#fff;padding:5px 14px;border-radius:20px;'
                        f'font-size:0.78rem;text-decoration:none;font-weight:600;">'
                        f'📱 WhatsApp {bk.get("name","")}</a>',
                        unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)

    col_form, col_list = st.columns([1, 1.7], gap="large")

    with col_form:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("new_booking")}</p>', unsafe_allow_html=True)

        b_name = st.text_input(u("client_name"), placeholder=u("name_ph"), key="b_name")

        col_d, col_t = st.columns(2)
        with col_d:
            b_date = st.date_input(u("book_date"), value=dt_date.today(),
                                   min_value=dt_date.today(), key="b_date")
        with col_t:
            b_time = st.selectbox(u("book_time"), TIME_SLOTS, index=2, key="b_time")

        sty_opts = st.session_state.stylists if st.session_state.stylists else ["—"]
        b_stylist = st.selectbox(u("stylist"), sty_opts, key="b_stylist")

        svc_list = list(svc_map().keys())
        b_svc    = st.selectbox(u("service"), svc_list, key="b_svc")
        b_price  = svc_map()[b_svc]   # stored silently for payment tab

        b_note = st.text_input(u("note"), placeholder=u("note_ph"), key="b_note")

        if st.button(u("confirm_btn"), key="confirm_booking"):
            if not b_name.strip():
                st.warning(u("name_warn"))
            else:
                new_bk = {
                    "name": b_name.strip(), "date": str(b_date), "time": b_time,
                    "stylist": b_stylist,   "service": b_svc,    "note": b_note,
                    "price": b_price, "paid": False, "method": "", "final": 0,
                }
                if _USE_DB:
                    try: db_add_booking(st.session_state.cur_branch, new_bk)
                    except Exception: pass
                st.session_state.bookings.append(new_bk)
                _bd()["bookings"] = st.session_state.bookings
                st.success(f"✦ {b_name}  ·  {b_stylist}  ·  {b_svc}  ·  {b_date} {b_time}")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("book_list")}</p>', unsafe_allow_html=True)

        if st.session_state.bookings:
            df_full = pd.DataFrame(st.session_state.bookings)
            # ensure all columns exist
            for c in ["name","date","time","stylist","service","note"] + HIDDEN_BK_COLS:
                if c not in df_full.columns:
                    df_full[c] = False if c == "paid" else (0 if c in ["price","final"] else "")

            display_cols = ["name","date","time","stylist","service","note"]
            df_show = df_full[display_cols].sort_values(["date","time"]).reset_index(drop=True)

            edited = st.data_editor(
                df_show,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
                height=390,
                column_config={
                    "name":    st.column_config.TextColumn(u("col_name"),    width="medium"),
                    "date":    st.column_config.TextColumn(u("col_date"),    width="small"),
                    "time":    st.column_config.SelectboxColumn(u("col_time"),
                                   options=TIME_SLOTS, width="small"),
                    "stylist": st.column_config.SelectboxColumn(u("col_stylist"),
                                   options=st.session_state.stylists or ["—"], width="small"),
                    "service": st.column_config.SelectboxColumn(u("col_service"),
                                   options=svc_list, width="medium"),
                    "note":    st.column_config.TextColumn(u("col_note"), width="large"),
                },
                key="booking_editor",
            )

            if st.button(u("save_bookings"), key="save_bk"):
                # Merge edited display cols back with hidden payment cols
                edited_clean = edited.dropna(subset=["name"]).copy()
                hidden_df    = df_full[["name","date","time"] + HIDDEN_BK_COLS].drop_duplicates(
                    subset=["name","date","time"])
                merged = edited_clean.merge(hidden_df, on=["name","date","time"], how="left")
                for c in HIDDEN_BK_COLS:
                    if c not in merged.columns:
                        merged[c] = False if c == "paid" else 0
                st.session_state.bookings = merged.to_dict("records")
                _bd()["bookings"] = st.session_state.bookings
                if _USE_DB:
                    try: db_save_all_bookings(st.session_state.cur_branch, st.session_state.bookings)
                    except Exception: pass
                st.success(u("bookings_saved"))
                st.rerun()
        else:
            st.info(u("no_bookings"))

        # ── WhatsApp Reminder buttons ─────────────────────────────────────
        bks_with_phone = [b for b in st.session_state.bookings if b.get("phone")]
        if bks_with_phone and _NOTIFY:
            st.markdown("---")
            st.markdown(f'<p style="color:#c9a84c;font-size:0.8rem;letter-spacing:2px;">📱 WHATSAPP {"提醒" if st.session_state.lang=="zh" else "REMINDER"}</p>',
                        unsafe_allow_html=True)
            for bk in bks_with_phone[:10]:
                salon_nm = st.session_state.branches.get(st.session_state.cur_branch, "Signature Kim")
                wa_msg   = wa_booking_reminder_msg(
                    bk.get("name",""), bk.get("service",""),
                    bk.get("date",""), bk.get("time",""), salon_nm
                )
                wa_url = whatsapp_link(bk["phone"], wa_msg)
                st.markdown(
                    f'<a href="{wa_url}" target="_blank" style="display:inline-block;margin:3px 4px 3px 0;'
                    f'background:#25D366;color:#fff;padding:5px 14px;border-radius:20px;'
                    f'font-size:0.78rem;text-decoration:none;font-weight:600;">'
                    f'📱 {bk.get("name","")} · {bk.get("date","")} {bk.get("time","")}</a>',
                    unsafe_allow_html=True
                )

        st.markdown('</div>', unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — STYLISTS
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f'<p class="card-title" style="margin-bottom:1rem;">{u("sty_title")}</p>',
                unsafe_allow_html=True)

    col_manage, col_right_sty = st.columns([1, 2.2], gap="large")

    # ── Left: Manage roster ───────────────────────────────────────────────────
    with col_manage:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("sty_add")}</p>', unsafe_allow_html=True)
        new_sty = st.text_input(u("sty_name_lbl"), placeholder=u("sty_name_ph"), key="new_sty")
        if st.button(u("sty_add_btn"), key="add_sty_btn"):
            if not new_sty.strip():
                st.warning(u("sty_name_warn"))
            elif new_sty.strip() in st.session_state.stylists:
                st.warning("已存在 / Already exists")
            else:
                st.session_state.stylists.append(new_sty.strip())
                st.success(u("sty_added").format(new_sty.strip()))
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("sty_roster")}</p>', unsafe_allow_html=True)
        for idx, sty in enumerate(st.session_state.stylists):
            color    = STYLIST_COLORS[idx % len(STYLIST_COLORS)]
            initials = sty[:2].upper()
            today_count = sum(
                1 for b in st.session_state.bookings
                if b.get("stylist") == sty and b.get("date") == str(dt_date.today())
            )
            r1, r2 = st.columns([3, 1])
            with r1:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;padding:6px 0;"
                    f"border-bottom:1px solid #1a1a1a;'>"
                    f"<div class='sched-avatar' style='background:{color}22;color:{color};'>{initials}</div>"
                    f"<div><div style='color:#f0ece0;font-size:0.9rem;'>{sty}</div>"
                    f"<div style='color:#666;font-size:0.72rem;letter-spacing:1px;'>"
                    f"{today_count} {u('sty_clients')}</div></div></div>",
                    unsafe_allow_html=True,
                )
            with r2:
                if st.button("✕", key=f"rm_sty_{idx}", help=u("sty_remove")):
                    st.session_state.stylists.pop(idx)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Right: Schedule / Performance toggle ──────────────────────────────────
    with col_right_sty:
        today_str_sty = str(dt_date.today())
        view_mode = st.radio(
            "view", [u("sty_view_sched"), u("sty_view_perf"), u("sty_view_comm")],
            horizontal=True, key="sty_view", label_visibility="collapsed",
        )

        # ════════════════════════════════════════════════════════════════════
        # SCHEDULE VIEW
        # ════════════════════════════════════════════════════════════════════
        if view_mode == u("sty_view_sched"):
            st.markdown(f'<p class="card-title">{u("sty_schedule")}</p>', unsafe_allow_html=True)
            all_opt    = [u("sty_all")] + st.session_state.stylists
            sty_filter = st.selectbox(u("sty_filter"), all_opt, key="sty_filter_sel")
            show_stys  = (st.session_state.stylists if sty_filter == u("sty_all") else [sty_filter])

            if not show_stys:
                st.info(u("sty_name_warn"))
            else:
                for row_start in range(0, len(show_stys), 2):
                    row_s    = show_stys[row_start:row_start+2]
                    sty_cols = st.columns(len(row_s), gap="medium")
                    for sc, sty in zip(sty_cols, row_s):
                        color    = STYLIST_COLORS[st.session_state.stylists.index(sty) % len(STYLIST_COLORS)] \
                                   if sty in st.session_state.stylists else "#c9a84c"
                        initials = sty[:2].upper()
                        sty_bks  = sorted(
                            [b for b in st.session_state.bookings
                             if b.get("stylist") == sty and b.get("date") == today_str_sty],
                            key=lambda x: x.get("time","")
                        )
                        with sc:
                            st.markdown(
                                f"<div class='sched-card'>"
                                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>"
                                f"<div class='sched-avatar' style='background:{color}22;color:{color};'>{initials}</div>"
                                f"<div><div class='sched-name'>{sty}</div>"
                                f"<div class='sched-count'>{len(sty_bks)} {u('sty_clients')}</div></div></div>",
                                unsafe_allow_html=True,
                            )
                            if not sty_bks:
                                st.markdown(f"<p style='color:#444;font-size:0.82rem;text-align:center;"
                                            f"padding:0.5rem 0;'>{u('sty_no_bk')}</p>",
                                            unsafe_allow_html=True)
                            else:
                                for bk in sty_bks:
                                    dot = "🟢" if bk.get("paid") else "⚪"
                                    st.markdown(
                                        f"<div class='sched-slot' style='border-left-color:{color};'>"
                                        f"<div class='sched-slot-time'>{dot} {bk.get('time','')}</div>"
                                        f"<div class='sched-slot-client'>{bk.get('name','')}</div>"
                                        f"<div class='sched-slot-svc'>{bk.get('service','')}</div></div>",
                                        unsafe_allow_html=True,
                                    )
                            st.markdown("</div>", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # COMMISSION RATE EDITOR
        # ════════════════════════════════════════════════════════════════════
        elif view_mode == u("sty_view_comm"):
            st.markdown(f'<p class="card-title">{u("comm_title")}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#888;font-size:0.82rem;margin-bottom:1rem;">{u("comm_desc")}</p>',
                        unsafe_allow_html=True)
            stylists_list = st.session_state.stylists
            if not stylists_list:
                st.info(u("comm_no_sty"))
            else:
                comm_data = st.session_state.commissions
                is_zh = (st.session_state.lang == "zh")

                # Build a DataFrame for the rate editor
                svc_labels = {z: (z if is_zh else SVC_ZH_EN[z]) for z in SVC_ALL_ZH}
                rows = []
                for sty in stylists_list:
                    row = {"髮型師 / Stylist": sty}
                    sty_rates = comm_data.get(sty, {})
                    for zh_svc, label in svc_labels.items():
                        row[label] = float(sty_rates.get(zh_svc, 0))
                    rows.append(row)

                import pandas as _pd_comm
                df_comm = _pd_comm.DataFrame(rows)
                col_config_comm = {"髮型師 / Stylist": st.column_config.TextColumn(disabled=True, width="medium")}
                for label in svc_labels.values():
                    col_config_comm[label] = st.column_config.NumberColumn(
                        label, min_value=0, max_value=100, step=1, format="%.0f%%", width="small"
                    )

                edited_comm = st.data_editor(
                    df_comm,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    column_config=col_config_comm,
                    key="comm_editor",
                )

                if st.button(u("comm_save"), key="save_comm_btn", type="primary"):
                    new_rates = {}
                    for _, row in edited_comm.iterrows():
                        sty = row["髮型師 / Stylist"]
                        new_rates[sty] = {}
                        for zh_svc, label in svc_labels.items():
                            new_rates[sty][zh_svc] = float(row.get(label, 0) or 0)
                    st.session_state.commissions = new_rates
                    _bd()["commissions"] = new_rates
                    if _USE_DB:
                        try:
                            db_save_commissions(st.session_state.cur_branch, new_rates)
                        except Exception:
                            pass
                    st.success(u("comm_saved"))
                    st.rerun()

        # ════════════════════════════════════════════════════════════════════
        # PERFORMANCE VIEW
        # ════════════════════════════════════════════════════════════════════
        else:
            st.markdown(f'<p class="card-title">{u("perf_title")}</p>', unsafe_allow_html=True)

            def get_perf(sty):
                all_paid   = [b for b in st.session_state.bookings
                              if b.get("stylist") == sty and b.get("paid")]
                today_paid = [b for b in all_paid if b.get("date") == today_str_sty]
                total_rev  = sum(b.get("final", b.get("price", 0)) for b in all_paid)
                today_rev  = sum(b.get("final", b.get("price", 0)) for b in today_paid)
                total_cnt  = len(all_paid)
                today_cnt  = len(today_paid)
                svc_cnt    = {}
                for b in all_paid:
                    s = b.get("service","—")
                    svc_cnt[s] = svc_cnt.get(s, 0) + 1
                top_svc = max(svc_cnt, key=svc_cnt.get) if svc_cnt else "—"
                avg_val = total_rev / total_cnt if total_cnt else 0
                return {
                    "total_rev": total_rev, "today_rev": today_rev,
                    "total_cnt": total_cnt, "today_cnt": today_cnt,
                    "top_svc":   top_svc,   "avg_val":   avg_val,
                }

            MEDALS = ["🥇", "🥈", "🥉"]
            perfs  = [(sty, get_perf(sty)) for sty in st.session_state.stylists]
            perfs.sort(key=lambda x: x[1]["total_rev"], reverse=True)
            max_rev = max((p[1]["total_rev"] for p in perfs), default=1) or 1

            if not perfs or all(p[1]["total_cnt"] == 0 for p in perfs):
                st.markdown(f'<div class="alert-warn" style="margin-top:1rem;">'
                            f'{u("perf_no_data")}</div>', unsafe_allow_html=True)
            else:
                for rank, (sty, p) in enumerate(perfs):
                    idx      = st.session_state.stylists.index(sty) \
                               if sty in st.session_state.stylists else 0
                    color    = STYLIST_COLORS[idx % len(STYLIST_COLORS)]
                    initials = sty[:2].upper()
                    medal    = MEDALS[rank] if rank < 3 else f"#{rank+1}"
                    bar_pct  = int(p["total_rev"] / max_rev * 100) if max_rev else 0

                    st.markdown(f"""
                    <div class="sched-card" style="margin-bottom:10px;">
                      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                        <div style="font-size:1.6rem;min-width:32px;text-align:center;">{medal}</div>
                        <div class="sched-avatar" style="background:{color}22;color:{color};">{initials}</div>
                        <div style="flex:1;">
                          <div style="color:#f0ece0;font-size:1rem;font-weight:600;">{sty}</div>
                          <div style="height:5px;background:#222;border-radius:3px;margin-top:5px;overflow:hidden;">
                            <div style="width:{bar_pct}%;height:100%;background:{color};border-radius:3px;
                              transition:width .6s;"></div>
                          </div>
                        </div>
                        <div style="text-align:right;min-width:90px;">
                          <div style="color:{color};font-family:'Playfair Display',serif;
                            font-size:1.2rem;font-weight:700;">RM {p['total_rev']:.2f}</div>
                          <div style="color:#666;font-size:0.7rem;letter-spacing:1px;">
                            {u('perf_total_rev')}</div>
                        </div>
                      </div>
                      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">
                        <div style="background:#1a1a1a;border-radius:8px;padding:7px 8px;text-align:center;">
                          <div style="color:#c9a84c;font-size:1rem;font-weight:700;">RM {p['today_rev']:.2f}</div>
                          <div style="color:#666;font-size:0.65rem;letter-spacing:1px;margin-top:2px;">{u('perf_today_rev')}</div>
                        </div>
                        <div style="background:#1a1a1a;border-radius:8px;padding:7px 8px;text-align:center;">
                          <div style="color:#f0ece0;font-size:1rem;font-weight:700;">{p['total_cnt']}</div>
                          <div style="color:#666;font-size:0.65rem;letter-spacing:1px;margin-top:2px;">{u('perf_clients')}</div>
                        </div>
                        <div style="background:#1a1a1a;border-radius:8px;padding:7px 8px;text-align:center;">
                          <div style="color:#f0ece0;font-size:0.82rem;font-weight:600;white-space:nowrap;
                            overflow:hidden;text-overflow:ellipsis;">{p['top_svc']}</div>
                          <div style="color:#666;font-size:0.65rem;letter-spacing:1px;margin-top:2px;">{u('perf_top_svc')}</div>
                        </div>
                        <div style="background:#1a1a1a;border-radius:8px;padding:7px 8px;text-align:center;">
                          <div style="color:#f0ece0;font-size:1rem;font-weight:700;">RM {p['avg_val']:.0f}</div>
                          <div style="color:#666;font-size:0.65rem;letter-spacing:1px;margin-top:2px;">{u('perf_avg')}</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — PAYMENT
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f'<p class="card-title" style="margin-bottom:1.2rem;">{u("pay_title")}</p>',
                unsafe_allow_html=True)

    today_str     = str(dt_date.today())
    today_bk      = [b for b in st.session_state.bookings if b.get("date") == today_str]
    paid_bk       = [b for b in today_bk if b.get("paid")]
    unpaid_bk     = [b for b in today_bk if not b.get("paid")]
    walkins_today = [w for w in st.session_state.walkins if w.get("date") == today_str]

    collected  = sum(b.get("final", b.get("price", 0)) for b in paid_bk) \
               + sum(w.get("final", 0) for w in walkins_today)
    unpaid_rev = sum(b.get("price", 0) for b in unpaid_bk)
    cli_count  = len(paid_bk) + len(walkins_today) + len(unpaid_bk)

    s1, s2, s3, s4 = st.columns(4, gap="medium")
    for col, (lbl, val) in zip([s1, s2, s3, s4], [
        (u("stat_paid"),    f"RM {collected:.2f}"),
        (u("stat_pending"), f"RM {unpaid_rev:.2f}"),
        (u("stat_total"),   f"RM {collected + unpaid_rev:.2f}"),
        (u("stat_count"),   str(cli_count)),
    ]):
        with col:
            st.markdown(f'<div class="stat-box"><div class="stat-val">{val}</div>'
                        f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    method_labels  = {v[0]: k for k, v in PAY_METHODS.items()}
    method_display = [v[0] for v in PAY_METHODS.values()]

    def method_radio(key):
        d = st.radio(u("pay_method"), method_display, horizontal=True,
                     key=key, label_visibility="collapsed")
        k = method_labels[d]
        ic, cl = PAY_METHODS[k][1], PAY_METHODS[k][2]
        st.markdown(f"<div style='text-align:center;margin:0.4rem 0 0.8rem;'>"
                    f"<span style='font-size:1.8rem;'>{ic}</span>"
                    f"<span style='display:block;color:{cl};font-size:0.78rem;"
                    f"letter-spacing:2px;margin-top:3px;'>{d}</span></div>",
                    unsafe_allow_html=True)
        return k, d

    col_left, col_right = st.columns([1, 1.3], gap="large")

    # ── Pending + Breakdown ───────────────────────────────────────────────────
    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("pending_list")}</p>', unsafe_allow_html=True)
        if not unpaid_bk:
            st.markdown(f'<div class="alert-safe">{u("no_pending")}</div>', unsafe_allow_html=True)
        else:
            for bk in unpaid_bk:
                st.markdown(
                    f"<div style='background:#1a1a1a;border:1px solid #c9a84c33;border-radius:10px;"
                    f"padding:10px 14px;margin-bottom:8px;display:flex;"
                    f"justify-content:space-between;align-items:center;'>"
                    f"<div><div style='color:#f0ece0;font-size:0.92rem;'>{bk['name']}</div>"
                    f"<div style='color:#888;font-size:0.73rem;letter-spacing:1px;'>"
                    f"{bk.get('stylist','')} · {bk['service']} · {bk['time']}</div></div>"
                    f"<div style='color:#c9a84c;font-weight:700;'>RM {bk.get('price',0):.2f}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)

        all_paid_items = [
            {"m": b.get("method","Cash"), "amt": b.get("final", b.get("price",0))}
            for b in paid_bk
        ] + [
            {"m": w.get("method","Cash"), "amt": w.get("final",0)}
            for w in walkins_today
        ]
        if all_paid_items:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title" style="font-size:0.95rem;">'
                        f'{u("breakdown_title")}</p>', unsafe_allow_html=True)
            mt = {}
            for item in all_paid_items:
                mt[item["m"]] = mt.get(item["m"], 0) + item["amt"]
            for m, amt in mt.items():
                ic, cl = PAY_METHODS.get(m,("","💰","#888"))[1], PAY_METHODS.get(m,("","💰","#888"))[2]
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:7px 0;"
                    f"border-bottom:1px solid #1e1e1e;'>"
                    f"<span style='color:#ccc;font-size:0.85rem;'>{ic} {m}</span>"
                    f"<span style='color:{cl};font-weight:700;'>RM {amt:.2f}</span></div>",
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Checkout Panel ────────────────────────────────────────────────────────
    with col_right:
        mode_opts = (u("mode_booked"), u("mode_walkin"))
        checkout_mode = st.radio("mode", mode_opts, horizontal=True,
                                 key="checkout_mode", label_visibility="collapsed")
        is_walkin = (checkout_mode == mode_opts[1])

        # ── Booked client ──────────────────────────────────────────────────
        if not is_walkin:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">{u("checkout_title")}</p>', unsafe_allow_html=True)

            if not unpaid_bk:
                st.markdown("<p style='color:#555;text-align:center;padding:1.5rem 0;'>"
                            + u("no_pending") + "</p>", unsafe_allow_html=True)
            else:
                bk_opts = {
                    f"{b['name']}  ·  {b.get('stylist','')}  ·  {b['service']}  ·  {b['time']}": i
                    for i, b in enumerate(unpaid_bk)
                }
                sel_label = st.selectbox(u("select_booking"), list(bk_opts.keys()),
                                         key="checkout_select")
                sel_bk = unpaid_bk[bk_opts[sel_label]]
                orig   = sel_bk.get("price", 0)

                # ── Member lookup ──────────────────────────────────────────
                mem_names = ["— " + ("非會員" if st.session_state.lang=="zh" else "Non-member") + " —"] + \
                            [f"{m['name']}  ({m.get('phone','')})  {tier_label(tier_for_points(m.get('points',0)))}"
                             for m in st.session_state.members]
                mem_sel_label = st.selectbox(u("mem_lookup"), mem_names, key="pay_mem_sel")
                pay_mem = None
                mem_disc_pct = 0
                if not mem_sel_label.startswith("—"):
                    sel_mem_name = mem_sel_label.split("  (")[0]
                    pay_mem = next((m for m in st.session_state.members if m["name"] == sel_mem_name), None)
                    if pay_mem:
                        mem_disc_pct = tier_for_points(pay_mem.get("points", 0))["disc"]
                        tier_lbl = tier_label(tier_for_points(pay_mem.get("points", 0)))
                        if mem_disc_pct:
                            st.markdown(
                                f'<div style="background:#1a1500;border:1px solid #c9a84c55;border-radius:8px;'
                                f'padding:6px 12px;font-size:0.8rem;color:#c9a84c;margin-bottom:6px;">'
                                f'{tier_lbl} · {u("mem_disc_hint").format(mem_disc_pct)}</div>',
                                unsafe_allow_html=True)

                a1, a2 = st.columns(2)
                with a1:
                    default_disc = mem_disc_pct
                    disc_pct = st.number_input(u("disc_label"), 0, 100, default_disc, 5, key="disc_pct")
                with a2:
                    extra = st.number_input(u("extra_label"), 0.0, 9999.0, 0.0, 5.0, key="extra_chg")

                final = round(orig * (1 - disc_pct / 100) + extra, 2)
                adj_note = ""
                if disc_pct or extra:
                    adj_note = (f"<div style='font-size:0.76rem;color:#e67e22;margin-top:4px;'>"
                                f"原價 RM {orig:.2f}"
                                + (f" · 折扣 {disc_pct}%" if disc_pct else "")
                                + (f" · 加收 RM {extra:.2f}" if extra else "")
                                + "</div>")

                pts_earn = int(final)
                pts_note = f"<div style='font-size:0.74rem;color:#3498db;margin-top:4px;'>+{pts_earn} pts</div>" if pay_mem else ""

                st.markdown(f"""
                <div class="checkout-box" style="margin:0.8rem 0;">
                  <div class="checkout-customer">{sel_bk['name']}</div>
                  <div class="checkout-svc">{sel_bk.get('stylist','')} · {sel_bk['service']} · {sel_bk['time']}</div>
                  {adj_note}
                  <div class="checkout-price">RM {final:.2f}</div>
                  {pts_note}
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"<p style='color:#ccb97a;font-size:0.82rem;letter-spacing:1px;'>"
                            f"{u('pay_method')}</p>", unsafe_allow_html=True)
                chosen_key, chosen_display = method_radio("pay_method_booked")

                if st.button(u("confirm_pay"), key="confirm_booked"):
                    for b in st.session_state.bookings:
                        if (b["name"] == sel_bk["name"] and b["date"] == sel_bk["date"]
                                and b["time"] == sel_bk["time"]):
                            b.update({"paid": True, "method": chosen_key, "final": final})
                            if _USE_DB and b.get("id"):
                                try: db_update_booking(b["id"], {"paid": True, "method": chosen_key, "final": final})
                                except Exception: pass
                            break
                    _bd()["bookings"] = st.session_state.bookings
                    # Pre-load receipt data
                    st.session_state.sel_receipt = {
                        "name":     sel_bk["name"],
                        "service":  sel_bk["service"],
                        "stylist":  sel_bk.get("stylist",""),
                        "time":     sel_bk["time"],
                        "date":     today_str,
                        "subtotal": orig,
                        "disc_pct": disc_pct,
                        "extra":    extra,
                        "final":    final,
                        "method":   chosen_key,
                        "member":   pay_mem["name"] if pay_mem else "",
                        "pts":      pts_earn if pay_mem else 0,
                    }
                    # Add points + history to member
                    if pay_mem:
                        for m in st.session_state.members:
                            if m["id"] == pay_mem["id"]:
                                old_pts  = m.get("points", 0)
                                m["points"]      = old_pts + pts_earn
                                m["total_spent"] = round(m.get("total_spent", 0) + final, 2)
                                m["visit_count"] = m.get("visit_count", 0) + 1
                                hist_entry = {"date": today_str, "service": sel_bk["service"], "amt": final, "pts": pts_earn}
                                m.setdefault("history", []).append(hist_entry)
                                if _USE_DB:
                                    try:
                                        db_update_member(m["id"], {"points": m["points"], "total_spent": m["total_spent"], "visit_count": m["visit_count"]})
                                        db_add_member_history(m["id"], hist_entry)
                                    except Exception: pass
                                new_tier = tier_for_points(m["points"])
                                old_tier = tier_for_points(old_pts)
                                if new_tier["key"] != old_tier["key"]:
                                    st.balloons()
                                    st.success(u("mem_tier_up").format(m["name"], tier_label(new_tier)))
                                else:
                                    st.info(u("mem_pts_added").format(pts_earn, m["name"]))
                                break
                        _bd()["members"] = st.session_state.members
                    st.success(u("pay_success").format(final, chosen_display))
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Walk-in ────────────────────────────────────────────────────────
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">{u("walkin_title")}</p>', unsafe_allow_html=True)

            wi_name = st.text_input(u("client_name"), placeholder=u("name_ph"), key="wi_name")
            _no_sty = "— " + ("不指定" if st.session_state.lang == "zh" else "No stylist") + " —"
            wi_stylist = st.selectbox(
                u("stylist"),
                [_no_sty] + (st.session_state.stylists or []),
                key="wi_stylist",
            )
            wi_stylist_val = "" if wi_stylist.startswith("—") else wi_stylist
            wi_svc  = st.text_input(u("service"), placeholder=u("wi_svc_ph"), key="wi_svc")
            wi_amt  = st.number_input(u("wi_amt_label"), 0.0, 99999.0, 50.0, 10.0, key="wi_amt")

            # Walk-in member lookup
            wi_mem_names = ["— " + ("非會員" if st.session_state.lang=="zh" else "Non-member") + " —"] + \
                           [f"{m['name']}  ({m.get('phone','')})" for m in st.session_state.members]
            wi_mem_sel = st.selectbox(u("mem_lookup"), wi_mem_names, key="wi_mem_sel")
            wi_pay_mem = None
            if not wi_mem_sel.startswith("—"):
                wi_mem_nm = wi_mem_sel.split("  (")[0]
                wi_pay_mem = next((m for m in st.session_state.members if m["name"] == wi_mem_nm), None)

            wi_pts_earn = int(wi_amt)
            wi_pts_note = f"<div style='font-size:0.74rem;color:#3498db;'>+{wi_pts_earn} pts</div>" if wi_pay_mem else ""

            st.markdown(f"""
            <div class="checkout-box" style="margin:0.8rem 0;">
              <div class="checkout-customer">{wi_name or "—"}</div>
              <div class="checkout-svc">{(" · ".join(filter(None,[wi_stylist_val, wi_svc]))) or "—"}</div>
              <div class="checkout-price">RM {wi_amt:.2f}</div>
              {wi_pts_note}
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"<p style='color:#ccb97a;font-size:0.82rem;letter-spacing:1px;'>"
                        f"{u('pay_method')}</p>", unsafe_allow_html=True)
            wi_key, wi_display = method_radio("pay_method_walkin")

            if st.button(u("wi_confirm"), key="confirm_walkin"):
                if not wi_name.strip():
                    st.warning(u("name_warn"))
                else:
                    new_wi = {"name": wi_name.strip(), "service": wi_svc or "—",
                              "stylist": wi_stylist_val,
                              "date": today_str, "final": wi_amt, "method": wi_key}
                    st.session_state.walkins.append(new_wi)
                    _bd()["walkins"] = st.session_state.walkins
                    if _USE_DB:
                        try: db_add_walkin(st.session_state.cur_branch, new_wi)
                        except Exception: pass
                    st.session_state.sel_receipt = {
                        "name":     wi_name.strip(),
                        "service":  wi_svc or "—",
                        "stylist":  wi_stylist_val,
                        "time":     "",
                        "date":     today_str,
                        "subtotal": wi_amt,
                        "disc_pct": 0,
                        "extra":    0,
                        "final":    wi_amt,
                        "method":   wi_key,
                        "member":   wi_pay_mem["name"] if wi_pay_mem else "",
                        "pts":      wi_pts_earn if wi_pay_mem else 0,
                    }
                    if wi_pay_mem:
                        for m in st.session_state.members:
                            if m["id"] == wi_pay_mem["id"]:
                                old_pts = m.get("points", 0)
                                m["points"]      = old_pts + wi_pts_earn
                                m["total_spent"] = round(m.get("total_spent", 0) + wi_amt, 2)
                                m["visit_count"] = m.get("visit_count", 0) + 1
                                m.setdefault("history", []).append({
                                    "date":    today_str,
                                    "service": wi_svc or "—",
                                    "amt":     wi_amt,
                                    "pts":     wi_pts_earn,
                                })
                                new_tier = tier_for_points(m["points"])
                                old_tier = tier_for_points(old_pts)
                                if new_tier["key"] != old_tier["key"]:
                                    st.balloons()
                                    st.success(u("mem_tier_up").format(m["name"], tier_label(new_tier)))
                                break
                    st.success(u("pay_success").format(wi_amt, wi_display))
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── History ───────────────────────────────────────────────────────
        history = [
            {"tag":"📅","type":"booking","ref":b,
             "name":b["name"],"svc":b.get("service",""),
             "time":b.get("time",""),"stylist":b.get("stylist",""),
             "final":b.get("final",b.get("price",0)),"method":b.get("method","Cash")}
            for b in paid_bk
        ] + [
            {"tag":"🚶","type":"walkin","ref":w,
             "name":w["name"],"svc":w.get("service",""),
             "time":"","stylist":w.get("stylist",""),
             "final":w.get("final",0),"method":w.get("method","Cash")}
            for w in walkins_today
        ]
        _can_void = _can("settlement")
        is_zh_pay = (st.session_state.lang == "zh")
        if history:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title" style="font-size:0.95rem;">'
                        f'{u("history_title")}</p>', unsafe_allow_html=True)
            for idx, h in enumerate(history):
                m  = h["method"]
                ic = PAY_METHODS.get(m,("","💰","#888"))[1]
                cl = PAY_METHODS.get(m,("","💰","#888"))[2]
                sub = " · ".join(filter(None, [h["stylist"], h["svc"], h["time"]]))
                n_cols = [4, 1, 1] if _can_void else [4, 1]
                cols = st.columns(n_cols)
                with cols[0]:
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;padding:8px 0;"
                        f"border-bottom:1px solid #1a1a1a;'>"
                        f"<div><span style='color:#f0ece0;font-size:0.88rem;'>{h['tag']} {h['name']}</span>"
                        f"<span style='color:#555;font-size:0.74rem;margin-left:8px;'>{sub}</span></div>"
                        f"<div style='text-align:right;'>"
                        f"<span style='color:#c9a84c;font-weight:700;'>RM {h['final']:.2f}</span>"
                        f"<span style='display:block;color:{cl};font-size:0.7rem;'>{ic} {m}</span>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    if st.button(u("rcpt_btn"), key=f"rcpt_{idx}"):
                        st.session_state.sel_receipt = {
                            "name":     h["name"],
                            "service":  h["svc"],
                            "stylist":  h["stylist"],
                            "time":     h["time"],
                            "date":     today_str,
                            "subtotal": h["final"],
                            "disc_pct": 0,
                            "extra":    0,
                            "final":    h["final"],
                            "method":   h["method"],
                            "member":   "",
                            "pts":      0,
                        }
                        st.rerun()
                if _can_void:
                    with cols[2]:
                        void_lbl = "❌ " + ("取消" if is_zh_pay else "Void")
                        if st.button(void_lbl, key=f"void_{idx}",
                                     help=("取消收費（限經理以上）" if is_zh_pay
                                           else "Cancel payment (manager+ only)")):
                            st.session_state[f"confirm_void_{idx}"] = True
                    # Confirm dialog
                    if st.session_state.get(f"confirm_void_{idx}"):
                        st.warning(
                            ("⚠️ 確定要取消此收費嗎？此操作不可撤回。" if is_zh_pay
                             else "⚠️ Confirm void this payment? This cannot be undone.")
                        )
                        cv1, cv2 = st.columns(2)
                        with cv1:
                            if st.button("✅ " + ("確認取消" if is_zh_pay else "Confirm Void"),
                                         key=f"void_yes_{idx}", type="primary"):
                                ref = h["ref"]
                                if h["type"] == "booking":
                                    for b in st.session_state.bookings:
                                        if (b.get("name") == ref.get("name") and
                                                b.get("date") == ref.get("date") and
                                                b.get("time") == ref.get("time")):
                                            b.update({"paid": False, "method": "", "final": 0})
                                            if _USE_DB and b.get("id"):
                                                try:
                                                    db_update_booking(b["id"],
                                                        {"paid": False, "method": "", "final": 0})
                                                except Exception: pass
                                            break
                                    _bd()["bookings"] = st.session_state.bookings
                                else:
                                    st.session_state.walkins = [
                                        w for w in st.session_state.walkins
                                        if not (w.get("name") == ref.get("name") and
                                                w.get("date") == ref.get("date") and
                                                w.get("final") == ref.get("final"))
                                    ]
                                    _bd()["walkins"] = st.session_state.walkins
                                    if _USE_DB and ref.get("id"):
                                        try: db_delete_walkin(ref["id"])
                                        except Exception: pass
                                st.session_state.pop(f"confirm_void_{idx}", None)
                                st.success("✅ " + ("已取消收費" if is_zh_pay else "Payment voided"))
                                st.rerun()
                        with cv2:
                            if st.button("↩ " + ("返回" if is_zh_pay else "Cancel"),
                                         key=f"void_no_{idx}"):
                                st.session_state.pop(f"confirm_void_{idx}", None)
                                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Receipt panel ──────────────────────────────────────────────────
        rcpt = st.session_state.sel_receipt
        if rcpt:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">🧾 {u("rcpt_title")}</p>', unsafe_allow_html=True)

            # Build HTML and offer as download (opens in browser → Ctrl+P / Print button)
            if "salon" not in rcpt:
                rcpt["salon"] = st.session_state.branches.get(st.session_state.cur_branch, "IQSALON")
            rcpt_html  = build_receipt_html(rcpt, st.session_state.lang)
            rcpt_bytes = rcpt_html.encode("utf-8")

            rc1, rc2, rc3 = st.columns([1, 1, 1])
            with rc1:
                st.download_button(
                    label=u("rcpt_print"),
                    data=rcpt_bytes,
                    file_name=f"receipt_{rcpt['name'].replace(' ','_')}_{rcpt['date']}.html",
                    mime="text/html",
                    key="dl_receipt",
                )
            with rc2:
                # Email via mailto: link
                email_body = (
                    f"Signature Kim Receipt\n"
                    f"{'=' * 30}\n"
                    f"{'客戶' if st.session_state.lang=='zh' else 'Client'}: {rcpt['name']}\n"
                    f"{'日期' if st.session_state.lang=='zh' else 'Date'}: {rcpt['date']} {rcpt['time']}\n"
                    f"{'服務' if st.session_state.lang=='zh' else 'Service'}: {rcpt['service']}\n"
                    + (f"{'髮型師' if st.session_state.lang=='zh' else 'Stylist'}: {rcpt['stylist']}\n" if rcpt.get('stylist') else "")
                    + (f"{'折扣' if st.session_state.lang=='zh' else 'Discount'}: {rcpt['disc_pct']}%\n" if rcpt.get('disc_pct') else "")
                    + f"{'總計' if st.session_state.lang=='zh' else 'Total'}: RM {rcpt['final']:.2f}\n"
                    f"{'付款方式' if st.session_state.lang=='zh' else 'Payment'}: {rcpt['method']}\n"
                    + (f"{'積分' if st.session_state.lang=='zh' else 'Points'}: +{rcpt['pts']} pts\n" if rcpt.get('pts') else "")
                    + f"\n{'感謝您的光臨！' if st.session_state.lang=='zh' else 'Thank you for visiting Signature Kim!'}"
                )
                email_to = st.text_input(u("rcpt_email_to"), placeholder=u("rcpt_email_ph"), key="rcpt_email_addr", label_visibility="collapsed")
                import urllib.parse as _up
                subject = _up.quote(f"Signature Kim Receipt — {rcpt['name']} {rcpt['date']}")
                body    = _up.quote(email_body)
                mailto  = f"mailto:{email_to}?subject={subject}&body={body}"
                st.markdown(
                    f'<a href="{mailto}" target="_blank" style="display:block;background:linear-gradient(135deg,#3498db,#1a6fa8);'
                    f'color:#fff;text-align:center;padding:10px 16px;border-radius:8px;font-size:0.82rem;'
                    f'font-weight:700;letter-spacing:2px;text-decoration:none;margin-top:2px;">'
                    f'{u("rcpt_email")}</a>',
                    unsafe_allow_html=True)
            with rc3:
                if st.button(u("rcpt_close"), key="close_receipt"):
                    st.session_state.sel_receipt = None
                    st.rerun()

            # Preview
            import streamlit.components.v1 as _components
            _components.html(rcpt_html, height=520, scrolling=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — INVENTORY
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown(f'<p class="card-title" style="margin-bottom:1rem;">{u("inv_title")}</p>',
                unsafe_allow_html=True)

    low_stock = [p for p in st.session_state.inventory if p["qty"] / p["max"] < 0.3]
    if low_stock:
        st.markdown(
            f'<div class="alert-warn">'
            f'{u("low_warn").format("、".join(p["name"] for p in low_stock))}</div>',
            unsafe_allow_html=True,
        )

    col_add, col_cards = st.columns([1, 2.2], gap="large")

    with col_add:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">{u("add_product")}</p>', unsafe_allow_html=True)
        p_name = st.text_input(u("p_name"), placeholder=u("p_name_ph"), key="p_name_inp")
        p_cat  = st.selectbox(u("p_cat"), CATS[st.session_state.lang], key="p_cat_sel")
        c1, c2 = st.columns(2)
        with c1: p_qty = st.number_input(u("p_qty"), 0, 9999, 0, key="p_qty_inp")
        with c2: p_max = st.number_input(u("p_max"), 1, 9999, 20, key="p_max_inp")
        p_unit = st.selectbox(u("p_unit"), UNITS[st.session_state.lang], key="p_unit_sel")
        if st.button(u("add_btn"), key="add_product_btn"):
            if not p_name.strip():
                st.warning(u("name_req"))
            else:
                st.session_state.inventory.append({
                    "name": p_name.strip(), "category": p_cat,
                    "qty": p_qty, "max": p_max, "unit": p_unit,
                })
                st.success(u("add_success").format(p_name.strip()))
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cards:
        fc1, fc2 = st.columns(2)
        with fc1:
            all_cats   = [u("all_cat")] + sorted({p["category"] for p in st.session_state.inventory})
            cat_filter = st.selectbox(u("filter"), all_cats, key="cat_filter")
        with fc2:
            search_q = st.text_input(u("search"), placeholder=u("search_ph"), key="inv_search")

        filtered = st.session_state.inventory
        if cat_filter != u("all_cat"):
            filtered = [p for p in filtered if p["category"] == cat_filter]
        if search_q:
            filtered = [p for p in filtered if search_q.lower() in p["name"].lower()]

        for i in range(0, len(filtered), 3):
            row_items = filtered[i:i+3]
            row_cols  = st.columns(3, gap="small")
            for rc, prod in zip(row_cols, row_items):
                ratio = prod["qty"] / prod["max"]
                fill  = bar_color(ratio)
                pct   = int(ratio * 100)
                with rc:
                    st.markdown(f"""
                    <div class="inv-card">
                      <div class="inv-name">{prod['name']}</div>
                      <div class="inv-qty">{prod['qty']}</div>
                      <div class="inv-unit">{prod['unit']} · {u('remain')}</div>
                      <div style="font-size:0.7rem;color:#555;margin-top:2px;">{prod['category']}</div>
                      <div class="inv-bar">
                        <div class="inv-fill" style="width:{pct}%;background:{fill};"></div>
                      </div>
                      <div style="font-size:0.7rem;color:{fill};margin-top:4px;">{pct}%</div>
                    </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    with st.expander(u("edit_section")):
        df_inv = pd.DataFrame(st.session_state.inventory)
        edited_inv = st.data_editor(
            df_inv,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "name":     st.column_config.TextColumn(u("col_pname"), width="large"),
                "category": st.column_config.SelectboxColumn(u("col_pcat"),
                                options=CATS["zh"] + CATS["en"], width="medium"),
                "qty":      st.column_config.NumberColumn(u("col_pqty"), min_value=0, max_value=9999, width="small"),
                "max":      st.column_config.NumberColumn(u("col_pmax"), min_value=1, max_value=9999, width="small"),
                "unit":     st.column_config.TextColumn(u("col_punit"), width="small"),
            },
            key="inv_editor",
        )
        if st.button(u("save_inv"), key="save_inv_btn"):
            st.session_state.inventory = edited_inv.dropna(subset=["name"]).to_dict("records")
            _bd()["inventory"] = st.session_state.inventory
            if _USE_DB:
                try: db_save_all_inventory(st.session_state.cur_branch, st.session_state.inventory)
                except Exception: pass
            st.success(u("inv_saved"))
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — SETTLEMENT & EXCEL EXPORT
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    if not _can("settlement"):
        st.info("⛔ " + ("您沒有權限查看結算報告" if st.session_state.lang=="zh" else "No permission to view reports"))
    else:
        st.markdown(f'<p class="card-title" style="margin-bottom:1rem;">{u("settle_title")}</p>',
                    unsafe_allow_html=True)

        # Mode toggle
        settle_mode = st.radio(
            "settle_mode", [u("settle_mode_day"), u("settle_mode_mth"), u("settle_mode_comm")],
            horizontal=True, key="settle_mode_radio", label_visibility="collapsed",
        )
        is_monthly   = (settle_mode == u("settle_mode_mth"))
        is_comm_mode = (settle_mode == u("settle_mode_comm"))
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    
        # ════════════════════════════════════════════════════════════════════════
        # DAILY MODE
        # ════════════════════════════════════════════════════════════════════════
        if not is_monthly and not is_comm_mode:
            # Date picker + export button on same row
            settle_col1, settle_col2, settle_col3 = st.columns([1.2, 2, 1])
            with settle_col1:
                settle_date = st.date_input(u("settle_date"), value=dt_date.today(), key="settle_date_pick")
            settle_str = str(settle_date)
    
            # ── Gather data for selected date ──────────────────────────────────
            day_bk      = [b for b in st.session_state.bookings if b.get("date") == settle_str]
            day_paid    = [b for b in day_bk if b.get("paid")]
            day_unpaid  = [b for b in day_bk if not b.get("paid")]
            day_walkins = [w for w in st.session_state.walkins  if w.get("date") == settle_str]
    
            total_collected = sum(b.get("final", b.get("price", 0)) for b in day_paid) \
                            + sum(w.get("final", 0) for w in day_walkins)
            total_pending   = sum(b.get("price", 0) for b in day_unpaid)
            walkin_total    = sum(w.get("final", 0) for w in day_walkins)
    
            # ── Summary stats ──────────────────────────────────────────────────
            c1, c2, c3, c4 = st.columns(4, gap="medium")
            for col, (lbl, val, col_override) in zip([c1, c2, c3, c4], [
                (u("settle_total"),   f"RM {total_collected + total_pending:.2f}", "#c9a84c"),
                (u("settle_paid"),    f"RM {total_collected:.2f}",                 "#2ecc71"),
                (u("settle_pending"), f"RM {total_pending:.2f}",                   "#e67e22"),
                (u("settle_walkin"),  f"RM {walkin_total:.2f}",                    "#9b59b6"),
            ]):
                with col:
                    st.markdown(
                        f'<div class="stat-box"><div class="stat-val" style="color:{col_override};">'
                        f'{val}</div><div class="stat-lbl">{lbl}</div></div>',
                        unsafe_allow_html=True,
                    )
    
            # ── Excel export helper ────────────────────────────────────────────
            def build_excel():
                output = io.BytesIO()
                lang = st.session_state.lang
    
                # All bookings for selected date (not just paid)
                all_bk_rows = [
                    {
                        (u("col_s_name")):    b.get("name",""),
                        (u("col_s_stylist")): b.get("stylist",""),
                        (u("col_s_svc")):     b.get("service",""),
                        ("時間" if lang=="zh" else "Time"): b.get("time",""),
                        (u("col_s_method")):  b.get("method",""),
                        (u("col_s_amt")):     b.get("final", b.get("price",0)),
                        ("已付款" if lang=="zh" else "Paid"): ("是" if b.get("paid") else "否") if lang=="zh" else ("Yes" if b.get("paid") else "No"),
                    }
                    for b in day_bk
                ]
                # Paid + walk-ins
                paid_rows = [
                    {
                        u("col_s_name"):    b.get("name",""),
                        u("col_s_stylist"): b.get("stylist",""),
                        u("col_s_svc"):     b.get("service",""),
                        u("col_s_method"):  b.get("method",""),
                        u("col_s_amt"):     b.get("final", b.get("price",0)),
                        u("col_s_type"):    ("預約" if lang=="zh" else "Booking"),
                    }
                    for b in day_paid
                ] + [
                    {
                        u("col_s_name"):    w.get("name",""),
                        u("col_s_stylist"): "—",
                        u("col_s_svc"):     w.get("service",""),
                        u("col_s_method"):  w.get("method",""),
                        u("col_s_amt"):     w.get("final",0),
                        u("col_s_type"):    ("即場客" if lang=="zh" else "Walk-in"),
                    }
                    for w in day_walkins
                ]
                summary_data = [
                    {("項目" if lang=="zh" else "Item"): ("結算日期" if lang=="zh" else "Date"), ("數值" if lang=="zh" else "Value"): settle_str},
                    {("項目" if lang=="zh" else "Item"): u("settle_total"),   ("數值" if lang=="zh" else "Value"): f"RM {total_collected + total_pending:.2f}"},
                    {("項目" if lang=="zh" else "Item"): u("settle_paid"),    ("數值" if lang=="zh" else "Value"): f"RM {total_collected:.2f}"},
                    {("項目" if lang=="zh" else "Item"): u("settle_pending"), ("數值" if lang=="zh" else "Value"): f"RM {total_pending:.2f}"},
                    {("項目" if lang=="zh" else "Item"): u("settle_walkin"),  ("數值" if lang=="zh" else "Value"): f"RM {walkin_total:.2f}"},
                ]
    
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name=("摘要" if lang=="zh" else "Summary"), index=False)
                    if all_bk_rows:
                        pd.DataFrame(all_bk_rows).to_excel(writer, sheet_name=("全部預約" if lang=="zh" else "All Bookings"), index=False)
                    if paid_rows:
                        pd.DataFrame(paid_rows).to_excel(writer, sheet_name=("收款明細" if lang=="zh" else "Payments"), index=False)
                    for sheet in writer.sheets.values():
                        for col_cells in sheet.columns:
                            max_len = max((len(str(c.value)) for c in col_cells if c.value), default=10)
                            sheet.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 40)
                return output.getvalue()
    
            with settle_col3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                st.download_button(
                    label=u("settle_export"),
                    data=build_excel(),
                    file_name=f"SignatureKim_{settle_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="excel_download",
                )
    
            st.markdown("<hr>", unsafe_allow_html=True)
    
            # ── Detail rows ────────────────────────────────────────────────────
            detail_rows = [
                {
                    u("col_s_name"):    b.get("name", ""),
                    u("col_s_stylist"): b.get("stylist", ""),
                    u("col_s_svc"):     b.get("service", ""),
                    u("col_s_method"):  b.get("method", ""),
                    u("col_s_amt"):     b.get("final", b.get("price", 0)),
                    u("col_s_type"):    "預約" if st.session_state.lang == "zh" else "Booking",
                }
                for b in day_paid
            ] + [
                {
                    u("col_s_name"):    w.get("name", ""),
                    u("col_s_stylist"): "—",
                    u("col_s_svc"):     w.get("service", ""),
                    u("col_s_method"):  w.get("method", ""),
                    u("col_s_amt"):     w.get("final", 0),
                    u("col_s_type"):    "即場客" if st.session_state.lang == "zh" else "Walk-in",
                }
                for w in day_walkins
            ]
    
            if not detail_rows:
                st.markdown(f'<div class="alert-warn">{u("settle_no_data")}</div>', unsafe_allow_html=True)
            else:
                df_detail, df_sty, df_svc, df_mth = _settle_build_panels(
                    day_paid, day_walkins, total_collected)
                left_col, right_col = st.columns([1.6, 1], gap="large")
                with left_col:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="card-title">{u("settle_detail")}</p>', unsafe_allow_html=True)
                    st.dataframe(df_detail, use_container_width=True, hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    _render_sty_panel(df_sty)
                with right_col:
                    _render_right_panels(df_svc, df_mth, total_collected)
    
        # ════════════════════════════════════════════════════════════════════════
        # MONTHLY MODE
        # ════════════════════════════════════════════════════════════════════════
        if is_monthly:
            today_now = dt_date.today()
            month_names_zh = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
            month_names_en = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            mnames = month_names_zh if st.session_state.lang == "zh" else month_names_en
    
            mc1, mc2, mc3 = st.columns([0.8, 0.8, 1.4])
            with mc1:
                sel_year  = st.number_input(
                    "年份 / Year", min_value=2020, max_value=2035,
                    value=today_now.year, step=1, key="settle_year",
                )
            with mc2:
                sel_mname = st.selectbox(
                    "月份 / Month", mnames,
                    index=today_now.month - 1, key="settle_month_sel",
                )
                sel_month = mnames.index(sel_mname) + 1
            settle_mth_str = f"{int(sel_year)}-{sel_month:02d}"
    
            # ── Gather monthly data ───────────────────────────────────────────
            mth_prefix   = settle_mth_str
            mth_bk       = [b for b in st.session_state.bookings if b.get("date","").startswith(mth_prefix)]
            mth_paid     = [b for b in mth_bk if b.get("paid")]
            mth_unpaid   = [b for b in mth_bk if not b.get("paid")]
            mth_walkins  = [w for w in st.session_state.walkins if w.get("date","").startswith(mth_prefix)]
    
            mth_collected = sum(b.get("final",b.get("price",0)) for b in mth_paid) \
                          + sum(w.get("final",0) for w in mth_walkins)
            mth_pending   = sum(b.get("price",0) for b in mth_unpaid)
            mth_walkin_t  = sum(w.get("final",0) for w in mth_walkins)
            mth_clients   = len(mth_paid) + len(mth_walkins)
    
            # ── Build Excel for monthly ───────────────────────────────────────
            def build_excel_monthly():
                df_det_m, df_sty_m, df_svc_m, df_mth_m = _settle_build_panels(
                    mth_paid, mth_walkins, mth_collected)
                # daily breakdown
                days_in_m = _cal.monthrange(int(sel_year), sel_month)[1]
                daily_rows = []
                for d in range(1, days_in_m + 1):
                    ds = f"{int(sel_year)}-{sel_month:02d}-{d:02d}"
                    dp = [b for b in mth_paid if b.get("date") == ds]
                    dw = [w for w in mth_walkins if w.get("date") == ds]
                    if dp or dw:
                        rev = sum(b.get("final",b.get("price",0)) for b in dp) + sum(w.get("final",0) for w in dw)
                        daily_rows.append({
                            u("col_s_date"): ds,
                            u("col_s_clients"): len(dp)+len(dw),
                            u("col_s_rev"): round(rev,2),
                        })
                lang = st.session_state.lang
                summary_data = [
                    {("月份" if lang=="zh" else "Month"): settle_mth_str},
                    {("已收款" if lang=="zh" else "Collected"): f"RM {mth_collected:.2f}"},
                    {("待收款" if lang=="zh" else "Pending"):   f"RM {mth_pending:.2f}"},
                    {("即場客" if lang=="zh" else "Walk-ins"):  f"RM {mth_walkin_t:.2f}"},
                    {("總客數" if lang=="zh" else "Clients"):   mth_clients},
                ]
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name=("摘要" if lang=="zh" else "Summary"), index=False)
                    if daily_rows: pd.DataFrame(daily_rows).to_excel(writer, sheet_name=("每日明細" if lang=="zh" else "Daily"), index=False)
                    if not df_det_m.empty: df_det_m.to_excel(writer, sheet_name=("收款明細" if lang=="zh" else "Payments"), index=False)
                    if not df_sty_m.empty: df_sty_m.to_excel(writer, sheet_name=("髮型師業績" if lang=="zh" else "Stylists"), index=False)
                    if not df_svc_m.empty: df_svc_m.to_excel(writer, sheet_name=("服務統計" if lang=="zh" else "Services"), index=False)
                    if not df_mth_m.empty: df_mth_m.to_excel(writer, sheet_name=("付款方式" if lang=="zh" else "Methods"), index=False)
                    for sheet in writer.sheets.values():
                        for col_cells in sheet.columns:
                            ml = max((len(str(c.value)) for c in col_cells if c.value), default=10)
                            sheet.column_dimensions[col_cells[0].column_letter].width = min(ml+4, 40)
                return out.getvalue()
    
            with mc3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                st.download_button(
                    label=u("settle_export"),
                    data=build_excel_monthly(),
                    file_name=f"SignatureKim_{settle_mth_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="excel_monthly",
                )
    
            # ── Monthly stats ─────────────────────────────────────────────────
            st.markdown("<hr>", unsafe_allow_html=True)
            ms1,ms2,ms3,ms4 = st.columns(4, gap="medium")
            for col,(lbl,val,cl) in zip([ms1,ms2,ms3,ms4],[
                (u("settle_paid"),    f"RM {mth_collected:.2f}", "#2ecc71"),
                (u("settle_pending"), f"RM {mth_pending:.2f}",   "#e67e22"),
                (u("settle_walkin"),  f"RM {mth_walkin_t:.2f}",  "#9b59b6"),
                (u("settle_clients"), str(mth_clients),           "#c9a84c"),
            ]):
                with col:
                    st.markdown(
                        f'<div class="stat-box"><div class="stat-val" style="color:{cl};">'
                        f'{val}</div><div class="stat-lbl">{lbl}</div></div>',
                        unsafe_allow_html=True)
    
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    
            if not mth_paid and not mth_walkins:
                st.markdown(f'<div class="alert-warn">{u("settle_no_data")}</div>', unsafe_allow_html=True)
            else:
                df_det_m, df_sty_m, df_svc_m, df_mth_m = _settle_build_panels(
                    mth_paid, mth_walkins, mth_collected)
    
                # Daily bar chart (text-based)
                days_in_m = _cal.monthrange(int(sel_year), sel_month)[1]
                daily_rows = []
                for d in range(1, days_in_m+1):
                    ds = f"{int(sel_year)}-{sel_month:02d}-{d:02d}"
                    dp = [b for b in mth_paid if b.get("date")==ds]
                    dw = [w for w in mth_walkins if w.get("date")==ds]
                    rev = sum(b.get("final",b.get("price",0)) for b in dp)+sum(w.get("final",0) for w in dw)
                    daily_rows.append({u("col_s_date"):ds, u("col_s_clients"):len(dp)+len(dw), u("col_s_rev"):round(rev,2)})
                df_daily = pd.DataFrame(daily_rows)
                df_daily_show = df_daily[df_daily[u("col_s_rev")]>0].reset_index(drop=True)
    
                ml_col, mr_col = st.columns([1.6, 1], gap="large")
                with ml_col:
                    # Daily breakdown table
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="card-title">{u("settle_daily_bk")}</p>', unsafe_allow_html=True)
                    if df_daily_show.empty:
                        st.markdown("<p style='color:#555;font-size:0.85rem;'>—</p>", unsafe_allow_html=True)
                    else:
                        max_rev_d = df_daily_show[u("col_s_rev")].max() or 1
                        for _, row in df_daily_show.iterrows():
                            bar_w = int(row[u("col_s_rev")] / max_rev_d * 100)
                            date_label = row[u("col_s_date")][5:]  # MM-DD
                            st.markdown(
                                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
                                f"<span style='color:#888;font-size:0.78rem;min-width:42px;'>{date_label}</span>"
                                f"<div style='flex:1;height:18px;background:#1a1a1a;border-radius:4px;overflow:hidden;'>"
                                f"<div style='width:{bar_w}%;height:100%;background:linear-gradient(90deg,#c9a84c,#f5e19a);border-radius:4px;'></div>"
                                f"</div>"
                                f"<span style='color:#c9a84c;font-size:0.82rem;min-width:75px;text-align:right;font-weight:700;'>"
                                f"RM {row[u('col_s_rev')]:.2f}</span>"
                                f"<span style='color:#666;font-size:0.72rem;min-width:28px;'>"
                                f"×{int(row[u('col_s_clients')])}</span>"
                                f"</div>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    _render_sty_panel(df_sty_m)
                with mr_col:
                    _render_right_panels(df_svc_m, df_mth_m, mth_collected)

        # ════════════════════════════════════════════════════════════════════════
        # COMMISSION REPORT MODE
        # ════════════════════════════════════════════════════════════════════════
        if is_comm_mode:
            st.markdown(f'<p class="card-title">{u("comm_report_title")}</p>', unsafe_allow_html=True)
            is_zh = (st.session_state.lang == "zh")

            # Date range selector
            cr1, cr2, cr3 = st.columns([1, 1, 1.5])
            with cr1:
                comm_start = st.date_input(
                    "開始日期" if is_zh else "From", value=dt_date.today().replace(day=1),
                    key="comm_start_date")
            with cr2:
                comm_end = st.date_input(
                    "結束日期" if is_zh else "To", value=dt_date.today(),
                    key="comm_end_date")

            comm_start_s = str(comm_start)
            comm_end_s   = str(comm_end)

            # Gather all paid bookings and walk-ins in range
            def _in_range(d):
                return comm_start_s <= str(d) <= comm_end_s

            range_paid    = [b for b in st.session_state.bookings
                             if b.get("paid") and _in_range(b.get("date",""))]
            range_walkins = [w for w in st.session_state.walkins
                             if _in_range(w.get("date",""))]
            comm_rates    = st.session_state.commissions

            # Build per-stylist per-service breakdown
            def _comm_rows():
                """Return list of row dicts for commission table."""
                from collections import defaultdict
                # Map (stylist, canonical_svc) -> revenue
                rev_map = defaultdict(float)
                all_stylists = set()
                for b in range_paid:
                    sty  = b.get("stylist","") or ("—" if is_zh else "—")
                    svc  = _canonical_svc(b.get("service",""))
                    amt  = float(b.get("final", b.get("price", 0)) or 0)
                    rev_map[(sty, svc)] += amt
                    all_stylists.add(sty)
                for w in range_walkins:
                    sty  = w.get("stylist","") or ("—" if is_zh else "—")
                    svc  = _canonical_svc(w.get("service",""))
                    amt  = float(w.get("final", 0) or 0)
                    rev_map[(sty, svc)] += amt
                    all_stylists.add(sty)

                rows_out = []
                grand_rev = 0.0
                grand_comm = 0.0
                for sty in sorted(all_stylists):
                    sty_rev   = 0.0
                    sty_comm  = 0.0
                    sty_rates = comm_rates.get(sty, {})
                    for zh_svc in SVC_ALL_ZH:
                        rev = rev_map.get((sty, zh_svc), 0.0)
                        if rev == 0:
                            continue
                        rate   = float(sty_rates.get(zh_svc, 0) or 0)
                        earned = rev * rate / 100
                        label  = zh_svc if is_zh else SVC_ZH_EN.get(zh_svc, zh_svc)
                        rows_out.append({
                            u("comm_stylist"): sty,
                            u("comm_service"): label,
                            u("comm_revenue"): round(rev, 2),
                            u("comm_rate_col"): f"{rate:.0f}%",
                            u("comm_amount"):  round(earned, 2),
                        })
                        sty_rev  += rev
                        sty_comm += earned
                    # Subtotal row per stylist
                    if sty_rev:
                        rows_out.append({
                            u("comm_stylist"): sty,
                            u("comm_service"): ("── " + ("小計" if is_zh else "Subtotal")),
                            u("comm_revenue"): round(sty_rev, 2),
                            u("comm_rate_col"): "—",
                            u("comm_amount"):  round(sty_comm, 2),
                        })
                    grand_rev  += sty_rev
                    grand_comm += sty_comm
                # Grand total
                rows_out.append({
                    u("comm_stylist"): "TOTAL",
                    u("comm_service"): "",
                    u("comm_revenue"): round(grand_rev, 2),
                    u("comm_rate_col"): "—",
                    u("comm_amount"):  round(grand_comm, 2),
                })
                return rows_out, grand_rev, grand_comm

            comm_rows_data, grand_rev, grand_comm = _comm_rows()

            if len(comm_rows_data) <= 1:
                st.markdown(f'<div class="alert-warn">{u("comm_no_data")}</div>',
                            unsafe_allow_html=True)
            else:
                # Summary stats
                cs1, cs2, cs3 = st.columns(3, gap="medium")
                for col, (lbl, val, cl) in zip([cs1, cs2, cs3], [
                    (("總業績" if is_zh else "Total Revenue"), f"RM {grand_rev:.2f}", "#c9a84c"),
                    (("總抽成" if is_zh else "Total Commission"), f"RM {grand_comm:.2f}", "#2ecc71"),
                    (("報表期間" if is_zh else "Period"),
                     f"{comm_start_s} → {comm_end_s}", "#3498db"),
                ]):
                    with col:
                        st.markdown(
                            f'<div class="stat-box"><div class="stat-val" style="color:{cl};font-size:1.1rem;">'
                            f'{val}</div><div class="stat-lbl">{lbl}</div></div>',
                            unsafe_allow_html=True)

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                df_comm_report = pd.DataFrame(comm_rows_data)

                # Highlight total rows
                def _style_comm(row):
                    svc_val = str(row.get(u("comm_service"), ""))
                    if row.get(u("comm_stylist")) == "TOTAL":
                        return ["background-color:#2c2000;color:#f5e19a;font-weight:bold"] * len(row)
                    if "小計" in svc_val or "Subtotal" in svc_val:
                        return ["background-color:#1a1a0a;color:#c9a84c;font-style:italic"] * len(row)
                    return [""] * len(row)

                styled_df = df_comm_report.style.apply(_style_comm, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

                # Excel export
                def _build_comm_excel():
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine="openpyxl") as writer:
                        df_comm_report.to_excel(writer, sheet_name=("抽成報表" if is_zh else "Commission"), index=False)
                        ws = writer.sheets[("抽成報表" if is_zh else "Commission")]
                        for col_cells in ws.columns:
                            ml = max((len(str(c.value)) for c in col_cells if c.value), default=10)
                            ws.column_dimensions[col_cells[0].column_letter].width = min(ml + 4, 40)
                    return out.getvalue()

                with cr3:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    st.download_button(
                        label=u("comm_export"),
                        data=_build_comm_excel(),
                        file_name=f"Commission_{comm_start_s}_{comm_end_s}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="comm_excel_dl",
                    )

    # ═════════════════════════════════════════════════════════════════════════════
    # TAB 6 — MEMBERS
    # ═════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown(f'<p class="card-title" style="font-size:1.3rem;">{u("mem_title")}</p>', unsafe_allow_html=True)

    # ── Overview stats ─────────────────────────────────────────────────────
    total_mem   = len(st.session_state.members)
    vip_count   = sum(1 for m in st.session_state.members if tier_for_points(m.get("points",0))["key"]=="VIP")
    total_pts   = sum(m.get("points",0) for m in st.session_state.members)

    ov1, ov2, ov3 = st.columns(3, gap="medium")
    for col, (lbl, val, clr) in zip([ov1, ov2, ov3], [
        (u("mem_total"),      str(total_mem), "#c9a84c"),
        (u("mem_vip_count"),  str(vip_count), "#e74c3c"),
        (u("mem_pts_issued"), f"{total_pts:,}", "#3498db"),
    ]):
        with col:
            st.markdown(
                f'<div class="stat-box"><div class="stat-val" style="color:{clr};">'
                f'{val}</div><div class="stat-lbl">{lbl}</div></div>',
                unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    mem_left, mem_right = st.columns([1, 1.6], gap="large")

    # ── LEFT: Add form + search + list ────────────────────────────────────
    with mem_left:
        # Add member form
        with st.expander(u("mem_add"), expanded=(total_mem == 0)):
            new_name  = st.text_input(u("mem_name"),  placeholder=u("mem_name_ph"),  key="new_mem_name")
            new_phone = st.text_input(u("mem_phone"), placeholder=u("mem_phone_ph"), key="new_mem_phone")
            new_bday  = st.text_input(u("mem_bday"),  placeholder="YYYY-MM-DD",      key="new_mem_bday")
            new_notes = st.text_area(u("mem_notes"),  placeholder=u("mem_notes_ph"), key="new_mem_notes", height=80)
            if st.button(u("mem_add_btn"), key="add_mem_btn"):
                if not new_name.strip():
                    st.markdown(f'<div class="alert-warn">{u("mem_name_warn")}</div>', unsafe_allow_html=True)
                else:
                    import uuid as _uuid
                    new_mem = {
                        "id":         str(_uuid.uuid4())[:8],
                        "name":       new_name.strip(),
                        "phone":      new_phone.strip(),
                        "birthday":   new_bday.strip(),
                        "tier":       "普通",
                        "points":     0,
                        "total_spent":0.0,
                        "visit_count":0,
                        "notes":      new_notes.strip(),
                        "join_date":  str(dt_date.today()),
                        "history":    [],
                    }
                    st.session_state.members.append(new_mem)
                    _bd()["members"] = st.session_state.members
                    if _USE_DB:
                        try: db_add_member(st.session_state.cur_branch, new_mem)
                        except Exception: pass
                    st.markdown(f'<div class="alert-safe">{u("mem_added").format(new_name.strip())}</div>', unsafe_allow_html=True)
                    st.rerun()

        # Search
        mem_q = st.text_input(u("mem_search"), placeholder=u("mem_search_ph"), key="mem_search_q", label_visibility="collapsed")
        st.markdown(f"<p style='margin:0 0 8px;font-size:0.78rem;letter-spacing:2px;color:#666;'>{u('mem_search').upper()}</p>", unsafe_allow_html=True)

        filtered = [
            m for m in st.session_state.members
            if mem_q.lower() in m.get("name","").lower() or mem_q.lower() in m.get("phone","").lower()
        ] if mem_q else st.session_state.members

        if not st.session_state.members:
            st.markdown(f'<div class="alert-warn">{u("mem_no_members")}</div>', unsafe_allow_html=True)
        elif not filtered:
            st.markdown(f'<div class="alert-warn">{u("mem_no_result")}</div>', unsafe_allow_html=True)
        else:
            for m in filtered:
                t     = tier_for_points(m.get("points", 0))
                tlbl  = tier_label(t)
                is_sel = (st.session_state.sel_member_id == m["id"])
                border = f"2px solid {t['color']}" if is_sel else f"1px solid #c9a84c33"
                bg     = "#1a1500" if is_sel else "#111"
                st.markdown(
                    f'<div style="background:{bg};border:{border};border-radius:12px;'
                    f'padding:10px 14px;margin-bottom:8px;cursor:pointer;">',
                    unsafe_allow_html=True)
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(
                        f'<div style="font-family:\'Playfair Display\',serif;color:#c9a84c;font-size:0.95rem;">'
                        f'{t["badge"]} {m["name"]}</div>'
                        f'<div style="font-size:0.72rem;color:#666;letter-spacing:1px;">'
                        f'{m.get("phone","—")} &nbsp;|&nbsp; {m.get("points",0)} pts</div>',
                        unsafe_allow_html=True)
                with c2:
                    if st.button(tlbl, key=f"sel_mem_{m['id']}", help=m["name"]):
                        st.session_state.sel_member_id = m["id"]
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ── RIGHT: Member detail ───────────────────────────────────────────────
    with mem_right:
        sel_id  = st.session_state.sel_member_id
        sel_mem = next((m for m in st.session_state.members if m["id"] == sel_id), None)

        if sel_mem is None:
            st.markdown(
                f'<div class="card" style="text-align:center;padding:3rem 1rem;">'
                f'<div style="font-size:3rem;">👥</div>'
                f'<div style="color:#555;font-size:0.9rem;letter-spacing:2px;margin-top:1rem;">'
                f'{u("mem_select")}</div></div>',
                unsafe_allow_html=True)
        else:
            t     = tier_for_points(sel_mem.get("points", 0))
            tlbl  = tier_label(t)

            # Profile header
            st.markdown(
                f'<div class="card">'
                f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:1rem;">'
                f'<div style="width:56px;height:56px;border-radius:50%;background:{t["color"]}22;'
                f'border:2px solid {t["color"]};display:flex;align-items:center;justify-content:center;'
                f'font-size:1.6rem;">{t["badge"]}</div>'
                f'<div><div style="font-family:\'Playfair Display\',serif;font-size:1.3rem;color:#f0ece0;">'
                f'{sel_mem["name"]}</div>'
                f'<div style="font-size:0.75rem;color:{t["color"]};letter-spacing:2px;font-weight:700;">'
                f'{tlbl} — {t["disc"]}% {("折扣" if st.session_state.lang=="zh" else "discount")}</div></div></div>',
                unsafe_allow_html=True)

            # Points progress bar to next tier
            next_tiers = [x for x in TIERS if x["min_pts"] > sel_mem.get("points",0)]
            if next_tiers:
                nt       = next_tiers[0]
                pts_now  = sel_mem.get("points", 0)
                pts_need = nt["min_pts"]
                prog     = min(pts_now / pts_need, 1.0)
                nt_lbl   = nt["en"] if st.session_state.lang=="en" else nt["key"]
                st.markdown(
                    f'<div style="margin-bottom:0.8rem;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#666;margin-bottom:4px;">'
                    f'<span>{pts_now} pts</span>'
                    f'<span>→ {nt_lbl} @ {pts_need} pts</span></div>'
                    f'<div style="height:6px;background:#1a1a1a;border-radius:3px;">'
                    f'<div style="width:{int(prog*100)}%;height:100%;background:linear-gradient(90deg,{t["color"]},{nt["color"]});border-radius:3px;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True)

            # Stats grid
            stats_data = [
                (u("mem_points"),  f'{sel_mem.get("points",0):,}',             "#c9a84c"),
                (u("mem_spent"),   f'RM {sel_mem.get("total_spent",0):.2f}',   "#2ecc71"),
                (u("mem_visits"),  str(sel_mem.get("visit_count",0)),           "#3498db"),
                (u("mem_joined"),  sel_mem.get("join_date","—"),                "#888"),
            ]
            sg1, sg2 = st.columns(2)
            for col, (lbl, val, clr) in zip([sg1, sg2, sg1, sg2], stats_data):
                with col:
                    st.markdown(
                        f'<div style="background:#0a0a0a;border:1px solid #c9a84c22;border-radius:8px;'
                        f'padding:8px 12px;margin-bottom:8px;text-align:center;">'
                        f'<div style="font-size:1rem;color:{clr};font-weight:700;">{val}</div>'
                        f'<div style="font-size:0.65rem;color:#555;letter-spacing:1px;">{lbl}</div></div>',
                        unsafe_allow_html=True)

            # Birthday
            if sel_mem.get("birthday"):
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#888;margin-bottom:6px;">🎂 {sel_mem["birthday"]}</div>',
                    unsafe_allow_html=True)
            if sel_mem.get("phone"):
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#888;margin-bottom:6px;">📞 {sel_mem["phone"]}</div>',
                    unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # Notes editor
            with st.expander(u("mem_edit_notes")):
                new_notes_val = st.text_area(
                    "", value=sel_mem.get("notes",""),
                    placeholder=u("mem_notes_ph"), key=f"edit_notes_{sel_id}", height=100,
                    label_visibility="collapsed")
                if st.button(u("mem_save_notes"), key=f"save_notes_{sel_id}"):
                    for m in st.session_state.members:
                        if m["id"] == sel_id:
                            m["notes"] = new_notes_val
                    st.markdown(f'<div class="alert-safe">{u("mem_notes_saved")}</div>', unsafe_allow_html=True)
                    st.rerun()

            # Spending history
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">{u("mem_history")}</p>', unsafe_allow_html=True)
            hist = sel_mem.get("history", [])
            if not hist:
                st.markdown(f'<div style="color:#555;font-size:0.85rem;">{u("mem_no_history")}</div>', unsafe_allow_html=True)
            else:
                for h in reversed(hist[-20:]):
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'border-bottom:1px solid #c9a84c11;padding:6px 0;font-size:0.82rem;">'
                        f'<span style="color:#888;">{h.get("date","")}</span>'
                        f'<span style="color:#f0ece0;">{h.get("service","")}</span>'
                        f'<span style="color:#c9a84c;font-weight:700;">RM {h.get("amt",0):.2f}</span>'
                        f'<span style="color:#3498db;font-size:0.72rem;">+{h.get("pts",0)} pts</span>'
                        f'</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Delete button (manager+ only)
            if _can("member_delete"):
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                if st.button(f"🗑 {u('mem_delete')} — {sel_mem['name']}", key=f"del_mem_{sel_id}"):
                    mem_name_del = sel_mem["name"]
                    st.session_state.members = [m for m in st.session_state.members if m["id"] != sel_id]
                    _bd()["members"] = st.session_state.members
                    st.session_state.sel_member_id = None
                    st.markdown(f'<div class="alert-warn">{u("mem_deleted").format(mem_name_del)}</div>', unsafe_allow_html=True)
                    st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS TAB — Owner + Manager
# ═════════════════════════════════════════════════════════════════════════════
if _can("analytics"):
    with tab_analytics:
        import plotly.express as px
        import plotly.graph_objects as go
        from datetime import datetime as _dt_now, timedelta as _td
        import datetime as _dtt

        is_zh = st.session_state.lang == "zh"

        st.markdown(f'<p class="card-title" style="font-size:1.3rem;">📊 {"業績分析" if is_zh else "Analytics Dashboard"}</p>',
                    unsafe_allow_html=True)

        # ── Combine walkins + paid bookings into one revenue list ──────────
        revenue_rows = []
        for w in st.session_state.walkins:
            revenue_rows.append({
                "date":    w.get("date", ""),
                "service": w.get("service", ""),
                "stylist": w.get("name", ""),   # walkin has no stylist field; use name as fallback
                "amount":  float(w.get("final", 0) or 0),
                "method":  w.get("method", "Cash"),
                "type":    "walkin",
            })
        for b in st.session_state.bookings:
            if b.get("paid"):
                revenue_rows.append({
                    "date":    b.get("date", ""),
                    "service": b.get("service", ""),
                    "stylist": b.get("stylist", "—"),
                    "amount":  float(b.get("final", 0) or 0),
                    "method":  b.get("method", "Cash"),
                    "type":    "booking",
                })

        df_rev = pd.DataFrame(revenue_rows) if revenue_rows else pd.DataFrame(
            columns=["date","service","stylist","amount","method","type"])

        # Parse dates safely
        if not df_rev.empty:
            df_rev["date"] = pd.to_datetime(df_rev["date"], errors="coerce")
            df_rev = df_rev.dropna(subset=["date"])

        today    = _dtt.date.today()
        wk_start = today - _td(days=6)
        mo_start = today.replace(day=1)

        def _filt(df, period):
            if df.empty: return df
            if period == "week":  return df[df["date"].dt.date >= wk_start]
            if period == "month": return df[df["date"].dt.date >= mo_start]
            return df

        # ── Period selector ────────────────────────────────────────────────
        period = st.radio(
            "", ["week","month","all"],
            format_func=lambda x: {"week": "本週 / This Week",
                                   "month": "本月 / This Month",
                                   "all": "全部 / All Time"}[x],
            horizontal=True, key="analytics_period"
        )
        df_p = _filt(df_rev, period)

        # ── KPI Cards ──────────────────────────────────────────────────────
        total_rev  = df_p["amount"].sum() if not df_p.empty else 0
        total_txn  = len(df_p)
        avg_txn    = (total_rev / total_txn) if total_txn > 0 else 0
        total_bk   = len([b for b in st.session_state.bookings
                          if b.get("date","") >= str(mo_start if period=="month"
                          else wk_start if period=="week" else "2000-01-01")])

        k1, k2, k3, k4 = st.columns(4)
        for col, val, lbl in [
            (k1, f"RM {total_rev:,.0f}", "💰 " + ("總收入" if is_zh else "Revenue")),
            (k2, str(total_txn),          "🧾 " + ("交易數" if is_zh else "Transactions")),
            (k3, f"RM {avg_txn:,.0f}",    "📈 " + ("平均客單" if is_zh else "Avg Ticket")),
            (k4, str(total_bk),           "📅 " + ("預約數" if is_zh else "Bookings")),
        ]:
            col.markdown(
                f'<div class="stat-box"><div class="stat-val">{val}</div>'
                f'<div class="stat-lbl">{lbl}</div></div>',
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── Revenue Trend Chart ────────────────────────────────────────────
        if not df_p.empty:
            df_daily = df_p.groupby(df_p["date"].dt.date)["amount"].sum().reset_index()
            df_daily.columns = ["date", "revenue"]
            fig_trend = px.area(
                df_daily, x="date", y="revenue",
                title="📈 " + ("收入走勢" if is_zh else "Revenue Trend"),
                labels={"date": "", "revenue": "RM"},
                color_discrete_sequence=["#c9a84c"],
            )
            fig_trend.update_layout(
                plot_bgcolor="#111", paper_bgcolor="#111",
                font_color="#f0ece0", title_font_color="#c9a84c",
                xaxis=dict(gridcolor="#1a1a1a", linecolor="#333"),
                yaxis=dict(gridcolor="#1a1a1a", linecolor="#333"),
                margin=dict(l=10, r=10, t=50, b=10),
            )
            fig_trend.update_traces(fillcolor="rgba(201,168,76,0.15)", line_color="#c9a84c")
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("📊 " + ("暫無收入資料" if is_zh else "No revenue data yet"))

        # ── Service + Stylist Charts side by side ─────────────────────────
        ch1, ch2 = st.columns(2)

        with ch1:
            if not df_p.empty and df_p["service"].any():
                df_svc = df_p.groupby("service")["amount"].sum().reset_index()
                df_svc = df_svc.sort_values("amount", ascending=False)
                fig_svc = px.pie(
                    df_svc, values="amount", names="service",
                    title="✂️ " + ("服務收入佔比" if is_zh else "Revenue by Service"),
                    color_discrete_sequence=px.colors.sequential.Oranges_r,
                    hole=0.4,
                )
                fig_svc.update_layout(
                    plot_bgcolor="#111", paper_bgcolor="#111",
                    font_color="#f0ece0", title_font_color="#c9a84c",
                    legend=dict(font=dict(color="#aaa"), bgcolor="#111"),
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_svc, use_container_width=True)
            else:
                st.info("No service data")

        with ch2:
            bk_stylists = [b.get("stylist","—") for b in st.session_state.bookings
                           if b.get("stylist") and b.get("date","") >= str(
                               mo_start if period=="month" else wk_start if period=="week" else "2000-01-01")]
            if bk_stylists:
                df_sty = pd.Series(bk_stylists).value_counts().reset_index()
                df_sty.columns = ["stylist", "bookings"]
                fig_sty = px.bar(
                    df_sty, x="stylist", y="bookings",
                    title="💇 " + ("髮型師預約數" if is_zh else "Bookings by Stylist"),
                    labels={"stylist": "", "bookings": ("預約" if is_zh else "Bookings")},
                    color_discrete_sequence=["#c9a84c"],
                )
                fig_sty.update_layout(
                    plot_bgcolor="#111", paper_bgcolor="#111",
                    font_color="#f0ece0", title_font_color="#c9a84c",
                    xaxis=dict(gridcolor="#1a1a1a"),
                    yaxis=dict(gridcolor="#1a1a1a"),
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_sty, use_container_width=True)
            else:
                st.info("No stylist data")

        # ── Payment Methods + Peak Hours ───────────────────────────────────
        ch3, ch4 = st.columns(2)

        with ch3:
            if not df_p.empty and df_p["method"].any():
                df_pay = df_p.groupby("method")["amount"].sum().reset_index()
                COLORS = {"Cash":"#2ecc71","Visa/Card":"#3498db",
                          "Touch 'n Go":"#e74c3c","DuitNow QR":"#9b59b6"}
                fig_pay = px.pie(
                    df_pay, values="amount", names="method",
                    title="💳 " + ("付款方式" if is_zh else "Payment Methods"),
                    color="method",
                    color_discrete_map=COLORS,
                    hole=0.4,
                )
                fig_pay.update_layout(
                    plot_bgcolor="#111", paper_bgcolor="#111",
                    font_color="#f0ece0", title_font_color="#c9a84c",
                    legend=dict(font=dict(color="#aaa"), bgcolor="#111"),
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_pay, use_container_width=True)
            else:
                st.info("No payment data")

        with ch4:
            # Peak hours from bookings
            all_hours = [b.get("time","")[:2] for b in st.session_state.bookings
                         if b.get("time") and len(b.get("time","")) >= 2]
            if all_hours:
                df_hr = pd.Series(all_hours).value_counts().sort_index().reset_index()
                df_hr.columns = ["hour", "count"]
                df_hr["label"] = df_hr["hour"] + ":00"
                fig_hr = px.bar(
                    df_hr, x="label", y="count",
                    title="⏰ " + ("預約高峰時段" if is_zh else "Peak Hours"),
                    labels={"label": "", "count": ("預約數" if is_zh else "Bookings")},
                    color_discrete_sequence=["#a07830"],
                )
                fig_hr.update_layout(
                    plot_bgcolor="#111", paper_bgcolor="#111",
                    font_color="#f0ece0", title_font_color="#c9a84c",
                    xaxis=dict(gridcolor="#1a1a1a"),
                    yaxis=dict(gridcolor="#1a1a1a"),
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_hr, use_container_width=True)
            else:
                st.info("No booking time data")

        # ── Top Services table ─────────────────────────────────────────────
        if not df_p.empty:
            st.markdown("---")
            st.markdown(f'<p class="card-title">🏆 {"熱門服務排行" if is_zh else "Top Services"}</p>',
                        unsafe_allow_html=True)
            df_top = df_p.groupby("service").agg(
                {"amount": ["sum","count","mean"]}
            ).round(1)
            df_top.columns = [("總收入 RM" if is_zh else "Revenue RM"),
                               ("次數" if is_zh else "Count"),
                               ("平均 RM" if is_zh else "Avg RM")]
            df_top = df_top.sort_values(("總收入 RM" if is_zh else "Revenue RM"), ascending=False)
            st.dataframe(df_top, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# ADMIN TAB — Owner only
# ═════════════════════════════════════════════════════════════════════════════
if _can("admin"):
    with tab_admin:
        is_zh = st.session_state.lang == "zh"
        is_platform_admin = _can("super_admin")

        # Title with role badge
        role_badge_clr = "#e74c3c" if is_platform_admin else "#c9a84c"
        role_badge_txt = ("🔴 平台管理員" if is_zh else "🔴 Platform Admin") if is_platform_admin \
                         else ("👑 老闆" if is_zh else "👑 Owner")
        st.markdown(
            f'<p class="card-title" style="font-size:1.3rem;">⚙️ {"系統管理" if is_zh else "Admin Panel"}'
            f' <span style="background:{role_badge_clr}22;border:1px solid {role_badge_clr}55;'
            f'color:{role_badge_clr};font-size:0.7rem;padding:3px 10px;border-radius:20px;'
            f'vertical-align:middle;letter-spacing:1px">{role_badge_txt}</span></p>',
            unsafe_allow_html=True
        )

        # ── Platform Overview (admin only) ────────────────────────────────
        if is_platform_admin:
            st.markdown('<div class="card" style="margin-bottom:1rem;border-color:#e74c3c44">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title" style="color:#e74c3c">🔴 {"平台總覽" if is_zh else "Platform Overview"}</p>',
                        unsafe_allow_html=True)
            total_salons  = len(st.session_state.branches)
            total_accts   = len(st.session_state.accounts)
            owner_accts   = len([a for a in st.session_state.accounts.values() if a["role"] == "owner"])
            active_subs   = len([i for i in st.session_state.get("salon_info",{}).values()
                                 if i.get("plan") == "active"])
            trial_subs    = len([i for i in st.session_state.get("salon_info",{}).values()
                                 if i.get("plan","trial") == "trial"])
            po1,po2,po3,po4 = st.columns(4)
            for col, val, lbl in [
                (po1, total_salons,  "🏠 " + ("分店總數" if is_zh else "Total Branches")),
                (po2, owner_accts,   "👑 " + ("髮廊老闆" if is_zh else "Owners")),
                (po3, active_subs,   "✅ " + ("已訂閱" if is_zh else "Active Subs")),
                (po4, trial_subs,    "⏳ " + ("試用中" if is_zh else "On Trial")),
            ]:
                col.markdown(
                    f'<div class="stat-box"><div class="stat-val">{val}</div>'
                    f'<div class="stat-lbl">{lbl}</div></div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Salon Profile ──────────────────────────────────────────────────
        if not is_platform_admin:
            # Show profile editor for the current owner's own salon
            cur_bid  = st.session_state.cur_branch
            cur_info = st.session_state.get("salon_info", {}).get(cur_bid, {})
            st.markdown('<div class="card" style="margin-bottom:1rem;border-color:#c9a84c55">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">🏪 {"髮廊基本資料" if is_zh else "Salon Profile"}</p>',
                        unsafe_allow_html=True)
            st.markdown(f'<p style="color:#888;font-size:0.8rem;margin-bottom:1rem;">'
                        f'{"以下資料將顯示在收據上，請確保填寫正確。" if is_zh else "This information appears on receipts — please keep it accurate."}'
                        f'</p>', unsafe_allow_html=True)

            prof_c1, prof_c2 = st.columns(2)
            with prof_c1:
                pf_cname  = st.text_input("聯絡人 / Contact Person",
                                          value=cur_info.get("contact_name",""), key="pf_cname")
                pf_phone  = st.text_input("電話 / Phone No.",
                                          value=cur_info.get("contact_phone",""), key="pf_phone",
                                          placeholder="011-1234 5678")
                pf_email  = st.text_input("Email",
                                          value=cur_info.get("contact_email",""), key="pf_email",
                                          placeholder="salon@email.com")
                pf_web    = st.text_input("Website / Instagram",
                                          value=cur_info.get("website",""), key="pf_web",
                                          placeholder="https://instagram.com/yoursalon")
            with prof_c2:
                pf_addr   = st.text_area("Alamat / 地址",
                                         value=cur_info.get("address",""), key="pf_addr",
                                         placeholder="No. 12, Jalan ABC, Taman XYZ", height=80)
                ca1, ca2  = st.columns(2)
                with ca1:
                    pf_city = st.text_input("Bandar / 城市",
                                            value=cur_info.get("city",""), key="pf_city",
                                            placeholder="Kuala Lumpur")
                with ca2:
                    pf_post = st.text_input("Poskod / 郵編",
                                            value=cur_info.get("postcode",""), key="pf_post",
                                            placeholder="50000")
                pf_ssm    = st.text_input("No. SSM / ROC (Pendaftaran Perniagaan)",
                                          value=cur_info.get("ssm_no",""), key="pf_ssm",
                                          placeholder="SA0123456-X")
                pf_hours  = st.text_input("Waktu Operasi / 營業時間",
                                          value=cur_info.get("operating_hours",""), key="pf_hours",
                                          placeholder="Mon–Sat: 10am – 8pm, Sun: Closed")

            if st.button("💾 " + ("儲存基本資料" if is_zh else "Save Profile"),
                         key="save_profile_btn", type="primary"):
                profile_data = {
                    "contact_name":    pf_cname.strip(),
                    "contact_phone":   pf_phone.strip(),
                    "contact_email":   pf_email.strip(),
                    "address":         pf_addr.strip(),
                    "city":            pf_city.strip(),
                    "postcode":        pf_post.strip(),
                    "ssm_no":          pf_ssm.strip(),
                    "operating_hours": pf_hours.strip(),
                    "website":         pf_web.strip(),
                }
                if _USE_DB:
                    try:
                        db_update_salon_profile(cur_bid, profile_data)
                        fresh = db_get_salon_info(cur_bid)
                        st.session_state.setdefault("salon_info", {})[cur_bid] = fresh
                        st.success("✅ " + ("基本資料已儲存！" if is_zh else "Profile saved!"))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.session_state.setdefault("salon_info", {})[cur_bid].update(profile_data)
                    st.success("✅ " + ("已儲存（本機）" if is_zh else "Saved (local)"))

            # Preview card
            if any([cur_info.get("address"), cur_info.get("contact_phone"),
                    cur_info.get("ssm_no"), cur_info.get("operating_hours")]):
                st.markdown("<hr style='margin:12px 0;border-color:#1a1a1a'>", unsafe_allow_html=True)
                st.markdown(f'<p style="color:#888;font-size:0.72rem;letter-spacing:1px;margin-bottom:6px;">'
                            f'{"預覽（收據上顯示）" if is_zh else "PREVIEW (as shown on receipt)"}</p>',
                            unsafe_allow_html=True)
                addr_full = ", ".join(filter(None, [
                    cur_info.get("address",""),
                    cur_info.get("city",""),
                    cur_info.get("postcode","")
                ]))
                preview_parts = []
                if addr_full:       preview_parts.append(f"📍 {addr_full}")
                if cur_info.get("contact_phone"): preview_parts.append(f"📞 {cur_info['contact_phone']}")
                if cur_info.get("contact_email"): preview_parts.append(f"✉️ {cur_info['contact_email']}")
                if cur_info.get("website"):       preview_parts.append(f"🌐 {cur_info['website']}")
                if cur_info.get("ssm_no"):        preview_parts.append(f"📋 SSM: {cur_info['ssm_no']}")
                if cur_info.get("operating_hours"):preview_parts.append(f"🕐 {cur_info['operating_hours']}")
                st.markdown(
                    "<div style='background:#111;border-radius:8px;padding:12px 16px;"
                    "font-size:0.78rem;color:#aaa;line-height:2;'>"
                    + "<br>".join(preview_parts)
                    + "</div>", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # ── Subscription Management ────────────────────────────────────────
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">💳 {"訂閱管理" if is_zh else "Subscription Management"}</p>',
                    unsafe_allow_html=True)

        PLAN_COLORS = {"trial":"#e67e22","active":"#2ecc71","expired":"#e74c3c","owner":"#c9a84c"}
        PLAN_LABELS = {"trial":"試用中","active":"已訂閱","expired":"已到期","owner":"系統擁有者"}

        for bid, bname in st.session_state.branches.items():
            info  = st.session_state.get("salon_info", {}).get(bid, {})
            plan  = info.get("plan", "trial")
            tend  = info.get("trial_ends","—")
            pend  = info.get("plan_ends","—")
            color = PLAN_COLORS.get(plan, "#888")
            label = PLAN_LABELS.get(plan, plan)

            with st.expander(f"🏠 {bname} ({bid})  ·  "
                             f"[{label}]  {'到期：'+str(pend) if plan=='active' else '試用至：'+str(tend)}", expanded=False):
                sub_c1, sub_c2 = st.columns(2)

                with sub_c1:
                    st.markdown(f'<span style="color:{color};font-weight:700">{label}</span>', unsafe_allow_html=True)
                    new_stripe = st.text_input("Stripe Payment Link", value=info.get("stripe_link",""),
                                               key=f"stripe_{bid}", placeholder="https://buy.stripe.com/...")
                    new_contact_name  = st.text_input("聯絡人 / Contact", value=info.get("contact_name",""), key=f"cn_{bid}")
                    new_contact_phone = st.text_input("電話 / Phone",    value=info.get("contact_phone",""), key=f"cp_{bid}")
                    new_contact_email = st.text_input("Email",            value=info.get("contact_email",""), key=f"ce_{bid}")

                with sub_c2:
                    st.markdown(f"**{'啟用試用' if is_zh else 'Trial'}**")
                    trial_days = st.number_input("試用天數", value=30, min_value=1, max_value=365, key=f"td_{bid}")
                    if st.button("🔄 " + ("重設試用期" if is_zh else "Reset Trial"), key=f"trial_btn_{bid}"):
                        if _USE_DB:
                            try:
                                db_activate_trial(bid, int(trial_days))
                                st.success("✅ 試用期已重設")
                            except Exception as e:
                                st.error(str(e))

                    st.markdown(f"**{'啟用訂閱' if is_zh else 'Activate Plan'}**")
                    plan_end_date = st.date_input("訂閱到期日", key=f"ped_{bid}",
                                                   value=_sub_dt.date.today() + _sub_dt.timedelta(days=30))
                    if st.button("✅ " + ("啟用訂閱" if is_zh else "Activate"), key=f"act_btn_{bid}"):
                        if _USE_DB:
                            try:
                                db_update_salon_subscription(bid, "active", str(plan_end_date), new_stripe)
                                db_update_salon_contact(bid, new_contact_name, new_contact_phone, new_contact_email)
                                # Reload salon info
                                fresh = db_get_salon_info(bid)
                                st.session_state.setdefault("salon_info", {})[bid] = fresh
                                st.success(f"✅ 已啟用至 {plan_end_date}")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Online Booking Links ───────────────────────────────────────────
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">🔗 {"客戶預約連結" if is_zh else "Customer Booking Links"}</p>',
                    unsafe_allow_html=True)
        app_base = st.text_input(
            "App URL (from Streamlit Cloud)",
            placeholder="https://your-app-name.streamlit.app",
            key="app_base_url",
            help="Fill in your Streamlit Cloud app URL to generate booking links"
        )
        if app_base.strip():
            for bid, bname in st.session_state.branches.items():
                link = f"{app_base.rstrip('/')}/booking?salon={bid}"
                st.markdown(
                    f"**{bname}** (`{bid}`)  \n"
                    f"[{link}]({link})",
                    unsafe_allow_html=False
                )
                st.code(link, language=None)
        else:
            st.info("填入上方的 App URL 就能生成每間分店的客戶預約連結 / Enter your App URL above to generate booking links")
        st.markdown('</div>', unsafe_allow_html=True)

        ROLE_COLOR = {"admin":"#e74c3c","owner":"#c9a84c","manager":"#3498db","staff":"#2ecc71"}
        ROLE_ICON  = {"admin":"🔴","owner":"👑","manager":"💼","staff":"✂️"}
        ROLE_LABEL = {"admin":   ("平台管理員" if is_zh else "Platform Admin"),
                      "owner":   ("老闆" if is_zh else "Owner"),
                      "manager": ("經理" if is_zh else "Manager"),
                      "staff":   ("員工" if is_zh else "Staff")}

        # ════════════════════════════════════════════════════════════════════
        # BRANCH MANAGEMENT
        # ════════════════════════════════════════════════════════════════════
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">🏠 {"分店管理" if is_zh else "Branch Management"}</p>',
                    unsafe_allow_html=True)

        for bid, bname in list(st.session_state.branches.items()):
            info      = st.session_state.get("salon_info", {}).get(bid, {})
            plan      = info.get("plan", "trial")
            tend      = info.get("trial_ends", "—")
            pend      = info.get("plan_ends",  "—")
            PLAN_CLR  = {"trial":"#e67e22","active":"#2ecc71","expired":"#e74c3c"}
            PLAN_LBL  = {"trial":"試用中" if is_zh else "Trial",
                         "active":"已訂閱" if is_zh else "Active",
                         "expired":"已到期" if is_zh else "Expired"}
            plan_clr  = PLAN_CLR.get(plan, "#888")
            plan_lbl  = PLAN_LBL.get(plan, plan)
            # Count accounts in this branch
            branch_accts = [u for u, a in st.session_state.accounts.items()
                            if a.get("branch") in (bid, "all")]
            n_accts   = len(branch_accts)
            n_bk      = len(st.session_state.get("branch_data",{}).get(bid,{}).get("bookings",[]))
            n_members = len(st.session_state.get("branch_data",{}).get(bid,{}).get("members",[]))

            with st.expander(
                f"🏠 **{bname}**  `{bid}`  ·  "
                f"[{plan_lbl}]  ·  {n_accts} {'帳號' if is_zh else 'accounts'}",
                expanded=False
            ):
                ex_c1, ex_c2 = st.columns([1.5, 1])
                with ex_c1:
                    # Stats row
                    st.markdown(f"""
                    <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap">
                      <div class="stat-box" style="flex:1;min-width:80px">
                        <div class="stat-val" style="font-size:1.2rem">{n_bk}</div>
                        <div class="stat-lbl">{"預約" if is_zh else "Bookings"}</div>
                      </div>
                      <div class="stat-box" style="flex:1;min-width:80px">
                        <div class="stat-val" style="font-size:1.2rem">{n_members}</div>
                        <div class="stat-lbl">{"會員" if is_zh else "Members"}</div>
                      </div>
                      <div class="stat-box" style="flex:1;min-width:80px">
                        <div class="stat-val" style="font-size:1.2rem">{n_accts}</div>
                        <div class="stat-lbl">{"帳號" if is_zh else "Accounts"}</div>
                      </div>
                    </div>
                    <div style="font-size:0.8rem;color:#888;margin-bottom:6px">
                      {"訂閱狀態" if is_zh else "Subscription"}:
                      <span style="color:{plan_clr};font-weight:700">{plan_lbl}</span>
                      {"· 試用至: "+str(tend) if plan=="trial" else "· 到期: "+str(pend) if plan=="active" else ""}
                    </div>
                    """, unsafe_allow_html=True)

                    # Edit branch name
                    new_name_val = st.text_input(
                        "✏️ " + ("分店名稱" if is_zh else "Branch Name"),
                        value=bname, key=f"edit_bname_{bid}"
                    )
                    # Contact info from salon_info
                    st.markdown(f'<div style="font-size:0.78rem;color:#888;margin-top:4px">'
                                f'👤 {info.get("contact_name","—")}  '
                                f'📞 {info.get("contact_phone","—")}  '
                                f'✉️ {info.get("contact_email","—")}'
                                f'</div>', unsafe_allow_html=True)

                with ex_c2:
                    st.markdown(f'<div style="font-size:0.8rem;color:#c9a84c;margin-bottom:6px">{"關聯帳號" if is_zh else "Linked Accounts"}</div>',
                                unsafe_allow_html=True)
                    for ua in branch_accts:
                        a = st.session_state.accounts[ua]
                        r_clr = ROLE_COLOR.get(a["role"],"#888")
                        r_ico = ROLE_ICON.get(a["role"],"👤")
                        st.markdown(
                            f'<div style="font-size:0.82rem;padding:3px 0;border-bottom:1px solid #1a1a1a">'
                            f'{r_ico} <span style="color:#f0ece0">{ua}</span>'
                            f' <span style="color:{r_clr};font-size:0.7rem">({ROLE_LABEL.get(a["role"],a["role"])})</span>'
                            f'</div>', unsafe_allow_html=True
                        )

                save_c, del_c = st.columns([2, 1])
                with save_c:
                    if st.button("💾 " + ("儲存名稱" if is_zh else "Save Name"), key=f"save_bname_{bid}"):
                        if new_name_val.strip():
                            st.session_state.branches[bid] = new_name_val.strip()
                            if _USE_DB:
                                try:
                                    from db import get_supabase as _get_sb; _get_sb().table("salons").update({"name": new_name_val.strip()}).eq("id", bid).execute()
                                except Exception: pass
                            st.success("✅ " + ("已儲存" if is_zh else "Saved"))
                            st.rerun()
                with del_c:
                    if len(st.session_state.branches) > 1:
                        if st.button("🗑 " + ("刪除" if is_zh else "Delete"), key=f"del_branch_{bid}",
                                     help="⚠️ This will delete all branch data"):
                            del st.session_state.branches[bid]
                            if _USE_DB:
                                try: db_delete_salon(bid)
                                except Exception: pass
                            if st.session_state.cur_branch == bid:
                                st.session_state.cur_branch = next(iter(st.session_state.branches))
                            st.rerun()

        # Add new branch
        st.markdown(f'<p style="color:#c9a84c;font-size:0.82rem;letter-spacing:1px;margin-top:0.8rem">{"＋ 新增分店" if is_zh else "＋ Add Branch"}</p>',
                    unsafe_allow_html=True)
        nb_c1, nb_c2, nb_c3 = st.columns([1, 2, 1])
        with nb_c1:
            new_bid   = st.text_input("ID", placeholder="B002", key="new_bid")
        with nb_c2:
            new_bname = st.text_input("名稱 / Name", placeholder="Signature Kim — PJ", key="new_bname")
        with nb_c3:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("＋ " + ("新增" if is_zh else "Add"), key="add_branch_btn"):
                if new_bid.strip() and new_bname.strip():
                    st.session_state.branches[new_bid.strip()] = new_bname.strip()
                    _init_branch(new_bid.strip())
                    if _USE_DB:
                        try: db_add_salon(new_bid.strip(), new_bname.strip())
                        except Exception: pass
                    st.success(f"✅ {new_bname.strip()}")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # ACCOUNT MANAGEMENT
        # ════════════════════════════════════════════════════════════════════
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">👤 {"帳號管理" if is_zh else "Account Management"}</p>',
                    unsafe_allow_html=True)

        # Filter by branch
        filter_opts = ["全部 / All"] + [f"{bid} · {nm}" for bid, nm in st.session_state.branches.items()]
        acct_filter = st.selectbox("🔍 " + ("篩選分店" if is_zh else "Filter by Branch"),
                                   filter_opts, key="acct_filter")
        filter_bid  = None if acct_filter == "全部 / All" else acct_filter.split(" · ")[0]

        for uname, acct in list(st.session_state.accounts.items()):
            if filter_bid and acct.get("branch") not in (filter_bid, "all"):
                continue
            r_clr    = ROLE_COLOR.get(acct["role"],"#888")
            r_ico    = ROLE_ICON.get(acct["role"],"👤")
            r_lbl    = ROLE_LABEL.get(acct["role"], acct["role"])
            b_lbl    = ("全部分店" if is_zh else "All Branches") if acct.get("branch") == "all" \
                       else st.session_state.branches.get(acct.get("branch",""), acct.get("branch",""))
            is_me    = (uname == st.session_state.username)

            with st.expander(
                f"{r_ico} **{uname}**  ·  {acct.get('name','')}  ·  "
                f"[{r_lbl}]  ·  {b_lbl}" + (" 🔵 (你)" if is_me else ""),
                expanded=False
            ):
                ea_c1, ea_c2 = st.columns(2)
                with ea_c1:
                    st.markdown(f'<div style="display:inline-block;padding:4px 12px;border-radius:20px;'
                                f'background:{r_clr}22;border:1px solid {r_clr}55;'
                                f'color:{r_clr};font-size:0.78rem;font-weight:700;margin-bottom:10px">'
                                f'{r_ico} {r_lbl}</div>', unsafe_allow_html=True)

                    # Edit display name
                    new_disp = st.text_input("顯示名稱 / Display Name",
                                             value=acct.get("name",""), key=f"dn_{uname}")
                    # Edit role
                    role_opts = ["staff","manager","owner"]
                    new_role  = st.selectbox("角色 / Role", role_opts,
                                             index=role_opts.index(acct["role"]) if acct["role"] in role_opts else 0,
                                             key=f"role_{uname}",
                                             format_func=lambda r: f"{ROLE_ICON[r]} {ROLE_LABEL[r]}")
                    # Edit branch
                    bl        = list(st.session_state.branches.keys())
                    bn        = [st.session_state.branches[b] for b in bl]
                    all_opt   = ["all"]
                    all_disp  = [("全部 / All" if is_zh else "All Branches")]
                    cur_br    = acct.get("branch","")
                    all_opts_combined = all_opt + bl
                    all_disp_combined = all_disp + bn
                    br_idx    = all_opts_combined.index(cur_br) if cur_br in all_opts_combined else 1
                    new_br    = st.selectbox("分店 / Branch", all_opts_combined, index=br_idx,
                                             key=f"br_{uname}",
                                             format_func=lambda b: all_disp_combined[all_opts_combined.index(b)])

                with ea_c2:
                    st.markdown(f'<div style="color:#888;font-size:0.8rem;margin-bottom:8px">'
                                f'{"重設密碼" if is_zh else "Reset Password"}</div>', unsafe_allow_html=True)
                    new_pw    = st.text_input("新密碼 / New Password", type="password", key=f"npw_{uname}",
                                              placeholder="6+ chars")
                    new_pw2   = st.text_input("確認 / Confirm", type="password", key=f"npw2_{uname}")
                    if st.button("🔑 " + ("重設密碼" if is_zh else "Reset"), key=f"rpw_{uname}"):
                        if len(new_pw) < 6:
                            st.error("❌ " + ("密碼至少6位" if is_zh else "Min 6 chars"))
                        elif new_pw != new_pw2:
                            st.error("❌ " + ("密碼不一致" if is_zh else "Passwords don't match"))
                        else:
                            st.session_state.accounts[uname]["hash"] = _hash(new_pw)
                            if _USE_DB:
                                try: db_update_password(uname, _hash(new_pw))
                                except Exception: pass
                            st.success("✅ " + ("密碼已重設" if is_zh else "Password reset"))

                save_col, del_col = st.columns([2, 1])
                with save_col:
                    if st.button("💾 " + ("儲存變更" if is_zh else "Save Changes"), key=f"save_acct_{uname}"):
                        st.session_state.accounts[uname]["name"]   = new_disp.strip() or uname
                        st.session_state.accounts[uname]["role"]   = new_role
                        st.session_state.accounts[uname]["branch"] = new_br
                        if _USE_DB:
                            try:
                                db_delete_account(uname)
                                db_add_account(uname, st.session_state.accounts[uname]["hash"],
                                               new_role, new_br if new_br != "all" else None,
                                               new_disp.strip() or uname)
                            except Exception: pass
                        st.success("✅ " + ("已儲存" if is_zh else "Saved"))
                        st.rerun()
                with del_col:
                    if not is_me:
                        if st.button("🗑 " + ("刪除" if is_zh else "Delete"), key=f"del_acct_{uname}"):
                            del st.session_state.accounts[uname]
                            if _USE_DB:
                                try: db_delete_account(uname)
                                except Exception: pass
                            st.rerun()

        # ── Add New Account ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(f'<p style="color:#c9a84c;font-size:0.9rem;letter-spacing:1px;font-weight:700">＋ {"新增帳號" if is_zh else "Add New Account"}</p>',
                    unsafe_allow_html=True)
        na1, na2 = st.columns(2)
        with na1:
            na_user = st.text_input("Username", placeholder="staff01", key="na_user")
            na_name = st.text_input("顯示名稱 / Display Name", placeholder="Kim", key="na_name")
            na_pass = st.text_input("密碼 / Password", type="password", key="na_pass", placeholder="Min 6 chars")
        with na2:
            # Admin can create any role; owner cannot create admin
            role_choices = (["admin","owner","manager","staff"]
                            if _can("super_admin") else ["owner","manager","staff"])
            na_role = st.selectbox("角色 / Role", role_choices, key="na_role",
                                   format_func=lambda r: f"{ROLE_ICON[r]} {ROLE_LABEL[r]}")
            branch_list = list(st.session_state.branches.keys())
            branch_disp = [st.session_state.branches[b] for b in branch_list]
            na_branch_opts = branch_list + ["all"]
            na_branch_disp = branch_disp + [("全部 / All" if is_zh else "All Branches")]
            na_branch_sel  = st.selectbox("分店 / Branch", na_branch_opts, key="na_branch_sel",
                                          format_func=lambda b: na_branch_disp[na_branch_opts.index(b)])
            role_desc = {
                "admin":   "🔴 平台管理員：最高權限，管理所有髮廊、訂閱、帳號" if is_zh else "🔴 Platform Admin: Full control over all salons, subscriptions & accounts",
                "owner":   "👑 老闆：管理自己的分店、帳號、訂閱" if is_zh else "👑 Owner: Manage own branches, accounts & subscription",
                "manager": "💼 經理：管理自己分店的全部功能" if is_zh else "💼 Manager: Full access to own branch functions",
                "staff":   "✂️ 員工：只能使用預約和收費功能" if is_zh else "✂️ Staff: Bookings and payment only",
            }
            st.markdown(f"""
            <div style="background:#1a1a1a;border-radius:8px;padding:8px 12px;margin-top:6px;font-size:0.78rem;color:#888;border-left:3px solid {ROLE_COLOR.get(na_role,'#888')}">
              <b style="color:{ROLE_COLOR.get(na_role,'#888')}">{ROLE_LABEL.get(na_role,'')}</b><br>
              {role_desc.get(na_role,'')}
            </div>
            """, unsafe_allow_html=True)

        if st.button("＋ " + ("新增帳號" if is_zh else "Add Account"), key="add_acct_btn",
                     use_container_width=True):
            if na_user.strip() and na_pass.strip() and len(na_pass) >= 6:
                if na_user.strip() in st.session_state.accounts:
                    st.error("⚠ " + ("用戶名已存在" if is_zh else "Username already exists"))
                else:
                    new_acct = {
                        "hash":   _hash(na_pass),
                        "role":   na_role,
                        "branch": na_branch_sel,
                        "name":   na_name.strip() or na_user.strip(),
                    }
                    st.session_state.accounts[na_user.strip()] = new_acct
                    if _USE_DB:
                        try:
                            db_add_account(na_user.strip(), _hash(na_pass), na_role,
                                           na_branch_sel if na_branch_sel != "all" else None,
                                           na_name.strip() or na_user.strip())
                        except Exception: pass
                    st.success(f"✅ {na_user.strip()} ({ROLE_LABEL[na_role]}) — " +
                               (st.session_state.branches.get(na_branch_sel,"All")))
                    st.rerun()
            elif len(na_pass) < 6:
                st.warning("⚠ " + ("密碼至少6位" if is_zh else "Password must be 6+ chars"))
            else:
                st.warning("⚠ " + ("請填寫用戶名和密碼" if is_zh else "Please fill in username and password"))

        # ── Change own password ────────────────────────────────────────────
        st.markdown("---")
        with st.expander("🔑 " + ("修改自己的密碼" if is_zh else "Change My Password")):
            cp_old  = st.text_input("舊密碼 / Old Password", type="password", key="cp_old")
            cp_new  = st.text_input("新密碼 / New Password", type="password", key="cp_new")
            cp_new2 = st.text_input("確認 / Confirm",        type="password", key="cp_new2")
            if st.button("Update / 更新", key="cp_btn"):
                me = st.session_state.accounts.get(st.session_state.username)
                if not me or me["hash"] != _hash(cp_old):
                    st.error("❌ " + ("舊密碼不正確" if is_zh else "Old password incorrect"))
                elif cp_new != cp_new2:
                    st.error("❌ " + ("新密碼不一致" if is_zh else "Passwords don't match"))
                elif len(cp_new) < 6:
                    st.warning("⚠ " + ("密碼至少6位" if is_zh else "Password must be 6+ chars"))
                else:
                    st.session_state.accounts[st.session_state.username]["hash"] = _hash(cp_new)
                    if _USE_DB:
                        try: db_update_password(st.session_state.username, _hash(cp_new))
                        except Exception: pass
                    st.success("✦ " + ("密碼已更新" if is_zh else "Password updated"))

            st.markdown('</div>', unsafe_allow_html=True)
