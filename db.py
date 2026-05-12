"""
Supabase database layer for Signature Kim SaaS.
All reads/writes go through this module.
"""
import streamlit as st
from supabase import create_client, Client

# ── Client singleton ──────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def _sb() -> Client:
    return get_supabase()


# ═════════════════════════════════════════════════════════════════════════════
# SESSION TOKENS  (persistent login via URL query param)
# ═════════════════════════════════════════════════════════════════════════════

def db_create_session(username: str) -> str:
    """Create a new session token for the user, return the token string."""
    import secrets, datetime
    token = secrets.token_urlsafe(32)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()
    _sb().table("sessions").insert({
        "token": token, "username": username, "expires_at": expires
    }).execute()
    return token


def db_get_session(token: str) -> str:
    """Return username if token is valid and not expired, else empty string."""
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    res = _sb().table("sessions").select("username, expires_at")\
               .eq("token", token)\
               .gt("expires_at", now)\
               .execute()
    if res.data:
        return res.data[0]["username"]
    return ""


def db_delete_session(token: str):
    """Delete a specific session (logout)."""
    _sb().table("sessions").delete().eq("token", token).execute()


def db_cleanup_sessions():
    """Remove expired sessions (maintenance, optional)."""
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    _sb().table("sessions").delete().lt("expires_at", now).execute()


# ═════════════════════════════════════════════════════════════════════════════
# AUTH
# ═════════════════════════════════════════════════════════════════════════════

def db_login(username: str, password_hash: str):
    """Return account dict if credentials match, else None."""
    res = _sb().table("accounts")\
               .select("*")\
               .eq("username", username)\
               .eq("password_hash", password_hash)\
               .execute()
    return res.data[0] if res.data else None


def db_get_accounts(salon_id: str = None):
    """Return all accounts (optionally filtered by salon_id or 'all')."""
    q = _sb().table("accounts").select("*")
    if salon_id and salon_id != "all":
        q = q.or_(f"salon_id.eq.{salon_id},role.eq.owner")
    return q.execute().data or []


def db_add_account(username, password_hash, role, salon_id, display_name):
    _sb().table("accounts").insert({
        "username":      username,
        "password_hash": password_hash,
        "role":          role,
        "salon_id":      salon_id,
        "display_name":  display_name,
    }).execute()


def db_update_account(username: str, updates: dict):
    """Update account fields (role, salon_id, display_name)."""
    allowed = {"role", "salon_id", "display_name"}
    payload = {k: v for k, v in updates.items() if k in allowed}
    if payload:
        _sb().table("accounts").update(payload).eq("username", username).execute()


def db_delete_account(username: str):
    _sb().table("accounts").delete().eq("username", username).execute()


def db_update_password(username: str, new_hash: str):
    _sb().table("accounts").update({"password_hash": new_hash})\
         .eq("username", username).execute()


# ═════════════════════════════════════════════════════════════════════════════
# SALONS / BRANCHES
# ═════════════════════════════════════════════════════════════════════════════

def db_get_salons():
    """Return list of salon dicts {id, name}."""
    return _sb().table("salons").select("*").execute().data or []


def db_add_salon(salon_id: str, name: str):
    _sb().table("salons").insert({"id": salon_id, "name": name}).execute()
    # Seed default inventory for the new salon
    db_seed_inventory(salon_id)


def db_delete_salon(salon_id: str):
    _sb().table("salons").delete().eq("id", salon_id).execute()


def db_get_salon_info(salon_id: str) -> dict:
    """Return full salon row including subscription info."""
    res = _sb().table("salons").select("*").eq("id", salon_id).execute()
    return res.data[0] if res.data else {}


def db_update_salon_subscription(salon_id: str, plan: str, plan_ends: str,
                                  stripe_link: str = ""):
    """Set subscription plan and expiry for a salon."""
    _sb().table("salons").update({
        "plan":        plan,
        "plan_ends":   plan_ends,
        "stripe_link": stripe_link,
    }).eq("id", salon_id).execute()


def db_activate_trial(salon_id: str, days: int = 30):
    """Start/reset trial period for a salon."""
    import datetime
    ends = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    _sb().table("salons").update({
        "plan": "trial", "trial_ends": ends, "plan_ends": None
    }).eq("id", salon_id).execute()


def db_update_salon_contact(salon_id: str, name: str, phone: str, email: str):
    _sb().table("salons").update({
        "contact_name": name, "contact_phone": phone, "contact_email": email
    }).eq("id", salon_id).execute()


