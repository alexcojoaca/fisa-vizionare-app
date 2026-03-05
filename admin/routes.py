import os
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone

from flask import render_template, request, redirect, url_for, flash, Response, abort
from flask_login import current_user
from sqlalchemy import or_

from extensions import db
from models import User, UserProfile, UserDevice, BuyerRequest, Announcement, UserAnnouncementRead, SellerOffer

# Blueprint (import din admin/__init__.py)
from . import admin_bp


# -------------------------
# Helpers
# -------------------------

def _utcnow():
    return datetime.now(timezone.utc)


def _is_production() -> bool:
    # Railway seteză de obicei una din astea
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RAILWAY_STATIC_URL")
    )


def _require_local_only():
    """
    Hard gate:
    - In productie: /admin nu exista (404)
    - Local: accepta doar localhost (127.0.0.1 / ::1)
    """
    if _is_production():
        abort(404)

    remote = request.remote_addr
    if remote not in ("127.0.0.1", "::1"):
        abort(403)


def _fmt_dt(dt):
    if not dt:
        return "-"
    try:
        return dt.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(dt)


def _user_access_bucket(u: User) -> str:
    """
    Return: 'paid' | 'expired' | 'blocked' (trial eliminat)
    Preferă metodele tale din model (access_source), altfel fallback.
    """
    # dacă ai deja metoda access_source() în model, o folosim
    if hasattr(u, "access_source"):
        src = u.access_source()
        if src in ("paid", "none", "blocked"):
            return "expired" if src == "none" else src

    # fallback:
    if not getattr(u, "is_active", True):
        return "blocked"

    now = _utcnow()
    paid_ok = bool(u.paid_ends_at and u.paid_ends_at > now)

    if paid_ok:
        return "paid"
    return "expired"


def _access_until_dt(u: User):
    """
    Data până la care are acces (doar paid, trial eliminat). Dacă ai access_until în model, o folosește.
    """
    if hasattr(u, "access_until"):
        try:
            return u.access_until()
        except Exception:
            pass

    # fallback: doar paid
    return u.paid_ends_at if u.paid_ends_at is not None else None


