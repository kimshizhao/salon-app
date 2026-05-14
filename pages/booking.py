"""
Public customer self-booking page.
URL: https://<your-app>.streamlit.app/booking?salon=B001
"""
import streamlit as st
from datetime import date as dt_date, timedelta
try:
    from notify import (
        send_booking_received, send_salon_new_booking_alert,
        email_configured, whatsapp_link
    )
    _NOTIFY = True
except Exception:
    _NOTIFY = False

def _get_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

st.set_page_config(
    page_title="Book Now — IQSALON",
    page_icon="✂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Try to connect to Supabase ────────────────────────────────────────────────
try:
    from supabase import create_client
    _url = st.secrets.get("SUPABASE_URL", "")
    _key = st.secrets.get("SUPABASE_KEY", "")
    _USE_DB = bool(_url and _key and not _url.startswith("https://YOUR"))
    if _USE_DB:
        @st.cache_resource
        def _sb():
            return create_client(_url, _key)
except Exception:
    _USE_DB = False

# ── CSS (same brand theme) ────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Raleway:wght@300;400;600;700&display=swap');
  /* Nusantara Theme — Malaysian Batik for booking page */
  html { background-color:#060e09 !important; }
  body { background:#060e09 !important; }
  html,body,[class*="css"]{ font-family:'Raleway',sans-serif; color:#f2ede3; }
  .stApp {
    background-color:#060e09;
    background-image:
      repeating-linear-gradient(45deg,transparent 0,transparent 18px,rgba(212,160,48,0.04) 18px,rgba(212,160,48,0.04) 19px),
      repeating-linear-gradient(-45deg,transparent 0,transparent 18px,rgba(212,160,48,0.04) 18px,rgba(212,160,48,0.04) 19px),
      radial-gradient(ellipse 110% 65% at 50% -8%, rgba(26,100,70,0.25), transparent 58%),
      radial-gradient(ellipse 60% 45% at 100% 12%, rgba(212,160,48,0.09), transparent 52%),
      linear-gradient(170deg,#07110a,#040c07 45%,#060f08,#050a06);
    background-attachment:fixed;
  }
  section[data-testid="stMain"], section.main {
    background-image:radial-gradient(ellipse 130% 80% at 50% 0%, rgba(0,0,0,0), rgba(0,0,0,0.3));
    background-attachment:fixed;
  }
  #MainMenu, footer, header, [data-testid="stSidebarNav"] { visibility:hidden; display:none; }
  .block-container { padding:1.2rem 1.4rem 2rem; max-width:580px !important; }

  /* Hero banner */
  .hero {
    text-align:center; padding:2.2rem 1rem 1.3rem; margin-bottom:1.6rem; border-radius:16px;
    border:1px solid rgba(212,160,48,0.25);
    background:repeating-linear-gradient(90deg,transparent,transparent 28px,rgba(212,160,48,0.03) 28px,rgba(212,160,48,0.03) 29px),
    linear-gradient(158deg,rgba(10,24,14,0.97),rgba(6,14,9,0.90));
    box-shadow:inset 0 1px 0 rgba(212,160,48,0.12), 0 6px 38px rgba(0,0,0,0.55);
    backdrop-filter:saturate(130%) blur(12px);
    -webkit-backdrop-filter:saturate(130%) blur(12px);
  }
  .hero-title {
    font-family:'Cinzel',serif; font-size:2.2rem; font-weight:600; letter-spacing:7px;
    background:linear-gradient(135deg,#8ecfa0,#d4a030,#f5d470,#d4a030,#6db88a);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
    filter:drop-shadow(0 2px 6px rgba(212,160,48,0.28)); margin:0;
  }
  .hero-sub { font-size:0.70rem; letter-spacing:5px; color:#3a6a4a; margin-top:5px; text-transform:uppercase; font-weight:600; }
  .hero-branch { font-size:0.82rem; color:#d4a030; margin-top:5px; letter-spacing:2px; }

  /* Steps */
  .step-label { font-family:'Cinzel',serif; font-size:0.95rem; color:#d4a030;
    letter-spacing:2px; margin:1.4rem 0 0.6rem; }

  /* Service cards */
  .svc-card { background:rgba(10,22,14,0.90); border:1px solid rgba(212,160,48,0.20); border-radius:13px;
    padding:0.9rem 1.2rem; margin-bottom:0.5rem; cursor:pointer; transition:all .2s; display:flex;
    justify-content:space-between; align-items:center; }
  .svc-card:hover { border-color:rgba(212,160,48,0.55); background:rgba(12,26,16,0.92); }
  .svc-card.selected { border-color:#d4a030; background:rgba(20,40,22,0.95); box-shadow:0 0 0 1px rgba(212,160,48,0.3); }
  .svc-name { font-size:0.95rem; color:#f2ede3; }
  .svc-price { font-family:'Cinzel',serif; font-size:1.05rem; color:#d4a030; }

  /* Time slots */
  .slot-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:1rem; }
  .slot { background:rgba(8,20,12,0.90); border:1px solid rgba(212,160,48,0.18); border-radius:9px;
    padding:8px 0; text-align:center; font-size:0.82rem; color:#8aaa8a;
    cursor:pointer; transition:all .2s; }
  .slot:hover { border-color:rgba(212,160,48,0.5); color:#d4a030; }
  .slot.taken { opacity:0.30; cursor:default; text-decoration:line-through; }
  .slot.selected { background:linear-gradient(135deg,#d4a030,#9a7020); color:#060e09;
    font-weight:700; border-color:#d4a030; box-shadow:0 3px 12px rgba(212,160,48,0.3); }

  /* Confirm box */
  .confirm-box { background:linear-gradient(148deg,rgba(10,22,14,0.96),rgba(6,14,9,0.90));
    border:1px solid rgba(212,160,48,0.28); border-radius:14px; padding:1.4rem 1.6rem; margin:1rem 0;
    box-shadow:inset 0 1px 0 rgba(212,160,48,0.08), 0 6px 30px rgba(0,0,0,0.42); }
  .confirm-row { display:flex; justify-content:space-between; padding:0.4rem 0;
    border-bottom:1px solid rgba(212,160,48,0.08); font-size:0.88rem; }
  .confirm-label { color:#4a6a52; }
  .confirm-val { color:#f2ede3; font-weight:600; }

  /* Success */
  .success-icon { font-size:3.5rem; text-align:center; margin:1rem 0; }
  .success-title { font-family:'Cinzel',serif; font-size:1.5rem; color:#d4a030;
    text-align:center; letter-spacing:3px; }
  .success-msg { text-align:center; color:#5a8a6a; font-size:0.85rem; margin-top:0.5rem; line-height:1.6; }

  /* Inputs */
  .stTextInput>div>div>input, .stSelectbox>div>div {
    background:rgba(8,20,12,0.95) !important; border:1px solid rgba(212,160,48,0.30) !important;
    border-radius:9px !important; color:#f2ede3 !important; font-size:16px !important; min-height:44px !important; }
  label, .stMarkdown p { color:#6a9a7a !important; font-size:0.85rem; letter-spacing:0.8px; }
  .stButton>button {
    background:linear-gradient(135deg,#2a7a50,#1a5a3a,#d4a030); color:#f2ede3;
    font-family:'Raleway',sans-serif; font-weight:700; font-size:0.85rem; letter-spacing:2px;
    text-transform:uppercase; border:none; border-radius:9px; padding:0.88rem 2rem;
    min-height:48px; transition:all .25s; width:100%; }
  .stButton>button:hover {
    background:linear-gradient(135deg,#d4a030,#2a7a50); transform:translateY(-1px);
    box-shadow:0 4px 20px rgba(212,160,48,0.3); }
  .stDateInput>div>div>input {
    background:rgba(8,20,12,0.95) !important; border:1px solid rgba(212,160,48,0.30) !important;
    color:#f2ede3 !important; border-radius:9px !important; min-height:44px !important; font-size:16px !important; }
  .stSelectbox [data-baseweb="select"]>div { background:rgba(8,20,12,0.95) !important; border-color:rgba(212,160,48,0.35) !important; }
  .stSelectbox svg { fill:#d4a030 !important; }
  ::-webkit-scrollbar { width:4px; } ::-webkit-scrollbar-track { background:#060e09; }
  ::-webkit-scrollbar-thumb { background:#1a4a28; border-radius:3px; }

  @media(max-width:480px){
    .hero-title{font-size:1.5rem !important; letter-spacing:4px !important;}
    .slot-grid{grid-template-columns:repeat(3,1fr) !important;}
    .block-container{padding:0.6rem 0.6rem 1rem !important;}
  }
</style>
""", unsafe_allow_html=True)

# ── Services & Stylists data ──────────────────────────────────────────────────
SERVICES_EN = {
    "Haircut": 50, "Hair Coloring": 180, "Scalp Treatment": 120,
    "Perm": 250, "Keratin Treatment": 350, "Scalp SPA": 100,
}
SERVICES_ZH = {
    "剪发": 50, "染发": 180, "头皮护理": 120,
    "烫发": 250, "角蛋白护理": 350, "头皮SPA": 100,
}
TIME_SLOTS = [
    "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00", "17:30", "18:00", "18:30",
]

# ── Read salon ID from URL params ─────────────────────────────────────────────
params     = st.query_params
salon_id   = params.get("salon", "")
lang_param = params.get("lang", "zh")   # ?lang=en to switch language

# ── Language toggle ───────────────────────────────────────────────────────────
if "bk_lang" not in st.session_state:
    st.session_state.bk_lang = lang_param

L = st.session_state.bk_lang

T = {
    "zh": {
        "sub": "MANAGEMENT SYSTEM", "book_title": "线上预约",
        "step_svc": "① 选择服务", "step_stylist": "② 选择发型师",
        "step_date": "③ 选择日期", "step_time": "④ 选择时间",
        "step_info": "⑤ 填写资料",
        "any_stylist": "不指定 (Any Stylist)",
        "your_name": "您的姓名", "your_phone": "手机号码",
        "step_confirm": "⑥ 确认预约",
        "service": "服务", "stylist": "发型师",
        "date": "日期", "time": "时间",
        "name": "姓名", "phone": "电话",
        "price_est": "预估费用",
        "submit_btn": "确认预约",
        "success_title": "预约成功！",
        "success_msg": "我们已收到您的预约申请\n发廊将尽快与您确认时间\n请保持电话畅通",
        "new_booking": "再次预约",
        "taken": "已订",
        "invalid": "无效的预约链接",
        "invalid_msg": "请联系发廊获取正确的预约链接。",
        "name_req": "请填写您的姓名",
        "phone_req": "请填写手机号码",
        "svc_req": "请选择服务",
        "time_req": "请选择时间",
        "lang_toggle": "English",
        "from": "来自",
        "pending_note": "预约待确认，我们会尽快联系您",
        "your_email": "电子邮件（选填）",
        "email_ph": "例如：name@gmail.com",
    },
    "en": {
        "sub": "MANAGEMENT SYSTEM", "book_title": "ONLINE BOOKING",
        "step_svc": "① Select Service", "step_stylist": "② Select Stylist",
        "step_date": "③ Select Date", "step_time": "④ Select Time",
        "step_info": "⑤ Your Details",
        "any_stylist": "No Preference (Any Stylist)",
        "your_name": "Your Name", "your_phone": "Phone Number",
        "step_confirm": "⑥ Confirm Booking",
        "service": "Service", "stylist": "Stylist",
        "date": "Date", "time": "Time",
        "name": "Name", "phone": "Phone",
        "price_est": "Estimated Price",
        "submit_btn": "Confirm Booking",
        "success_title": "Booking Received!",
        "success_msg": "We have received your booking request.\nOur team will contact you shortly to confirm.\nPlease keep your phone available.",
        "new_booking": "Book Again",
        "taken": "Taken",
        "invalid": "Invalid Booking Link",
        "invalid_msg": "Please contact the salon for the correct booking link.",
        "name_req": "Please enter your name",
        "phone_req": "Please enter your phone number",
        "svc_req": "Please select a service",
        "time_req": "Please select a time slot",
        "lang_toggle": "简体",
        "from": "From",
        "pending_note": "Booking pending — we will contact you to confirm",
        "your_email": "Email Address (optional)",
        "email_ph": "e.g. name@gmail.com",
    },
}

def t(key): return T[L].get(key, key)

SERVICES = SERVICES_ZH if L == "zh" else SERVICES_EN

def get_price(svc_name: str) -> int:
    """Look up price from either language dictionary."""
    return SERVICES_ZH.get(svc_name, 0) or SERVICES_EN.get(svc_name, 0)

# ── Load salon data ───────────────────────────────────────────────────────────
salon_name = "Signature Kim"
stylists   = ["Kim", "Lily", "Jason"]
booked_slots = {}   # {date: [time1, time2]} for chosen stylist

if not salon_id:
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">✦ IQSALON ✦</div>
      <div class="hero-sub">{t('sub')}</div>
    </div>
    """, unsafe_allow_html=True)
    st.error(f"### {t('invalid')}\n{t('invalid_msg')}")
    st.stop()

if _USE_DB:
    try:
        sb = _sb()
        sal_res = sb.table("salons").select("name").eq("id", salon_id).execute()
        if sal_res.data:
            salon_name = sal_res.data[0]["name"]
        else:
            # salon_id not found in database — show invalid link error
            st.markdown(f"""
            <div class="hero">
              <div class="hero-title">❋ IQSALON ❋</div>
              <div class="hero-sub">{t('sub')}</div>
            </div>
            """, unsafe_allow_html=True)
            st.error(f"### {t('invalid')}\n{t('invalid_msg')}")
            st.stop()
        sty_res = sb.table("stylists").select("name").eq("salon_id", salon_id).execute()
        if sty_res.data:
            stylists = [r["name"] for r in sty_res.data]
    except Exception:
        pass

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [
    ("bk_step", 1), ("bk_service", ""), ("bk_stylist", ""),
    ("bk_date", dt_date.today() + timedelta(days=1)),
    ("bk_time", ""), ("bk_name", ""), ("bk_phone", ""), ("bk_email", ""),
    ("bk_done", False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Hero header ───────────────────────────────────────────────────────────────
col_h, col_lang = st.columns([5, 1])
with col_h:
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">❋ {salon_name.upper()} ❋</div>
      <div class="hero-sub">{t('sub')}</div>
    </div>
    """, unsafe_allow_html=True)
with col_lang:
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    if st.button(t("lang_toggle"), key="lang_btn"):
        st.session_state.bk_lang = "en" if L == "zh" else "zh"
        st.rerun()

# ── Success screen ────────────────────────────────────────────────────────────
if st.session_state.bk_done:
    st.markdown(f"""
    <div class="success-icon">✅</div>
    <div class="success-title">{t('success_title')}</div>
    <div class="success-msg">{t('success_msg').replace(chr(10),'<br>')}</div>
    <br>
    <div class="confirm-box">
      <div class="confirm-row"><span class="confirm-label">{t('name')}</span>
        <span class="confirm-val">{st.session_state.bk_name}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('service')}</span>
        <span class="confirm-val">{st.session_state.bk_service}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('stylist')}</span>
        <span class="confirm-val">{st.session_state.bk_stylist or t('any_stylist')}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('date')}</span>
        <span class="confirm-val">{st.session_state.bk_date}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('time')}</span>
        <span class="confirm-val">{st.session_state.bk_time}</span></div>
      <div class="confirm-row" style="border:none"><span class="confirm-label">{t('price_est')}</span>
        <span class="confirm-val" style="color:#c9a84c">RM {get_price(st.session_state.bk_service)}</span></div>
    </div>
    <p style="text-align:center;color:#888;font-size:0.78rem;margin-top:0.5rem">
      ⚡ {t('pending_note')}</p>
    """, unsafe_allow_html=True)
    if st.button(t("new_booking"), key="new_bk"):
        for k in ["bk_step","bk_service","bk_stylist","bk_time","bk_name","bk_phone","bk_done"]:
            st.session_state[k] = "" if isinstance(st.session_state[k], str) else \
                                   (False if k == "bk_done" else 1 if k == "bk_step" else st.session_state[k])
        st.session_state.bk_step = 1
        st.session_state.bk_done = False
        st.rerun()
    st.stop()

# ── Step 1: Service ───────────────────────────────────────────────────────────
st.markdown(f'<div class="step-label">{t("step_svc")}</div>', unsafe_allow_html=True)
for svc, price in SERVICES.items():
    selected = "selected" if st.session_state.bk_service == svc else ""
    if st.button(f"{'✓ ' if selected else ''}{svc}  —  RM {price}", key=f"svc_{svc}"):
        st.session_state.bk_service = svc
        st.rerun()

st.markdown("---")

# ── Step 2: Stylist ───────────────────────────────────────────────────────────
st.markdown(f'<div class="step-label">{t("step_stylist")}</div>', unsafe_allow_html=True)
sty_options = [t("any_stylist")] + stylists
sty_choice  = st.selectbox("", sty_options, key="sty_sel",
                            label_visibility="collapsed")
st.session_state.bk_stylist = "" if sty_choice == t("any_stylist") else sty_choice

st.markdown("---")

# ── Step 3: Date ──────────────────────────────────────────────────────────────
st.markdown(f'<div class="step-label">{t("step_date")}</div>', unsafe_allow_html=True)
min_date = dt_date.today() + timedelta(days=1)
max_date = dt_date.today() + timedelta(days=60)
chosen_date = st.date_input("", value=st.session_state.bk_date,
                             min_value=min_date, max_value=max_date,
                             key="date_pick", label_visibility="collapsed")
st.session_state.bk_date = chosen_date

# Load taken slots for selected date + stylist
taken_times = set()
if _USE_DB:
    try:
        sb = _sb()
        q = sb.table("bookings").select("time")\
               .eq("salon_id", salon_id)\
               .eq("date", str(chosen_date))
        if st.session_state.bk_stylist:
            q = q.eq("stylist", st.session_state.bk_stylist)
        taken_res = q.execute()
        taken_times = {r["time"] for r in (taken_res.data or [])}
    except Exception:
        pass

st.markdown("---")

# ── Step 4: Time ──────────────────────────────────────────────────────────────
st.markdown(f'<div class="step-label">{t("step_time")}</div>', unsafe_allow_html=True)

# Build grid HTML for time slots
slot_html = '<div class="slot-grid">'
for ts in TIME_SLOTS:
    if ts in taken_times:
        slot_html += f'<div class="slot taken">{ts}<br><small>{t("taken")}</small></div>'
    else:
        sel = "selected" if st.session_state.bk_time == ts else ""
        slot_html += f'<div class="slot {sel}">{ts}</div>'
slot_html += "</div>"
st.markdown(slot_html, unsafe_allow_html=True)

# Fallback: selectbox for actual selection (since HTML div clicks aren't interactive)
available_slots = [ts for ts in TIME_SLOTS if ts not in taken_times]
if available_slots:
    current_idx = available_slots.index(st.session_state.bk_time) \
                  if st.session_state.bk_time in available_slots else 0
    picked_time = st.selectbox(
        "选择时间 / Select Time", available_slots, index=current_idx,
        key="time_sel"
    )
    st.session_state.bk_time = picked_time
else:
    st.warning("⚠️ 该日期已全部约满，请选择其他日期 / All slots taken for this date")
    st.session_state.bk_time = ""

st.markdown("---")

# ── Step 5: Customer Info ─────────────────────────────────────────────────────
st.markdown(f'<div class="step-label">{t("step_info")}</div>', unsafe_allow_html=True)
name_val  = st.text_input(t("your_name"),  value=st.session_state.bk_name,
                           placeholder="e.g. Mei Ling / 小明", key="name_input")
phone_val = st.text_input(t("your_phone"), value=st.session_state.bk_phone,
                           placeholder="e.g. 012-3456789", key="phone_input")
email_val = st.text_input(t("your_email"), value=st.session_state.bk_email,
                           placeholder=t("email_ph"), key="email_input")
st.session_state.bk_name  = name_val
st.session_state.bk_phone = phone_val
st.session_state.bk_email = email_val

st.markdown("---")

# ── Step 6: Confirm ───────────────────────────────────────────────────────────
if st.session_state.bk_service:
    st.markdown(f'<div class="step-label">{t("step_confirm")}</div>', unsafe_allow_html=True)
    price_est = get_price(st.session_state.bk_service)
    st.markdown(f"""
    <div class="confirm-box">
      <div class="confirm-row"><span class="confirm-label">{t('service')}</span>
        <span class="confirm-val">{st.session_state.bk_service}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('stylist')}</span>
        <span class="confirm-val">{st.session_state.bk_stylist or t('any_stylist')}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('date')}</span>
        <span class="confirm-val">{st.session_state.bk_date}</span></div>
      <div class="confirm-row"><span class="confirm-label">{t('time')}</span>
        <span class="confirm-val">{st.session_state.bk_time or '—'}</span></div>
      <div class="confirm-row" style="border:none">
        <span class="confirm-label">{t('price_est')}</span>
        <span class="confirm-val" style="color:#c9a84c;font-size:1.2rem">RM {price_est}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(t("submit_btn"), key="submit_bk"):
        # Validate
        errors = []
        if not st.session_state.bk_name.strip():
            errors.append(t("name_req"))
        if not st.session_state.bk_phone.strip():
            errors.append(t("phone_req"))
        if not st.session_state.bk_service:
            errors.append(t("svc_req"))
        if not st.session_state.bk_time:
            errors.append(t("time_req"))

        if errors:
            for e in errors:
                st.error(e)
        else:
            bk_payload = {
                "name":    st.session_state.bk_name.strip(),
                "phone":   st.session_state.bk_phone.strip(),
                "email":   st.session_state.bk_email.strip(),
                "service": st.session_state.bk_service,
                "stylist": st.session_state.bk_stylist,
                "date":    str(st.session_state.bk_date),
                "time":    st.session_state.bk_time,
                "note":    "📱 Online booking",
                "price":   price_est,
                "paid":    False,
                "method":  "",
                "final":   0,
                "source":  "online",
                "status":  "pending",
            }
            saved = False
            if _USE_DB:
                try:
                    _sb().table("bookings").insert(
                        {**bk_payload, "salon_id": salon_id}
                    ).execute()
                    saved = True
                except Exception as ex:
                    st.error(f"Error saving: {ex}")
            else:
                saved = True  # Demo mode

            if saved:
                # Send emails if configured
                if _NOTIFY:
                    salon_phone_cfg = _get_secret("SALON_PHONE", "")
                    # Email to customer
                    if st.session_state.bk_email.strip():
                        send_booking_received(
                            to_email=st.session_state.bk_email.strip(),
                            customer_name=st.session_state.bk_name.strip(),
                            service=st.session_state.bk_service,
                            stylist=st.session_state.bk_stylist,
                            date=str(st.session_state.bk_date),
                            time=st.session_state.bk_time,
                            price=price_est,
                            salon_name=salon_name,
                            salon_phone=salon_phone_cfg,
                        )
                    # Alert email to salon owner/manager
                    notify_email = _get_secret("NOTIFY_EMAIL", "")
                    if notify_email:
                        send_salon_new_booking_alert(
                            to_email=notify_email,
                            customer_name=st.session_state.bk_name.strip(),
                            customer_phone=st.session_state.bk_phone.strip(),
                            service=st.session_state.bk_service,
                            stylist=st.session_state.bk_stylist,
                            date=str(st.session_state.bk_date),
                            time=st.session_state.bk_time,
                            salon_name=salon_name,
                        )
                st.session_state.bk_done = True
                st.rerun()