def db_update_salon_profile(salon_id: str, profile: dict):
    """Save full salon profile (address, ssm_no, hours, website, tin, msic_code, etc.)."""
    allowed = {"contact_name", "contact_phone", "contact_email",
               "address", "city", "postcode", "ssm_no",
               "operating_hours", "website",
               "tin", "msic_code", "state_code"}
    payload = {k: v for k, v in profile.items() if k in allowed}
    if payload:
        _sb().table("salons").update(payload).eq("id", salon_id).execute()


# ═════════════════════════════════════════════════════════════════════════════
# SERVICES
# ═════════════════════════════════════════════════════════════════════════════

def db_get_services(salon_id: str):
    """Return list of {name, price} dicts for the salon, ordered by sort_order."""
    res = _sb().table("services").select("name,price,sort_order") \
               .eq("salon_id", salon_id).order("sort_order").execute()
    return [{"name": r["name"], "price": float(r.get("price") or 0)} for r in (res.data or [])]


def db_set_services(salon_id: str, services: list):
    """Replace service list for a salon. services = [{name, price}, ...]"""
    _sb().table("services").delete().eq("salon_id", salon_id).execute()
    if services:
        _sb().table("services").insert([
            {"salon_id": salon_id, "name": s["name"], "price": float(s.get("price", 0)),
             "sort_order": i}
            for i, s in enumerate(services)
        ]).execute()


# ═════════════════════════════════════════════════════════════════════════════
# STYLISTS
# ═════════════════════════════════════════════════════════════════════════════

def db_get_stylists(salon_id: str):
    res = _sb().table("stylists").select("name").eq("salon_id", salon_id).execute()
    return [r["name"] for r in (res.data or [])]


def db_set_stylists(salon_id: str, names: list):
    """Replace stylist list for a salon."""
    _sb().table("stylists").delete().eq("salon_id", salon_id).execute()
    if names:
        _sb().table("stylists").insert(
            [{"salon_id": salon_id, "name": n} for n in names]
        ).execute()


# ═════════════════════════════════════════════════════════════════════════════
# COMMISSIONS
# ═════════════════════════════════════════════════════════════════════════════

def db_get_commissions(salon_id: str) -> dict:
    """Return nested dict {stylist: {service: rate}}."""
    res = _sb().table("commissions").select("*").eq("salon_id", salon_id).execute()
    result = {}
    for row in (res.data or []):
        st_name = row["stylist"]
        svc     = row["service"]
        rate    = float(row.get("rate") or 0)
        result.setdefault(st_name, {})[svc] = rate
    return result


def db_set_commission(salon_id: str, stylist: str, service: str, rate: float):
    """Upsert a single commission rate."""
    _sb().table("commissions").upsert({
        "salon_id": salon_id,
        "stylist":  stylist,
        "service":  service,
        "rate":     rate,
    }, on_conflict="salon_id,stylist,service").execute()


def db_save_commissions(salon_id: str, rates: dict):
    """Save all commission rates for a salon (rates = {stylist: {service: rate}})."""
    rows = []
    for stylist, svcs in rates.items():
        for svc, rate in svcs.items():
            rows.append({"salon_id": salon_id, "stylist": stylist,
                         "service": svc, "rate": float(rate)})
    _sb().table("commissions").delete().eq("salon_id", salon_id).execute()
    if rows:
        _sb().table("commissions").insert(rows).execute()


# ═════════════════════════════════════════════════════════════════════════════
# BOOKINGS
# ═════════════════════════════════════════════════════════════════════════════

def db_get_bookings(salon_id: str):
    res = _sb().table("bookings").select(
        "id,name,phone,email,date,time,stylist,service,note,"
        "price,paid,method,final,source,status,created_at"
    ).eq("salon_id", salon_id)\
     .order("date").order("time").execute()
    return res.data or []


def db_add_booking(salon_id: str, bk: dict):
    payload = {k: v for k, v in bk.items() if k != "id"}
    payload["salon_id"] = salon_id
    res = _sb().table("bookings").insert(payload).execute()
    return res.data[0] if res.data else None


def db_update_booking(booking_id: str, updates: dict):
    _sb().table("bookings").update(updates).eq("id", booking_id).execute()


def db_delete_booking(booking_id: str):
    _sb().table("bookings").delete().eq("id", booking_id).execute()


def db_confirm_booking(booking_id: str):
    _sb().table("bookings").update({"status": "confirmed"})\
         .eq("id", booking_id).execute()


def db_cancel_booking(booking_id: str):
    _sb().table("bookings").update({"status": "cancelled"})\
         .eq("id", booking_id).execute()


def db_get_pending_count(salon_id: str) -> int:
    res = _sb().table("bookings").select("id", count="exact")\
               .eq("salon_id", salon_id)\
               .eq("source", "online")\
               .eq("status", "pending").execute()
    return res.count or 0