def _days_left(u: User) -> int:
    """
    Zile rămase (rotunjit în sus). 0 dacă expirat/blocked.
    Dacă ai days_left în model, o folosește.
    """
    if hasattr(u, "days_left"):
        try:
            return int(u.days_left())
        except Exception:
            pass

    if not getattr(u, "is_active", True):
        return 0

    until = _access_until_dt(u)
    if not until:
        return 0

    now = _utcnow()
    delta = until - now
    if delta.total_seconds() <= 0:
        return 0

    # rotunjire în sus
    return int((delta.total_seconds() + 86400 - 1) // 86400)


def _extend_paid(u: User, days: int):
    now = _utcnow()
    base = u.paid_ends_at if (u.paid_ends_at and u.paid_ends_at > now) else now
    u.paid_ends_at = base + timedelta(days=days)


def _keep_filters_kwargs():
    """
    Păstrează filtrele curente când faci POST și te întorci înapoi.
    """
    kwargs = dict(
        q=request.args.get("q", ""),
        status=request.args.get("status", "all"),
        access=request.args.get("access", "all"),
    )
    if request.args.get("cleanup"):
        kwargs["cleanup"] = "1"
    return kwargs


# --- Marketplace quotas (anunțuri / cereri) pentru afișare în admin ---
OFFER_FREE_SLOTS = 3
REQUEST_FREE_SLOTS = 5
OFFER_EXPIRE_DAYS = 30
QUOTA_DAYS = 30


def _admin_offer_paid_effective(u: User):
    n = getattr(u, "offer_paid_slots", None) or 0
    if n <= 0:
        return 0
    exp = getattr(u, "offer_paid_slots_expires_at", None)
    if not exp or exp <= _utcnow():
        return 0
    return n


def _admin_request_paid_effective(u: User):
    n = getattr(u, "request_paid_slots", None) or 0
    if n <= 0:
        return 0
    exp = getattr(u, "request_paid_slots_expires_at", None)
    if not exp or exp <= _utcnow():
        return 0
    return n


def _admin_offer_quota_limit(u: User):
    if not getattr(u, "has_access", lambda: False)():
        return 0
    base = OFFER_FREE_SLOTS + _admin_offer_paid_effective(u)
    cap = getattr(u, "offer_quota_limit", None)
    if cap is not None and cap > 0:
        return max(base, cap)
    return base


def _admin_offer_quota_used(u: User):
    cutoff = _utcnow() - timedelta(days=OFFER_EXPIRE_DAYS)
    return SellerOffer.query.filter(
        SellerOffer.user_id == u.id,
        SellerOffer.created_at >= cutoff,
    ).count()


def _admin_request_quota_limit(u: User):
    base = REQUEST_FREE_SLOTS + _admin_request_paid_effective(u)
    cap = getattr(u, "request_quota_limit", None)
    if cap is not None and cap > 0:
        return max(base, cap)
    return base


def _admin_request_quota_used(u: User):
    cutoff = _utcnow() - timedelta(days=QUOTA_DAYS)
    return BuyerRequest.query.filter(
        BuyerRequest.user_id == u.id,
        BuyerRequest.created_at >= cutoff,
    ).count()


CLEANUP_DAYS = 120  # 4 months


def _get_cleanup_users_query(query, exclude_user_id=None):
    """
    Filter for cleanup: not paid, created_at older than CLEANUP_DAYS.
    exclude_user_id: optional user id to exclude (e.g. current admin).
    """
    now = _utcnow()
    cutoff = now - timedelta(days=CLEANUP_DAYS)
    # Not paid: paid_ends_at is NULL or already expired
    q = query.filter(User.created_at <= cutoff)
    q = q.filter(db.or_(User.paid_ends_at.is_(None), User.paid_ends_at <= now))
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    return q


def _user_can_be_cleanup_deleted(u: User, exclude_user_id=None) -> bool:
    """True if user is not paid and can be deleted (exclude current user)."""
    if exclude_user_id is not None and u.id == exclude_user_id:
        return False
    if hasattr(u, "access_source") and u.access_source() == "paid":
        return False
    return True


def _get_emails_list(users, access_filter: str = "all") -> list:
    """
    Get clean email list: trimmed, lowercased, unique, sorted.
    access_filter: 'paid' | 'expired' | 'blocked' | 'all' (trial eliminat)
    """
    emails_set = set()
    for u in users:
        bucket = _user_access_bucket(u)
        if access_filter == "all" or bucket == access_filter:
            email = u.email.strip().lower()
            if email:
                emails_set.add(email)
    return sorted(list(emails_set))


def _normalize_phone_ro(phone: str, add_romania_prefix: bool = False) -> str:
    """Trim phone; if add_romania_prefix, ensure +4 (România) în față."""
    phone = (phone or "").strip()
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return phone
    if add_romania_prefix:
        if digits.startswith("0") and len(digits) >= 10:
            digits = "4" + digits[1:]
        elif not digits.startswith("4"):
            digits = "4" + digits
        return "+" + digits
    if phone.startswith("+"):
        return phone
    if digits.startswith("0"):
        return "+4" + digits[1:] if len(digits) >= 10 else phone
    return phone


def _get_phones_list(users, access_filter: str = "all", add_romania_prefix_for_unpaid: bool = False) -> list:
    """
    Get list of agent phones (from UserProfile). add_romania_prefix_for_unpaid: add +4 for expired/blocked.
    """
    out = []
    seen = set()
    for u in users:
        bucket = _user_access_bucket(u)
        if access_filter != "all" and bucket != access_filter:
            continue
        phone = ""
        try:
            if getattr(u, "profile", None) and getattr(u.profile, "agent_phone", None):
                phone = (u.profile.agent_phone or "").strip()
        except Exception:
            pass
        add_prefix = add_romania_prefix_for_unpaid and bucket in ("expired", "blocked")
        phone = _normalize_phone_ro(phone, add_romania_prefix=add_prefix)
        if phone and phone not in seen:
            seen.add(phone)
            out.append(phone)
    return sorted(out)


def _emails_format(emails, fmt: str) -> str:
    """
    fmt:
      - "lines" => one per line
      - "csv"   => separated by comma+space (mail marketing friendly)
    """
    emails = [e.strip() for e in emails if e and e.strip()]
    if fmt == "csv":
        return ", ".join(emails)
    return "\n".join(emails)


# -------------------------
# Routes
# -------------------------

@admin_bp.get("/")
def admin_index():
    _require_local_only()

    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "all").strip()     # active / inactive / all
    access = (request.args.get("access") or "all").strip()     # paid / expired / blocked / all (trial eliminat)
    cleanup_mode = request.args.get("cleanup") == "1"

    query = User.query

    # search: dacă e ID numeric => caută și după id
    if q:
        if q.isdigit():
            query = query.filter(
                or_(
                    User.id == int(q),
                    db.func.lower(User.email).like(f"%{q.lower()}%"),
                    db.func.lower(User.full_name).like(f"%{q.lower()}%"),
                )
            )
        else:
            like = f"%{q.lower()}%"
            query = query.filter(
                or_(
                    db.func.lower(User.email).like(like),
                    db.func.lower(User.full_name).like(like),
                )
            )

    # active filter
    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))

    users = query.options(db.joinedload(User.profile)).order_by(User.created_at.desc()).limit(1500).all()
    user_ids = [u.id for u in users]

    # Încarcă toate dispozitivele într-o singură interogare (evită relația dynamic)
    devices_by_user = {}
    if user_ids:
        try:
            all_devices = UserDevice.query.filter(UserDevice.user_id.in_(user_ids)).all()
            for d in all_devices:
                devices_by_user.setdefault(d.user_id, []).append({
                    "label": (d.label or "Device").strip() or "Device",
                    "last_seen": _fmt_dt(d.last_seen_at) if d.last_seen_at else "-",
                    "device_id_preview": (d.device_id or "")[:10] + ("…" if len(d.device_id or "") > 10 else ""),
                })
            for uid in devices_by_user:
                devices_by_user[uid].sort(key=lambda x: x["last_seen"], reverse=True)
        except Exception:
            pass

    # build view models + counts (trial eliminat)
    buckets = {"paid": 0, "expired": 0, "blocked": 0}
    rows = []

    for u in users:
        bucket = _user_access_bucket(u)
        buckets[bucket] += 1

        # agency name (din profile) - dacă există
        agency_name = "-"
        agent_phone_raw = ""
        try:
            if getattr(u, "profile", None):
                if getattr(u.profile, "agency_name", None):
                    agency_name = u.profile.agency_name
                if getattr(u.profile, "agent_phone", None):
                    agent_phone_raw = (u.profile.agent_phone or "").strip()
        except Exception:
            pass

        # Telefon afișat: pentru neplătiți adăugăm prefix România (+4)
        add_prefix = bucket in ("expired", "blocked")
        agent_phone_display = _normalize_phone_ro(agent_phone_raw, add_romania_prefix=add_prefix) if agent_phone_raw else "-"
        agent_phone_copy = _normalize_phone_ro(agent_phone_raw, add_romania_prefix=add_prefix) if agent_phone_raw else ""

        devices_list = devices_by_user.get(u.id, [])

        until_dt = _access_until_dt(u)
        offer_used = _admin_offer_quota_used(u)
        offer_limit = _admin_offer_quota_limit(u)
        offer_paid = _admin_offer_paid_effective(u)
        offer_exp = getattr(u, "offer_paid_slots_expires_at", None)
        request_used = _admin_request_quota_used(u)
        request_limit = _admin_request_quota_limit(u)
        request_paid = _admin_request_paid_effective(u)
        request_exp = getattr(u, "request_paid_slots_expires_at", None)
        rows.append({
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "agent_phone_display": agent_phone_display,
            "agent_phone_copy": agent_phone_copy,
            "devices_list": devices_list,
            "created_at": _fmt_dt(u.created_at),

            "trial_ends_at": _fmt_dt(u.trial_ends_at),  # Legacy field, păstrat pentru compatibilitate
            "paid_ends_at": _fmt_dt(u.paid_ends_at),
            "free_rental_viewing_used": getattr(u, "free_rental_viewing_used", False),
            "free_sale_viewing_used": getattr(u, "free_sale_viewing_used", False),

            "is_active": bool(u.is_active),
            "bucket": bucket,
            "access_label": bucket.upper(),
            "access_until": _fmt_dt(until_dt) if until_dt else "-",
            "days_left": _days_left(u),
            "agency_name": agency_name,

            "offer_used": offer_used,
            "offer_limit": offer_limit,
            "offer_paid_slots": offer_paid,
            "offer_paid_expires_at": _fmt_dt(offer_exp) if offer_exp else "-",
            "request_used": request_used,
            "request_limit": request_limit,
            "request_paid_slots": request_paid,
            "request_paid_expires_at": _fmt_dt(request_exp) if request_exp else "-",
        })

    # apply access filter after bucket computed
    if access != "all":
        rows = [r for r in rows if r["bucket"] == access]

    total = sum(buckets.values())

    # Get email lists for copy functionality (use same users list)
    emails_paid = _get_emails_list(users, "paid")
    emails_expired = _get_emails_list(users, "expired")
    emails_all = sorted(list(set(emails_paid + emails_expired)))

    # Telefoane: paid fără prefix, expired/blocked cu prefix +4 România
    try:
        phones_paid = _get_phones_list(users, "paid", add_romania_prefix_for_unpaid=False)
        phones_expired = _get_phones_list(users, "expired", add_romania_prefix_for_unpaid=True)
        phones_all = []
        seen_phones = set()
        for u in users:
            bucket = _user_access_bucket(u)
            add_prefix = bucket in ("expired", "blocked")
            phone = ""
            try:
                if getattr(u, "profile", None) and getattr(u.profile, "agent_phone", None):
                    phone = _normalize_phone_ro((u.profile.agent_phone or "").strip(), add_romania_prefix=add_prefix)
            except Exception:
                pass
            if phone and phone not in seen_phones:
                seen_phones.add(phone)
                phones_all.append(phone)
        phones_all = sorted(phones_all)
    except Exception:
        phones_paid = []
        phones_expired = []
        phones_all = []

    # Cleanup list: not paid, created > 120 days ago, exclude current user
    cleanup_users = []
    if cleanup_mode:
        admin_id = current_user.id if current_user.is_authenticated else None
        cleanup_query = _get_cleanup_users_query(query, exclude_user_id=admin_id)
        cleanup_list = cleanup_query.order_by(User.created_at.asc()).limit(2000).all()
        for u in cleanup_list:
            if not _user_can_be_cleanup_deleted(u, admin_id):
                continue
            until_dt = _access_until_dt(u)
            src = u.access_source() if hasattr(u, "access_source") else _user_access_bucket(u)
            # Pill class: paid, trial, expired, blocked (template uses these)
            pill_class = "expired" if src == "none" else src
            cleanup_users.append({
                "id": u.id,
                "email": u.email,
                "full_name": getattr(u, "full_name", "") or "-",
                "created_at": _fmt_dt(u.created_at),
                "created_at_short": u.created_at.strftime("%d.%m.%Y") if u.created_at else "-",
                "access_source": src,
                "pill_class": pill_class,
                "access_until": _fmt_dt(until_dt) if until_dt else "-",
                "days_left": _days_left(u),
            })

    return render_template(
        "admin_dashboard.html",
        users=rows,
        q=q,
        status=status,
        access=access,
        total=total,
        buckets=buckets,
        emails_paid=emails_paid,
        emails_expired=emails_expired,
        emails_all=emails_all,
        phones_paid=phones_paid,
        phones_expired=phones_expired,
        phones_all=phones_all,
        emails_paid_text="\n".join(emails_paid),
        emails_expired_text="\n".join(emails_expired),
        emails_all_text="\n".join(emails_all),
        phones_paid_text="\n".join(phones_paid),
        phones_expired_text="\n".join(phones_expired),
        phones_all_text="\n".join(phones_all),
        cleanup_mode=cleanup_mode,
        cleanup_users=cleanup_users,
    )


