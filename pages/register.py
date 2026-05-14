"""
Customer self-registration page.
URL: https://<your-app>.streamlit.app/register?salon=B001
"""
import streamlit as st
from datetime import date as dt_date
import uuid, re

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

st.set_page_config(
    page_title="Daftar Ahli — IQSALON",
    page_icon="🌟",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Raleway:wght@300;400;600;700&display=swap');
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
  #MainMenu, footer, header, [data-testid="stSidebarNav"] { visibility:hidden; display:none; }
  .block-container { padding:1.2rem 1.4rem 2.5rem; max-width:560px !important; }

  /* Hero */
  .hero {
    text-align:center; padding:2.2rem 1rem 1.4rem; margin-bottom:1.8rem; border-radius:16px;
    border:1px solid rgba(212,160,48,0.25);
    background:repeating-linear-gradient(90deg,transparent,transparent 28px,rgba(212,160,48,0.03) 28px,rgba(212,160,48,0.03) 29px),
    linear-gradient(158deg,rgba(10,24,14,0.97),rgba(6,14,9,0.90));
    box-shadow:inset 0 1px 0 rgba(212,160,48,0.12), 0 6px 38px rgba(0,0,0,0.55);
  }
  .hero-title {
    font-family:'Cinzel',serif; font-size:2rem; font-weight:600; letter-spacing:7px;
    background:linear-gradient(135deg,#8ecfa0,#d4a030,#f5d470,#d4a030,#6db88a);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
    filter:drop-shadow(0 2px 6px rgba(212,160,48,0.28)); margin:0;
  }
  .hero-sub { font-size:0.68rem; letter-spacing:5px; color:#3a6a4a; margin-top:5px; text-transform:uppercase; font-weight:600; }
  .hero-badge {
    display:inline-block; margin-top:10px;
    background:linear-gradient(135deg,rgba(212,160,48,0.15),rgba(212,160,48,0.05));
    border:1px solid rgba(212,160,48,0.3); border-radius:20px;
    padding:4px 16px; font-size:0.72rem; color:#d4a030; letter-spacing:2px;
  }

  /* Form section labels */
  .section-label {
    font-family:'Cinzel',serif; font-size:0.82rem; color:#d4a030;
    letter-spacing:2px; margin:1.4rem 0 0.5rem; text-transform:uppercase;
  }

  /* Tier preview cards */
  .tier-row {
    display:flex; gap:8px; margin:12px 0;
  }
  .tier-card {
    flex:1; text-align:center; border-radius:10px; padding:10px 6px;
    border:1px solid; font-size:0.72rem; letter-spacing:1px;
  }
  .tier-icon { font-size:1.4rem; }
  .tier-name { font-weight:700; margin:4px 0 2px; }
  .tier-pts  { font-size:0.65rem; opacity:0.7; }

  /* Inputs */
  .stTextInput>div>div>input, .stSelectbox>div>div, .stTextArea>div>div>textarea {
    background:rgba(8,20,12,0.95) !important; border:1px solid rgba(212,160,48,0.28) !important;
    border-radius:9px !important; color:#f2ede3 !important; font-size:16px !important; min-height:44px !important;
  }
  .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
    border-color:#d4a030 !important; box-shadow:0 0 0 2px rgba(212,160,48,0.18) !important;
  }
  .stTextInput>div>div>input::placeholder, .stTextArea>div>div>textarea::placeholder {
    color:#3a5a42 !important; opacity:1 !important;
  }
  label { color:#90c090 !important; font-size:0.85rem !important; letter-spacing:0.8px; }
  .stMarkdown p { color:#90c090 !important; font-size:0.85rem; }

  /* Date input */
  .stDateInput>div>div>input {
    background:rgba(8,20,12,0.95) !important; border:1px solid rgba(212,160,48,0.28) !important;
    color:#f2ede3 !important; border-radius:9px !important; min-height:44px !important; font-size:16px !important;
  }

  /* Checkbox */
  .stCheckbox label { color:#a0c0a0 !important; font-size:0.85rem !important; }

  /* Register button */
  .stButton>button {
    background:linear-gradient(135deg,#2a7a50,#1a5a3a,#d4a030); color:#f2ede3;
    font-family:'Cinzel',serif; font-weight:600; font-size:0.9rem; letter-spacing:3px;
    text-transform:uppercase; border:none; border-radius:10px; padding:1rem 2rem;
    min-height:52px; transition:all .25s; width:100%;
  }
  .stButton>button:hover {
    background:linear-gradient(135deg,#d4a030,#2a7a50); transform:translateY(-2px);
    box-shadow:0 6px 24px rgba(212,160,48,0.35);
  }

  /* Success */
  .success-wrap { text-align:center; padding:2rem 1rem; }
  .success-icon { font-size:4rem; margin-bottom:0.8rem; }
  .success-title { font-family:'Cinzel',serif; font-size:1.6rem; color:#d4a030; letter-spacing:3px; }
  .success-id {
    display:inline-block; margin:14px auto;
    background:rgba(212,160,48,0.12); border:1px solid rgba(212,160,48,0.3);
    border-radius:10px; padding:10px 24px;
    font-family:'Cinzel',serif; font-size:1.3rem; color:#f2ede3; letter-spacing:4px;
  }
  .success-msg { color:#5a8a6a; font-size:0.88rem; line-height:1.7; margin-top:8px; }

  /* Error / info */
  .alert-warn { background:rgba(40,18,5,0.9); border-left:4px solid #e67e22;
    border-radius:9px; padding:0.9rem 1.2rem; margin-bottom:1rem; color:#f5c88a; }
  .alert-dup  { background:rgba(40,5,5,0.9); border-left:4px solid #e74c3c;
    border-radius:9px; padding:0.9rem 1.2rem; margin-bottom:1rem; color:#f5a8a8; }

  /* Selectbox */
  .stSelectbox [data-baseweb="select"]>div { background:rgba(8,20,12,0.95) !important; border-color:rgba(212,160,48,0.35) !important; }
  .stSelectbox svg { fill:#d4a030 !important; }

  hr { border:none; border-top:1px solid rgba(212,160,48,0.15); margin:1.2rem 0; }
  ::-webkit-scrollbar { width:4px; } ::-webkit-scrollbar-track { background:#060e09; }
  ::-webkit-scrollbar-thumb { background:#1a4a28; border-radius:3px; }

  @media(max-width:480px){
    .hero-title { font-size:1.4rem !important; letter-spacing:4px !important; }
    .tier-row { flex-direction:column; }
    .block-container { padding:0.6rem 0.6rem 1.2rem !important; }
  }
</style>
""", unsafe_allow_html=True)

# ── Language setup ────────────────────────────────────────────────────────────
params   = st.query_params
salon_id = params.get("salon", "")
lang_p   = params.get("lang", "zh")
if "reg_lang" not in st.session_state:
    st.session_state.reg_lang = lang_p
L = st.session_state.reg_lang

T = {
    "zh": {
        "sub":          "MEMBER REGISTRATION",
        "join_as":      "成为会员",
        "tagline":      "享受专属积分与会员优惠",
        "sec_basic":    "① 基本资料",
        "sec_contact":  "② 联系方式",
        "sec_extra":    "③ 其他资料",
        "name":         "姓名 *",
        "name_ph":      "请输入您的姓名",
        "gender":       "性别",
        "gender_opts":  ["不填", "女士", "先生", "其他"],
        "phone":        "手机号码 *",
        "phone_ph":     "例：011-1234 5678",
        "email":        "电子邮件",
        "email_ph":     "例：name@gmail.com",
        "dob":          "生日",
        "dob_help":     "生日当月可享专属优惠",
        "notes":        "备注",
        "notes_ph":     "过敏史、发质特点等（选填）",
        "agree":        "我同意授权此发廊使用我的资料以提供服务",
        "register":     "立即注册",
        "name_req":     "⚠ 请填写姓名",
        "phone_req":    "⚠ 请填写手机号码",
        "agree_req":    "⚠ 请勾选同意条款",
        "dup_phone":    "⚠ 此手机号码已注册，请直接告知发廊更新资料",
        "success_title":"注册成功！",
        "success_msg":  "欢迎加入我们的会员计划\n请出示此会员编号给发型师",
        "register_again":"再次注册",
        "tier_title":   "会员等级",
        "tier_sub":     "消费越多，等级越高，折扣越大",
        "invalid":      "无效链接",
        "invalid_msg":  "请向发廊索取正确的注册链接。",
        "lang_zh":      "🇨🇳 简体",
        "lang_en":      "🇬🇧 EN",
    },
    "en": {
        "sub":          "MEMBER REGISTRATION",
        "join_as":      "Join As Member",
        "tagline":      "Earn points and enjoy exclusive member benefits",
        "sec_basic":    "① Basic Info",
        "sec_contact":  "② Contact",
        "sec_extra":    "③ Additional Info",
        "name":         "Full Name *",
        "name_ph":      "Enter your full name",
        "gender":       "Gender",
        "gender_opts":  ["Prefer not to say", "Female", "Male", "Other"],
        "phone":        "Phone Number *",
        "phone_ph":     "e.g. 011-1234 5678",
        "email":        "Email Address",
        "email_ph":     "e.g. name@gmail.com",
        "dob":          "Date of Birth",
        "dob_help":     "Enjoy special birthday month perks",
        "notes":        "Notes",
        "notes_ph":     "Allergies, hair type, preferences (optional)",
        "agree":        "I consent to this salon using my details to provide services",
        "register":     "Register Now",
        "name_req":     "⚠ Please enter your name",
        "phone_req":    "⚠ Please enter your phone number",
        "agree_req":    "⚠ Please accept the terms",
        "dup_phone":    "⚠ This phone number is already registered. Please inform the salon to update your details.",
        "success_title":"Registration Successful!",
        "success_msg":  "Welcome to our membership programme!\nPlease show this Member ID to your stylist.",
        "register_again":"Register Again",
        "tier_title":   "Membership Tiers",
        "tier_sub":     "More visits = higher tier = bigger discounts",
        "invalid":      "Invalid Link",
        "invalid_msg":  "Please obtain the correct registration link from the salon.",
        "lang_zh":      "🇨🇳 简体",
        "lang_en":      "🇬🇧 EN",
    },
}

def t(k): return T[L].get(k, k)

# ── Validate salon ────────────────────────────────────────────────────────────
salon_name = salon_id
salon_valid = False
if salon_id and _USE_DB:
    try:
        res = _sb().table("salons").select("name").eq("id", salon_id).execute()
        if res.data:
            salon_name  = res.data[0]["name"]
            salon_valid = True
    except Exception:
        pass
elif salon_id and not _USE_DB:
    salon_valid = True   # local mode: accept any salon_id

# ── Hero + lang toggle ────────────────────────────────────────────────────────
col_h, col_l = st.columns([5, 1])
with col_h:
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">❋ {salon_name.upper() if salon_valid else "IQ SALON"} ❋</div>
      <div class="hero-sub">{t('sub')}</div>
      <div class="hero-badge">🌟 {t('join_as')}</div>
    </div>
    """, unsafe_allow_html=True)
with col_l:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    _lang_opts = ["zh","en"]
    _lang_disp = {"zh": t("lang_zh"), "en": t("lang_en")}
    _sel = st.selectbox("lang", options=_lang_opts,
                        index=_lang_opts.index(L),
                        format_func=lambda x: _lang_disp[x],
                        key="reg_lang_sel", label_visibility="collapsed")
    if _sel != L:
        st.session_state.reg_lang = _sel
        st.rerun()

# ── Invalid salon ─────────────────────────────────────────────────────────────
if not salon_valid:
    st.markdown(f'<div class="alert-dup"><b>{t("invalid")}</b><br>{t("invalid_msg")}</div>',
                unsafe_allow_html=True)
    st.stop()

# ── Success state ─────────────────────────────────────────────────────────────
if st.session_state.get("reg_done"):
    mem_id = st.session_state.get("reg_mem_id","—")
    mem_nm = st.session_state.get("reg_mem_name","")
    st.markdown(f"""
    <div class="success-wrap">
      <div class="success-icon">🌟</div>
      <div class="success-title">{t('success_title')}</div>
      <div class="success-id">#{mem_id}</div>
      <div class="success-msg">{t('success_msg').replace(chr(10),'<br>')}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"<hr>", unsafe_allow_html=True)
    if st.button("🔄 " + t("register_again"), key="reg_again"):
        for k in ["reg_done","reg_mem_id","reg_mem_name"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.stop()

# ── Membership tier info ──────────────────────────────────────────────────────
TIERS = [
    {"icon":"⭐","name":"普通" if L=="zh" else "Regular", "pts":"0 pts","color":"#5a8a6a","bg":"rgba(90,138,106,0.1)"},
    {"icon":"💎","name":"银卡" if L=="zh" else "Silver",  "pts":"500 pts","color":"#aaa","bg":"rgba(170,170,170,0.1)"},
    {"icon":"👑","name":"金卡" if L=="zh" else "Gold",    "pts":"1500 pts","color":"#d4a030","bg":"rgba(212,160,48,0.12)"},
    {"icon":"💠","name":"VIP", "pts":"3000 pts","color":"#a0c8ff","bg":"rgba(160,200,255,0.12)"},
]
with st.expander(f"🌟 {t('tier_title')} — {t('tier_sub')}", expanded=False):
    cols_t = st.columns(4)
    for ci, tier in enumerate(TIERS):
        cols_t[ci].markdown(
            f"<div class='tier-card' style='border-color:{tier['color']}44;background:{tier['bg']};color:{tier['color']};'>"
            f"<div class='tier-icon'>{tier['icon']}</div>"
            f"<div class='tier-name'>{tier['name']}</div>"
            f"<div class='tier-pts'>{tier['pts']}</div></div>",
            unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Registration form ─────────────────────────────────────────────────────────
st.markdown(f'<p class="section-label">{t("sec_basic")}</p>', unsafe_allow_html=True)
fc1, fc2 = st.columns([3, 2])
with fc1:
    reg_name = st.text_input(t("name"), placeholder=t("name_ph"), key="reg_name")
with fc2:
    reg_gender = st.selectbox(t("gender"), t("gender_opts"), key="reg_gender")

st.markdown(f'<p class="section-label">{t("sec_contact")}</p>', unsafe_allow_html=True)
pc1, pc2 = st.columns(2)
with pc1:
    reg_phone = st.text_input(t("phone"), placeholder=t("phone_ph"), key="reg_phone")
with pc2:
    reg_email = st.text_input(t("email"), placeholder=t("email_ph"), key="reg_email")

st.markdown(f'<p class="section-label">{t("sec_extra")}</p>', unsafe_allow_html=True)
dc1, dc2 = st.columns([2, 3])
with dc1:
    reg_dob = st.date_input(t("dob"), value=None, min_value=dt_date(1940,1,1),
                             max_value=dt_date.today(), key="reg_dob",
                             help=t("dob_help"))
with dc2:
    reg_notes = st.text_area(t("notes"), placeholder=t("notes_ph"), key="reg_notes", height=90)

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
reg_agree = st.checkbox(t("agree"), key="reg_agree")
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Submit ────────────────────────────────────────────────────────────────────
if st.button(f"🌟 {t('register')}", key="reg_submit_btn", type="primary"):
    err = None
    if not reg_name.strip():
        err = t("name_req")
    elif not reg_phone.strip():
        err = t("phone_req")
    elif not reg_agree:
        err = t("agree_req")

    if err:
        st.markdown(f'<div class="alert-warn">{err}</div>', unsafe_allow_html=True)
    else:
        # Check for duplicate phone number
        phone_clean = re.sub(r"[\s\-]", "", reg_phone.strip())
        dup_found = False
        if _USE_DB:
            try:
                dup_res = _sb().table("members").select("id").eq("salon_id", salon_id).eq("phone", phone_clean).execute()
                if dup_res.data:
                    dup_found = True
            except Exception:
                pass

        if dup_found:
            st.markdown(f'<div class="alert-dup">{t("dup_phone")}</div>', unsafe_allow_html=True)
        else:
            mem_id = str(uuid.uuid4())[:8].upper()
            dob_str = str(reg_dob) if reg_dob else ""
            new_mem = {
                "id":          mem_id,
                "salon_id":    salon_id,
                "name":        reg_name.strip(),
                "phone":       phone_clean,
                "email":       reg_email.strip(),
                "birthday":    dob_str,
                "gender":      reg_gender,
                "notes":       reg_notes.strip(),
                "tier":        "普通",
                "points":      0,
                "total_spent": 0.0,
                "visit_count": 0,
                "join_date":   str(dt_date.today()),
            }
            saved = False
            if _USE_DB:
                try:
                    _sb().table("members").insert(new_mem).execute()
                    saved = True
                except Exception as e:
                    st.error(f"注册失败 / Registration failed: {e}")
            else:
                saved = True   # local mode

            if saved:
                st.session_state["reg_done"]     = True
                st.session_state["reg_mem_id"]   = mem_id
                st.session_state["reg_mem_name"] = reg_name.strip()
                st.rerun()
