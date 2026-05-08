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
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Raleway:wght@300;400;600&display=swap');
  html,body,[class*="css"]{ font-family:'Raleway',sans-serif; background:#0a0a0a; color:#f0ece0; }
  .stApp { background:#0a0a0a; }
  #MainMenu, footer, header, [data-testid="stSidebarNav"] { visibility:hidden; display:none; }
  .block-container { padding:1.2rem 1.4rem 2rem; max-width:600px !important; }

  .hero { text-align:center; padding:2rem 1rem 1.2rem; border-bottom:1px solid #c9a84c44; margin-bottom:1.6rem; }
  .hero-title { font-family:'Playfair Display',serif; font-size:2.4rem; font-weight:700; letter-spacing:6px;
    background:linear-gradient(135deg,#c9a84c,#f5e19a,#c9a84c);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; margin:0; }
  .hero-sub { font-size:0.75rem; letter-spacing:4px; color:#888; margin-top:0.3rem; }
  .hero-branch { font-size:0.85rem; color:#c9a84c99; margin-top:0.5rem; letter-spacing:2px; }

  .step-label { font-family:'Playfair Display',serif; font-size:1rem; color:#c9a84c;
    letter-spacing:2px; margin:1.4rem 0 0.5rem; }
  .svc-card { background:#111; border:1px solid #c9a84c33; border-radius:12px;
    padding:0.9rem 1.2rem; margin-bottom:0.5rem; cursor:pointer; transition:all .2s; display:flex;
    justify-content:space-between; align-items:center; }
  .svc-card:hover { border-color:#c9a84c99; }
  .svc-card.selected { border-color:#c9a84c; background:#1a1500; }
  .svc-name { font-size:0.95rem; color:#f0ece0; }
  .svc-price { font-family:'Playfair Display',serif; font-size:1.1rem; color:#c9a84c; }

  .slot-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:1rem; }
  .slot { background:#111; border:1px solid #c9a84c33; border-radius:8px;
    padding:8px 0; text-align:center; font-size:0.82rem; color:#ccc;
    cursor:pointer; transition:all .2s; }
  .slot:hover { border-color:#c9a84c99; }
  .slot.taken { opacity:0.35; cursor:default; text-decoration:line-through; }
  .slot.selected { background:linear-gradient(135deg,#c9a84c,#a07830); color:#0a0a0a;
    font-weight:700; border-color:#c9a84c; }

  .confirm-box { background:linear-gradient(135deg,#1a1500,#0f0f0f);
    border:1px solid #c9a84c55; border-radius:14px; padding:1.4rem 1.6rem; margin:1rem 0; }
  .confirm-row { display:flex; justify-content:space-between; padding:0.4rem 0;
    border-bottom:1px solid #c9a84c11; font-size:0.88rem; }
  .confirm-label { color:#888; }
  .confirm-val { color:#f0ece0; font-weight:600; }

  .success-icon { font-size:3.5rem; text-align:center; margin:1rem 0; }
  .success-title { font-family:'Playfair Display',serif; font-size:1.6rem; color:#c9a84c;
    text-align:center; letter-spacing:3px; }
  .success-msg { text-align:center; color:#aaa; font-size:0.85rem; margin-top:0.5rem; line-height:1.6; }

  .stTextInput>div>div>input, .stSelectbox>div>div {
    background:#1a1a1a !important; border:1px solid #c9a84c55 !important;
    border-radius:8px !important; color:#f0ece0 !important; font-size:16px !important;
    min-height:44px !important; }
  label, .stMarkdown p { color:#ccb97a !important; font-size:0.85rem; letter-spacing:1px; }
  .stButton>button { background:linear-gradient(135deg,#c9a84c,#a07830); color:#0a0a0a;
    font-family:'Raleway',sans-serif; font-weight:700; font-size:0.85rem; letter-spacing:2px;
    text-transform:uppercase; border:none; border-radius:8px; padding:0.85rem 2rem;
    min-height:48px; transition:all .25s; width:100%; }
  .stButton>button:hover { background:linear-gradient(135deg,#f5e19a,#c9a84c); transform:translateY(-1px); }
  .stDateInput>div>div>input { background:#1a1a1a !important; border:1px solid #c9a84c55 !important;
    color:#f0ece0 !important; border-radius:8px !important; min-height:44px !important; font-size:16px !important; }

  @media(max-width:480px){
    .hero-title{font-size:1.6rem !important;}
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
    "剪髮": 50, "染髮": 180, "頭皮護理": 120,
    "燙髮": 250, "角蛋白護理": 350, "頭皮SPA": 100,
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
        "sub": "MANAGEMENT SYSTEM", "book_title": "線上預約",
        "step_svc": "① 選擇服務", "step_stylist": "② 選擇髮型師",
        "step_date": "③ 選擇日期", "step_time": "④ 選擇時間",
        "step_info": "⑤ 填寫資料",
        "any_stylist": "不指定 (Any Stylist)",
        "your_name": "您的姓名", "your_phone": "手機號碼",
        "step_confirm": "⑥ 確認預約",
        "service": "服務", "stylist": "髮型師",
        "date": "日期", "time": "時間",
        "name": "姓名", "phone": "電話",
        "price_est": "預估費用",
        "submit_btn": "確認預約",
        "success_title": "預約成功！",
        "success_msg": "我們已收到您的預約申請\n髮廊將盡快與您確認時間\n請保持電話暢通",
        "new_booking": "再次預約",
        "taken": "已訂",
        "invalid": "無效的預約連結",
        "invalid_msg": "請聯繫髮廊獲取正確的預約連結。",
        "name_req": "請填寫您的姓名",
        "phone_req": "請填寫手機號碼",
        "svc_req": "請選擇服務",
        "time_req": "請選擇時間",
        "lang_toggle": "English",
        "from": "來自",
        "pending_note": "預約待確認，我們會盡快聯絡您",
        "your_email": "電子郵件（選填）",
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
        "lang_toggle": "中文",
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
      <div class="hero-title">✦ SIGNATURE KIM ✦</div>
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
      <div class="hero-title">✦ SIGNATURE KIM ✦</div>
      <div class="hero-sub">{t('sub')}</div>
      <div class="hero-branch">{salon_name}</div>
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
        "選擇時間 / Select Time", available_slots, index=current_idx,
        key="time_sel"
    )
    st.session_state.bk_time = picked_time
else:
    st.warning("⚠️ 該日期已全部預約，請選擇其他日期 / All slots taken for this date")
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