@admin_bp.post("/user/<int:user_id>/set-active")
def admin_set_active(user_id: int):
    """
    explicit: active=1 sau active=0
    (mai clar decât toggle)
    """
    _require_local_only()

    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    active = (request.form.get("active") or "").strip()
    if active not in ("0", "1"):
        flash("Valoare invalidă pentru active.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    u.is_active = (active == "1")
    db.session.commit()

    flash(f"{u.email} -> is_active={u.is_active}", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/extend")
def admin_extend_paid(user_id: int):
    _require_local_only()

    days_str = (request.form.get("days") or "").strip()
    try:
        days = int(days_str)
        if days <= 0 or days > 3650:
            raise ValueError()
    except Exception:
        flash("Zile invalide (1..3650).", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    _extend_paid(u, days)
    db.session.commit()

    flash(f"Prelungit {u.email} cu {days} zile. Paid până la {_fmt_dt(u.paid_ends_at)}.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/extend-1m")
def admin_extend_1m(user_id: int):
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))
    _extend_paid(u, 30)
    db.session.commit()
    flash(f"+1 lună (30 zile) pentru {u.email}.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/extend-3m")
def admin_extend_3m(user_id: int):
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))
    _extend_paid(u, 90)
    db.session.commit()
    flash(f"+3 luni (90 zile) pentru {u.email}.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/extend-6m")
def admin_extend_6m(user_id: int):
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))
    _extend_paid(u, 180)
    db.session.commit()
    flash(f"+6 luni (180 zile) pentru {u.email}.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/logout-other-devices")
def admin_logout_other_devices(user_id: int):
    """
    Pentru userul respectiv:
    1) Șterge toate device-urile din user_device (eliberează sloturile de max 3 device-uri).
    2) Incrementează session_version ca la următoarea accesare să fie delogat.
    Astfel userul poate loga din nou pe device-urile actuale fără să rămână blocat pe „prea multe device-uri”.
    """
    _require_local_only()

    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    deleted = UserDevice.query.filter_by(user_id=user_id).delete()
    u.session_version = getattr(u, "session_version", 1) + 1
    db.session.commit()

    flash(
        f"Deconectat și șters {deleted} device(uri) pentru {u.email}. "
        f"La următoarea accesare va fi delogat și va putea loga din nou pe device-urile actuale (max 3).",
        "ok",
    )
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/reset-free-uses")
def admin_reset_free_uses(user_id: int):
    """Resetează flag-urile free_rental_viewing_used și free_sale_viewing_used pentru user."""
    _require_local_only()

    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    u.free_rental_viewing_used = False
    u.free_sale_viewing_used = False
    db.session.commit()

    flash(f"Resetate utilizările gratuite pentru {u.email}.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/user/<int:user_id>/reset-password")
