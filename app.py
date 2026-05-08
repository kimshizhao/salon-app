import streamlit as st
import pandas as pd
import io
import calendar as _cal
from datetime import date as dt_date

st.set_page_config(
    page_title="Signature Kim",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Raleway:wght@300;400;600&display=swap');
  html, body, [class*="css"] { font-family:'Raleway',sans-serif; background:#0a0a0a; color:#f0ece0; }
  .stApp { background-color:#0a0a0a; }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:1.5rem 2.5rem 2rem; max-width:1200px; }

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
        "perf_title":    "📊 業績排行",
        "perf_today_rev":"今日業績",
        "perf_total_rev":"累計業績",
        "perf_clients":  "接待人次",
        "perf_top_svc":  "最多服務",
        "perf_avg":      "平均客單價",
        "perf_rank":     "排行",
        "perf_no_data":  "尚無業績記錄（未有結帳數據）",
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
        "perf_title":    "📊 Performance Ranking",
        "perf_today_rev":"Today's Revenue",
        "perf_total_rev":"Total Revenue",
        "perf_clients":  "Clients Served",
        "perf_top_svc":  "Top Service",
        "perf_avg":      "Avg. Per Client",
        "perf_rank":     "Rank",
        "perf_no_data":  "No performance data yet (no completed payments)",
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
    },
}

def u(key):    return UI[st.session_state.lang][key]
def svc_map(): return SERVICES[st.session_state.lang]
def bar_color(r): return "#2ecc71" if r > 0.6 else ("#e67e22" if r > 0.3 else "#e74c3c")

# ── Session State ─────────────────────────────────────────────────────────────
if "stylists" not in st.session_state:
    st.session_state.stylists = ["Kim", "Lily", "Jason"]

if "bookings" not in st.session_state:
    st.session_state.bookings = [
        {"name":"Siti Aminah",   "date":"2026-05-08","time":"10:00","stylist":"Kim",   "service":"染髮",    "note":"",         "price":180,"paid":False,"method":"","final":0},
        {"name":"Raj Kumar",     "date":"2026-05-08","time":"13:00","stylist":"Jason",  "service":"剪髮",    "note":"",         "price":50, "paid":False,"method":"","final":0},
        {"name":"Mei Ling",      "date":"2026-05-08","time":"15:30","stylist":"Lily",   "service":"頭皮護理","note":"第一次光顧","price":120,"paid":False,"method":"","final":0},
        {"name":"Ahmad Firdaus", "date":"2026-05-09","time":"11:00","stylist":"Kim",   "service":"燙髮",    "note":"",         "price":250,"paid":False,"method":"","final":0},
    ]

if "walkins" not in st.session_state:
    st.session_state.walkins = []

if "inventory" not in st.session_state:
    st.session_state.inventory = [
        {"name":"OSiS+ Dust It",        "category":"造型品",   "qty":14,"max":30,"unit":"瓶"},
        {"name":"OSiS+ Freeze",          "category":"定型噴霧","qty":7, "max":24,"unit":"瓶"},
        {"name":"Schwarzkopf IGORA",     "category":"染髮劑",  "qty":22,"max":50,"unit":"管"},
        {"name":"Fibre Clinix 蛋白護理", "category":"護髮品",  "qty":5, "max":20,"unit":"瓶"},
        {"name":"BLONDME 漂髮粉",        "category":"漂髮",    "qty":9, "max":25,"unit":"盒"},
        {"name":"OSiS+ Session Label",   "category":"造型品",  "qty":18,"max":30,"unit":"瓶"},
        {"name":"Chroma ID 酸性染",      "category":"染髮劑",  "qty":31,"max":60,"unit":"管"},
        {"name":"Scalp Clinix 頭皮精華", "category":"頭皮護理","qty":3, "max":15,"unit":"瓶"},
    ]

TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 20) for m in (0, 30)]
HIDDEN_BK_COLS = ["price", "paid", "method", "final"]

# ── Header ────────────────────────────────────────────────────────────────────
_, _, hdr_r = st.columns([3, 3, 1])
with hdr_r:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button(u("lang_btn"), key="lang_toggle"):
        st.session_state.lang = "en" if st.session_state.lang == "zh" else "zh"
        st.rerun()