def db_save_all_bookings(salon_id: str, bookings: list):
    """Overwrite all bookings for salon (used after data_editor save)."""
    _sb().table("bookings").delete().eq("salon_id", salon_id).execute()
    if bookings:
        for bk in bookings:
            payload = {k: v for k, v in bk.items() if k != "id"}
            payload["salon_id"] = salon_id
            _sb().table("bookings").insert(payload).execute()


# ═════════════════════════════════════════════════════════════════════════════
# WALK-INS
# ═════════════════════════════════════════════════════════════════════════════

def db_get_walkins(salon_id: str):
    res = _sb().table("walkins").select("*")\
               .eq("salon_id", salon_id)\
               .order("created_at").execute()
    return res.data or []


def db_add_walkin(salon_id: str, w: dict):
    payload = {k: v for k, v in w.items() if k != "id"}
    payload["salon_id"] = salon_id
    _sb().table("walkins").insert(payload).execute()


def db_delete_walkin(walkin_id: str):
    _sb().table("walkins").delete().eq("id", walkin_id).execute()


# ═════════════════════════════════════════════════════════════════════════════
# INVENTORY
# ═════════════════════════════════════════════════════════════════════════════

def db_get_inventory(salon_id: str):
    res = _sb().table("inventory").select("*").eq("salon_id", salon_id).execute()
    return res.data or []


def db_save_all_inventory(salon_id: str, items: list):
    """Overwrite entire inventory for salon."""
    _sb().table("inventory").delete().eq("salon_id", salon_id).execute()
    if items:
        for item in items:
            payload = {k: v for k, v in item.items() if k != "id"}
            payload["salon_id"] = salon_id
            _sb().table("inventory").insert(payload).execute()


def db_seed_inventory(salon_id: str):
    default = [
        {"name": "OSiS+ Dust It",        "category": "造型品",   "qty": 14, "max": 30, "unit": "瓶"},
        {"name": "OSiS+ Freeze",          "category": "定型喷雾", "qty": 7,  "max": 24, "unit": "瓶"},
        {"name": "Schwarzkopf IGORA",     "category": "染发剂",  "qty": 22, "max": 50, "unit": "管"},
        {"name": "Fibre Clinix 蛋白护理", "category": "护发品",  "qty": 5,  "max": 20, "unit": "瓶"},
        {"name": "BLONDME 漂发粉",        "category": "漂发",    "qty": 9,  "max": 25, "unit": "盒"},
    ]
    for item in default:
        item["salon_id"] = salon_id
    _sb().table("inventory").insert(default).execute()


# ═════════════════════════════════════════════════════════════════════════════
# MEMBERS
# ═════════════════════════════════════════════════════════════════════════════

def db_get_members(salon_id: str):
    res = _sb().table("members").select("*, member_history(*)").eq("salon_id", salon_id).execute()
    members = []
    for m in (res.data or []):
        hist = m.pop("member_history", []) or []
        m["history"] = hist
        members.append(m)
    return members


def db_add_member(salon_id: str, member: dict):
    payload = {k: v for k, v in member.items() if k not in ("id", "history")}
    payload["salon_id"] = salon_id
    payload["id"]       = member["id"]
    _sb().table("members").insert(payload).execute()


def db_update_member(member_id: str, updates: dict):
    safe = {k: v for k, v in updates.items() if k not in ("id", "salon_id", "history")}
    if safe:
        _sb().table("members").update(safe).eq("id", member_id).execute()


def db_add_member_history(member_id: str, entry: dict):
    payload = dict(entry)
    payload["member_id"] = member_id
    _sb().table("member_history").insert(payload).execute()


def db_delete_member(member_id: str):
    _sb().table("members").delete().eq("id", member_id).execute()


# ═════════════════════════════════════════════════════════════════════════════
# LOAD ALL — call once on login
# ═════════════════════════════════════════════════════════════════════════════

def db_load_salon(salon_id: str) -> dict:
    """Load all data for a salon into a dict."""
    return {
        "stylists":    db_get_stylists(salon_id),
        "services":    db_get_services(salon_id),
        "bookings":    db_get_bookings(salon_id),
        "walkins":     db_get_walkins(salon_id),
        "inventory":   db_get_inventory(salon_id),
        "members":     db_get_members(salon_id),
        "commissions": db_get_commissions(salon_id),
    }


def db_load_branches_and_accounts():
    """Load salons + accounts into session state (called on login)."""
    salons  = db_get_salons()
    st.session_state.branches     = {s["id"]: s["name"] for s in salons}
    st.session_state.salon_info   = {s["id"]: s for s in salons}
    accts   = db_get_accounts()
    st.session_state.accounts = {
        a["username"]: {
            "hash":   a["password_hash"],
            "role":   a["role"],
            "branch": a["salon_id"] or "all",
            "name":   a["display_name"] or a["username"],
        }
        for a in accts
    }
