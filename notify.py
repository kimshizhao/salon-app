"""
Notification module for Signature Kim SaaS.
Handles email (Gmail SMTP) and WhatsApp (wa.me) notifications.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import streamlit as st
    def _get_secret(key, default=""):
        return st.secrets.get(key, default)
except Exception:
    def _get_secret(key, default=""):
        return default


# ── Helpers ───────────────────────────────────────────────────────────────────

def email_configured() -> bool:
    return bool(_get_secret("GMAIL_USER") and _get_secret("GMAIL_APP_PASSWORD"))


def whatsapp_link(phone: str, message: str) -> str:
    """Generate a wa.me click-to-send link."""
    # Clean phone number: keep digits only, add MY country code if needed
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0"):
        digits = "60" + digits[1:]   # 012-xxx → 6012-xxx
    elif not digits.startswith("60"):
        digits = "60" + digits
    import urllib.parse
    return f"https://wa.me/{digits}?text={urllib.parse.quote(message)}"


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via Gmail SMTP. Returns True on success."""
    user = _get_secret("GMAIL_USER")
    pwd  = _get_secret("GMAIL_APP_PASSWORD")
    if not user or not pwd or not to:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Signature Kim <{user}>"
        msg["To"]      = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
        return True
    except Exception:
        return False


# ── Email Templates ───────────────────────────────────────────────────────────