st.markdown(f"""
<div class="hero">
  <p class="hero-title">✦ SIGNATURE KIM ✦</p>
  <p class="hero-sub">{u('subtitle')}</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([u("tab1"), u("tab2"), u("tab3"), u("tab4"), u("tab5")])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — BOOKINGS  (no pricing shown)
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
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
                st.session_state.bookings.append({
                    "name": b_name.strip(), "date": str(b_date), "time": b_time,
                    "stylist": b_stylist,   "service": b_svc,    "note": b_note,
                    "price": b_price, "paid": False, "method": "", "final": 0,
                })
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
                st.success(u("bookings_saved"))
                st.rerun()
        else:
            st.info(u("no_bookings"))
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
            "view", [u("sty_view_sched"), u("sty_view_perf")],
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

                a1, a2 = st.columns(2)
                with a1:
                    disc_pct = st.number_input(u("disc_label"), 0, 100, 0, 5, key="disc_pct")
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

                st.markdown(f"""
                <div class="checkout-box" style="margin:0.8rem 0;">
                  <div class="checkout-customer">{sel_bk['name']}</div>
                  <div class="checkout-svc">{sel_bk.get('stylist','')} · {sel_bk['service']} · {sel_bk['time']}</div>
                  {adj_note}
                  <div class="checkout-price">RM {final:.2f}</div>
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
                            break
                    st.success(u("pay_success").format(final, chosen_display))
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Walk-in ────────────────────────────────────────────────────────
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">{u("walkin_title")}</p>', unsafe_allow_html=True)

            wi_name = st.text_input(u("client_name"), placeholder=u("name_ph"), key="wi_name")
            wi_svc  = st.text_input(u("service"), placeholder=u("wi_svc_ph"), key="wi_svc")
            wi_amt  = st.number_input(u("wi_amt_label"), 0.0, 99999.0, 50.0, 10.0, key="wi_amt")

            st.markdown(f"""
            <div class="checkout-box" style="margin:0.8rem 0;">
              <div class="checkout-customer">{wi_name or "—"}</div>
              <div class="checkout-svc">{wi_svc or "—"}</div>
              <div class="checkout-price">RM {wi_amt:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"<p style='color:#ccb97a;font-size:0.82rem;letter-spacing:1px;'>"
                        f"{u('pay_method')}</p>", unsafe_allow_html=True)
            wi_key, wi_display = method_radio("pay_method_walkin")

            if st.button(u("wi_confirm"), key="confirm_walkin"):
                if not wi_name.strip():
                    st.warning(u("name_warn"))
                else:
                    st.session_state.walkins.append({
                        "name": wi_name.strip(), "service": wi_svc or "—",
                        "date": today_str, "final": wi_amt, "method": wi_key,
                    })
                    st.success(u("pay_success").format(wi_amt, wi_display))
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── History ───────────────────────────────────────────────────────
        history = [
            {"tag":"📅","name":b["name"],"svc":b.get("service",""),
             "time":b.get("time",""),"stylist":b.get("stylist",""),
             "final":b.get("final",b.get("price",0)),"method":b.get("method","Cash")}
            for b in paid_bk
        ] + [
            {"tag":"🚶","name":w["name"],"svc":w.get("service",""),
             "time":"","stylist":"",
             "final":w.get("final",0),"method":w.get("method","Cash")}
            for w in walkins_today
        ]
        if history:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title" style="font-size:0.95rem;">'
                        f'{u("history_title")}</p>', unsafe_allow_html=True)
            for h in history:
                m  = h["method"]
                ic = PAY_METHODS.get(m,("","💰","#888"))[1]
                cl = PAY_METHODS.get(m,("","💰","#888"))[2]
                sub = " · ".join(filter(None, [h["stylist"], h["svc"], h["time"]]))
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
            st.markdown('</div>', unsafe_allow_html=True)

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
            st.success(u("inv_saved"))
            st.rerun()

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

    # Stylist
    sty_rows = []
    for sty in sorted({b.get("stylist","") for b in paid_list} - {"","—"}):
        items = [b for b in paid_list if b.get("stylist")==sty]
        rev = sum(b.get("final",b.get("price",0)) for b in items)
        cnt = len(items)
        sty_rows.append({u("col_s_stylist"):sty, u("col_s_count"):cnt,
                         u("col_s_rev"):round(rev,2), u("col_s_avg"):round(rev/cnt,2) if cnt else 0})
    df_sty = pd.DataFrame(sty_rows) if sty_rows else pd.DataFrame()

    # Service
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

    # Method
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


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — SETTLEMENT & EXCEL EXPORT
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown(f'<p class="card-title" style="margin-bottom:1rem;">{u("settle_title")}</p>',
                unsafe_allow_html=True)

    # Mode toggle
    settle_mode = st.radio(
        "settle_mode", [u("settle_mode_day"), u("settle_mode_mth")],
        horizontal=True, key="settle_mode_radio", label_visibility="collapsed",
    )
    is_monthly = (settle_mode == u("settle_mode_mth"))
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # DAILY MODE
    # ════════════════════════════════════════════════════════════════════════
    if not is_monthly:
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