def admin_reset_password(user_id: int):
    _require_local_only()

    new_pass = (request.form.get("new_password") or "").strip()
    if len(new_pass) < 6:
        flash("Parola prea scurtă (min 6).", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    u.set_password(new_pass)
    db.session.commit()

    flash(f"Parola resetată pentru {u.email}.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


# -------------------------
# Cleanup: delete inactive/unpaid users (local-only)
# -------------------------

def _build_cleanup_base_query():
    """Same filters as admin_index (q, status) for consistency."""
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "all").strip()
    query = User.query
    if q:
        if q.isdigit():
            query = query.filter(
                or_(
                    User.id == int(q),
                    db.func.lower(User.email).like(f"%{q.lower()}%"),
                    db.func.lower(User.full_name).like(f"%{q.lower()}%"),
                )
            )
        else:
            like = f"%{q.lower()}%"
            query = query.filter(
                or_(
                    db.func.lower(User.email).like(like),
                    db.func.lower(User.full_name).like(like),
                )
            )
    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))
    return query


@admin_bp.post("/cleanup/delete-selected")
def admin_cleanup_delete_selected():
    _require_local_only()

    user_ids = request.form.getlist("user_ids")
    if not user_ids:
        flash("Niciun user selectat.", "error")
        return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))

    admin_id = current_user.id if current_user.is_authenticated else None
    deleted = 0
    for uid_str in user_ids:
        try:
            uid = int(uid_str)
        except (TypeError, ValueError):
            continue
        u = db.session.get(User, uid)
        if not u or not _user_can_be_cleanup_deleted(u, admin_id):
            continue
        db.session.delete(u)
        deleted += 1

    db.session.commit()
    flash(f"{deleted} conturi șterse.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.post("/cleanup/delete-all")
def admin_cleanup_delete_all():
    _require_local_only()

    admin_id = current_user.id if current_user.is_authenticated else None
    query = _build_cleanup_base_query()
    cleanup_query = _get_cleanup_users_query(query, exclude_user_id=admin_id)
    users_to_delete = cleanup_query.all()

    deleted = 0
    for u in users_to_delete:
        if not _user_can_be_cleanup_deleted(u, admin_id):
            continue
        db.session.delete(u)
        deleted += 1

    db.session.commit()
    flash(f"{deleted} conturi șterse.", "ok")
    return redirect(url_for("admin.admin_index", **_keep_filters_kwargs()))


@admin_bp.get("/emails.txt")
def admin_emails_txt():
    """
    Returnează emailuri filtrate (paid/trial/expired/blocked/all) ca text.
    Exemple:
      /admin/emails.txt?access=paid&fmt=csv
      /admin/emails.txt?access=trial&fmt=lines
    """
    _require_local_only()

    access = (request.args.get("access") or "all").strip()
    status = (request.args.get("status") or "all").strip()
    q = (request.args.get("q") or "").strip()
    fmt = (request.args.get("fmt") or "csv").strip()  # csv by default (marketing-friendly)

    query = User.query

    if q:
        if q.isdigit():
            query = query.filter(
                or_(
                    User.id == int(q),
                    db.func.lower(User.email).like(f"%{q.lower()}%"),
                    db.func.lower(User.full_name).like(f"%{q.lower()}%"),
                )
            )
        else:
            like = f"%{q.lower()}%"
            query = query.filter(
                or_(
                    db.func.lower(User.email).like(like),
                    db.func.lower(User.full_name).like(like),
                )
            )

    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))

    users = query.order_by(User.created_at.desc()).all()

    emails = []
    for u in users:
        bucket = _user_access_bucket(u)
        if access == "all" or bucket == access:
            emails.append(u.email)

    body = _emails_format(emails, fmt=fmt)
    return Response(body, mimetype="text/plain; charset=utf-8")


@admin_bp.get("/export.csv")
def admin_export_csv():
    _require_local_only()

    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "all").strip()
    access = (request.args.get("access") or "all").strip()

    query = User.query

    if q:
        if q.isdigit():
            query = query.filter(
                or_(
                    User.id == int(q),
                    db.func.lower(User.email).like(f"%{q.lower()}%"),
                    db.func.lower(User.full_name).like(f"%{q.lower()}%"),
                )
            )
        else:
            like = f"%{q.lower()}%"
            query = query.filter(
                or_(
                    db.func.lower(User.email).like(like),
                    db.func.lower(User.full_name).like(like),
                )
            )

    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))

    users = query.order_by(User.created_at.desc()).all()

    # Get emails only (unique, sorted)
    emails = _get_emails_list(users, access)

    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["email"])

    for email in emails:
        w.writerow([email])

    csv_data = buf.getvalue()
    today = datetime.now().strftime("%Y-%m-%d")
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=emails_export_{today}.csv"},
    )


# -------------------------
# Anunțuri către toți utilizatorii (local-only)
# -------------------------

@admin_bp.get("/announcements")
def admin_announcements():
    """Pagina de trimitere anunțuri către toți utilizatorii."""
    _require_local_only()

    announcements = (
        Announcement.query
        .order_by(Announcement.created_at.desc())
        .limit(50)
        .all()
    )
    rows = []
    for a in announcements:
        read_by = UserAnnouncementRead.query.filter_by(announcement_id=a.id).all()
        read_by_list = []
        for r in read_by:
            u = db.session.get(User, r.user_id)
            if u:
                read_by_list.append({"id": u.id, "email": u.email or "-"})
        rows.append({
            "id": a.id,
            "message": a.message,
            "created_at": _fmt_dt(a.created_at),
            "read_by": read_by_list,
        })
    return render_template(
        "admin/announcements.html",
        announcements=rows,
    )


