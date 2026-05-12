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
        db_create_session, db_get_session, db_delete_session,
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
  /* ── Premium system shell: layered depth ───────────────────────────────── */
  html {
    font-family:'Raleway',sans-serif;
    color:#f0ece0;
    background-color:#060608 !important;
  }
  body { background:#060608 !important; }
  html, body, [class*="css"] {
    font-family:'Raleway',sans-serif;
    color:#f0ece0;
  }
  .stApp {
    background-color:#060608;
    background-image:
      radial-gradient(ellipse 100% 80% at 50% -15%, rgba(201,168,76,0.14), transparent 55%),
      radial-gradient(ellipse 70% 50% at 110% 5%, rgba(201,168,76,0.06), transparent 50%),
      radial-gradient(ellipse 70% 50% at -10% 95%, rgba(245,225,154,0.05), transparent 50%),
      linear-gradient(168deg,
        #0c0c11 0%,
        #08080c 38%,
        #0a0910 72%,
        #060607 100%);
    background-attachment: fixed;
  }
  section[data-testid="stMain"], section.main {
    background-image:
      repeating-linear-gradient(90deg, transparent 0px, transparent 63px,
        rgba(201,168,76,0.028) 63px, rgba(201,168,76,0.028) 64px),
      repeating-linear-gradient(0deg, transparent 0px, transparent 63px,
        rgba(201,168,76,0.028) 63px, rgba(201,168,76,0.028) 64px),
      radial-gradient(ellipse 120% 100% at 50% 0%, rgba(0,0,0,0), rgba(0,0,0,0.25) 100%);
    background-attachment: fixed;
    position: relative;
  }
  .block-container {
    padding:1.5rem 2rem 2rem !important;
    max-width:960px !important;
    width:100% !important;
    margin:0 auto !important;
  }
  #MainMenu, footer, header { visibility:hidden; }

  .hero {
    text-align:center;
    padding:2.2rem 1rem 1.2rem;
    margin-bottom:1.6rem;
    border-radius:14px;
    border:1px solid rgba(201,168,76,0.18);
    background:linear-gradient(145deg, rgba(16,14,18,0.92) 0%, rgba(8,8,12,0.55) 100%);
    box-shadow:
      inset 0 1px 0 rgba(245,225,154,0.06),
      0 4px 32px rgba(0,0,0,0.45),
      0 0 0 1px rgba(255,255,255,0.02);
    backdrop-filter:saturate(120%) blur(10px);
    -webkit-backdrop-filter:saturate(120%) blur(10px);
  }
  .hero-title { font-family:'Playfair Display',serif; font-size:2.8rem; font-weight:700; letter-spacing:8px;
    background:linear-gradient(135deg,#c9a84c,#f5e19a,#c9a84c);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; margin:0; }
  .hero-sub { font-size:0.78rem; letter-spacing:4px; color:#888; margin-top:0.3rem; text-transform:uppercase; }

  .stTabs [data-baseweb="tab-list"] { gap:4px;
    background:rgba(14,13,17,0.85); border-radius:10px; padding:6px;
    border:1px solid rgba(201,168,76,0.22);
    box-shadow:inset 0 1px 0 rgba(255,255,255,0.04), 0 8px 24px rgba(0,0,0,0.35);
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
  }
  .stTabs [data-baseweb="tab"] { font-family:'Raleway',sans-serif; font-weight:600; letter-spacing:2px; font-size:0.76rem;
    text-transform:uppercase; color:#888 !important; background:transparent; border:none; border-radius:6px;
    padding:9px 18px; transition:all .25s; }
  .stTabs [aria-selected="true"] { background:linear-gradient(135deg,#c9a84c,#a07830) !important; color:#0a0a0a !important; }
  .stTabs [data-baseweb="tab-highlight"] { background:transparent !important; }
  .stTabs [data-baseweb="tab-border"] { display:none; }

  .card {
    background:linear-gradient(155deg, rgba(18,16,22,0.92) 0%, rgba(10,10,14,0.78) 100%);
    border:1px solid rgba(201,168,76,0.2);
    border-radius:13px;
    padding:1.5rem 1.8rem;
    margin-bottom:1.2rem;
    box-shadow:
      inset 0 1px 0 rgba(245,225,154,0.05),
      0 4px 28px rgba(0,0,0,0.42);
    backdrop-filter:saturate(115%) blur(8px);
    -webkit-backdrop-filter:saturate(115%) blur(8px);
  }
  .card-title { font-family:'Playfair Display',serif; font-size:1.15rem; color:#c9a84c; margin-bottom:0.8rem; letter-spacing:1px; }

  .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div,
  .stDateInput>div>div>input, .stNumberInput>div>div>input {
    background-color:rgba(16,15,18,0.92) !important; border:1px solid rgba(201,168,76,0.35) !important;
    border-radius:8px !important; color:#f0ece0 !important; font-family:'Raleway',sans-serif !important;
    backdrop-filter:saturate(110%) blur(4px); -webkit-backdrop-filter:saturate(110%) blur(4px);
  }
  .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
    border-color:#c9a84c !important; box-shadow:0 0 0 2px #c9a84c22 !important; }
  label, .stMarkdown p { color:#ccb97a !important; font-size:0.85rem; letter-spacing:1px; }

  .stButton>button { background:linear-gradient(135deg,#c9a84c,#a07830); color:#0a0a0a;
    font-family:'Raleway',sans-serif; font-weight:700; font-size:0.82rem; letter-spacing:2px;
    text-transform:uppercase; border:none; border-radius:8px; padding:0.65rem 2rem;
    transition:all .25s; width:100%; white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; }
  .stButton>button:hover { background:linear-gradient(135deg,#f5e19a,#c9a84c); transform:translateY(-1px);
    box-shadow:0 4px 20px #c9a84c44; }

  .alert-warn { background:#2b1a0d; border-left:4px solid #e67e22; border-radius:8px;
    padding:0.9rem 1.2rem; margin-bottom:1rem; color:#f5c88a; }
  .alert-safe { background:#0d2b1a; border-left:4px solid #2ecc71; border-radius:8px;
    padding:0.9rem 1.2rem; margin-bottom:1rem; color:#a8f5c8; }

  /* Stat boxes */
  .stat-box {
    background:linear-gradient(160deg, rgba(16,14,18,0.9) 0%, rgba(8,9,12,0.75) 100%);
    border:1px solid rgba(201,168,76,0.18);
    border-radius:12px;
    padding:1rem 1.2rem; text-align:center;
    box-shadow:inset 0 1px 0 rgba(255,255,255,0.04), 0 6px 20px rgba(0,0,0,0.35);
    backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
  }
  .stat-val { font-family:'Playfair Display',serif; font-size:1.6rem; color:#c9a84c; font-weight:700; }
  .stat-lbl { font-size:0.68rem; letter-spacing:2px; color:#666; text-transform:uppercase; margin-top:2px; }

  /* Checkout */
  .checkout-box { background:linear-gradient(145deg, rgba(26,21,14,0.95), rgba(8,10,14,0.88));
    border:1px solid rgba(201,168,76,0.28); border-radius:14px; padding:1.4rem 1.6rem;
    box-shadow:0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(245,225,154,0.06); }
  .checkout-price { font-family:'Playfair Display',serif; font-size:2.8rem; color:#c9a84c;
    font-weight:700; text-align:center; margin:0.5rem 0; }
  .checkout-customer { font-size:1.05rem; color:#f0ece0; text-align:center; letter-spacing:2px; }
  .checkout-svc { font-size:0.78rem; color:#888; text-align:center; margin-top:2px; letter-spacing:1px; }

  /* Stylist schedule card */
  .sched-card {
    background:linear-gradient(160deg, rgba(16,14,18,0.9) 0%, rgba(8,9,13,0.82) 100%);
    border:1px solid rgba(201,168,76,0.18); border-radius:12px;
    padding:1.2rem 1.4rem; margin-bottom:0.8rem;
    box-shadow:0 4px 20px rgba(0,0,0,0.35); }
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
  .inv-card {
    background:linear-gradient(175deg, rgba(16,15,18,0.92) 0%, rgba(8,9,11,0.8) 100%);
    border:1px solid rgba(201,168,76,0.16); border-radius:12px; padding:1.1rem;
    text-align:center; transition:border-color .2s, transform .2s, box-shadow .2s;
    margin-bottom:4px;
    box-shadow:0 4px 18px rgba(0,0,0,0.32); }
  .inv-card:hover { border-color:rgba(201,168,76,0.45); transform:translateY(-2px);
    box-shadow:0 8px 26px rgba(0,0,0,0.45); }
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
    .stButton>button { padding:0.85rem 0.5rem !important; font-size:0.75rem !important;
      min-height:48px !important; white-space:nowrap !important;
      letter-spacing:1px !important; overflow:hidden !important;
      text-overflow:ellipsis !important; }

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
# Session key `lang=="zh"` is Simplified Chinese (简体中文).
if "lang" not in st.session_state:
    st.session_state.lang = "zh"

SERVICES = {
    "zh": {"剪发": 50, "染发": 180, "头皮护理": 120, "烫发": 250, "角蛋白护理": 350, "头皮SPA": 100},
    "en": {"Haircut": 50, "Hair Coloring": 180, "Scalp Treatment": 120,
           "Perm": 250, "Keratin Treatment": 350, "Scalp SPA": 100},
    "ms": {"Gunting Rambut": 50, "Warna Rambut": 180, "Rawatan Kulit Kepala": 120,
           "Kerinting": 250, "Rawatan Keratin": 350, "Spa Kulit Kepala": 100},
}
# Canonical service names (Simplified CN <-> EN; legacy Trad. mapped in _canonical_svc)
SVC_ZH_EN = {"剪发":"Haircut","染发":"Hair Coloring","头皮护理":"Scalp Treatment",
              "烫发":"Perm","角蛋白护理":"Keratin Treatment","头皮SPA":"Scalp SPA"}
SVC_EN_ZH = {v: k for k, v in SVC_ZH_EN.items()}
SVC_MS_ZH = {"Gunting Rambut":"剪发","Warna Rambut":"染发","Rawatan Kulit Kepala":"头皮护理",
             "Kerinting":"烫发","Rawatan Keratin":"角蛋白护理","Spa Kulit Kepala":"头皮SPA"}
SVC_LEGACY_TRADITIONAL_TO_SC = {
    "剪髮":"剪发","染髮":"染发","頭皮護理":"头皮护理","燙髮":"烫发","角蛋白護理":"角蛋白护理","頭皮SPA":"头皮SPA",
}
SVC_ALL_ZH = list(SVC_ZH_EN.keys())  # canonical service name list

def _canonical_svc(svc: str) -> str:
    """Normalise a service name to Simplified-CN canonical form (maps legacy Trad. spellings)."""
    if svc in SVC_ZH_EN:
        return svc
    if svc in SVC_EN_ZH:
        return SVC_EN_ZH[svc]
    if svc in SVC_MS_ZH:
        return SVC_MS_ZH[svc]
    return SVC_LEGACY_TRADITIONAL_TO_SC.get(svc, svc)
CATS  = {"zh": ["造型品","定型喷雾","染发剂","护发品","漂发","头皮护理"],
         "en": ["Styling","Setting Spray","Hair Color","Hair Care","Bleach","Scalp Care"],
         "ms": ["Penggayaan","Semburan Set","Pewarna Rambut","Penjagaan Rambut","Bleach","Rawatan Kulit Kepala"]}
UNITS = {"zh": ["瓶","管","盒","罐","组"], "en": ["bottle","tube","box","can","set"],
         "ms": ["botol","tiub","kotak","tin","set"]}

PAY_METHODS = {
    "Cash":        ("Cash 现金",    "💵", "#2ecc71"),
    "Visa/Card":   ("Visa / Card",  "💳", "#3498db"),
    "Touch 'n Go": ("Touch 'n Go", "📱", "#e74c3c"),
    "DuitNow QR":  ("DuitNow QR",  "📲", "#9b59b6"),
}

# Avatar colours cycling for stylists
STYLIST_COLORS = ["#c9a84c","#3498db","#e74c3c","#2ecc71","#9b59b6","#e67e22","#1abc9c","#e91e8c"]

UI = {
    "zh": {
        "subtitle":      "发廊智能管理系统 · Malaysia",
        "lang_btn":      "🌐 English",
        "tab1":          "  ✂  预约管理  ",
        "tab2":          "  💇  发型师  ",
        "tab3":          "  💳  收费  ",
        "tab4":          "  📦  库存  ",
        "tab5":          "  📊  结算  ",
        # Booking
        "new_booking":   "＋ 新增预约",
        "client_name":   "客户姓名",
        "name_ph":       "请输入全名",
        "book_date":     "预约日期",
        "book_time":     "预约时间",
        "stylist":       "发型师",
        "service":       "服务项目",
        "note":          "备注（选填）",
        "note_ph":       "例如：过敏史、头发状况…",
        "confirm_btn":   "确认预约 →",
        "name_warn":     "请输入客户姓名",
        "online_pending": "待确认网上预约",
        "any_stylist":    "不指定发型师",
        "cancel":         "拒绝",
        "book_list":     "📅 预约名单",
        "save_bookings": "保存更改",
        "bookings_saved":"✦ 预约已更新",
        "no_bookings":   "尚无预约记录",
        "col_name":      "姓名",
        "col_date":      "日期",
        "col_time":      "时间",
        "col_stylist":   "发型师",
        "col_service":   "服务",
        "col_note":      "备注",
        # Stylist
        "sty_title":     "💇 发型师管理",
        "sty_roster":    "发型师名单",
        "sty_add":       "新增发型师",
        "sty_name_lbl":  "名称",
        "sty_name_ph":   "例如：Kim",
        "sty_add_btn":   "新增 →",
        "sty_name_warn": "请输入发型师名称",
        "sty_added":     "✦ 已新增 **{}**",
        "sty_removed":   "✦ 已移除 **{}**",
        "sty_schedule":  "今日排班",
        "sty_filter":    "筛选发型师",
        "sty_all":       "全部",
        "sty_no_bk":     "今日无预约",
        "sty_clients":   "位客户",
        "sty_remove":    "移除",
        "sty_view_sched":"📅 排班",
        "sty_view_perf": "📊 业绩",
        "sty_view_comm": "💰 提成设置",
        "perf_title":    "📊 业绩排行",
        "perf_today_rev":"今日业绩",
        "perf_total_rev":"累计业绩",
        "perf_clients":  "接待人次",
        "perf_top_svc":  "最多服务",
        "perf_avg":      "平均客单价",
        "perf_rank":     "排行",
        "perf_no_data":  "尚无业绩记录（未有结账数据）",
        "comm_title":    "💰 提成比例设置",
        "comm_desc":     "为每位发型师的每种服务设定提成百分比（%）",
        "comm_save":     "保存提成设置",
        "comm_saved":    "✦ 提成设置已保存",
        "comm_svc":      "服务",
        "comm_rate":     "比例 (%)",
        "comm_no_sty":   "请先在左侧新增发型师",
        "comm_report_title": "💰 提成报表",
        "comm_stylist":  "发型师",
        "comm_service":  "服务",
        "comm_revenue":  "业绩收入",
        "comm_rate_col": "提成 %",
        "comm_amount":   "提成金额",
        "comm_subtotal": "小计",
        "comm_grand":    "合计",
        "comm_period":   "报表期间",
        "comm_export":   "导出提成报表 (Excel)",
        "comm_no_data":  "所选期间没有已结账记录",
        # Payment
        "pay_title":     "💳 今日收费",
        "stat_paid":     "已收款",
        "stat_pending":  "待收款",
        "stat_total":    "今日总计",
        "stat_count":    "今日客数",
        "pending_list":  "⏳ 待付款",
        "no_pending":    "✦ 今日所有预约已结清",
        "checkout_title":"结账",
        "select_booking":"选择预约",
        "pay_method":    "付款方式",
        "confirm_pay":   "确认收款 →",
        "pay_success":   "✦ 已收款 RM {:.2f}（{}）",
        "history_title": "📋 今日收款记录",
        "breakdown_title":"付款方式分布",
        "disc_label":    "折扣 Discount (%)",
        "extra_label":   "额外收费 Extra (RM)",
        "walkin_title":  "现场客收费",
        "wi_svc_ph":     "剪发 / 染发 / 护理…",
        "wi_amt_label":  "金额 (RM)",
        "wi_confirm":    "收款 →",
        "mode_booked":   "预约客户",
        "mode_walkin":   "现场客 Walk-in",
        # Inventory
        "inv_title":     "📦 产品库存",
        "add_product":   "＋ 新增产品",
        "p_name":        "产品名称",
        "p_name_ph":     "例如：OSiS+ Dust It",
        "p_cat":         "分类",
        "p_qty":         "数量",
        "p_max":         "最大库存",
        "p_unit":        "单位",
        "add_btn":       "新增产品 →",
        "name_req":      "请输入产品名称",
        "add_success":   "✦ 已新增 **{}**",
        "low_warn":      "⚠ 库存不足警告：{}",
        "filter":        "分类筛选",
        "search":        "搜索产品",
        "search_ph":     "输入产品名称…",
        "all_cat":       "全部",
        "edit_section":  "✏  编辑 / 删除库存",
        "save_inv":      "保存库存更改",
        "inv_saved":     "✦ 库存已更新",
        "remain":        "剩余",
        "col_pname":     "产品名称",
        "col_pcat":      "分类",
        "col_pqty":      "数量",
        "col_pmax":      "最大库存",
        "col_punit":     "单位",
        # Settlement
        "settle_title":   "📊 结算报告",
        "settle_mode_day":  "📅 每日结算",
        "settle_mode_mth":  "📆 每月结算",
        "settle_mode_comm": "💰 提成报表",
        "settle_date":    "选择结算日期",
        "settle_month":   "选择月份",
        "settle_mth_title":"📆 每月结算报告",
        "settle_clients": "总客数",
        "settle_daily_bk":"每日收款明细",
        "col_s_date":     "日期",
        "col_s_clients":  "客数",
        "settle_total":   "结算总额",
        "settle_paid":    "已收款",
        "settle_pending": "待收款",
        "settle_walkin":  "现场客",
        "settle_detail":  "收款明细",
        "settle_sty":     "发型师业绩",
        "settle_svc":     "服务统计",
        "settle_method":  "付款方式统计",
        "settle_no_data": "所选日期无收款记录",
        "settle_export":  "📥 导出 Excel",
        "settle_exporting":"正在生成…",
        "col_s_name":     "客户姓名",
        "col_s_stylist":  "发型师",
        "col_s_svc":      "服务",
        "col_s_method":   "付款方式",
        "col_s_amt":      "金额 (RM)",
        "col_s_type":     "类型",
        "col_s_count":    "人次",
        "col_s_rev":      "业绩 (RM)",
        "col_s_avg":      "平均 (RM)",
        # Members
        "tab6":           "  👥  会员  ",
        "mem_title":      "👥 会员管理",
        "mem_add":        "＋ 新增会员",
        "mem_name":       "姓名",
        "mem_name_ph":    "例如：Siti Aminah",
        "mem_phone":      "电话号码",
        "mem_phone_ph":   "例如：012-3456789",
        "mem_bday":       "生日（选填）",
        "mem_notes":      "备注（头发状况、过敏等）",
        "mem_notes_ph":   "例如：对氨水过敏，头发细软…",
        "mem_add_btn":    "新增会员 →",
        "mem_name_warn":  "请输入会员姓名",
        "mem_added":      "✦ 已新增会员 **{}**",
        "mem_search":     "搜索会员",
        "mem_search_ph":  "输入姓名或电话…",
        "mem_no_result":  "找不到符合的会员",
        "mem_no_members": "尚无会员资料",
        "mem_select":     "点选会员查看详情",
        "mem_detail":     "会员详情",
        "mem_tier":       "等级",
        "mem_points":     "积分",
        "mem_spent":      "累计消费 (RM)",
        "mem_visits":     "到访次数",
        "mem_joined":     "加入日期",
        "mem_edit_notes": "更新备注",
        "mem_save_notes": "保存备注",
        "mem_notes_saved":"✦ 备注已保存",
        "mem_delete":     "删除会员",
        "mem_deleted":    "✦ 已删除会员 **{}**",
        "mem_history":    "消费记录",
        "mem_no_history": "尚无消费记录",
        "mem_stats":      "会员总览",
        "mem_total":      "总会员数",
        "mem_vip_count":  "VIP 会员",
        "mem_pts_issued": "已发积分",
        "mem_tier_up":    "✦ {} 已升级至 {}！",
        "mem_disc_hint":  "会员折扣 {}%",
        "mem_lookup":     "会员查询（选填）",
        "mem_pts_added":  "已为 {} 累加 {} 积分",
        # Member DB enhancements
        "bk_phone":       "客户电话",
        "bk_phone_ph":    "例如：012-3456789",
        "mem_on_file":    "✓ 已建档  · {}  {}",
        "mem_new_client": "✦ 新客户 — 可在【会员】页建档",
        "mem_auto_match": "🔗 自动匹配：{} {}",
        "mem_bk_section": "📅 预约记录",
        "mem_upcoming":   "即将到来",
        "mem_past_bk":    "过去记录",
        "mem_no_upcoming":"暂无即将到来的预约",
        "mem_no_bk":      "尚无预约记录",
        "wi_phone":       "客户电话（选填）",
        "wi_quick_mem":   "＋ 将此客户加入会员",
        "wi_mem_created": "✦ 已建立会员档案：**{}**",
        # Receipt
        "rcpt_btn":       "🧾 收据",
        "rcpt_title":     "收据",
        "rcpt_print":     "🖨️ 打印收据",
        "rcpt_email":     "📧 Email 收据",
        "rcpt_email_to":  "收件人 Email",
        "rcpt_email_ph":  "例如：client@email.com",
        "rcpt_send":      "发送 →",
        "rcpt_sent":      "✦ 邮件已打开，请在邮件 App 确认发送",
        "rcpt_close":     "关闭",
        "rcpt_service":   "服务",
        "rcpt_stylist":   "发型师",
        "rcpt_subtotal":  "小计",
        "rcpt_discount":  "折扣",
        "rcpt_total":     "总计",
        "rcpt_method":    "付款方式",
        "rcpt_member":    "会员",
        "rcpt_pts":       "本次积分",
        "rcpt_thanks":    "感谢您的光临，期待再次为您服务！",
        "rcpt_no_sel":    "请先从收款记录中选择一笔收据",
    },
    "en": {
        "subtitle":      "Salon Management System · Malaysia",
        "lang_btn":      "🌐 简体",
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
        # Member DB enhancements
        "bk_phone":       "Client Phone",
        "bk_phone_ph":    "e.g. 012-3456789",
        "mem_on_file":    "✓ On file  · {}  {}",
        "mem_new_client": "✦ New client — add profile in Members tab",
        "mem_auto_match": "🔗 Auto-matched: {} {}",
        "mem_bk_section": "📅 Bookings",
        "mem_upcoming":   "Upcoming",
        "mem_past_bk":    "Past",
        "mem_no_upcoming":"No upcoming bookings",
        "mem_no_bk":      "No bookings on record",
        "wi_phone":       "Client Phone (optional)",
        "wi_quick_mem":   "＋ Add to Members",
        "wi_mem_created": "✦ Member profile created: **{}**",
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
    "ms": {
        "subtitle":      "Sistem Pengurusan Salun · Malaysia",
        "lang_btn":      "🌐 简体",
        "tab1":          "  ✂  Tempahan  ",
        "tab2":          "  💇  Jurugaya  ",
        "tab3":          "  💳  Bayaran  ",
        "tab4":          "  📦  Inventori  ",
        "tab5":          "  📊  Laporan  ",
        "new_booking":   "＋ Tempahan Baru",
        "client_name":   "Nama Pelanggan",
        "name_ph":       "Masukkan nama penuh",
        "book_date":     "Tarikh",
        "book_time":     "Masa",
        "stylist":       "Jurugaya",
        "service":       "Perkhidmatan",
        "note":          "Nota (pilihan)",
        "note_ph":       "Cth: Alahan, keadaan rambut…",
        "confirm_btn":   "Sahkan Tempahan →",
        "name_warn":     "Sila masukkan nama pelanggan",
        "online_pending":"Permintaan Tempahan Dalam Talian",
        "any_stylist":   "Tiada keutamaan",
        "cancel":        "Tolak",
        "book_list":     "📅 Senarai Tempahan",
        "save_bookings": "Simpan Perubahan",
        "bookings_saved":"✦ Tempahan dikemaskini",
        "no_bookings":   "Tiada rekod tempahan",
        "col_name":      "Nama",
        "col_date":      "Tarikh",
        "col_time":      "Masa",
        "col_stylist":   "Jurugaya",
        "col_service":   "Perkhidmatan",
        "col_note":      "Nota",
        "sty_title":     "💇 Pengurusan Jurugaya",
        "sty_roster":    "Senarai Jurugaya",
        "sty_add":       "Tambah Jurugaya",
        "sty_name_lbl":  "Nama",
        "sty_name_ph":   "Cth: Kim",
        "sty_add_btn":   "Tambah →",
        "sty_name_warn": "Sila masukkan nama jurugaya",
        "sty_added":     "✦ **{}** ditambah",
        "sty_removed":   "✦ **{}** dibuang",
        "sty_schedule":  "Jadual Hari Ini",
        "sty_filter":    "Tapis Jurugaya",
        "sty_all":       "Semua",
        "sty_no_bk":     "Tiada tempahan hari ini",
        "sty_clients":   "pelanggan",
        "sty_remove":    "Buang",
        "sty_view_sched":"📅 Jadual",
        "sty_view_perf": "📊 Prestasi",
        "sty_view_comm": "💰 Kadar Komisen",
        "perf_title":    "📊 Kedudukan Prestasi",
        "perf_today_rev":"Hasil Hari Ini",
        "perf_total_rev":"Jumlah Hasil",
        "perf_clients":  "Bilangan Pelanggan",
        "perf_top_svc":  "Perkhidmatan Teratas",
        "perf_avg":      "Purata / Pelanggan",
        "perf_rank":     "Kedudukan",
        "perf_no_data":  "Tiada data prestasi lagi",
        "comm_title":    "💰 Tetapan Kadar Komisen",
        "comm_desc":     "Tetapkan peratusan komisen (%) untuk setiap jurugaya bagi setiap perkhidmatan",
        "comm_save":     "Simpan Kadar Komisen",
        "comm_saved":    "✦ Kadar komisen disimpan",
        "comm_svc":      "Perkhidmatan",
        "comm_rate":     "Kadar (%)",
        "comm_no_sty":   "Sila tambah jurugaya dahulu",
        "comm_report_title": "💰 Laporan Komisen",
        "comm_stylist":  "Jurugaya",
        "comm_service":  "Perkhidmatan",
        "comm_revenue":  "Hasil",
        "comm_rate_col": "Komisen %",
        "comm_amount":   "Jumlah Komisen",
        "comm_subtotal": "Subtotal",
        "comm_grand":    "Jumlah Keseluruhan",
        "comm_period":   "Tempoh Laporan",
        "comm_export":   "Eksport Laporan Komisen (Excel)",
        "comm_no_data":  "Tiada bayaran selesai dalam tempoh yang dipilih",
        "pay_title":     "💳 Bayaran Hari Ini",
        "stat_paid":     "Diterima",
        "stat_pending":  "Tertunggak",
        "stat_total":    "Jumlah Hari Ini",
        "stat_count":    "Pelanggan Hari Ini",
        "pending_list":  "⏳ Belum Bayar",
        "no_pending":    "✦ Semua bayaran telah diselesaikan",
        "checkout_title":"Daftar Keluar",
        "select_booking":"Pilih Tempahan",
        "pay_method":    "Kaedah Bayaran",
        "confirm_pay":   "Sahkan Bayaran →",
        "pay_success":   "✦ Diterima RM {:.2f} ({})",
        "history_title": "📋 Rekod Bayaran Hari Ini",
        "breakdown_title":"Pecahan Kaedah Bayaran",
        "disc_label":    "Diskaun (%)",
        "extra_label":   "Caj Tambahan (RM)",
        "walkin_title":  "Bayaran Terus (Walk-in)",
        "wi_svc_ph":     "Gunting / Warna / Rawatan…",
        "wi_amt_label":  "Jumlah (RM)",
        "wi_confirm":    "Terima →",
        "mode_booked":   "Pelanggan Bertempahan",
        "mode_walkin":   "Terus Masuk",
        "inv_title":     "📦 Inventori Produk",
        "add_product":   "＋ Tambah Produk",
        "p_name":        "Nama Produk",
        "p_name_ph":     "Cth: OSiS+ Dust It",
        "p_cat":         "Kategori",
        "p_qty":         "Kuantiti",
        "p_max":         "Stok Maksimum",
        "p_unit":        "Unit",
        "add_btn":       "Tambah Produk →",
        "name_req":      "Sila masukkan nama produk",
        "add_success":   "✦ **{}** ditambah",
        "low_warn":      "⚠ Stok Rendah: {}",
        "filter":        "Tapis",
        "search":        "Cari",
        "search_ph":     "Masukkan nama produk…",
        "all_cat":       "Semua",
        "edit_section":  "✏  Edit / Padam Inventori",
        "save_inv":      "Simpan Perubahan",
        "inv_saved":     "✦ Inventori dikemaskini",
        "remain":        "baki",
        "col_pname":     "Produk",
        "col_pcat":      "Kategori",
        "col_pqty":      "Kuantiti",
        "col_pmax":      "Maks",
        "col_punit":     "Unit",
        "settle_title":   "📊 Laporan Penyelesaian",
        "settle_mode_day":  "📅 Harian",
        "settle_mode_mth":  "📆 Bulanan",
        "settle_mode_comm": "💰 Komisen",
        "settle_date":    "Pilih Tarikh",
        "settle_month":   "Pilih Bulan",
        "settle_mth_title":"📆 Laporan Bulanan",
        "settle_clients": "Jumlah Pelanggan",
        "settle_daily_bk":"Terperinci Harian",
        "col_s_date":     "Tarikh",
        "col_s_clients":  "Pelanggan",
        "settle_total":   "Jumlah Hasil",
        "settle_paid":    "Diterima",
        "settle_pending": "Tertunggak",
        "settle_walkin":  "Terus Masuk",
        "settle_detail":  "Terperinci Bayaran",
        "settle_sty":     "Prestasi Jurugaya",
        "settle_svc":     "Ringkasan Perkhidmatan",
        "settle_method":  "Kaedah Bayaran",
        "settle_no_data": "Tiada rekod bayaran pada tarikh ini",
        "settle_export":  "📥 Eksport Excel",
        "settle_exporting":"Sedang menjana…",
        "col_s_name":     "Pelanggan",
        "col_s_stylist":  "Jurugaya",
        "col_s_svc":      "Perkhidmatan",
        "col_s_method":   "Kaedah",
        "col_s_amt":      "Jumlah (RM)",
        "col_s_type":     "Jenis",
        "col_s_count":    "Bilangan",
        "col_s_rev":      "Hasil (RM)",
        "col_s_avg":      "Purata (RM)",
        "tab6":           "  👥  Ahli  ",
        "mem_title":      "👥 Pengurusan Ahli",
        "mem_add":        "＋ Tambah Ahli",
        "mem_name":       "Nama",
        "mem_name_ph":    "Cth: Siti Aminah",
        "mem_phone":      "Nombor Telefon",
        "mem_phone_ph":   "Cth: 012-3456789",
        "mem_bday":       "Tarikh Lahir (pilihan)",
        "mem_notes":      "Nota (keadaan rambut, alahan, dll.)",
        "mem_notes_ph":   "Cth: Alahan ammonia, rambut halus…",
        "mem_add_btn":    "Tambah Ahli →",
        "mem_name_warn":  "Sila masukkan nama ahli",
        "mem_added":      "✦ Ahli **{}** ditambah",
        "mem_search":     "Cari Ahli",
        "mem_search_ph":  "Masukkan nama atau telefon…",
        "mem_no_result":  "Tiada ahli yang sepadan",
        "mem_no_members": "Tiada rekod ahli lagi",
        "mem_select":     "Pilih ahli untuk melihat butiran",
        "mem_detail":     "Profil Ahli",
        "mem_tier":       "Tahap",
        "mem_points":     "Mata",
        "mem_spent":      "Jumlah Perbelanjaan (RM)",
        "mem_visits":     "Bilangan Kunjungan",
        "mem_joined":     "Ahli Sejak",
        "mem_edit_notes": "Kemaskini Nota",
        "mem_save_notes": "Simpan Nota",
        "mem_notes_saved":"✦ Nota disimpan",
        "mem_delete":     "Padam Ahli",
        "mem_deleted":    "✦ Ahli **{}** dipadam",
        "mem_history":    "Sejarah Perbelanjaan",
        "mem_no_history": "Tiada sejarah perbelanjaan lagi",
        "mem_stats":      "Ringkasan Ahli",
        "mem_total":      "Jumlah Ahli",
        "mem_vip_count":  "Ahli VIP",
        "mem_pts_issued": "Mata Dikeluarkan",
        "mem_tier_up":    "✦ {} dinaikkan ke {}!",
        "mem_disc_hint":  "Diskaun ahli {}%",
        "mem_lookup":     "Cari Ahli (pilihan)",
        "mem_pts_added":  "Tambah {} mata untuk {}",
        "bk_phone":       "Telefon Pelanggan",
        "bk_phone_ph":    "Cth: 012-3456789",
        "mem_on_file":    "✓ Ada rekod  · {}  {}",
        "mem_new_client": "✦ Pelanggan baru — boleh tambah di tab Ahli",
        "mem_auto_match": "🔗 Padanan automatik: {} {}",
        "mem_bk_section": "📅 Rekod Tempahan",
        "mem_upcoming":   "Akan Datang",
        "mem_past_bk":    "Lepas",
        "mem_no_upcoming":"Tiada tempahan akan datang",
        "mem_no_bk":      "Tiada rekod tempahan",
        "wi_phone":       "Telefon Pelanggan (pilihan)",
        "wi_quick_mem":   "＋ Tambah ke Ahli",
        "wi_mem_created": "✦ Profil ahli dicipta: **{}**",
        "rcpt_btn":       "🧾 Resit",
        "rcpt_title":     "Resit",
        "rcpt_print":     "🖨️ Cetak Resit",
        "rcpt_email":     "📧 E-mel Resit",
        "rcpt_email_to":  "Penerima E-mel",
        "rcpt_email_ph":  "Cth: pelanggan@email.com",
        "rcpt_send":      "Hantar →",
        "rcpt_sent":      "✦ Aplikasi e-mel dibuka — sahkan untuk hantar",
        "rcpt_close":     "Tutup",
        "rcpt_service":   "Perkhidmatan",
        "rcpt_stylist":   "Jurugaya",
        "rcpt_subtotal":  "Subtotal",
        "rcpt_discount":  "Diskaun",
        "rcpt_total":     "Jumlah",
        "rcpt_method":    "Bayaran",
        "rcpt_member":    "Ahli",
        "rcpt_pts":       "Mata Diperoleh",
        "rcpt_thanks":    "Terima kasih kerana melawat — kami berharap dapat melayani anda lagi!",
        "rcpt_no_sel":    "Pilih resit daripada rekod bayaran",
    },
}

def u(key):
    lang = st.session_state.lang
    if key in UI[lang]:
        return UI[lang][key]
    # Fallback: ms → en, then zh → en
    if lang == "ms" and key in UI["en"]:
        return UI["en"][key]
    return UI["zh"].get(key, key)

def svc_map(): return SERVICES[st.session_state.lang]
def bar_color(r): return "#2ecc71" if r > 0.6 else ("#e67e22" if r > 0.3 else "#e74c3c")

def _t(zh: str, en: str, ms: str = None) -> str:
    """Inline trilingual string helper."""
    lang = st.session_state.lang
    if lang == "zh":  return zh
    if lang == "ms":  return ms if ms is not None else en
    return en

# ── Member tier system ────────────────────────────────────────────────────────
TIERS = [
    {"key": "普通",  "en": "Regular", "ms": "Biasa",  "min_pts": 0,    "disc": 0,    "color": "#888888", "badge": "⚪"},
    {"key": "银卡",  "en": "Silver",  "ms": "Perak",  "min_pts": 500,  "disc": 5,    "color": "#adb5bd", "badge": "🥈"},
    {"key": "金卡",  "en": "Gold",    "ms": "Emas",   "min_pts": 1500, "disc": 10,   "color": "#c9a84c", "badge": "🥇"},
    {"key": "VIP",   "en": "VIP",     "ms": "VIP",    "min_pts": 3000, "disc": 15,   "color": "#e74c3c", "badge": "💎"},
]

def tier_for_points(pts):
    t = TIERS[0]
    for tier in TIERS:
        if pts >= tier["min_pts"]:
            t = tier
    return t

def tier_label(tier_dict):
    lang = st.session_state.lang
    if lang == "en":  return tier_dict["en"]
    if lang == "ms":  return tier_dict.get("ms", tier_dict["en"])
    return tier_dict["key"]

# ── Session token helpers (persistent login via URL ?t=TOKEN) ─────────────────
def _save_session_token(username: str):
    """Create DB session token and write it to the URL query params."""
    if not _USE_DB:
        return
    try:
        token = db_create_session(username)
        st.query_params["t"] = token
    except Exception:
        pass

def _clear_session_token():
    """Delete DB session and remove token from URL."""
    token = st.query_params.get("t", "")
    if token and _USE_DB:
        try:
            db_delete_session(token)
        except Exception:
            pass
    st.query_params.clear()

def _get_session_user() -> str:
    """Return username if URL token is valid, else empty string."""
    token = st.query_params.get("t", "")
    if not token or not _USE_DB:
        return ""
    try:
        return db_get_session(token)
    except Exception:
        return ""

# ── Branch-scoped data helpers (must be defined before auto-login uses them) ───
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
                {"name":"OSiS+ Freeze",          "category":"定型喷雾","qty":7, "max":24,"unit":"瓶"},
                {"name":"Schwarzkopf IGORA",     "category":"染发剂",  "qty":22,"max":50,"unit":"管"},
                {"name":"Fibre Clinix 蛋白护理", "category":"护发品",  "qty":5, "max":20,"unit":"瓶"},
                {"name":"BLONDME 漂发粉",        "category":"漂发",    "qty":9, "max":25,"unit":"盒"},
                {"name":"OSiS+ Session Label",   "category":"造型品",  "qty":18,"max":30,"unit":"瓶"},
                {"name":"Chroma ID 酸性染",      "category":"染发剂",  "qty":31,"max":60,"unit":"管"},
                {"name":"Scalp Clinix 头皮精华", "category":"头皮护理","qty":3, "max":15,"unit":"瓶"},
            ],
        }

def _bd():
    """Return current branch data dict."""
    _init_branch(st.session_state.cur_branch)
    return st.session_state.branch_data[st.session_state.cur_branch]

def _sync_ss():
    """Sync top-level session state aliases to current branch."""
    bd = _bd()
    st.session_state.stylists    = bd["stylists"]
    st.session_state.bookings    = bd["bookings"]
    st.session_state.walkins     = bd["walkins"]
    st.session_state.members     = bd["members"]
    st.session_state.inventory   = bd["inventory"]
    st.session_state.commissions = bd.setdefault("commissions", {})

# ── Auth session state ────────────────────────────────────────────────────────
if "logged_in"  not in st.session_state: st.session_state.logged_in  = False
if "username"   not in st.session_state: st.session_state.username   = ""
if "role"       not in st.session_state: st.session_state.role       = ""
if "user_name"  not in st.session_state: st.session_state.user_name  = ""
if "cur_branch" not in st.session_state: st.session_state.cur_branch = ""
if "accounts"   not in st.session_state: st.session_state.accounts   = dict(_DEFAULT_ACCOUNTS)
if "branches"   not in st.session_state: st.session_state.branches   = dict(_DEFAULT_BRANCHES)

# ── Auto-login from URL session token (F5-persistent) ────────────────────────
if not st.session_state.logged_in:
    _token_user = _get_session_user()
    if _token_user:
        if _USE_DB:
            try: db_load_branches_and_accounts()
            except Exception: pass
        acct = st.session_state.accounts.get(_token_user)
        if acct:
            st.session_state.logged_in = True
            st.session_state.username  = _token_user
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
            lg_user = st.text_input("👤 Username / 用户名", key="lg_user", placeholder="username")
            lg_pass = st.text_input("🔑 Password / 密码",   key="lg_pass", placeholder="password", type="password")
            if st.button("Login / 登录", key="login_btn", use_container_width=True):
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

                    _save_session_token(uname)
                    _sync_ss()
                    st.rerun()
                else:
                    st.error("❌ 账号或密码错误 / Wrong username or password")
    st.stop()

# ── Logged in — sync data aliases ────────────────────────────────────────────
_sync_ss()

# ── Subscription status check (owner + platform admin bypass; see _sub below) ──
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
        if not trial_ends:
            # No end date ⇒ treat trial as ongoing (avoid locking out DB rows missing this field).
            return {"ok": True, "plan": "trial", "days_left": 999, "ends": None}
        end = _sub_dt.date.fromisoformat(str(trial_ends))
        days_left = (end - today).days
        if days_left >= 0:
            return {"ok": True, "plan": "trial", "days_left": days_left, "ends": end}
        return {"ok": False, "plan": "expired", "days_left": 0, "ends": None}

    return {"ok": False, "plan": "expired", "days_left": 0, "ends": None}

# Bypass paywall for salon owner and platform admin (admin manages billing / infra).
_sub = _get_sub_status(st.session_state.cur_branch) if st.session_state.role not in ("owner", "admin") \
    else {"ok": True, "plan": "owner" if st.session_state.role == "owner" else "admin", "days_left": 999, "ends": None}

# ── Subscription expired page ─────────────────────────────────────────────────
if not _sub["ok"] and st.session_state.role not in ("owner", "admin"):
    stripe_link = st.session_state.get("salon_info", {}).get(
        st.session_state.cur_branch, {}).get("stripe_link", "")
    is_zh = st.session_state.lang == "zh"
    st.markdown(f"""
    <div style="max-width:480px;margin:8vh auto;background:#111;border:1px solid #e74c3c55;
      border-radius:16px;padding:2.5rem 2.8rem;text-align:center;">
      <div style="font-size:3rem;margin-bottom:1rem">🔒</div>
      <div style="font-family:'Playfair Display',serif;font-size:1.5rem;color:#e74c3c;
        letter-spacing:3px;margin-bottom:0.8rem">
        {"订阅已到期" if is_zh else "Subscription Expired"}
      </div>
      <div style="color:#888;font-size:0.88rem;line-height:1.8;margin-bottom:1.5rem">
        {"您的试用期已结束，请订阅以继续使用所有功能。" if is_zh else
         "Your trial has ended. Please subscribe to continue using all features."}
      </div>
      {'<a href="' + stripe_link + '" target="_blank" style="display:inline-block;' +
       'background:linear-gradient(135deg,#c9a84c,#a07830);color:#0a0a0a;font-weight:700;' +
       'font-size:0.9rem;letter-spacing:2px;text-transform:uppercase;padding:1rem 2.5rem;' +
       'border-radius:8px;text-decoration:none;margin-bottom:1rem">💳 ' +
       ("立即订阅" if is_zh else "Subscribe Now") + '</a>'
       if stripe_link else
       '<div style="background:#1a1a1a;border:1px solid #c9a84c33;border-radius:8px;' +
       'padding:1rem;color:#888;font-size:0.82rem">' +
       ("请联系管理员启用订阅。" if is_zh else "Please contact admin to activate your subscription.") +
       '</div>'}
      <div style="margin-top:1.5rem;color:#555;font-size:0.75rem">
        {"或联系 IQSALON 支持" if is_zh else "Or contact Signature Kim support"}
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚪 " + ("退出" if is_zh else "Logout"), key="exp_logout"):
        _clear_session_token()
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
    # Override button style for narrow header buttons
    st.markdown("""<style>
    div[data-testid="stHorizontalBlock"] .stButton>button {
        letter-spacing:0.5px !important; font-size:0.78rem !important;
        padding:0.55rem 0.6rem !important; text-transform:none !important;
    }
    </style>""", unsafe_allow_html=True)
    _lang_cycle  = {"zh": "en", "en": "ms", "ms": "zh"}
    _lang_labels = {"zh": "🌐 EN", "en": "🌐 BM", "ms": "🌐 简体"}
    _lang_label  = _lang_labels[st.session_state.lang]
    _logout_label = f"{role_icon} " + _t("退出登录", "Logout", "Log Keluar")
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button(_lang_label, key="lang_toggle"):
            st.session_state.lang = _lang_cycle[st.session_state.lang]
            st.rerun()
    with rc2:
        if st.button(_logout_label, key="logout_btn"):
            _clear_session_token()
            for k in ["logged_in","username","role","user_name","cur_branch"]:
                del st.session_state[k]
            st.rerun()

# Build subscription badge for header
_sub_badge = ""
if _sub["plan"] == "trial" and _sub["days_left"] <= 7:
    _sub_badge = f'<span style="background:#e67e22;color:#fff;font-size:0.65rem;padding:3px 10px;border-radius:20px;letter-spacing:1px;margin-left:8px">⏳ {_t("试用期还剩","Trial","Percubaan")} {_sub["days_left"]} {_t("天","days","hari")}</span>'
elif _sub["plan"] == "trial":
    _sub_badge = f'<span style="background:#2ecc71;color:#0a0a0a;font-size:0.65rem;padding:3px 10px;border-radius:20px;letter-spacing:1px;margin-left:8px">✓ {_t("试用期","Trial","Percubaan")} {_sub["days_left"]}{_t("天","d","h")}</span>'
elif _sub["plan"] == "active":
    _sub_badge = f'<span style="background:#c9a84c;color:#0a0a0a;font-size:0.65rem;padding:3px 10px;border-radius:20px;letter-spacing:1px;margin-left:8px">✦ {_t("已订阅","Subscribed","Dilanggan")}</span>'

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
        extra_lbl = "Caj Tambahan" if not is_zh else "加收费用"
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
        pts_lbl = f"Mata Ganjaran / 积分" if not is_zh else "积分"
        member_rows = f"""
      <tr class="info-row">
        <td colspan="2">{'Ahli / 会员' if not is_zh else '会员'}</td>
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
        sty_lbl = "Penata Rambut / 发型师" if not is_zh else "发型师"
        stylist_row = f"""
      <tr class="info-row">
        <td colspan="2">{sty_lbl}</td>
        <td colspan="2" style="text-align:right;">{stylist}</td>
      </tr>"""

    pay_lbl   = "Kaedah Pembayaran" if not is_zh else "付款方式"
    total_lbl = "JUMLAH / TOTAL" if not is_zh else "总计"
    sst_note  = "Harga adalah termasuk SST / Harga tidak termasuk SST (Dikecualikan)" \
                if not is_zh else "价格已含/免收 SST（服务税）"
    thanks_my = "Terima Kasih Kerana Sudi Hadir" if not is_zh else "感谢您的光临"
    thanks_en = "We look forward to serving you again!" if not is_zh else "期待再次为您服务！"

    contact_parts = []
    if salon_address: contact_parts.append(f"📍 {salon_address}")
    if salon_phone:   contact_parts.append(f"📞 {salon_phone}")
    if salon_email:   contact_parts.append(f"✉ {salon_email}")
    if salon_web:     contact_parts.append(f"🌐 {salon_web}")
    contact_line = ("".join(f"<div class='contact'>{p}</div>" for p in contact_parts)
                    if contact_parts else "")

    footer_meta_parts = []
    if salon_ssm:   footer_meta_parts.append(f"SSM No: {salon_ssm}")
    if salon_hours: footer_meta_parts.append(f"{'Waktu Operasi' if not is_zh else '营业时间'}: {salon_hours}")
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
      <div class="customer-label">{'Pelanggan / 客户' if not is_zh else '客户'}</div>
      <div class="customer-name">{name}</div>
      {'<div class="customer-time">' + ('Temujanji / 预约时间: ' if not is_zh else '预约时间: ') + time_str + '</div>' if time_str else ''}
    </div>

    <!-- ITEMS TABLE -->
    <table>
      <thead>
        <tr>
          <td class="desc">{'Perkhidmatan / 服务项目' if not is_zh else '服务项目'}</td>
          <td class="qty">Qty</td>
          <td class="price">{'Harga' if not is_zh else '单价'}</td>
          <td class="amt">{'Jumlah' if not is_zh else '金额'}</td>
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
    {'🖨️  Cetak Resit / 打印收据' if not is_zh else '🖨️  打印收据'}
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
         u("col_s_type"):    _t("预约","Booking","Tempahan")}
        for b in paid_list
    ] + [
        {u("col_s_name"):    w.get("name",""),  u("col_s_stylist"): "—",
         u("col_s_svc"):     w.get("service",""), u("col_s_method"):  w.get("method",""),
         u("col_s_amt"):     w.get("final",0),
         u("col_s_type"):    _t("现场客","Walk-in","Terus Masuk")}
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
    _tabs_labels.append("  📊  " + _t("业绩","Analytics","Analitik") + "  ")
if _can("admin"):
    _tabs_labels.append("  ⚙️  " + _t("管理后台","Admin","Pentadbir") + "  ")

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
        if st.button("🔄 " + _t("刷新","Refresh","Muat Semula"), key="manual_refresh_bk"):
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
            f'⏱ {_t("上次更新","Last updated","Kemaskini terakhir")}: {_now_str} '
            f'· {_t("每60秒自动刷新","Auto-refresh every 60s","Muat semula setiap 60s")}</p>',
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
                                    st.toast(f"✉️ 确认邮件已发送至 {cust_email}", icon="✅")
                                else:
                                    st.toast("⚠️ 邮件发送失败，请检查 Gmail 设置", icon="⚠️")
                            except Exception as e:
                                st.toast(f"邮件错误: {e}", icon="❌")
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
        b_phone = st.text_input(u("bk_phone"), placeholder=u("bk_phone_ph"), key="b_phone")

        # Auto-match member by phone or name
        _bk_matched_mem = None
        _bk_phone_clean = b_phone.strip()
        _bk_name_clean  = b_name.strip()
        if _bk_phone_clean:
            _bk_matched_mem = next(
                (m for m in st.session_state.members
                 if m.get("phone","").strip() == _bk_phone_clean), None)
        if not _bk_matched_mem and _bk_name_clean:
            _bk_matched_mem = next(
                (m for m in st.session_state.members
                 if m.get("name","").strip() == _bk_name_clean), None)
        if _bk_matched_mem:
            _bt = tier_for_points(_bk_matched_mem.get("points", 0))
            st.markdown(
                f'<div style="background:#0d1a00;border:1px solid #2ecc71;border-radius:8px;'
                f'padding:6px 12px;font-size:0.8rem;color:#2ecc71;margin-bottom:4px;">'
                f'{u("mem_on_file").format(_bk_matched_mem["name"], tier_label(_bt))}</div>',
                unsafe_allow_html=True)
        elif _bk_phone_clean or _bk_name_clean:
            st.markdown(
                f'<div style="background:#1a1000;border:1px solid #c9a84c33;border-radius:8px;'
                f'padding:6px 12px;font-size:0.78rem;color:#888;margin-bottom:4px;">'
                f'{u("mem_new_client")}</div>',
                unsafe_allow_html=True)

        col_d, col_t = st.columns(2)
        with col_d:
            b_date = st.date_input(u("book_date"), value=dt_date.today(),
                                   min_value=dt_date.today(), key="b_date")
        with col_t:
            b_time = st.selectbox(u("book_time"), TIME_SLOTS, index=2, key="b_time")

        _any_sty  = u("any_stylist")
        sty_opts  = [_any_sty] + (st.session_state.stylists or [])
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
                    "name": b_name.strip(), "phone": b_phone.strip(),
                    "date": str(b_date), "time": b_time,
                    "stylist": ("" if b_stylist == _any_sty else b_stylist),
                    "service": b_svc,    "note": b_note,
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

            # Build backwards-compatible option lists for the editor dropdowns.
            # Include legacy Traditional + all locale names so existing DB rows
            # (which may have been saved under an older spelling) still show
            # properly in the SelectboxColumn instead of appearing blank.
            _editor_sty_opts = (
                ["", u("any_stylist")] + (st.session_state.stylists or [])
            )
            _editor_svc_opts = list(dict.fromkeys(
                svc_list
                + list(SERVICES["en"].keys())
                + list(SERVICES["ms"].keys())
                + list(SVC_LEGACY_TRADITIONAL_TO_SC.keys())
            ))

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
                                   options=_editor_sty_opts, width="small"),
                    "service": st.column_config.SelectboxColumn(u("col_service"),
                                   options=_editor_svc_opts, width="medium"),
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
            st.markdown(f'<p style="color:#c9a84c;font-size:0.8rem;letter-spacing:2px;">📱 WHATSAPP {_t("提醒","REMINDER","PERINGATAN")}</p>',
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
                    row = {"发型师 / Stylist": sty}
                    sty_rates = comm_data.get(sty, {})
                    for zh_svc, label in svc_labels.items():
                        row[label] = float(sty_rates.get(zh_svc, 0))
                    rows.append(row)

                import pandas as _pd_comm
                df_comm = _pd_comm.DataFrame(rows)
                col_config_comm = {"发型师 / Stylist": st.column_config.TextColumn(disabled=True, width="medium")}
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
                        sty = row["发型师 / Stylist"]
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
                    f"{bk.get('stylist','') or u('any_stylist')} · {bk['service']} · {bk['time']}</div></div>"
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
                    f"{b['name']}  ·  {b.get('stylist','') or u('any_stylist')}  ·  {b['service']}  ·  {b['time']}": i
                    for i, b in enumerate(unpaid_bk)
                }
                sel_label = st.selectbox(u("select_booking"), list(bk_opts.keys()),
                                         key="checkout_select")
                sel_bk = unpaid_bk[bk_opts[sel_label]]
                orig   = sel_bk.get("price", 0)

                # ── Member lookup (auto-match by phone or name) ────────────
                _bk_phone = sel_bk.get("phone", "").strip()
                _bk_cname = sel_bk.get("name", "").strip()
                _pre_match_idx = 0
                for _mi, _mm in enumerate(st.session_state.members):
                    if _bk_phone and _mm.get("phone","").strip() == _bk_phone:
                        _pre_match_idx = _mi + 1
                        break
                    elif not _bk_phone and _mm.get("name","").strip() == _bk_cname:
                        _pre_match_idx = _mi + 1
                        break
                _non_mem_lbl = "— " + _t("非会员","Non-member","Bukan Ahli") + " —"
                mem_names = [_non_mem_lbl] + \
                            [f"{m['name']}  ({m.get('phone','')})  {tier_label(tier_for_points(m.get('points',0)))}"
                             for m in st.session_state.members]
                if _pre_match_idx > 0:
                    _am = st.session_state.members[_pre_match_idx - 1]
                    _at = tier_for_points(_am.get("points", 0))
                    st.markdown(
                        f'<div style="background:#0d1a00;border:1px solid #2ecc71;border-radius:8px;'
                        f'padding:6px 12px;font-size:0.78rem;color:#2ecc71;margin-bottom:4px;">'
                        f'{u("mem_auto_match").format(_am["name"], tier_label(_at))}</div>',
                        unsafe_allow_html=True)
                mem_sel_label = st.selectbox(u("mem_lookup"), mem_names,
                                             index=_pre_match_idx, key="pay_mem_sel")
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
                  <div class="checkout-svc">{sel_bk.get('stylist','') or u('any_stylist')} · {sel_bk['service']} · {sel_bk['time']}</div>
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
            wi_phone = st.text_input(u("wi_phone"), placeholder=u("bk_phone_ph"), key="wi_phone")
            _no_sty = "— " + _t("不指定","No stylist","Tiada pilihan") + " —"
            wi_stylist = st.selectbox(
                u("stylist"),
                [_no_sty] + (st.session_state.stylists or []),
                key="wi_stylist",
            )
            wi_stylist_val = "" if wi_stylist.startswith("—") else wi_stylist
            wi_svc  = st.selectbox(u("service"), svc_list, key="wi_svc")
            wi_amt  = st.number_input(u("wi_amt_label"), 0.0, 99999.0, 50.0, 10.0, key="wi_amt")

            # Walk-in member lookup — auto-match by phone or name
            _wi_phone_clean = wi_phone.strip()
            _wi_name_clean  = wi_name.strip()
            _wi_pre_idx = 0
            for _wmi, _wmm in enumerate(st.session_state.members):
                if _wi_phone_clean and _wmm.get("phone","").strip() == _wi_phone_clean:
                    _wi_pre_idx = _wmi + 1
                    break
                elif not _wi_phone_clean and _wmm.get("name","").strip() == _wi_name_clean:
                    _wi_pre_idx = _wmi + 1
                    break
            if _wi_pre_idx > 0:
                _wam = st.session_state.members[_wi_pre_idx - 1]
                _wat = tier_for_points(_wam.get("points", 0))
                st.markdown(
                    f'<div style="background:#0d1a00;border:1px solid #2ecc71;border-radius:8px;'
                    f'padding:6px 12px;font-size:0.78rem;color:#2ecc71;margin-bottom:4px;">'
                    f'{u("mem_auto_match").format(_wam["name"], tier_label(_wat))}</div>',
                    unsafe_allow_html=True)
            wi_mem_names = ["— " + _t("非会员","Non-member","Bukan Ahli") + " —"] + \
                           [f"{m['name']}  ({m.get('phone','')})" for m in st.session_state.members]
            wi_mem_sel = st.selectbox(u("mem_lookup"), wi_mem_names,
                                      index=_wi_pre_idx, key="wi_mem_sel")
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
                    new_wi = {"name": wi_name.strip(), "phone": wi_phone.strip(),
                              "service": wi_svc or "—",
                              "stylist": wi_stylist_val,
                              "date": today_str, "final": wi_amt, "method": wi_key}
                    st.session_state.walkins.append(new_wi)
                    _bd()["walkins"] = st.session_state.walkins
                    if _USE_DB:
                        try: db_add_walkin(st.session_state.cur_branch, new_wi)
                        except Exception: pass
                    # Track non-member for quick-create prompt
                    if not wi_pay_mem and wi_name.strip():
                        st.session_state["_wi_quick_mem"] = {
                            "name":  wi_name.strip(),
                            "phone": wi_phone.strip(),
                            "svc":   wi_svc or "—",
                        }
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

            # ── Quick member create after walk-in ──────────────────────────
            _qm = st.session_state.get("_wi_quick_mem")
            if _qm:
                _already_mem = any(
                    m.get("name","").strip() == _qm["name"]
                    or (m.get("phone","").strip() and m.get("phone","").strip() == _qm.get("phone","").strip())
                    for m in st.session_state.members)
                if not _already_mem:
                    st.markdown('<div class="card" style="border-color:#c9a84c55;">', unsafe_allow_html=True)
                    st.markdown(
                        f'<p style="color:#c9a84c;font-size:0.82rem;letter-spacing:1px;margin-bottom:8px;">'
                        f'{_t("💡 新客户，是否建立会员档案？","💡 New client — create member profile?","💡 Pelanggan baru — buat profil ahli?")}'
                        f'<strong style="margin-left:6px;">{_qm["name"]}</strong></p>',
                        unsafe_allow_html=True)
                    _qcol1, _qcol2 = st.columns([3, 1])
                    with _qcol1:
                        _qphone = st.text_input(u("mem_phone"), value=_qm.get("phone",""),
                                                key="_qm_phone", label_visibility="collapsed",
                                                placeholder=u("bk_phone_ph"))
                    with _qcol2:
                        if st.button(u("wi_quick_mem"), key="_qm_create_btn"):
                            import uuid as _uuid
                            _nm = {
                                "id":          str(_uuid.uuid4())[:8],
                                "name":        _qm["name"],
                                "phone":       _qphone.strip(),
                                "birthday":    "",
                                "tier":        "普通",
                                "points":      0,
                                "total_spent": 0.0,
                                "visit_count": 0,
                                "notes":       "",
                                "join_date":   str(dt_date.today()),
                                "history":     [],
                            }
                            st.session_state.members.append(_nm)
                            _bd()["members"] = st.session_state.members
                            if _USE_DB:
                                try: db_add_member(st.session_state.cur_branch, _nm)
                                except Exception: pass
                            del st.session_state["_wi_quick_mem"]
                            st.markdown(f'<div class="alert-safe">{u("wi_mem_created").format(_qm["name"])}</div>',
                                        unsafe_allow_html=True)
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
                                     help=("取消收费（限经理以上）" if is_zh_pay
                                           else "Cancel payment (manager+ only)")):
                            st.session_state[f"confirm_void_{idx}"] = True
                    # Confirm dialog
                    if st.session_state.get(f"confirm_void_{idx}"):
                        st.warning(
                            ("⚠️ 确定要取消此收费吗？此操作不可撤回。" if is_zh_pay
                             else "⚠️ Confirm void this payment? This cannot be undone.")
                        )
                        cv1, cv2 = st.columns(2)
                        with cv1:
                            if st.button("✅ " + ("确认取消" if is_zh_pay else "Confirm Void"),
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
                                st.success("✅ " + ("已取消收费" if is_zh_pay else "Payment voided"))
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
                    f"{'客户' if st.session_state.lang=='zh' else 'Client'}: {rcpt['name']}\n"
                    f"{'日期' if st.session_state.lang=='zh' else 'Date'}: {rcpt['date']} {rcpt['time']}\n"
                    f"{'服务' if st.session_state.lang=='zh' else 'Service'}: {rcpt['service']}\n"
                    + (f"{'发型师' if st.session_state.lang=='zh' else 'Stylist'}: {rcpt['stylist']}\n" if rcpt.get('stylist') else "")
                    + (f"{'折扣' if st.session_state.lang=='zh' else 'Discount'}: {rcpt['disc_pct']}%\n" if rcpt.get('disc_pct') else "")
                    + f"{'总计' if st.session_state.lang=='zh' else 'Total'}: RM {rcpt['final']:.2f}\n"
                    f"{'付款方式' if st.session_state.lang=='zh' else 'Payment'}: {rcpt['method']}\n"
                    + (f"{'积分' if st.session_state.lang=='zh' else 'Points'}: +{rcpt['pts']} pts\n" if rcpt.get('pts') else "")
                    + f"\n{'感谢您的光临！' if st.session_state.lang=='zh' else 'Thank you for visiting Signature Kim!'}"
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
                                options=CATS["zh"] + CATS["en"] + CATS["ms"], width="medium"),
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
        st.info("⛔ " + _t("您没有权限查看结算报告","No permission to view reports","Tiada kebenaran untuk melihat laporan"))
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
                        _t("时间","Time","Masa"): b.get("time",""),
                        (u("col_s_method")):  b.get("method",""),
                        (u("col_s_amt")):     b.get("final", b.get("price",0)),
                        _t("已付款","Paid","Dibayar"): _t("是","Yes","Ya") if b.get("paid") else _t("否","No","Tidak"),
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
                        u("col_s_type"):    _t("预约","Booking","Tempahan"),
                    }
                    for b in day_paid
                ] + [
                    {
                        u("col_s_name"):    w.get("name",""),
                        u("col_s_stylist"): "—",
                        u("col_s_svc"):     w.get("service",""),
                        u("col_s_method"):  w.get("method",""),
                        u("col_s_amt"):     w.get("final",0),
                        u("col_s_type"):    _t("现场客","Walk-in","Terus Masuk"),
                    }
                    for w in day_walkins
                ]
                _k_item  = _t("项目","Item","Perkara")
                _k_value = _t("数值","Value","Nilai")
                summary_data = [
                    {_k_item: _t("结算日期","Date","Tarikh"), _k_value: settle_str},
                    {_k_item: u("settle_total"),   _k_value: f"RM {total_collected + total_pending:.2f}"},
                    {_k_item: u("settle_paid"),    _k_value: f"RM {total_collected:.2f}"},
                    {_k_item: u("settle_pending"), _k_value: f"RM {total_pending:.2f}"},
                    {_k_item: u("settle_walkin"),  _k_value: f"RM {walkin_total:.2f}"},
                ]
    
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name=_t("摘要","Summary","Ringkasan"), index=False)
                    if all_bk_rows:
                        pd.DataFrame(all_bk_rows).to_excel(writer, sheet_name=_t("全部预约","All Bookings","Semua Tempahan"), index=False)
                    if paid_rows:
                        pd.DataFrame(paid_rows).to_excel(writer, sheet_name=_t("收款明細","Payments","Bayaran"), index=False)
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
                    u("col_s_type"):    _t("预约","Booking","Tempahan"),
                }
                for b in day_paid
            ] + [
                {
                    u("col_s_name"):    w.get("name", ""),
                    u("col_s_stylist"): "—",
                    u("col_s_svc"):     w.get("service", ""),
                    u("col_s_method"):  w.get("method", ""),
                    u("col_s_amt"):     w.get("final", 0),
                    u("col_s_type"):    _t("现场客","Walk-in","Terus Masuk"),
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
            month_names_ms = ["Jan","Feb","Mac","Apr","Mei","Jun","Jul","Ogos","Sep","Okt","Nov","Dis"]
            _mn_map = {"zh": month_names_zh, "en": month_names_en, "ms": month_names_ms}
            mnames = _mn_map.get(st.session_state.lang, month_names_en)
    
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
                summary_data = [
                    {_t("月份","Month","Bulan"): settle_mth_str},
                    {_t("已收款","Collected","Diterima"): f"RM {mth_collected:.2f}"},
                    {_t("待收款","Pending","Tertunggak"):   f"RM {mth_pending:.2f}"},
                    {_t("现场客","Walk-ins","Terus Masuk"):  f"RM {mth_walkin_t:.2f}"},
                    {_t("总客数","Clients","Pelanggan"):   mth_clients},
                ]
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name=_t("摘要","Summary","Ringkasan"), index=False)
                    if daily_rows: pd.DataFrame(daily_rows).to_excel(writer, sheet_name=_t("每日明細","Daily","Harian"), index=False)
                    if not df_det_m.empty: df_det_m.to_excel(writer, sheet_name=_t("收款明細","Payments","Bayaran"), index=False)
                    if not df_sty_m.empty: df_sty_m.to_excel(writer, sheet_name=_t("发型师业绩","Stylists","Jurugaya"), index=False)
                    if not df_svc_m.empty: df_svc_m.to_excel(writer, sheet_name=_t("服务统计","Services","Perkhidmatan"), index=False)
                    if not df_mth_m.empty: df_mth_m.to_excel(writer, sheet_name=_t("付款方式","Methods","Kaedah"), index=False)
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

            # ── LHDN e-Invoice (Consolidated B2C) ─────────────────────────
            with st.expander(f"📄 {_t('生成合并 e-Invoice','Generate Consolidated e-Invoice','Jana e-Invois Disatukan')} — {settle_mth_str}"):
                _si = st.session_state.get("salon_info", {}).get(st.session_state.cur_branch, {})
                _tin  = _si.get("tin","")
                _msic = _si.get("msic_code","96020")
                _sc   = _si.get("state_code","14")

                if not _tin:
                    st.warning(_t(
                        "⚠ 请先在【管理】页面填写 TIN（税务编号）才能生成 e-Invoice",
                        "⚠ Please enter your TIN (Tax ID) in the Admin tab before generating e-Invoice",
                        "⚠ Sila masukkan TIN anda dalam tab Pentadbir sebelum menjana e-Invois"
                    ))
                else:
                    _salon_nm  = st.session_state.branches.get(st.session_state.cur_branch,"Salon")
                    _salon_adr = _si.get("address","NA")
                    _salon_cty = _si.get("city","Kuala Lumpur")
                    _salon_pst = _si.get("postcode","50000")
                    _salon_tel = _si.get("contact_phone","")
                    _salon_eml = _si.get("contact_email","")
                    _salon_ssm = _si.get("ssm_no","NA")

                    # Totals
                    _ei_total   = round(mth_collected + mth_walkin_t, 2)
                    _inv_num    = f"CIN-{int(sel_year)}{sel_month:02d}-001"
                    _start_date = f"{int(sel_year)}-{sel_month:02d}-01"
                    _days_em    = _cal.monthrange(int(sel_year), sel_month)[1]
                    _end_date   = f"{int(sel_year)}-{sel_month:02d}-{_days_em:02d}"
                    _issue_date = _end_date
                    _issue_time = "23:59:59Z"

                    st.markdown(
                        f'<div style="background:#0d1a00;border:1px solid #2ecc7133;border-radius:8px;'
                        f'padding:10px 14px;font-size:0.8rem;color:#aaa;margin-bottom:8px;">'
                        f'<b style="color:#2ecc71;">Invoice No:</b> {_inv_num} &nbsp;·&nbsp; '
                        f'<b style="color:#2ecc71;">Period:</b> {_start_date} → {_end_date} &nbsp;·&nbsp; '
                        f'<b style="color:#c9a84c;">Total:</b> RM {_ei_total:.2f} &nbsp;·&nbsp; '
                        f'<b>Tax:</b> RM 0.00 (SST-Exempt) &nbsp;·&nbsp; '
                        f'<b>TIN:</b> {_tin}</div>',
                        unsafe_allow_html=True)

                    def _build_einvoice_json():
                        """Build LHDN UBL 2.1 compliant JSON for consolidated B2C monthly invoice."""
                        import json as _json
                        doc = {
                          "_D": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                          "_A": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                          "_B": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                          "Invoice": [{
                            "ID": [{"_": _inv_num}],
                            "IssueDate": [{"_": _issue_date}],
                            "IssueTime": [{"_": _issue_time}],
                            "InvoiceTypeCode": [{"_": "01", "listVersionID": "1.0"}],
                            "DocumentCurrencyCode": [{"_": "MYR"}],
                            "TaxCurrencyCode": [{"_": "MYR"}],
                            "InvoicePeriod": [{
                              "StartDate": [{"_": _start_date}],
                              "EndDate": [{"_": _end_date}],
                              "Description": [{"_": "Monthly"}]
                            }],
                            "BillingReference": [{"AdditionalDocumentReference": [{"ID": [{"_": "NA"}]}]}],
                            "AccountingSupplierParty": [{
                              "Party": [{
                                "IndustryClassificationCode": [{"_": _msic, "name": "Hairdressing and other beauty treatment"}],
                                "PartyIdentification": [
                                  {"ID": [{"_": _tin,      "schemeID": "TIN"}]},
                                  {"ID": [{"_": _salon_ssm or "NA", "schemeID": "BRN"}]},
                                  {"ID": [{"_": "NA",      "schemeID": "SST"}]},
                                  {"ID": [{"_": "NA",      "schemeID": "TTX"}]},
                                ],
                                "PostalAddress": [{
                                  "CityName": [{"_": _salon_cty}],
                                  "PostalZone": [{"_": _salon_pst}],
                                  "CountrySubentityCode": [{"_": _sc}],
                                  "AddressLine": [{"Line": [{"_": _salon_adr or "NA"}]}],
                                  "Country": [{"IdentificationCode": [{"_": "MYS"}]}]
                                }],
                                "PartyLegalEntity": [{"RegistrationName": [{"_": _salon_nm}]}],
                                "Contact": [{"Telephone": [{"_": _salon_tel or "NA"}], "ElectronicMail": [{"_": _salon_eml or "NA"}]}]
                              }]
                            }],
                            "AccountingCustomerParty": [{
                              "Party": [{
                                "PostalAddress": [{
                                  "CityName": [{"_": "NA"}],
                                  "PostalZone": [{"_": "00000"}],
                                  "CountrySubentityCode": [{"_": "14"}],
                                  "AddressLine": [{"Line": [{"_": "NA"}]}],
                                  "Country": [{"IdentificationCode": [{"_": "MYS"}]}]
                                }],
                                "PartyIdentification": [{"ID": [{"_": "EI00000000010", "schemeID": "TIN"}]}],
                                "PartyLegalEntity": [{"RegistrationName": [{"_": "General Public"}]}]
                              }]
                            }],
                            "Delivery": [{"DeliveryParty": [{"PostalAddress": [{"CityName": [{"_": "NA"}], "PostalZone": [{"_": "00000"}], "CountrySubentityCode": [{"_": "14"}], "AddressLine": [{"Line": [{"_": "NA"}]}], "Country": [{"IdentificationCode": [{"_": "MYS"}]}]}], "PartyLegalEntity": [{"RegistrationName": [{"_": "General Public"}]}]}]}],
                            "PaymentMeans": [{"PaymentMeansCode": [{"_": "01"}], "PayeeFinancialAccount": [{"ID": [{"_": "NA"}]}]}],
                            "PaymentTerms": [{"Note": [{"_": "Cash / Card / E-wallet"}]}],
                            "TaxTotal": [{
                              "TaxAmount": [{"_": 0, "currencyID": "MYR"}],
                              "TaxSubtotal": [{
                                "TaxableAmount": [{"_": _ei_total, "currencyID": "MYR"}],
                                "TaxAmount": [{"_": 0, "currencyID": "MYR"}],
                                "TaxCategory": [{
                                  "ID": [{"_": "E"}],
                                  "TaxExemptionReason": [{"_": "SST-Exempt"}],
                                  "TaxScheme": [{"ID": [{"_": "OTH", "schemeID": "UN/ECE 5153", "schemeAgencyID": "6"}]}]
                                }]
                              }]
                            }],
                            "LegalMonetaryTotal": [{
                              "LineExtensionAmount": [{"_": _ei_total, "currencyID": "MYR"}],
                              "TaxExclusiveAmount": [{"_": _ei_total, "currencyID": "MYR"}],
                              "TaxInclusiveAmount": [{"_": _ei_total, "currencyID": "MYR"}],
                              "AllowanceTotalAmount": [{"_": 0, "currencyID": "MYR"}],
                              "ChargeTotalAmount": [{"_": 0, "currencyID": "MYR"}],
                              "PayableRoundingAmount": [{"_": 0, "currencyID": "MYR"}],
                              "PayableAmount": [{"_": _ei_total, "currencyID": "MYR"}]
                            }],
                            "InvoiceLine": [{
                              "ID": [{"_": "1"}],
                              "InvoicedQuantity": [{"_": 1, "unitCode": "C62"}],
                              "LineExtensionAmount": [{"_": _ei_total, "currencyID": "MYR"}],
                              "AllowanceCharge": [{"ChargeIndicator": [{"_": False}], "MultiplierFactorNumeric": [{"_": 0}], "Amount": [{"_": 0, "currencyID": "MYR"}]}],
                              "TaxTotal": [{
                                "TaxAmount": [{"_": 0, "currencyID": "MYR"}],
                                "TaxSubtotal": [{
                                  "TaxableAmount": [{"_": _ei_total, "currencyID": "MYR"}],
                                  "TaxAmount": [{"_": 0, "currencyID": "MYR"}],
                                  "TaxCategory": [{
                                    "ID": [{"_": "E"}],
                                    "TaxExemptionReason": [{"_": "SST-Exempt"}],
                                    "TaxScheme": [{"ID": [{"_": "OTH", "schemeID": "UN/ECE 5153", "schemeAgencyID": "6"}]}]
                                  }]
                                }]
                              }],
                              "Item": [{
                                "CommodityClassification": [{"ItemClassificationCode": [{"_": "022", "listID": "CLASS"}]}],
                                "Description": [{"_": f"Salon Services (Consolidated B2C) — {_start_date} to {_end_date}"}]
                              }],
                              "Price": [{"PriceAmount": [{"_": _ei_total, "currencyID": "MYR"}]}],
                              "ItemPriceExtension": [{"Amount": [{"_": _ei_total, "currencyID": "MYR"}]}]
                            }]
                          }]
                        }
                        return _json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")

                    _ei_col1, _ei_col2 = st.columns(2)
                    with _ei_col1:
                        st.download_button(
                            label=f"⬇ {_t('下載 e-Invoice JSON','Download e-Invoice JSON','Muat Turun e-Invois JSON')}",
                            data=_build_einvoice_json(),
                            file_name=f"eInvoice_{_inv_num}.json",
                            mime="application/json",
                            key="einv_json_dl",
                        )
                    with _ei_col2:
                        st.markdown(
                            f'<a href="https://myinvois.hasil.gov.my" target="_blank" '
                            f'style="display:inline-block;background:#1a3300;border:1px solid #2ecc71;'
                            f'color:#2ecc71;padding:0.5rem 1rem;border-radius:8px;font-size:0.82rem;'
                            f'text-decoration:none;font-weight:600;margin-top:4px;">'
                            f'🌐 {_t("提交到 MyInvois Portal","Submit to MyInvois Portal","Hantar ke Portal MyInvois")}'
                            f'</a>',
                            unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="background:#1a1a00;border:1px solid #c9a84c33;border-radius:6px;'
                        f'padding:8px 12px;font-size:0.75rem;color:#888;margin-top:8px;">'
                        f'📌 {_t("步骤：① 下载 JSON ② 登录 MyInvois Portal ③ 选择「提交 e-Invoice」→「批量上传」→ 上传此 JSON 文件","Steps: ① Download JSON ② Log into MyInvois Portal ③ Select Submit e-Invoice → Bulk Upload → Upload this JSON file","Langkah: ① Muat turun JSON ② Log masuk ke Portal MyInvois ③ Pilih Hantar e-Invois → Muat Naik Pukal → Muat naik fail JSON ini")}'
                        f'</div>',
                        unsafe_allow_html=True)

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
                    "开始日期" if is_zh else "From", value=dt_date.today().replace(day=1),
                    key="comm_start_date")
            with cr2:
                comm_end = st.date_input(
                    "结束日期" if is_zh else "To", value=dt_date.today(),
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
                            u("comm_service"): ("── " + ("小计" if is_zh else "Subtotal")),
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
                    (("总业绩" if is_zh else "Total Revenue"), f"RM {grand_rev:.2f}", "#c9a84c"),
                    (("总抽成" if is_zh else "Total Commission"), f"RM {grand_comm:.2f}", "#2ecc71"),
                    (("报表期间" if is_zh else "Period"),
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
                    if "小计" in svc_val or "Subtotal" in svc_val:
                        return ["background-color:#1a1a0a;color:#c9a84c;font-style:italic"] * len(row)
                    return [""] * len(row)

                styled_df = df_comm_report.style.apply(_style_comm, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

                # Excel export
                def _build_comm_excel():
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine="openpyxl") as writer:
                        df_comm_report.to_excel(writer, sheet_name=("抽成报表" if is_zh else "Commission"), index=False)
                        ws = writer.sheets[("抽成报表" if is_zh else "Commission")]
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
                f'{tlbl} — {t["disc"]}% {_t("折扣","discount","diskaun")}</div></div></div>',
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

            # ── Booking history (matched by phone or name) ─────────────────
            _m_phone = sel_mem.get("phone","").strip()
            _m_name  = sel_mem.get("name","").strip()
            _mem_bks = [b for b in st.session_state.bookings
                        if ((_m_phone and b.get("phone","").strip() == _m_phone)
                            or (not _m_phone and b.get("name","").strip() == _m_name))]
            if _mem_bks:
                _today_s = str(dt_date.today())
                _upcoming_bks = sorted(
                    [b for b in _mem_bks if b.get("date","") >= _today_s and not b.get("paid")],
                    key=lambda x: (x.get("date",""), x.get("time","")))
                _past_bks = sorted(
                    [b for b in _mem_bks if b.get("paid") or b.get("date","") < _today_s],
                    key=lambda x: (x.get("date",""), x.get("time","")), reverse=True)

                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(f'<p class="card-title">{u("mem_bk_section")}</p>', unsafe_allow_html=True)

                # Upcoming
                st.markdown(
                    f'<div style="font-size:0.72rem;letter-spacing:2px;color:#c9a84c;'
                    f'margin-bottom:6px;">{u("mem_upcoming").upper()}</div>',
                    unsafe_allow_html=True)
                if _upcoming_bks:
                    for _bk in _upcoming_bks[:5]:
                        _bk_sub = " · ".join(filter(None,[_bk.get("stylist",""), _bk.get("service",""), _bk.get("time","")]))
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'border-bottom:1px solid #c9a84c11;padding:6px 0;font-size:0.82rem;">'
                            f'<span style="color:#c9a84c;font-weight:700;">{_bk.get("date","")}</span>'
                            f'<span style="color:#f0ece0;flex:1;margin-left:10px;">{_bk_sub}</span>'
                            f'<span style="color:#888;font-size:0.72rem;">📅</span></div>',
                            unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="color:#555;font-size:0.8rem;padding:4px 0;">{u("mem_no_upcoming")}</div>', unsafe_allow_html=True)

                # Past
                if _past_bks:
                    st.markdown(
                        f'<div style="font-size:0.72rem;letter-spacing:2px;color:#666;'
                        f'margin-top:10px;margin-bottom:6px;">{u("mem_past_bk").upper()}</div>',
                        unsafe_allow_html=True)
                    for _bk in _past_bks[:8]:
                        _bk_sub = " · ".join(filter(None,[_bk.get("stylist",""), _bk.get("service","")]))
                        _paid_clr = "#c9a84c" if _bk.get("paid") else "#555"
                        _paid_tag = f'RM {float(_bk.get("final",0) or 0):.2f}' if _bk.get("paid") else _t("已取消","Cancelled","Dibatal")
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'border-bottom:1px solid #1a1a1a;padding:5px 0;font-size:0.8rem;">'
                            f'<span style="color:#666;">{_bk.get("date","")}</span>'
                            f'<span style="color:#f0ece0;flex:1;margin-left:10px;">{_bk_sub}</span>'
                            f'<span style="color:{_paid_clr};font-weight:700;">{_paid_tag}</span></div>',
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

        st.markdown(f'<p class="card-title" style="font-size:1.3rem;">📊 {"业绩分析" if is_zh else "Analytics Dashboard"}</p>',
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
            format_func=lambda x: {"week": "本周 / This Week",
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
            (k1, f"RM {total_rev:,.0f}", "💰 " + ("总收入" if is_zh else "Revenue")),
            (k2, str(total_txn),          "🧾 " + ("交易次数" if is_zh else "Transactions")),
            (k3, f"RM {avg_txn:,.0f}",    "📈 " + ("平均客单" if is_zh else "Avg Ticket")),
            (k4, str(total_bk),           "📅 " + ("预约数" if is_zh else "Bookings")),
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
                title="📈 " + ("收入走势" if is_zh else "Revenue Trend"),
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
            st.info("📊 " + ("暂无收入数据" if is_zh else "No revenue data yet"))

        # ── Service + Stylist Charts side by side ─────────────────────────
        ch1, ch2 = st.columns(2)

        with ch1:
            if not df_p.empty and df_p["service"].any():
                df_svc = df_p.groupby("service")["amount"].sum().reset_index()
                df_svc = df_svc.sort_values("amount", ascending=False)
                fig_svc = px.pie(
                    df_svc, values="amount", names="service",
                    title="✂️ " + ("服务收入占比" if is_zh else "Revenue by Service"),
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
                    title="💇 " + ("发型师预约数" if is_zh else "Bookings by Stylist"),
                    labels={"stylist": "", "bookings": ("预约" if is_zh else "Bookings")},
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
                    title="⏰ " + ("预约高峰时段" if is_zh else "Peak Hours"),
                    labels={"label": "", "count": ("预约数" if is_zh else "Bookings")},
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
            st.markdown(f'<p class="card-title">🏆 {"热门服务排行" if is_zh else "Top Services"}</p>',
                        unsafe_allow_html=True)
            df_top = df_p.groupby("service").agg(
                {"amount": ["sum","count","mean"]}
            ).round(1)
            df_top.columns = [("总收入 RM" if is_zh else "Revenue RM"),
                               ("次数" if is_zh else "Count"),
                               ("平均 RM" if is_zh else "Avg RM")]
            df_top = df_top.sort_values(("总收入 RM" if is_zh else "Revenue RM"), ascending=False)
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
        role_badge_txt = ("🔴 平台管理员" if is_zh else "🔴 Platform Admin") if is_platform_admin \
                         else ("👑 老板" if is_zh else "👑 Owner")
        st.markdown(
            f'<p class="card-title" style="font-size:1.3rem;">⚙️ {"系统管理" if is_zh else "Admin Panel"}'
            f' <span style="background:{role_badge_clr}22;border:1px solid {role_badge_clr}55;'
            f'color:{role_badge_clr};font-size:0.7rem;padding:3px 10px;border-radius:20px;'
            f'vertical-align:middle;letter-spacing:1px">{role_badge_txt}</span></p>',
            unsafe_allow_html=True
        )

        # ── Platform Overview (admin only) ────────────────────────────────
        if is_platform_admin:
            st.markdown('<div class="card" style="margin-bottom:1rem;border-color:#e74c3c44">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title" style="color:#e74c3c">🔴 {"平台总览" if is_zh else "Platform Overview"}</p>',
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
                (po1, total_salons,  "🏠 " + ("分店总数" if is_zh else "Total Branches")),
                (po2, owner_accts,   "👑 " + ("发廊老板" if is_zh else "Owners")),
                (po3, active_subs,   "✅ " + ("已订阅" if is_zh else "Active Subs")),
                (po4, trial_subs,    "⏳ " + ("试用中" if is_zh else "On Trial")),
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
            st.markdown(f'<p class="card-title">🏪 {"发廊基本资料" if is_zh else "Salon Profile"}</p>',
                        unsafe_allow_html=True)
            st.markdown(f'<p style="color:#888;font-size:0.8rem;margin-bottom:1rem;">'
                        f'{"以下资料将显示在收据上，请确保填写正确。" if is_zh else "This information appears on receipts — please keep it accurate."}'
                        f'</p>', unsafe_allow_html=True)

            prof_c1, prof_c2 = st.columns(2)
            with prof_c1:
                pf_cname  = st.text_input("联系人 / Contact Person",
                                          value=cur_info.get("contact_name",""), key="pf_cname")
                pf_phone  = st.text_input("电话 / Phone No.",
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
                    pf_post = st.text_input("Poskod / 邮编",
                                            value=cur_info.get("postcode",""), key="pf_post",
                                            placeholder="50000")
                pf_ssm    = st.text_input("No. SSM / ROC (Pendaftaran Perniagaan)",
                                          value=cur_info.get("ssm_no",""), key="pf_ssm",
                                          placeholder="SA0123456-X")
                pf_hours  = st.text_input("Waktu Operasi / 营业时间",
                                          value=cur_info.get("operating_hours",""), key="pf_hours",
                                          placeholder="Mon–Sat: 10am – 8pm, Sun: Closed")

            # ── e-Invoice (LHDN MyInvois) ──────────────────────────────────
            st.markdown("<hr style='margin:10px 0;border-color:#1a1a1a'>", unsafe_allow_html=True)
            st.markdown(
                f'<p style="color:#c9a84c;font-size:0.8rem;letter-spacing:2px;margin-bottom:6px;">'
                f'📄 e-INVOICE (LHDN MyInvois)</p>',
                unsafe_allow_html=True)
            _MY_STATES = {
                "14": "W.P. Kuala Lumpur", "12": "Selangor", "01": "Johor",
                "02": "Kedah", "09": "Pulau Pinang", "07": "Perak",
                "06": "Pahang", "05": "Negeri Sembilan", "04": "Melaka",
                "13": "Terengganu", "03": "Kelantan", "08": "Perlis",
                "10": "Sabah", "11": "Sarawak", "15": "W.P. Labuan",
                "16": "W.P. Putrajaya",
            }
            _state_labels = [f"{code} — {name}" for code, name in _MY_STATES.items()]
            _cur_state = cur_info.get("state_code", "14")
            _cur_state_label = next((l for l in _state_labels if l.startswith(_cur_state)), _state_labels[0])
            ei_c1, ei_c2, ei_c3 = st.columns(3)
            with ei_c1:
                pf_tin  = st.text_input("TIN (No. Cukai Pendapatan)",
                                        value=cur_info.get("tin",""), key="pf_tin",
                                        placeholder="C12345678901",
                                        help="LHDN Tax Identification Number")
            with ei_c2:
                pf_msic = st.text_input("Kod MSIC",
                                        value=cur_info.get("msic_code","96020"), key="pf_msic",
                                        placeholder="96020",
                                        help="96020 = Hairdressing & Beauty Treatment")
            with ei_c3:
                pf_state_sel = st.selectbox("Negeri / 州属", _state_labels,
                                            index=_state_labels.index(_cur_state_label),
                                            key="pf_state")
            pf_state_code = pf_state_sel.split(" — ")[0]
            st.markdown(
                f'<div style="background:#0d1000;border:1px solid #2ecc7133;border-radius:6px;'
                f'padding:6px 10px;font-size:0.75rem;color:#888;margin-top:4px;">'
                f'💡 {"TIN 可在 MyTax 门户网站查询：" if is_zh else "Find your TIN at: "}'
                f'<a href="https://mytax.hasil.gov.my" target="_blank" style="color:#2ecc71;">mytax.hasil.gov.my</a>'
                f'&nbsp;·&nbsp; MSIC 96020 = Hairdressing & Other Beauty Treatment</div>',
                unsafe_allow_html=True)

            if st.button("💾 " + ("保存基本资料" if is_zh else "Save Profile"),
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
                    "tin":             pf_tin.strip(),
                    "msic_code":       pf_msic.strip() or "96020",
                    "state_code":      pf_state_code,
                }
                if _USE_DB:
                    try:
                        db_update_salon_profile(cur_bid, profile_data)
                        fresh = db_get_salon_info(cur_bid)
                        st.session_state.setdefault("salon_info", {})[cur_bid] = fresh
                        st.success("✅ " + ("基本资料已保存！" if is_zh else "Profile saved!"))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.session_state.setdefault("salon_info", {})[cur_bid].update(profile_data)
                    st.success("✅ " + ("已保存（本地）" if is_zh else "Saved (local)"))

            # Preview card
            if any([cur_info.get("address"), cur_info.get("contact_phone"),
                    cur_info.get("ssm_no"), cur_info.get("operating_hours")]):
                st.markdown("<hr style='margin:12px 0;border-color:#1a1a1a'>", unsafe_allow_html=True)
                st.markdown(f'<p style="color:#888;font-size:0.72rem;letter-spacing:1px;margin-bottom:6px;">'
                            f'{"预览（收据上显示）" if is_zh else "PREVIEW (as shown on receipt)"}</p>',
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
        st.markdown(f'<p class="card-title">💳 {"订阅管理" if is_zh else "Subscription Management"}</p>',
                    unsafe_allow_html=True)

        PLAN_COLORS = {"trial":"#e67e22","active":"#2ecc71","expired":"#e74c3c","owner":"#c9a84c"}
        PLAN_LABELS = {"trial":"试用中","active":"已订阅","expired":"已到期","owner":"系统拥有者"}

        for bid, bname in st.session_state.branches.items():
            info  = st.session_state.get("salon_info", {}).get(bid, {})
            plan  = info.get("plan", "trial")
            tend  = info.get("trial_ends","—")
            pend  = info.get("plan_ends","—")
            color = PLAN_COLORS.get(plan, "#888")
            label = PLAN_LABELS.get(plan, plan)

            with st.expander(f"🏠 {bname} ({bid})  ·  "
                             f"[{label}]  {'到期：'+str(pend) if plan=='active' else '试用至：'+str(tend)}", expanded=False):
                sub_c1, sub_c2 = st.columns(2)

                with sub_c1:
                    st.markdown(f'<span style="color:{color};font-weight:700">{label}</span>', unsafe_allow_html=True)
                    new_stripe = st.text_input("Stripe Payment Link", value=info.get("stripe_link",""),
                                               key=f"stripe_{bid}", placeholder="https://buy.stripe.com/...")
                    new_contact_name  = st.text_input("联系人 / Contact", value=info.get("contact_name",""), key=f"cn_{bid}")
                    new_contact_phone = st.text_input("电话 / Phone",    value=info.get("contact_phone",""), key=f"cp_{bid}")
                    new_contact_email = st.text_input("Email",            value=info.get("contact_email",""), key=f"ce_{bid}")

                with sub_c2:
                    st.markdown(f"**{'启用试用' if is_zh else 'Trial'}**")
                    trial_days = st.number_input("试用天数", value=30, min_value=1, max_value=365, key=f"td_{bid}")
                    if st.button("🔄 " + ("重置试用期" if is_zh else "Reset Trial"), key=f"trial_btn_{bid}"):
                        if _USE_DB:
                            try:
                                db_activate_trial(bid, int(trial_days))
                                st.success("✅ 试用期已重置")
                            except Exception as e:
                                st.error(str(e))

                    st.markdown(f"**{'启用订阅' if is_zh else 'Activate Plan'}**")
                    plan_end_date = st.date_input("订阅到期日", key=f"ped_{bid}",
                                                   value=_sub_dt.date.today() + _sub_dt.timedelta(days=30))
                    if st.button("✅ " + ("启用订阅" if is_zh else "Activate"), key=f"act_btn_{bid}"):
                        if _USE_DB:
                            try:
                                db_update_salon_subscription(bid, "active", str(plan_end_date), new_stripe)
                                db_update_salon_contact(bid, new_contact_name, new_contact_phone, new_contact_email)
                                # Reload salon info
                                fresh = db_get_salon_info(bid)
                                st.session_state.setdefault("salon_info", {})[bid] = fresh
                                st.success(f"✅ 已启用至 {plan_end_date}")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

        # ── Add new subscribing salon ──────────────────────────────────────
        st.markdown(f'<p style="color:#c9a84c;font-size:0.82rem;letter-spacing:1px;margin-top:0.8rem">{"＋ 新增订阅店家" if is_zh else "＋ Add New Salon"}</p>',
                    unsafe_allow_html=True)
        sub_nb_c1, sub_nb_c2, sub_nb_c3 = st.columns([1, 2, 1])
        with sub_nb_c1:
            sub_new_bid   = st.text_input("ID", placeholder="S001", key="sub_new_bid")
        with sub_nb_c2:
            sub_new_bname = st.text_input("名称 / Name", placeholder="Beauty Salon KL", key="sub_new_bname")
        with sub_nb_c3:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("＋ " + ("新增" if is_zh else "Add"), key="sub_add_salon_btn"):
                if sub_new_bid.strip() and sub_new_bname.strip():
                    _sbid  = sub_new_bid.strip()
                    _sbname = sub_new_bname.strip()
                    st.session_state.branches[_sbid] = _sbname
                    _init_branch(_sbid)
                    if _USE_DB:
                        try:
                            db_add_salon(_sbid, _sbname)
                        except Exception as _e:
                            st.error(str(_e))
                    st.success(f"✅ {_sbname} " + ("已新增" if is_zh else "added"))
                    st.rerun()
                else:
                    st.warning("请填写 ID 和名称 / Please fill in ID and Name")

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Online Booking Links ───────────────────────────────────────────
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        st.markdown(f'<p class="card-title">🔗 {"客户预约链接" if is_zh else "Customer Booking Links"}</p>',
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
            st.info("填入上方的 App URL 就能生成每间分店的客户预约链接 / Enter your App URL above to generate booking links")
        st.markdown('</div>', unsafe_allow_html=True)

        ROLE_COLOR = {"admin":"#e74c3c","owner":"#c9a84c","manager":"#3498db","staff":"#2ecc71"}
        ROLE_ICON  = {"admin":"🔴","owner":"👑","manager":"💼","staff":"✂️"}
        ROLE_LABEL = {"admin":   ("平台管理员" if is_zh else "Platform Admin"),
                      "owner":   ("老板" if is_zh else "Owner"),
                      "manager": ("经理" if is_zh else "Manager"),
                      "staff":   ("员工" if is_zh else "Staff")}

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
            PLAN_LBL  = {"trial":"试用中" if is_zh else "Trial",
                         "active":"已订阅" if is_zh else "Active",
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
                f"[{plan_lbl}]  ·  {n_accts} {'账号' if is_zh else 'accounts'}",
                expanded=False
            ):
                ex_c1, ex_c2 = st.columns([1.5, 1])
                with ex_c1:
                    # Stats row
                    st.markdown(f"""
                    <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap">
                      <div class="stat-box" style="flex:1;min-width:80px">
                        <div class="stat-val" style="font-size:1.2rem">{n_bk}</div>
                        <div class="stat-lbl">{"预约" if is_zh else "Bookings"}</div>
                      </div>
                      <div class="stat-box" style="flex:1;min-width:80px">
                        <div class="stat-val" style="font-size:1.2rem">{n_members}</div>
                        <div class="stat-lbl">{"会员" if is_zh else "Members"}</div>
                      </div>
                      <div class="stat-box" style="flex:1;min-width:80px">
                        <div class="stat-val" style="font-size:1.2rem">{n_accts}</div>
                        <div class="stat-lbl">{"账号" if is_zh else "Accounts"}</div>
                      </div>
                    </div>
                    <div style="font-size:0.8rem;color:#888;margin-bottom:6px">
                      {"订阅状态" if is_zh else "Subscription"}:
                      <span style="color:{plan_clr};font-weight:700">{plan_lbl}</span>
                      {"· 试用至: "+str(tend) if plan=="trial" else "· 到期: "+str(pend) if plan=="active" else ""}
                    </div>
                    """, unsafe_allow_html=True)

                    # Edit branch name
                    new_name_val = st.text_input(
                        "✏️ " + ("分店名称" if is_zh else "Branch Name"),
                        value=bname, key=f"edit_bname_{bid}"
                    )
                    # Contact info from salon_info
                    st.markdown(f'<div style="font-size:0.78rem;color:#888;margin-top:4px">'
                                f'👤 {info.get("contact_name","—")}  '
                                f'📞 {info.get("contact_phone","—")}  '
                                f'✉️ {info.get("contact_email","—")}'
                                f'</div>', unsafe_allow_html=True)

                with ex_c2:
                    st.markdown(f'<div style="font-size:0.8rem;color:#c9a84c;margin-bottom:6px">{"关联账号" if is_zh else "Linked Accounts"}</div>',
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
                    if st.button("💾 " + ("保存名称" if is_zh else "Save Name"), key=f"save_bname_{bid}"):
                        if new_name_val.strip():
                            st.session_state.branches[bid] = new_name_val.strip()
                            if _USE_DB:
                                try:
                                    from db import get_supabase as _get_sb; _get_sb().table("salons").update({"name": new_name_val.strip()}).eq("id", bid).execute()
                                except Exception: pass
                            st.success("✅ " + ("已保存" if is_zh else "Saved"))
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
            new_bname = st.text_input("名称 / Name", placeholder="Signature Kim — PJ", key="new_bname")
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
        st.markdown(f'<p class="card-title">👤 {"账号管理" if is_zh else "Account Management"}</p>',
                    unsafe_allow_html=True)

        # Filter by branch
        filter_opts = ["全部 / All"] + [f"{bid} · {nm}" for bid, nm in st.session_state.branches.items()]
        acct_filter = st.selectbox("🔍 " + ("筛选分店" if is_zh else "Filter by Branch"),
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
                    new_disp = st.text_input("显示名称 / Display Name",
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
                                f'{"重置密码" if is_zh else "Reset Password"}</div>', unsafe_allow_html=True)
                    new_pw    = st.text_input("新密码 / New Password", type="password", key=f"npw_{uname}",
                                              placeholder="6+ chars")
                    new_pw2   = st.text_input("确认 / Confirm", type="password", key=f"npw2_{uname}")
                    if st.button("🔑 " + ("重置密码" if is_zh else "Reset"), key=f"rpw_{uname}"):
                        if len(new_pw) < 6:
                            st.error("❌ " + ("密码至少6位" if is_zh else "Min 6 chars"))
                        elif new_pw != new_pw2:
                            st.error("❌ " + ("密码不一致" if is_zh else "Passwords don't match"))
                        else:
                            st.session_state.accounts[uname]["hash"] = _hash(new_pw)
                            if _USE_DB:
                                try: db_update_password(uname, _hash(new_pw))
                                except Exception: pass
                            st.success("✅ " + ("密码已重置" if is_zh else "Password reset"))

                save_col, del_col = st.columns([2, 1])
                with save_col:
                    if st.button("💾 " + ("保存更改" if is_zh else "Save Changes"), key=f"save_acct_{uname}"):
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
                        st.success("✅ " + ("已保存" if is_zh else "Saved"))
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
        st.markdown(f'<p style="color:#c9a84c;font-size:0.9rem;letter-spacing:1px;font-weight:700">＋ {"新增账号" if is_zh else "Add New Account"}</p>',
                    unsafe_allow_html=True)
        na1, na2 = st.columns(2)
        with na1:
            na_user = st.text_input("Username", placeholder="staff01", key="na_user")
            na_name = st.text_input("显示名称 / Display Name", placeholder="Kim", key="na_name")
            na_pass = st.text_input("密码 / Password", type="password", key="na_pass", placeholder="Min 6 chars")
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
                "admin":   "🔴 平台管理员：最高权限，管理所有发廊、订阅、账号" if is_zh else "🔴 Platform Admin: Full control over all salons, subscriptions & accounts",
                "owner":   "👑 老板：管理自己的分店、账号、订阅" if is_zh else "👑 Owner: Manage own branches, accounts & subscription",
                "manager": "💼 经理：管理自己分店的全部功能" if is_zh else "💼 Manager: Full access to own branch functions",
                "staff":   "✂️ 员工：只能使用预约和收费功能" if is_zh else "✂️ Staff: Bookings and payment only",
            }
            st.markdown(f"""
            <div style="background:#1a1a1a;border-radius:8px;padding:8px 12px;margin-top:6px;font-size:0.78rem;color:#888;border-left:3px solid {ROLE_COLOR.get(na_role,'#888')}">
              <b style="color:{ROLE_COLOR.get(na_role,'#888')}">{ROLE_LABEL.get(na_role,'')}</b><br>
              {role_desc.get(na_role,'')}
            </div>
            """, unsafe_allow_html=True)

        if st.button("＋ " + ("新增账号" if is_zh else "Add Account"), key="add_acct_btn",
                     use_container_width=True):
            if na_user.strip() and na_pass.strip() and len(na_pass) >= 6:
                if na_user.strip() in st.session_state.accounts:
                    st.error("⚠ " + ("用户名已存在" if is_zh else "Username already exists"))
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
                st.warning("⚠ " + ("密码至少6位" if is_zh else "Password must be 6+ chars"))
            else:
                st.warning("⚠ " + ("请填写用户名和密码" if is_zh else "Please fill in username and password"))

        # ── Change own password ────────────────────────────────────────────
        st.markdown("---")
        with st.expander("🔑 " + ("修改自己的密码" if is_zh else "Change My Password")):
            cp_old  = st.text_input("旧密码 / Old Password", type="password", key="cp_old")
            cp_new  = st.text_input("新密码 / New Password", type="password", key="cp_new")
            cp_new2 = st.text_input("确认 / Confirm",        type="password", key="cp_new2")
            if st.button("Update / 更新", key="cp_btn"):
                me = st.session_state.accounts.get(st.session_state.username)
                if not me or me["hash"] != _hash(cp_old):
                    st.error("❌ " + ("旧密码不正确" if is_zh else "Old password incorrect"))
                elif cp_new != cp_new2:
                    st.error("❌ " + ("新密码不一致" if is_zh else "Passwords don't match"))
                elif len(cp_new) < 6:
                    st.warning("⚠ " + ("密码至少6位" if is_zh else "Password must be 6+ chars"))
                else:
                    st.session_state.accounts[st.session_state.username]["hash"] = _hash(cp_new)
                    if _USE_DB:
                        try: db_update_password(st.session_state.username, _hash(cp_new))
                        except Exception: pass
                    st.success("✦ " + ("密码已更新" if is_zh else "Password updated"))

            st.markdown('</div>', unsafe_allow_html=True)