def _base_template(content: str, salon_name: str = "Signature Kim") -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{margin:0;padding:0;background:#0a0a0a;font-family:'Helvetica Neue',Arial,sans-serif;color:#f0ece0}}
  .wrapper{{max-width:520px;margin:0 auto;padding:20px}}
  .header{{text-align:center;padding:32px 20px 20px;border-bottom:1px solid #c9a84c44}}
  .title{{font-size:24px;font-weight:700;letter-spacing:6px;
    background:linear-gradient(135deg,#c9a84c,#f5e19a,#c9a84c);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;margin:0}}
  .sub{{font-size:11px;letter-spacing:4px;color:#888;margin-top:6px;text-transform:uppercase}}
  .body{{padding:28px 20px}}
  .row{{display:flex;justify-content:space-between;padding:10px 0;
    border-bottom:1px solid #1a1a1a;font-size:14px}}
  .label{{color:#888}}
  .val{{color:#f0ece0;font-weight:600}}
  .price{{color:#c9a84c;font-size:18px;font-weight:700}}
  .box{{background:#111;border:1px solid #c9a84c33;border-radius:12px;
    padding:16px 20px;margin:20px 0}}
  .badge{{display:inline-block;padding:6px 16px;border-radius:20px;
    font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase}}
  .badge-pending{{background:#2b1a0d;color:#e67e22;border:1px solid #e67e22}}
  .badge-confirmed{{background:#0d2b1a;color:#2ecc71;border:1px solid #2ecc71}}
  .footer{{text-align:center;padding:20px;font-size:11px;color:#555;
    border-top:1px solid #1a1a1a;margin-top:10px}}
  .cta{{display:block;text-align:center;background:linear-gradient(135deg,#c9a84c,#a07830);
    color:#0a0a0a;font-weight:700;font-size:13px;letter-spacing:2px;text-transform:uppercase;
    padding:14px 28px;border-radius:8px;text-decoration:none;margin:20px 0}}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="title">✦ {salon_name.upper()} ✦</div>
    <div class="sub">Management System</div>
  </div>
  <div class="body">{content}</div>
  <div class="footer">
    © {salon_name} · Powered by Signature Kim SaaS<br>
    <span style="color:#333">Please do not reply to this email</span>
  </div>
</div>
</body>
</html>"""


def send_booking_received(
    to_email: str, customer_name: str, service: str, stylist: str,
    date: str, time: str, price: float, salon_name: str, salon_phone: str = ""
) -> bool:
    """Email to customer: booking request received, pending confirmation."""
    stylist_str = stylist if stylist else "Any Stylist / 不指定"
    phone_row = f'<div class="row"><span class="label">髮廊電話 / Salon Phone</span><span class="val">{salon_phone}</span></div>' if salon_phone else ""
    content = f"""
    <p style="font-size:16px;color:#c9a84c;font-weight:600">親愛的 {customer_name} / Dear {customer_name},</p>
    <p style="color:#aaa;font-size:14px;line-height:1.7">
      我們已收到您的預約申請！髮廊將盡快與您確認。<br>
      We have received your booking request! Our team will contact you to confirm shortly.
    </p>
    <div class="box">
      <div style="text-align:center;margin-bottom:14px">
        <span class="badge badge-pending">⏳ Pending Confirmation / 待確認</span>
      </div>
      <div class="row"><span class="label">服務 / Service</span><span class="val">{service}</span></div>
      <div class="row"><span class="label">髮型師 / Stylist</span><span class="val">{stylist_str}</span></div>
      <div class="row"><span class="label">日期 / Date</span><span class="val">{date}</span></div>
      <div class="row"><span class="label">時間 / Time</span><span class="val">{time}</span></div>
      {phone_row}
      <div class="row" style="border:none">
        <span class="label">預估費用 / Est. Price</span>
        <span class="price">RM {price}</span>
      </div>
    </div>
    <p style="color:#888;font-size:13px;line-height:1.7">
      ⚡ 請保持電話暢通，我們將盡快聯絡您確認時間。<br>
      Please keep your phone available. We will contact you to confirm.
    </p>"""
    return _send_email(
        to_email,
        f"[{salon_name}] 預約申請已收到 / Booking Request Received",
        _base_template(content, salon_name)
    )


def send_booking_confirmed(
    to_email: str, customer_name: str, service: str, stylist: str,
    date: str, time: str, price: float, salon_name: str, salon_phone: str = "",
    salon_address: str = ""
) -> bool:
    """Email to customer: booking confirmed by salon."""
    stylist_str = stylist if stylist else "Any Stylist / 不指定"
    phone_row = f'<div class="row"><span class="label">髮廊電話 / Phone</span><span class="val">{salon_phone}</span></div>' if salon_phone else ""
    addr_row  = f'<div class="row"><span class="label">地址 / Address</span><span class="val">{salon_address}</span></div>' if salon_address else ""
    content = f"""
    <p style="font-size:16px;color:#c9a84c;font-weight:600">親愛的 {customer_name} / Dear {customer_name},</p>
    <p style="color:#aaa;font-size:14px;line-height:1.7">
      您的預約已確認！我們期待您的到來。<br>
      Your appointment has been confirmed! We look forward to seeing you.
    </p>
    <div class="box">
      <div style="text-align:center;margin-bottom:14px">
        <span class="badge badge-confirmed">✅ Confirmed / 已確認</span>
      </div>
      <div class="row"><span class="label">服務 / Service</span><span class="val">{service}</span></div>
      <div class="row"><span class="label">髮型師 / Stylist</span><span class="val">{stylist_str}</span></div>
      <div class="row"><span class="label">日期 / Date</span><span class="val">{date}</span></div>
      <div class="row"><span class="label">時間 / Time</span><span class="val">{time}</span></div>
      {phone_row}
      {addr_row}
      <div class="row" style="border:none">
        <span class="label">預估費用 / Est. Price</span>
        <span class="price">RM {price}</span>
      </div>
    </div>
    <p style="color:#888;font-size:13px;line-height:1.7">
      如需更改或取消預約，請聯絡髮廊。<br>
      To reschedule or cancel, please contact the salon directly.
    </p>"""
    return _send_email(
        to_email,
        f"[{salon_name}] ✅ 預約已確認 / Appointment Confirmed",
        _base_template(content, salon_name)
    )


def send_salon_new_booking_alert(
    to_email: str, customer_name: str, customer_phone: str,
    service: str, stylist: str, date: str, time: str,
    salon_name: str
) -> bool:
    """Email alert to salon owner/manager: new online booking received."""
    stylist_str = stylist if stylist else "不指定 / Any"
    content = f"""
    <p style="font-size:16px;color:#e67e22;font-weight:600">🌐 新網上預約 / New Online Booking</p>
    <div class="box">
      <div class="row"><span class="label">客戶 / Client</span><span class="val">{customer_name}</span></div>
      <div class="row"><span class="label">電話 / Phone</span><span class="val">{customer_phone}</span></div>
      <div class="row"><span class="label">服務 / Service</span><span class="val">{service}</span></div>
      <div class="row"><span class="label">髮型師 / Stylist</span><span class="val">{stylist_str}</span></div>
      <div class="row"><span class="label">日期 / Date</span><span class="val">{date}</span></div>
      <div class="row" style="border:none"><span class="label">時間 / Time</span><span class="val">{time}</span></div>
    </div>
    <p style="color:#aaa;font-size:13px">
      請登入管理系統確認或拒絕此預約。<br>
      Please log in to the management system to confirm or decline.
    </p>"""
    return _send_email(
        to_email,
        f"[{salon_name}] 🌐 新網上預約 — {customer_name}",
        _base_template(content, salon_name)
    )


# ── WhatsApp message templates ────────────────────────────────────────────────

def wa_booking_confirmed_msg(
    customer_name: str, service: str, stylist: str,
    date: str, time: str, salon_name: str
) -> str:
    stylist_str = stylist if stylist else "不指定"
    return (
        f"✦ {salon_name} ✦\n\n"
        f"您好 {customer_name}！\n"
        f"您的預約已確認 ✅\n\n"
        f"📋 服務：{service}\n"
        f"💇 髮型師：{stylist_str}\n"
        f"📅 日期：{date}\n"
        f"⏰ 時間：{time}\n\n"
        f"期待您的光臨！如需更改請回覆此訊息。"
    )


def wa_booking_reminder_msg(
    customer_name: str, service: str, date: str, time: str, salon_name: str
) -> str:
    return (
        f"✦ {salon_name} ✦\n\n"
        f"您好 {customer_name}！\n"
        f"溫馨提醒：您明天的預約 ⏰\n\n"
        f"📋 服務：{service}\n"
        f"📅 日期：{date}\n"
        f"⏰ 時間：{time}\n\n"
        f"期待明天見到您！"
    )