@admin_bp.post("/announcements/send")
def admin_announcements_send():
    """Trimite anunț nou către toți utilizatorii."""
    _require_local_only()

    message = (request.form.get("message") or "").strip()
    if not message:
        flash("Mesajul este obligatoriu.", "error")
        return redirect(url_for("admin.admin_announcements"))

    a = Announcement(
        message=message,
        created_by_user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(a)
    db.session.commit()

    flash(f"Anunțul a fost trimis. Toți utilizatorii vor vedea notificarea în asistent.", "ok")
    return redirect(url_for("admin.admin_announcements"))


# -------------------------
# Marketplace moderation (local-only)
# -------------------------

@admin_bp.get("/marketplace")
def admin_marketplace_moderation():
    """List recent buyer requests and seller offers; delete abusive content. Local-only."""
    _require_local_only()

    requests = (
        BuyerRequest.query
        .order_by(BuyerRequest.created_at.desc())
        .limit(100)
        .all()
    )
    rows = []
    for req in requests:
        zones_str = ", ".join(z.name for z in req.zones) if req.zones else "-"
        desc_excerpt = (req.description or "")[:120]
        if req.description and len(req.description) > 120:
            desc_excerpt += "..."
        rows.append({
            "id": req.id,
            "user_id": req.user_id,
            "request_type": req.request_type,
            "property_type": req.property_type,
            "zones": zones_str,
            "budget_min": req.budget_min,
            "budget_max": req.budget_max,
            "created_at": _fmt_dt(req.created_at),
            "description_excerpt": desc_excerpt or "-",
        })

    offers = (
        SellerOffer.query
        .options(db.joinedload(SellerOffer.user))
        .order_by(SellerOffer.created_at.desc())
        .limit(100)
        .all()
    )
    offer_rows = []
    for off in offers:
        zones_str = ", ".join(z.name for z in off.zones) if off.zones else "-"
        desc_excerpt = (off.description or "")[:120]
        if off.description and len(off.description) > 120:
            desc_excerpt += "..."
        offer_rows.append({
            "id": off.id,
            "user_id": off.user_id,
            "title": off.title or "-",
            "zones": zones_str,
            "created_at": _fmt_dt(off.created_at),
            "description_excerpt": desc_excerpt or "-",
        })

    return render_template(
        "admin/marketplace_moderation.html",
        requests=rows,
        offers=offer_rows,
    )


@admin_bp.post("/marketplace/<int:req_id>/delete")
def admin_marketplace_delete(req_id: int):
    """Delete a buyer request by id. Local-only."""
    _require_local_only()

    req = BuyerRequest.query.get(req_id)
    if not req:
        flash("Cerere inexistentă.", "error")
        return redirect(url_for("admin.admin_marketplace_moderation"))
    db.session.delete(req)
    db.session.commit()
    flash(f"Cererea #{req_id} a fost ștearsă.", "ok")
    return redirect(url_for("admin.admin_marketplace_moderation"))


@admin_bp.get("/marketplace/offer-quotas")
def admin_offer_quotas():
    """Set per-user offer quota (câte oferte poate avea). Local-only."""
    _require_local_only()
    email = (request.args.get("email") or "").strip()
    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    return render_template("admin/offer_quotas.html", email=email, user=user)


@admin_bp.post("/marketplace/offer-quotas")
def admin_offer_quotas_post():
    """Set offer_quota_limit and request_quota_limit for a user by email. Local-only."""
    _require_local_only()
    email = (request.form.get("email") or "").strip()
    if not email:
        flash("Introdu adresa de email.", "error")
        return redirect(url_for("admin.admin_offer_quotas"))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash(f"Utilizator cu email {email} nu există.", "error")
        return redirect(url_for("admin.admin_offer_quotas"))

    def _parse_quota(s: str):
        s = (s or "").strip()
        if s == "":
            return None
        try:
            q = int(s)
            return q if 0 <= q <= 999 else None
        except ValueError:
            return None

    user.offer_quota_limit = _parse_quota(request.form.get("offer_quota"))
    user.request_quota_limit = _parse_quota(request.form.get("request_quota"))

    db.session.commit()
    flash(f"Limite actualizate pentru {email}: oferte={user.offer_quota_limit or 'default'}, cereri={user.request_quota_limit or 'default'}.", "ok")
    return redirect(url_for("admin.admin_offer_quotas"))


# Prețuri pachete anunțuri (lei): +3, +6, +12. Valabilitate 30 zile.
OFFER_PACKAGES = [(3, 15), (6, 30), (12, 50)]
OFFER_PAID_VALID_DAYS = 30
# Pachete cereri (sloturi, lei). Valabilitate 30 zile.
REQUEST_PACKAGES = [(3, 10), (5, 25), (10, 45)]
REQUEST_PAID_VALID_DAYS = 30


@admin_bp.get("/user/<int:user_id>")
def admin_user_detail(user_id: int):
    """Pagină detaliu user: anunțuri/cereri folosite, limite, pachete plătite, activare pachete."""
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index"))
    offer_used = _admin_offer_quota_used(u)
    offer_limit = _admin_offer_quota_limit(u)
    offer_paid = _admin_offer_paid_effective(u)
    offer_exp = getattr(u, "offer_paid_slots_expires_at", None)
    request_used = _admin_request_quota_used(u)
    request_limit = _admin_request_quota_limit(u)
    request_paid = _admin_request_paid_effective(u)
    request_exp = getattr(u, "request_paid_slots_expires_at", None)
    # Lista anunțuri (ultimele 30 zile sau toate?)
    cutoff_offer = _utcnow() - timedelta(days=OFFER_EXPIRE_DAYS)
    offers = SellerOffer.query.filter(
        SellerOffer.user_id == u.id,
        SellerOffer.created_at >= cutoff_offer,
    ).order_by(SellerOffer.created_at.desc()).all()
    cutoff_req = _utcnow() - timedelta(days=QUOTA_DAYS)
    requests_list = BuyerRequest.query.filter(
        BuyerRequest.user_id == u.id,
        BuyerRequest.created_at >= cutoff_req,
    ).order_by(BuyerRequest.created_at.desc()).all()
    agency_name = "-"
    if getattr(u, "profile", None) and getattr(u.profile, "agency_name", None):
        agency_name = u.profile.agency_name
    return render_template(
        "admin/user_detail.html",
        u=u,
        agency_name=agency_name,
        offer_used=offer_used,
        offer_limit=offer_limit,
        offer_paid_slots=offer_paid,
        offer_paid_expires_at=offer_exp,
        offer_paid_expires_at_fmt=_fmt_dt(offer_exp) if offer_exp else "-",
        request_used=request_used,
        request_limit=request_limit,
        request_paid_slots=request_paid,
        request_paid_expires_at=request_exp,
        request_paid_expires_at_fmt=_fmt_dt(request_exp) if request_exp else "-",
        offers=offers,
        requests_list=requests_list,
        offer_packages=OFFER_PACKAGES,
        request_packages=REQUEST_PACKAGES,
    )


@admin_bp.post("/user/<int:user_id>/activate-offer-package")
def admin_activate_offer_package(user_id: int):
    """Activează pachet anunțuri: +3 (15 lei), +6 (30 lei), +12 (50 lei), valabil 30 zile."""
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index"))
    slots = request.form.get("slots", type=int)
    if slots not in (3, 6, 12):
        flash("Pachet invalid. Alege +3, +6 sau +12.", "error")
        return redirect(url_for("admin.admin_user_detail", user_id=user_id))
    now = _utcnow()
    current_paid = _admin_offer_paid_effective(u)
    u.offer_paid_slots = current_paid + slots
    u.offer_paid_slots_expires_at = now + timedelta(days=OFFER_PAID_VALID_DAYS)
    db.session.commit()
    flash(f"Pachet anunțuri +{slots} activat pentru 30 zile. Total sloturi plătite: {u.offer_paid_slots}.", "ok")
    return redirect(url_for("admin.admin_user_detail", user_id=user_id))


@admin_bp.post("/user/<int:user_id>/activate-request-package")
def admin_activate_request_package(user_id: int):
    """Activează pachet cereri: +3/+5/+10, valabil 30 zile."""
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index"))
    slots = request.form.get("slots", type=int)
    allowed = [p[0] for p in REQUEST_PACKAGES]
    if slots not in allowed:
        flash(f"Pachet invalid. Alege {' / '.join(str(s) for s in allowed)}.", "error")
        return redirect(url_for("admin.admin_user_detail", user_id=user_id))
    now = _utcnow()
    current_paid = _admin_request_paid_effective(u)
    u.request_paid_slots = current_paid + slots
    u.request_paid_slots_expires_at = now + timedelta(days=REQUEST_PAID_VALID_DAYS)
    db.session.commit()
    flash(f"Pachet cereri +{slots} activat pentru 30 zile. Total sloturi plătite: {u.request_paid_slots}.", "ok")
    return redirect(url_for("admin.admin_user_detail", user_id=user_id))


@admin_bp.post("/user/<int:user_id>/reset-offer-paid-slots")
def admin_reset_offer_paid_slots(user_id: int):
    """Resetează sloturile plătite anunțuri (scoate pachetul)."""
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index"))
    u.offer_paid_slots = 0
    u.offer_paid_slots_expires_at = None
    db.session.commit()
    flash("Sloturi plătite anunțuri resetate (0).", "ok")
    return redirect(url_for("admin.admin_user_detail", user_id=user_id))


@admin_bp.post("/user/<int:user_id>/reset-request-paid-slots")
def admin_reset_request_paid_slots(user_id: int):
    """Resetează sloturile plătite cereri."""
    _require_local_only()
    u = db.session.get(User, user_id)
    if not u:
        flash("User inexistent.", "error")
        return redirect(url_for("admin.admin_index"))
    u.request_paid_slots = 0
    u.request_paid_slots_expires_at = None
    db.session.commit()
    flash("Sloturi plătite cereri resetate (0).", "ok")
    return redirect(url_for("admin.admin_user_detail", user_id=user_id))


@admin_bp.post("/marketplace/offer/<int:offer_id>/delete")
def admin_marketplace_offer_delete(offer_id: int):
    """Delete a seller offer by id. Local-only."""
    _require_local_only()

    offer = SellerOffer.query.get(offer_id)
    if not offer:
        flash("Ofertă inexistentă.", "error")
        return redirect(url_for("admin.admin_marketplace_moderation"))
    db.session.delete(offer)
    db.session.commit()
    flash(f"Oferta #{offer_id} a fost ștearsă.", "ok")
    return redirect(url_for("admin.admin_marketplace_moderation"))


# -------------------------
# Admin Cleaner (curățare DB)
# -------------------------

from admin.cleanup import (
    CATEGORIES,
    run_cleanup,
    save_cleanup_run,
    get_recent_runs,
    _safe_column_exists,
)


@admin_bp.get("/cleanup")
def admin_cleanup():
    """UI curățare bază de date + stats."""
    _require_local_only()

    runs = get_recent_runs(20)
    last_success = None
    for r in runs:
        if r.ok:
            last_success = r.ran_at
            break

    return render_template(
        "admin/cleanup.html",
        categories=CATEGORIES,
        runs=runs,
        last_success=last_success,
    )


@admin_bp.post("/cleanup/dry-run")
def admin_cleanup_dry_run():
    """Simulare: arată câte rânduri ar șterge per categorie."""
    _require_local_only()

    toggles = {
        "remote_expired": request.form.get("remote_expired") == "1",
        "buyer_request": request.form.get("buyer_request") == "1",
        "task_completed": request.form.get("task_completed") == "1",
        "assistant_usage": request.form.get("assistant_usage") == "1",
        "user_device": request.form.get("user_device") == "1",
        "device_trial": request.form.get("device_trial") == "1",
        "team_task_assignment_done": request.form.get("team_task_assignment_done") == "1",
        "daily_activity": request.form.get("daily_activity") == "1",
        "team_task_old_7_days": request.form.get("team_task_old_7_days") == "1",
    }

    result = run_cleanup(dry_run=True, toggles=toggles, mode="dry_run")
    if result.get("locked"):
        flash("Curățarea este deja în curs.", "error")
        return redirect(url_for("admin.admin_cleanup"))

    flash(
        f"Dry-run: s-ar șterge {result['total_deleted']} rânduri în total.",
        "ok",
    )
    runs = get_recent_runs(20)
    last_success = next((r.ran_at for r in runs if r.ok), None)
    return render_template(
        "admin/cleanup.html",
        categories=CATEGORIES,
        runs=runs,
        last_success=last_success,
        dry_run_result=result,
    )


@admin_bp.post("/cleanup/run")
def admin_cleanup_run():
    """Execută curățarea reală."""
    _require_local_only()

    toggles = {
        "remote_expired": request.form.get("remote_expired") == "1",
        "buyer_request": request.form.get("buyer_request") == "1",
        "task_completed": request.form.get("task_completed") == "1",
        "assistant_usage": request.form.get("assistant_usage") == "1",
        "user_device": request.form.get("user_device") == "1",
        "device_trial": request.form.get("device_trial") == "1",
        "team_task_assignment_done": request.form.get("team_task_assignment_done") == "1",
        "daily_activity": request.form.get("daily_activity") == "1",
        "team_task_old_7_days": request.form.get("team_task_old_7_days") == "1",
    }

    result = run_cleanup(
        dry_run=False,
        toggles=toggles,
        mode="manual",
        ran_by_user_id=current_user.id if current_user.is_authenticated else None,
    )

    if result.get("locked"):
        flash("Curățarea este deja în curs.", "error")
        return redirect(url_for("admin.admin_cleanup"))

    save_cleanup_run(
        mode="manual",
        ok=result["ok"],
        details=result["details"],
        error_text=result.get("error"),
        ran_by_user_id=current_user.id if current_user.is_authenticated else None,
    )

    if result["ok"]:
        flash(f"Curățare finalizată. Au fost șterse {result['total_deleted']} rânduri.", "ok")
    else:
        flash(f"Eroare: {result.get('error', 'necunoscută')}", "error")

    return redirect(url_for("admin.admin_cleanup"))


@admin_bp.get("/cleanup/runs.csv")
def admin_cleanup_runs_csv():
    """Export CSV cu ultimele rulări."""
    _require_local_only()

    runs = get_recent_runs(100)
    output = StringIO()
    w = csv.writer(output)
    w.writerow(["id", "ran_at", "ran_by_user_id", "mode", "ok", "total_deleted", "details_json", "error_text"])
    for r in runs:
        details = {}
        try:
            import json
            details = json.loads(r.details_json) if r.details_json else {}
        except Exception:
            pass
        total = 0
        for k, v in (details or {}).items():
            if isinstance(v, dict) and "count" in v:
                total += v.get("count", 0)
            elif isinstance(v, dict) and "chirie" in v:
                total += v.get("chirie", 0) + v.get("vanzare", 0)
        w.writerow([
            r.id,
            r.ran_at.isoformat() if r.ran_at else "",
            r.ran_by_user_id or "",
            r.mode or "",
            "da" if r.ok else "nu",
            total,
            (r.details_json or "")[:500],
            (r.error_text or "")[:200],
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cleanup_runs.csv"},
    )


@admin_bp.get("/cleanup/users-inactive")
def admin_cleanup_users_inactive():
    """Listare utilizatori inactivi (criterii: last_login, paid, activitate)."""
    _require_local_only()

    from models import Task, ChirieRemoteSigning, VanzareRemoteSigning

    now = _utcnow()
    cutoff_12m = now - timedelta(days=365)
    cutoff_4m = now - timedelta(days=120)
    cutoff_6m = now - timedelta(days=180)

    query = User.query
    # Exclude paid (trial eliminat complet)
    query = query.filter(db.or_(User.paid_ends_at.is_(None), User.paid_ends_at < now))

    # last_login_at < 12 luni (dacă există coloana)
    if _safe_column_exists("user", "last_login_at"):
        query = query.filter(
            db.or_(User.last_login_at.is_(None), User.last_login_at < cutoff_12m)
        )

    users = query.order_by(User.created_at.asc()).limit(500).all()

    rows = []
    for u in users:
        last_login = getattr(u, "last_login_at", None)
        br_count = task_count = chirie_count = vanzare_count = 0
        try:
            br_count = BuyerRequest.query.filter(
                BuyerRequest.user_id == u.id,
                BuyerRequest.created_at >= cutoff_6m,
            ).count()
        except Exception:
            pass
        try:
            task_count = Task.query.filter(
                Task.user_id == u.id,
                Task.created_at >= cutoff_6m,
            ).count()
        except Exception:
            pass
        try:
            chirie_count = ChirieRemoteSigning.query.filter(
                ChirieRemoteSigning.user_id == u.id,
                ChirieRemoteSigning.created_at >= cutoff_6m,
            ).count()
        except Exception:
            pass
        try:
            vanzare_count = VanzareRemoteSigning.query.filter(
                VanzareRemoteSigning.user_id == u.id,
                VanzareRemoteSigning.created_at >= cutoff_6m,
            ).count()
        except Exception:
            pass
        has_activity = (br_count + task_count + chirie_count + vanzare_count) > 0

        rows.append({
            "user": u,
            "last_login_at": _fmt_dt(last_login) if last_login else "-",
            "has_activity": has_activity,
            "br_count": br_count,
            "task_count": task_count,
            "chirie_count": chirie_count,
            "vanzare_count": vanzare_count,
        })

    return render_template(
        "admin/users_inactive.html",
        rows=rows,
    )


@admin_bp.post("/cleanup/users-inactive/delete")
def admin_cleanup_users_inactive_delete():
    """Ștergere selectivă utilizatori inactivi."""
    _require_local_only()

    user_ids = request.form.getlist("user_ids")
    admin_id = current_user.id if current_user.is_authenticated else None
    deleted = 0

    for uid_str in user_ids:
        try:
            uid = int(uid_str)
        except (TypeError, ValueError):
            continue
        if uid == admin_id:
            continue
        u = db.session.get(User, uid)
        if not u:
            continue
        if hasattr(u, "access_source") and u.access_source() == "paid":
            continue
        db.session.delete(u)
        deleted += 1

    db.session.commit()
    flash(f"{deleted} conturi șterse.", "ok")
    return redirect(url_for("admin.admin_cleanup_users_inactive"))


# -------------------------
# Client Management (local-only)
# -------------------------

@admin_bp.get("/clients")
def admin_clients():
    """Listare și gestionare clienți (role='client')."""
    _require_local_only()

    q = (request.args.get("q") or "").strip()
    query = User.query.filter_by(role="client")

    # Search
    if q:
        if q.isdigit():
            query = query.filter(
                or_(
                    User.id == int(q),
                    db.func.lower(User.email).like(f"%{q.lower()}%"),
                    db.func.lower(User.full_name).like(f"%{q.lower()}%"),
                    User.phone.like(f"%{q}%"),
                )
            )
        else:
            like = f"%{q.lower()}%"
            query = query.filter(
                or_(
                    db.func.lower(User.email).like(like),
                    db.func.lower(User.full_name).like(like),
                    User.phone.like(f"%{q}%"),
                )
            )

    clients = query.order_by(User.created_at.desc()).limit(1000).all()
    client_ids = [c.id for c in clients]

    # Încarcă cererile pentru fiecare client
    requests_by_client = {}
    if client_ids:
        try:
            all_requests = BuyerRequest.query.filter(BuyerRequest.user_id.in_(client_ids)).all()
            for req in all_requests:
                if req.user_id not in requests_by_client:
                    requests_by_client[req.user_id] = []
                requests_by_client[req.user_id].append({
                    "id": req.id,
                    "request_type": req.request_type,
                    "property_type": req.property_type,
                    "created_at": _fmt_dt(req.created_at),
                    "created_at_short": req.created_at.strftime("%d.%m.%Y") if req.created_at else "-",
                    "budget_min": req.budget_min,
                    "budget_max": req.budget_max,
                    "zones": ", ".join(z.name for z in req.zones[:3]) + ("..." if len(req.zones) > 3 else "") if req.zones else "-",
                })
        except Exception:
            pass

    rows = []
    for client in clients:
        requests_list = requests_by_client.get(client.id, [])
        rows.append({
            "id": client.id,
            "full_name": client.full_name,
            "email": client.email,
            "phone": client.phone or "-",
            "created_at": _fmt_dt(client.created_at),
            "created_at_short": client.created_at.strftime("%d.%m.%Y") if client.created_at else "-",
            "last_login_at": _fmt_dt(client.last_login_at) if client.last_login_at else "-",
            "requests_count": len(requests_list),
            "requests": requests_list,
            "is_active": bool(client.is_active),
        })

    return render_template(
        "admin/clients.html",
        clients=rows,
        q=q,
        total=len(rows),
    )


@admin_bp.post("/clients/<int:client_id>/delete-account")
def admin_clients_delete_account(client_id: int):
    """Șterge contul unui client și toate cererile asociate."""
    _require_local_only()

    client = db.session.get(User, client_id)
    if not client:
        flash("Client inexistent.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    if client.role != "client":
        flash("Utilizatorul nu este client.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    # Șterge cererile asociate (RequestZones și PossibleCollaboration se șterg automat prin CASCADE)
    from sqlalchemy import text
    try:
        db.session.execute(text("DELETE FROM possible_collaboration WHERE request_id IN (SELECT id FROM buyer_request WHERE user_id = :user_id)"), {"user_id": client_id})
        BuyerRequest.query.filter_by(user_id=client_id).delete()
    except Exception as e:
        _log.warning(f"Eroare la ștergerea cererilor clientului {client_id}: {e}")

    # Șterge contul
    db.session.delete(client)
    db.session.commit()

    flash(f"Contul clientului {client.email} și toate cererile asociate au fost șterse.", "ok")
    return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))


@admin_bp.post("/clients/<int:client_id>/delete-request/<int:request_id>")
def admin_clients_delete_request(client_id: int, request_id: int):
    """Șterge o cerere specifică a unui client."""
    _require_local_only()

    client = db.session.get(User, client_id)
    if not client or client.role != "client":
        flash("Client inexistent.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    req = BuyerRequest.query.filter_by(id=request_id, user_id=client_id).first()
    if not req:
        flash("Cerere inexistentă sau nu aparține clientului.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    # Șterge cererea (RequestZones și PossibleCollaboration se șterg automat prin CASCADE)
    from sqlalchemy import text
    try:
        db.session.execute(text("DELETE FROM possible_collaboration WHERE request_id = :req_id"), {"req_id": req.id})
    except Exception:
        pass

    db.session.delete(req)
    db.session.commit()

    flash(f"Cererea #{request_id} a fost ștearsă.", "ok")
    return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))


@admin_bp.post("/clients/<int:client_id>/delete-all-requests")
def admin_clients_delete_all_requests(client_id: int):
    """Șterge toate cererile unui client."""
    _require_local_only()

    client = db.session.get(User, client_id)
    if not client or client.role != "client":
        flash("Client inexistent.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    # Șterge toate cererile (RequestZones și PossibleCollaboration se șterg automat prin CASCADE)
    from sqlalchemy import text
    try:
        db.session.execute(text("DELETE FROM possible_collaboration WHERE request_id IN (SELECT id FROM buyer_request WHERE user_id = :user_id)"), {"user_id": client_id})
        deleted_count = BuyerRequest.query.filter_by(user_id=client_id).delete()
        db.session.commit()
        flash(f"{deleted_count} cereri șterse pentru clientul {client.email}.", "ok")
    except Exception as e:
        db.session.rollback()
        flash(f"Eroare la ștergerea cererilor: {e}", "error")

    return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))


@admin_bp.post("/clients/<int:client_id>/reset-password")
def admin_clients_reset_password(client_id: int):
    """Resetează parola unui client."""
    _require_local_only()

    new_pass = (request.form.get("new_password") or "").strip()
    if len(new_pass) < 6:
        flash("Parola prea scurtă (min 6 caractere).", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    client = db.session.get(User, client_id)
    if not client:
        flash("Client inexistent.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    if client.role != "client":
        flash("Utilizatorul nu este client.", "error")
        return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))

    client.set_password(new_pass)
    db.session.commit()

    flash(f"Parola resetată pentru clientul {client.email}.", "ok")
    return redirect(url_for("admin.admin_clients", **_keep_filters_kwargs()))


def _keep_filters_kwargs():
    """
    Păstrează filtrele curente când faci POST și te întorci înapoi.
    """
    kwargs = dict(
        q=request.args.get("q", ""),
    )
    return kwargs
