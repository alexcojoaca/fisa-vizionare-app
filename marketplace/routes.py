# marketplace/routes.py
import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from flask import render_template, request, redirect, url_for, flash, current_app, make_response
from flask_login import login_required, current_user
from sqlalchemy import or_, and_

from extensions import db
from models import BuyerRequest, Zone, RequestZones, User, utcnow, SellerOffer, OfferZones

from . import marketplace_bp
from .matching import run_matching_for_new_offer, run_matching_for_new_request
from .forms import (
    BuyerRequestForm,
    REQUEST_TYPE_CHOICES,
    REQUEST_TYPE_ANUNT_CHOICES,
    PROPERTY_TYPE_CHOICES,
    PROPERTY_TYPE_ANUNT_CHOICES,
    SellerOfferForm,
)


# --- Constants ---
QUOTA_DAYS = 30
REQUEST_FREE_SLOTS = 5   # cereri gratuite pe 30 zile pentru toți
REQUEST_EXPIRE_DAYS = 30
PER_PAGE = 20
PER_PAGE_OFFERS = 8
RATE_LIMIT_CREATES_PER_MINUTE = 10

# Oferte: 3 gratuite la 30 zile; peste acelea sloturi plătite (+3/+6/+12) valabile 30 zile
OFFER_EXPIRE_DAYS = 30
OFFER_FREE_SLOTS = 3     # anunțuri gratuite la 30 zile pentru toți (cu acces)
OFFER_PAID_VALID_DAYS = 30
REQUEST_PAID_VALID_DAYS = 30

# in-memory rate limit: {user_id: [timestamp, ...]}
_create_timestamps = defaultdict(list)

# Fair rotation: seed TTL 30 min, max IDs to shuffle (pentru performanță)
FAIR_SEED_TTL_SECONDS = 30 * 60
FAIR_MAX_IDS = 500


class _FairPagination:
    """Objekt paginare compatibil cu template-ul, pentru sortare fair (fără SQL paginate)."""
    def __init__(self, page, per_page, total, items):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, (total + per_page - 1) // per_page) if total else 1
        self.items = items
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if page > 1 else None
        self.next_num = page + 1 if page < self.pages else None


def _utcnow():
    return datetime.now(timezone.utc)


def get_marketplace_seed(request):
    """
    Seed pentru fair rotation: stabil 30 min per user/sesiune.
    Returnează (seed_str, expires_at_ts, is_new).
    Dacă is_new=True, view-ul trebuie să seteze cookie-urile pe response.
    """
    now_ts = int(time.time())
    cookie_seed = request.cookies.get("mp_seed")
    cookie_exp = request.cookies.get("mp_seed_exp")
    if cookie_seed and cookie_exp:
        try:
            exp_ts = int(cookie_exp)
            if exp_ts > now_ts:
                return (cookie_seed, exp_ts, False)
        except ValueError:
            pass
    seed = uuid.uuid4().hex[:16]
    expires_at = now_ts + FAIR_SEED_TTL_SECONDS
    return (seed, expires_at, True)


def _stable_shuffle_ids(seed, id_created_list):
    """
    Ordine deterministă: score = hash(seed + ":" + str(id)), tie-break created_at desc.
    id_created_list: list of (id, created_at).
    Returnează listă de id-uri ordonate.
    """
    def score_for(item):
        row_id, created_at = item
        key = f"{seed}:{row_id}"
        h = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
        ts = created_at.timestamp() if hasattr(created_at, "timestamp") else 0
        return (h, -ts)

    sorted_items = sorted(id_created_list, key=score_for)
    return [item[0] for item in sorted_items]


def _run_expiration_cleanup():
    """Șterge cererile mai vechi de REQUEST_EXPIRE_DAYS și toate datele asociate (request_zones)."""
    cutoff = _utcnow() - timedelta(days=REQUEST_EXPIRE_DAYS)
    expired_ids = [r[0] for r in db.session.query(BuyerRequest.id).filter(BuyerRequest.created_at < cutoff).all()]
    if expired_ids:
        RequestZones.query.filter(RequestZones.request_id.in_(expired_ids)).delete(synchronize_session=False)
        BuyerRequest.query.filter(BuyerRequest.id.in_(expired_ids)).delete(synchronize_session=False)
        db.session.commit()


def _run_offer_expiration_cleanup():
    """Șterge ofertele mai vechi de OFFER_EXPIRE_DAYS și toate datele asociate (offer_zones), fără să lase nimic în memorie."""
    cutoff = _utcnow() - timedelta(days=OFFER_EXPIRE_DAYS)
    expired_ids = [r[0] for r in db.session.query(SellerOffer.id).filter(SellerOffer.created_at < cutoff).all()]
    if expired_ids:
        OfferZones.query.filter(OfferZones.offer_id.in_(expired_ids)).delete(synchronize_session=False)
        SellerOffer.query.filter(SellerOffer.id.in_(expired_ids)).delete(synchronize_session=False)
        db.session.commit()


def _offer_paid_slots_effective(user):
    """Sloturi plătite anunțuri valabile (dacă nu au expirat)."""
    n = getattr(user, "offer_paid_slots", None) or 0
    if n <= 0:
        return 0
    exp = getattr(user, "offer_paid_slots_expires_at", None)
    if not exp or exp <= _utcnow():
        return 0
    return n


def _offer_quota_limit(user):
    """Limită oferte: 3 gratuite + sloturi plătite (dacă valabile). Admin offer_quota_limit cap opțional."""
    if not user.has_access():
        return 0
    base = OFFER_FREE_SLOTS + _offer_paid_slots_effective(user)
    cap = getattr(user, "offer_quota_limit", None)
    if cap is not None:
        return max(base, cap) if cap > 0 else base
    return base


def _offer_quota_used(user):
    """Câte oferte active (în ultimele OFFER_EXPIRE_DAYS) are userul."""
    cutoff = _utcnow() - timedelta(days=OFFER_EXPIRE_DAYS)
    return SellerOffer.query.filter(
        SellerOffer.user_id == user.id,
        SellerOffer.created_at >= cutoff,
    ).count()


def _offer_quota_remaining(user):
    return max(0, _offer_quota_limit(user) - _offer_quota_used(user))


def _request_paid_slots_effective(user):
    """Sloturi plătite cereri valabile (dacă nu au expirat)."""
    n = getattr(user, "request_paid_slots", None) or 0
    if n <= 0:
        return 0
    exp = getattr(user, "request_paid_slots_expires_at", None)
    if not exp or exp <= _utcnow():
        return 0
    return n


def _quota_limit(user):
    """Limită cereri: 5 gratuite + sloturi plătite (dacă valabile). Admin request_quota_limit cap opțional."""
    base = REQUEST_FREE_SLOTS + _request_paid_slots_effective(user)
    cap = getattr(user, "request_quota_limit", None)
    if cap is not None:
        return max(base, cap) if cap > 0 else base
    return base


def _quota_used(user):
    cutoff = _utcnow() - timedelta(days=QUOTA_DAYS)
    return BuyerRequest.query.filter(
        BuyerRequest.user_id == user.id,
        BuyerRequest.created_at >= cutoff,
    ).count()


def _quota_remaining(user):
    return max(0, _quota_limit(user) - _quota_used(user))


def _check_rate_limit():
    """Max RATE_LIMIT_CREATES_PER_MINUTE cereri per user per minut."""
    uid = current_user.id
    now = _utcnow()
    window_start = now - timedelta(minutes=1)
    _create_timestamps[uid] = [t for t in _create_timestamps[uid] if t > window_start]
    if len(_create_timestamps[uid]) >= RATE_LIMIT_CREATES_PER_MINUTE:
        return False
    _create_timestamps[uid].append(now)
    return True


def _whatsapp_support_phone():
    return current_app.config.get("WHATSAPP_SUPPORT_PHONE", "40764381795")


def _require_active_account():
    """Helper pentru a bloca marketplace pentru utilizatori neplătiți."""
    if not current_user.is_active_account():
        from flask import flash, redirect, url_for
        from menu.routes import menu_bp
        flash("Marketplace este disponibil doar pentru conturi active. Activează abonamentul pentru a accesa această funcție.", "error")
        return redirect(url_for("menu.menu_home"))
    return None


def _can_see_contact(user):
    """
    Users with active account (trial/paid) can see contact.
    Users with only free actions remaining CANNOT see contact (marketplace vizibil dar limitat).
    """
    return user.is_active_account()


def _normalize_budget(value):
    """Accept int or string with separators (100.000, 100 000); return int or None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    s = str(value).strip().replace(" ", "").replace(".", "").replace(",", "")
    if not s or not s.isdigit():
        return None
    return int(s)


def _parse_surface(value):
    """Accept string cu virgulă sau punct (ex: 45,5 sau 45.5); returnează float sau None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    s = str(value).strip().replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        f = float(s)
        return f if f >= 0 else None
    except ValueError:
        return None


def _format_surface(value):
    """Format float pentru afișare în form (ex: 45.5 -> '45,5')."""
    if value is None:
        return ""
    try:
        f = float(value)
        if f == int(f):
            return str(int(f))
        return str(f).replace(".", ",")
    except (ValueError, TypeError):
        return ""


# _is_utilizator removed - all users are agents


def _normalize_phone_display(value):
    """Normalize phone to display form (digits only, then format 07xx xxx xxx for RO 10-digit). Return None if empty/invalid."""
    if not value or not str(value).strip():
        return None
    import re
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 10 or len(digits) > 12:
        return None
    # RO 10-digit: 07xxxxxxxx -> 07xx xxx xxx
    if len(digits) == 10 and digits.startswith("07"):
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    if len(digits) == 11 and digits.startswith("40"):
        return f"+40 {digits[2:5]} {digits[5:8]} {digits[8:]}"
    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    return " ".join(digits[i : i + 3] for i in range(0, min(len(digits), 9), 3)) + (f" {digits[9:]}" if len(digits) > 9 else "")


# Grupuri zone: Sectoare (Sector 1..6, Ultracentral) separate, restul în Zone. Fără legătură cartier–sector.
ZONE_GROUP_ORDER = ["Sectoare", "Zone", "Ilfov"]


def _zones_by_group(zones):
    """Groupează zone după group. Ordine: Sectoare, Zone, Ilfov. În fiecare grup, sortare după nume."""
    from collections import OrderedDict
    groups = OrderedDict()
    for g in ZONE_GROUP_ORDER:
        groups[g] = []
    groups["Altele"] = []
    for z in zones:
        g = z.group or "Altele"
        if g not in groups:
            groups[g] = []
        groups[g].append(z)
    # Sortare după nume în fiecare grup
    for g in groups:
        groups[g] = sorted(groups[g], key=lambda x: (x.name or "").lower())
    return [(k, v) for k, v in groups.items() if v]


# --- Hub (choose Cereri or Oferte) ---
@marketplace_bp.get("/")
@login_required
def hub():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    return render_template("marketplace/hub.html")


# --- Cereri: List ---
@marketplace_bp.get("/cereri/")
@login_required
def list_requests():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    _run_expiration_cleanup()

    q = BuyerRequest.query
    # Eager-load user for display
    q = q.options(db.joinedload(BuyerRequest.user))

    # "Cererile mele"
    mine = request.args.get("mine", type=int)
    if mine:
        q = q.filter(BuyerRequest.user_id == current_user.id)

    # Search and zone filter: add joins when needed
    search = (request.args.get("q") or "").strip()
    zone_ids = request.args.getlist("zone_id", type=int)
    keywords = [k.strip() for k in search.split() if k.strip()] if search else []

    if keywords or zone_ids:
        q = q.outerjoin(RequestZones, BuyerRequest.id == RequestZones.request_id).outerjoin(Zone, RequestZones.zone_id == Zone.id)
    if keywords:
        for kw in keywords:
            term = f"%{kw}%"
            q = q.filter(
                or_(
                    BuyerRequest.description.ilike(term),
                    BuyerRequest.request_type.ilike(term),
                    BuyerRequest.property_type.ilike(term),
                    Zone.name.ilike(term),
                )
            )
    if zone_ids:
        q = q.filter(RequestZones.zone_id.in_(zone_ids))
    if keywords or zone_ids:
        q = q.distinct()

    # Filters
    req_type = (request.args.get("request_type") or "").strip()
    if req_type in ("cumparare", "inchiriere"):
        q = q.filter(BuyerRequest.request_type == req_type)

    prop_type = (request.args.get("property_type") or "").strip()
    if prop_type in ("apartament", "casa", "teren"):
        q = q.filter(BuyerRequest.property_type == prop_type)

    rooms_filter = request.args.get("rooms", type=int)
    if rooms_filter is not None and rooms_filter >= 1:
        if rooms_filter >= 4:
            q = q.filter(BuyerRequest.rooms >= 4)
        else:
            q = q.filter(BuyerRequest.rooms == rooms_filter)

    # Poster type filter removed - all users are agents

    budget_min = _normalize_budget(request.args.get("budget_min"))
    if budget_min is not None and budget_min >= 0:
        q = q.filter(BuyerRequest.budget_max >= budget_min)
    budget_max = _normalize_budget(request.args.get("budget_max"))
    if budget_max is not None and budget_max >= 0:
        q = q.filter(BuyerRequest.budget_min <= budget_max)

    urgent_filter = (request.args.get("urgent") or "").strip()
    if urgent_filter == "1":
        q = q.filter(BuyerRequest.urgent.is_(True))
    elif urgent_filter == "0":
        q = q.filter(BuyerRequest.urgent.is_(False))

    # Filter: cereri de la agenți vs clienți
    poster_type = (request.args.get("poster_type") or "").strip()
    if poster_type == "agents":
        q = q.filter(BuyerRequest.posted_by_role == "agent")
    elif poster_type == "clients":
        q = q.filter(BuyerRequest.posted_by_role == "client")
    # "all" or empty = show all

    # Filter: cereri cu comision vs fără comision (doar pentru cererile clienților)
    commission_filter = (request.args.get("commission") or "").strip()
    if commission_filter == "with_commission":
        q = q.filter(BuyerRequest.client_offers_commission.is_(True))
    elif commission_filter == "no_commission":
        q = q.filter(BuyerRequest.client_no_commission.is_(True))

    # Sort: default "fair" (rotație echitabilă), opțional "newest" sau altele
    sort = (request.args.get("sort") or "fair").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    seed_is_new = False
    seed, expires_at = None, None
    if sort == "fair":
        seed, expires_at, seed_is_new = get_marketplace_seed(request)
        total_count = q.count()
        rows = q.with_entities(BuyerRequest.id, BuyerRequest.created_at).limit(FAIR_MAX_IDS).all()
        ordered_ids = _stable_shuffle_ids(seed, rows)
        total_fair = len(ordered_ids)
        total_pages = max(1, (total_fair + PER_PAGE - 1) // PER_PAGE)
        page = min(page, total_pages)
        start = (page - 1) * PER_PAGE
        page_ids = ordered_ids[start : start + PER_PAGE]
        if page_ids:
            requests_list = BuyerRequest.query.filter(BuyerRequest.id.in_(page_ids)).options(
                db.joinedload(BuyerRequest.user)
            ).all()
            id_to_obj = {r.id: r for r in requests_list}
            requests_list = [id_to_obj[i] for i in page_ids if i in id_to_obj]
        else:
            requests_list = []
        pagination = _FairPagination(page, PER_PAGE, total_fair, requests_list)
    else:
        if sort == "budget_desc":
            q = q.order_by(BuyerRequest.budget_max.desc().nullslast(), BuyerRequest.created_at.desc())
        elif sort == "urgent_first":
            q = q.order_by(BuyerRequest.urgent.desc(), BuyerRequest.created_at.desc())
        else:
            q = q.order_by(BuyerRequest.created_at.desc())
        pagination = q.paginate(page=page, per_page=PER_PAGE, error_out=False)
        requests_list = pagination.items

    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    quota_used = _quota_used(current_user)
    quota_remaining = _quota_remaining(current_user)
    quota_limit = _quota_limit(current_user)
    wa_phone = _whatsapp_support_phone()

    pagination_query = {
        "q": search,
        "request_type": req_type,
        "property_type": prop_type,
        "rooms": rooms_filter if rooms_filter is not None else "",
        "budget_min": budget_min if budget_min is not None else "",
        "budget_max": budget_max if budget_max is not None else "",
        "urgent": urgent_filter,
        "poster_type": poster_type,
        "commission": commission_filter,
        "sort": sort,
        "mine": mine if mine else "",
    }
    if zone_ids:
        pagination_query["zone_id"] = zone_ids

    # Pass poster_type to template
    resp = make_response(
        render_template(
            "marketplace/list.html",
            requests_list=requests_list,
            pagination=pagination,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_used=quota_used,
            quota_remaining=quota_remaining,
            quota_limit=quota_limit,
            wa_phone=wa_phone,
            search=search,
            request_type=req_type,
            property_type=prop_type,
            zone_ids=zone_ids,
            budget_min=budget_min,
            budget_max=budget_max,
            rooms_filter=rooms_filter,
            urgent_filter=urgent_filter,
            poster_type=poster_type,
            commission_filter=commission_filter,
            sort=sort,
            pagination_query=pagination_query,
            mine=mine,
        )
    )
    if seed_is_new and seed:
        resp.set_cookie("mp_seed", seed, max_age=FAIR_SEED_TTL_SECONDS, samesite="Lax")
        resp.set_cookie("mp_seed_exp", str(expires_at), max_age=FAIR_SEED_TTL_SECONDS, samesite="Lax")
    return resp


# --- Cereri: New ---
@marketplace_bp.route("/cereri/new", methods=["GET", "POST"])
@login_required
def new_request():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    form = BuyerRequestForm()
    form.request_type.choices = REQUEST_TYPE_CHOICES
    form.property_type.choices = PROPERTY_TYPE_CHOICES
    form.zone_ids.choices = [(z.id, z.name) for z in zones]

    if request.method == "GET":
        quota_remaining = _quota_remaining(current_user)
        quota_limit = _quota_limit(current_user)
        if quota_remaining <= 0:
            flash(
                f"Ai atins limita de {quota_limit} cereri la 30 zile. Pentru mai multe, contactează-ne pe WhatsApp.",
                "error",
            )
            return redirect(url_for("marketplace.list_requests"))
        return render_template(
            "marketplace/form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=quota_remaining,
            quota_limit=quota_limit,
            wa_phone=_whatsapp_support_phone(),
        )

    if not form.validate_on_submit():
        if form.zone_ids.errors:
            flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "marketplace/form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=_quota_remaining(current_user),
            quota_limit=_quota_limit(current_user),
            wa_phone=_whatsapp_support_phone(),
        )

    if not _check_rate_limit():
        flash("Prea multe cereri în scurt timp. Așteaptă un minut.", "error")
        return redirect(url_for("marketplace.list_requests"))

    used = _quota_used(current_user)
    limit = _quota_limit(current_user)
    if used >= limit:
        flash(
            f"Ai atins limita de {limit} cereri la 30 zile. Pentru mai multe, contactează-ne pe WhatsApp.",
            "error",
        )
        return redirect(url_for("marketplace.list_requests"))

    zone_ids = [z for z in (form.zone_ids.data or []) if z is not None]
    if not zone_ids:
        flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "marketplace/form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=_quota_remaining(current_user),
            quota_limit=_quota_limit(current_user),
            wa_phone=_whatsapp_support_phone(),
        )

    # Asigură int sau None (form poate trimite string din input)
    budget_min = form.budget_min.data
    budget_max = form.budget_max.data
    if not isinstance(budget_min, int) and budget_min is not None:
        budget_min = _normalize_budget(str(budget_min).strip()) if str(budget_min).strip() else None
    if not isinstance(budget_max, int) and budget_max is not None:
        budget_max = _normalize_budget(str(budget_max).strip()) if str(budget_max).strip() else None
    if budget_min is not None and budget_max is not None and budget_max < budget_min:
        flash("Bugetul maxim trebuie să fie >= bugetul minim.", "error")
        return render_template(
            "marketplace/form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=_quota_remaining(current_user),
            quota_limit=_quota_limit(current_user),
            wa_phone=_whatsapp_support_phone(),
        )

    # Collaboration removed - all users are agents
    collaboration_type = None
    commission_percent = None

    contact_phone = _normalize_phone_display(request.form.get("contact_phone") or (form.contact_phone.data if form.contact_phone.data else None))
    posted_by_role = "agent"  # All users are agents

    client_phone_private = (form.client_phone_private.data or "").strip() or None
    if client_phone_private:
        client_phone_private = _normalize_phone_display(client_phone_private)
    br = BuyerRequest(
        user_id=current_user.id,
        request_type=form.request_type.data,
        property_type=form.property_type.data,
        budget_min=budget_min,
        budget_max=budget_max,
        rooms=form.rooms.data or None,
        year_min=form.year_min.data or None,
        year_max=form.year_max.data or None,
        description=(form.description.data or "").strip() or None,
        urgent=bool(form.urgent.data),
        plus_tva=bool(form.plus_tva.data),
        collaboration_type=collaboration_type,
        commission_percent=commission_percent,
        contact_phone=contact_phone,
        posted_by_role=posted_by_role,
        client_phone_private=client_phone_private,
    )
    db.session.add(br)
    db.session.flush()

    for zid in zone_ids:
        db.session.add(RequestZones(request_id=br.id, zone_id=zid))
    db.session.commit()

    run_matching_for_new_request(br.id)

    flash("Cererea a fost creată.", "success")
    return redirect(url_for("marketplace.detail", id=br.id))


# --- Cereri: Detail ---
@marketplace_bp.get("/cereri/<int:id>")
@login_required
def detail(id):
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    req = BuyerRequest.query.get_or_404(id)
    
    # Contact visibility logic:
    # 1) User with active account (trial/paid): show ONLY phone (no email/name)
    # 2) Users with only free actions: marketplace vizibil dar fără contact/detalii
    # 3) User expired: show "Reînnoiește accesul"
    has_active_access = current_user.is_active_account()
    can_view_contact_phone = has_active_access and bool(req.contact_phone)
    contact_phone = req.contact_phone if can_view_contact_phone else None
    contact_phone_digits = "".join(c for c in (req.contact_phone or "") if c.isdigit()) if can_view_contact_phone else None
    
    is_owner = req.user_id == current_user.id
    wa_phone = _whatsapp_support_phone()
    client_phone_private = getattr(req, "client_phone_private", None) if is_owner else None
    client_phone_private_digits = "".join(c for c in (client_phone_private or "") if c.isdigit()) or None

    # Increment view count if it's a client request and user is an agent
    if req.posted_by_role == "client" and current_user.is_agent and not is_owner:
        req.view_count = (req.view_count or 0) + 1
        db.session.commit()
    
    # Check if request is from a client
    is_client_request = req.posted_by_role == "client"
    client_commission_info = None
    if is_client_request:
        if req.client_no_commission:
            client_commission_info = "no_commission"
        elif req.client_offers_commission:
            client_commission_info = "offers_commission"
            if req.client_commission_value:
                client_commission_info = ("offers_commission", req.client_commission_value)
    
    return render_template(
        "marketplace/detail.html",
        req=req,
        can_view_contact_phone=can_view_contact_phone,
        contact_phone=contact_phone,
        contact_phone_digits=contact_phone_digits,
        has_active_access=has_active_access,
        is_owner=is_owner,
        wa_phone=wa_phone,
        client_phone_private=client_phone_private,
        client_phone_private_digits=client_phone_private_digits,
        is_client_request=is_client_request,
        client_commission_info=client_commission_info,
    )


# --- Cereri: Edit ---
@marketplace_bp.route("/cereri/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_request(id):
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    req = BuyerRequest.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    form = BuyerRequestForm()
    form.request_type.choices = REQUEST_TYPE_CHOICES
    form.property_type.choices = PROPERTY_TYPE_CHOICES
    form.zone_ids.choices = [(z.id, z.name) for z in zones]

    if request.method == "GET":
        form.request_type.data = req.request_type
        form.property_type.data = req.property_type
        form.zone_ids.data = [z.id for z in req.zones]
        # Format budget as string for StringField (e.g., "100.000")
        form.budget_min.data = "{:,.0f}".format(req.budget_min).replace(",", ".") if req.budget_min is not None else ""
        form.budget_max.data = "{:,.0f}".format(req.budget_max).replace(",", ".") if req.budget_max is not None else ""
        form.rooms.data = req.rooms
        form.year_min.data = req.year_min
        form.year_max.data = req.year_max
        form.description.data = req.description or ""
        form.urgent.data = req.urgent
        form.plus_tva.data = getattr(req, "plus_tva", False)
        form.contact_phone.data = req.contact_phone or ""
        form.client_phone_private.data = getattr(req, "client_phone_private", None) or ""
        return render_template(
            "marketplace/form_edit.html",
            form=form,
            req=req,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    if not form.validate_on_submit():
        if form.zone_ids.errors:
            flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "marketplace/form_edit.html",
            form=form,
            req=req,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    zone_ids = [z for z in (form.zone_ids.data or []) if z is not None]
    if not zone_ids:
        flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "marketplace/form_edit.html",
            form=form,
            req=req,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    # Normalize budget from StringField
    budget_min = None
    budget_max = None
    bmin_raw = form.budget_min.data
    bmax_raw = form.budget_max.data
    if bmin_raw is not None and (isinstance(bmin_raw, int) or str(bmin_raw).strip()):
        budget_min = bmin_raw if isinstance(bmin_raw, int) else _normalize_budget(str(bmin_raw))
    if bmax_raw is not None and (isinstance(bmax_raw, int) or str(bmax_raw).strip()):
        budget_max = bmax_raw if isinstance(bmax_raw, int) else _normalize_budget(str(bmax_raw))

    if budget_min is not None and budget_max is not None and budget_max < budget_min:
        flash("Bugetul maxim trebuie să fie >= bugetul minim.", "error")
        return render_template(
            "marketplace/form_edit.html",
            form=form,
            req=req,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    req.request_type = form.request_type.data
    req.property_type = form.property_type.data
    req.budget_min = budget_min
    req.budget_max = budget_max
    req.rooms = form.rooms.data or None
    req.year_min = form.year_min.data or None
    req.year_max = form.year_max.data or None
    req.description = (form.description.data or "").strip() or None
    req.urgent = bool(form.urgent.data)
    req.plus_tva = bool(form.plus_tva.data)
    req.contact_phone = _normalize_phone_display(request.form.get("contact_phone") or (form.contact_phone.data or ""))
    cp_private = (form.client_phone_private.data or "").strip() or None
    req.client_phone_private = _normalize_phone_display(cp_private) if cp_private else None

    # Collaboration removed - all users are agents
    req.collaboration_type = None
    req.commission_percent = None

    # Actualizează zonele - ștergem doar dacă există, folosind obiecte din sesiune
    existing_zones = RequestZones.query.filter_by(request_id=req.id).all()
    if existing_zones:
        # Ștergem doar dacă există zone existente
        for rz in existing_zones:
            db.session.delete(rz)
    
    # Adăugăm noile zone
    for zid in zone_ids:
        db.session.add(RequestZones(request_id=req.id, zone_id=zid))
    db.session.commit()

    run_matching_for_new_request(req.id)

    flash("Cererea a fost actualizată.", "success")
    return redirect(url_for("marketplace.detail", id=req.id))


# --- Cereri: Delete ---
@marketplace_bp.post("/cereri/<int:id>/delete")
@login_required
def delete_request(id):
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    req = BuyerRequest.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Nu trebuie să ștergem manual RequestZones sau PossibleCollaboration
    # Ambele au ondelete="CASCADE" în model, deci se șterg automat când ștergem BuyerRequest
    # Doar ștergem cererea și lăsăm CASCADE să se ocupe de restul
    db.session.delete(req)
    db.session.commit()
    flash("Cererea a fost ștearsă. Slotul este liber — poți adăuga altă cerere.", "success")
    return redirect(url_for("marketplace.profile_page"))


# ========== OFERTE ==========

@marketplace_bp.get("/oferte/")
@login_required
def list_offers():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    _run_offer_expiration_cleanup()

    q = SellerOffer.query.options(db.joinedload(SellerOffer.user))
    mine = request.args.get("mine", type=int)
    if mine:
        q = q.filter(SellerOffer.user_id == current_user.id)

    # Search and zone filter: add joins when needed
    search = (request.args.get("q") or "").strip()
    zone_ids = request.args.getlist("zone_id", type=int)
    keywords = [k.strip() for k in search.split() if k.strip()] if search else []

    if keywords or zone_ids:
        q = q.outerjoin(OfferZones, SellerOffer.id == OfferZones.offer_id).outerjoin(Zone, OfferZones.zone_id == Zone.id)
    if keywords:
        for kw in keywords:
            term = f"%{kw}%"
            q = q.filter(
                or_(
                    SellerOffer.description.ilike(term),
                    db.func.coalesce(SellerOffer.title, "").ilike(term),
                    SellerOffer.request_type.ilike(term),
                    SellerOffer.property_type.ilike(term),
                    Zone.name.ilike(term),
                )
            )
    if zone_ids:
        q = q.filter(OfferZones.zone_id.in_(zone_ids))
    if keywords or zone_ids:
        q = q.distinct()

    req_type = (request.args.get("request_type") or "").strip()
    if req_type in ("cumparare", "inchiriere"):
        q = q.filter(SellerOffer.request_type == req_type)
    prop_type = (request.args.get("property_type") or "").strip()
    if prop_type in ("apartament", "casa", "teren", "spatiu_comercial"):
        q = q.filter(SellerOffer.property_type == prop_type)
    rooms_filter = request.args.get("rooms", type=int)
    if rooms_filter is not None and rooms_filter >= 1:
        if rooms_filter >= 4:
            q = q.filter(SellerOffer.rooms >= 4)
        else:
            q = q.filter(SellerOffer.rooms == rooms_filter)
    price_min = _normalize_budget(request.args.get("budget_min"))  # query param stays budget_min/max
    price_max = _normalize_budget(request.args.get("budget_max"))
    if price_min is not None and price_min >= 0:
        q = q.filter(
            db.or_(
                SellerOffer.price >= price_min,
                db.and_(SellerOffer.price.is_(None), SellerOffer.budget_max >= price_min),
            )
        )
    if price_max is not None and price_max >= 0:
        q = q.filter(
            db.or_(
                SellerOffer.price <= price_max,
                db.and_(SellerOffer.price.is_(None), SellerOffer.budget_min <= price_max),
            )
        )

    # Sort: default "fair" (rotație echitabilă), opțional "newest" sau "budget_desc"
    sort = (request.args.get("sort") or "fair").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    seed_is_new = False
    seed, expires_at = None, None
    if sort == "fair":
        seed, expires_at, seed_is_new = get_marketplace_seed(request)
        rows = q.with_entities(SellerOffer.id, SellerOffer.created_at).limit(FAIR_MAX_IDS).all()
        ordered_ids = _stable_shuffle_ids(seed, rows)
        total_fair = len(ordered_ids)
        total_pages = max(1, (total_fair + PER_PAGE_OFFERS - 1) // PER_PAGE_OFFERS)
        page = min(page, total_pages)
        start = (page - 1) * PER_PAGE_OFFERS
        page_ids = ordered_ids[start : start + PER_PAGE_OFFERS]
        if page_ids:
            offers_list = SellerOffer.query.filter(SellerOffer.id.in_(page_ids)).options(
                db.joinedload(SellerOffer.user)
            ).all()
            id_to_obj = {o.id: o for o in offers_list}
            offers_list = [id_to_obj[i] for i in page_ids if i in id_to_obj]
        else:
            offers_list = []
        pagination = _FairPagination(page, PER_PAGE_OFFERS, total_fair, offers_list)
    else:
        if sort == "budget_desc":
            q = q.order_by(db.func.coalesce(SellerOffer.price, SellerOffer.budget_max).desc().nullslast(), SellerOffer.created_at.desc())
        else:
            q = q.order_by(SellerOffer.created_at.desc())
        pagination = q.paginate(page=page, per_page=PER_PAGE_OFFERS, error_out=False)
        offers_list = pagination.items

    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    offer_quota_used = _offer_quota_used(current_user)
    offer_quota_remaining = _offer_quota_remaining(current_user)
    offer_quota_limit = _offer_quota_limit(current_user)
    wa_phone = _whatsapp_support_phone()
    offer_extra_price_label = current_app.config.get("OFFER_EXTRA_PRICE_LABEL", "Contactează suportul pentru preț.")

    pagination_query = {
        "q": search,
        "request_type": req_type,
        "property_type": prop_type,
        "rooms": rooms_filter if rooms_filter is not None else "",
        "budget_min": price_min if price_min is not None else "",
        "budget_max": price_max if price_max is not None else "",
        "sort": sort,
        "mine": mine if mine else "",
    }
    if zone_ids:
        pagination_query["zone_id"] = zone_ids

    resp = make_response(
        render_template(
            "marketplace/offers_list.html",
            offers_list=offers_list,
            pagination=pagination,
            zones=zones,
            zones_by_group=zones_by_group,
            offer_quota_used=offer_quota_used,
            offer_quota_remaining=offer_quota_remaining,
            offer_quota_limit=offer_quota_limit,
            wa_phone=wa_phone,
            offer_extra_price_label=offer_extra_price_label,
            search=search,
            zone_ids=zone_ids,
            pagination_query=pagination_query,
            mine=mine,
            request_type=req_type,
            property_type=prop_type,
            rooms_filter=rooms_filter,
            budget_min=price_min,
            budget_max=price_max,
            sort=sort,
        )
    )
    if seed_is_new and seed:
        resp.set_cookie("mp_seed", seed, max_age=FAIR_SEED_TTL_SECONDS, samesite="Lax")
        resp.set_cookie("mp_seed_exp", str(expires_at), max_age=FAIR_SEED_TTL_SECONDS, samesite="Lax")
    return resp


def _etaj_from_request():
    """Etaj from form: list of values -> comma-separated string."""
    vals = request.form.getlist("etaj")
    if not vals:
        return None
    return ",".join(str(v).strip() for v in vals if str(v).strip())


@marketplace_bp.get("/profilul-meu")
@login_required
def profile_page():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    """Pagină unică „Profilul meu”: rezumat anunțuri + cereri, listele cu edit/delete, contact."""
    _run_offer_expiration_cleanup()
    _run_expiration_cleanup()
    has_access = current_user.has_access()
    # Anunțuri (doar dacă are acces)
    offer_used = _offer_quota_used(current_user)
    offer_limit = _offer_quota_limit(current_user)
    offer_remaining = _offer_quota_remaining(current_user)
    offer_paid_slots = _offer_paid_slots_effective(current_user)
    offer_paid_expires = getattr(current_user, "offer_paid_slots_expires_at", None)
    cutoff_offer = _utcnow() - timedelta(days=OFFER_EXPIRE_DAYS)
    offers_list = (
        SellerOffer.query.filter(
            SellerOffer.user_id == current_user.id,
            SellerOffer.created_at >= cutoff_offer,
        ).order_by(SellerOffer.created_at.desc()).all()
        if has_access
        else []
    )
    # Cereri
    request_used = _quota_used(current_user)
    request_limit = _quota_limit(current_user)
    request_remaining = _quota_remaining(current_user)
    request_paid_slots = _request_paid_slots_effective(current_user)
    request_paid_expires = getattr(current_user, "request_paid_slots_expires_at", None)
    cutoff_req = _utcnow() - timedelta(days=QUOTA_DAYS)
    requests_list = BuyerRequest.query.filter(
        BuyerRequest.user_id == current_user.id,
        BuyerRequest.created_at >= cutoff_req,
    ).order_by(BuyerRequest.created_at.desc()).all()
    wa_phone = _whatsapp_support_phone()
    return render_template(
        "marketplace/profile.html",
        has_access=has_access,
        offer_used=offer_used,
        offer_limit=offer_limit,
        offer_remaining=offer_remaining,
        offer_paid_slots=offer_paid_slots,
        offer_paid_expires=offer_paid_expires,
        offers_list=offers_list,
        request_used=request_used,
        request_limit=request_limit,
        request_remaining=request_remaining,
        request_paid_slots=request_paid_slots,
        request_paid_expires=request_paid_expires,
        requests_list=requests_list,
        wa_phone=wa_phone,
        OFFER_FREE_SLOTS=OFFER_FREE_SLOTS,
        REQUEST_FREE_SLOTS=REQUEST_FREE_SLOTS,
    )


@marketplace_bp.get("/anunturile-mele")
@login_required
def my_offers_page():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    """Redirect către Profilul meu."""
    return redirect(url_for("marketplace.profile_page"))


@marketplace_bp.get("/cererile-mele")
@login_required
def my_requests_page():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    """Redirect către Profilul meu."""
    return redirect(url_for("marketplace.profile_page"))


@marketplace_bp.route("/oferte/new", methods=["GET", "POST"])
@login_required
def new_offer():
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response

    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    form = SellerOfferForm()
    form.request_type.choices = REQUEST_TYPE_ANUNT_CHOICES
    form.property_type.choices = PROPERTY_TYPE_ANUNT_CHOICES
    form.zone_ids.choices = [(z.id, z.name) for z in zones]

    if request.method == "GET":
        quota_remaining = _offer_quota_remaining(current_user)
        quota_limit = _offer_quota_limit(current_user)
        if quota_remaining <= 0:
            flash(
                f"Ai atins limita de {quota_limit} anunțuri gratuite. Pentru mai multe, contactează-ne pe WhatsApp.",
                "error",
            )
            return redirect(url_for("marketplace.list_offers"))
        return render_template(
            "marketplace/offer_form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=quota_remaining,
            quota_limit=quota_limit,
            wa_phone=_whatsapp_support_phone(),
        )

    if not form.validate_on_submit():
        if form.zone_ids.errors:
            flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "marketplace/offer_form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=_offer_quota_remaining(current_user),
            quota_limit=_offer_quota_limit(current_user),
            wa_phone=_whatsapp_support_phone(),
        )

    used = _offer_quota_used(current_user)
    limit = _offer_quota_limit(current_user)
    if used >= limit:
        flash(
            f"Ai atins limita de {limit} anunțuri. Pentru mai multe, contactează-ne pe WhatsApp.",
            "error",
        )
        return redirect(url_for("marketplace.list_offers"))

    zone_ids = [z for z in (form.zone_ids.data or []) if z is not None]
    if not zone_ids:
        flash("Selectează cel puțin o zonă.", "error")
        return render_template(
            "marketplace/offer_form_new.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            quota_remaining=_offer_quota_remaining(current_user),
            quota_limit=_offer_quota_limit(current_user),
            wa_phone=_whatsapp_support_phone(),
        )

    contact_phone = _normalize_phone_display(request.form.get("contact_phone") or (form.contact_phone.data or ""))
    price_val = form.price.data  # already int from validator
    etaj_val = _etaj_from_request()

    offer = SellerOffer(
        user_id=current_user.id,
        request_type=form.request_type.data,
        property_type=form.property_type.data,
        price=price_val,
        budget_min=price_val,
        budget_max=price_val,
        price_negotiable=bool(form.price_negotiable.data),
        plus_tva=bool(form.plus_tva.data),
        rooms=form.rooms.data or None,
        anul_constructiei=form.anul_constructiei.data or None,
        surface_utila=_parse_surface(form.surface_utila.data),
        surface_totala=_parse_surface(form.surface_totala.data),
        surface_balcon=_parse_surface(form.surface_balcon.data),
        surface_terasa=_parse_surface(form.surface_terasa.data),
        surface_curte=_parse_surface(form.surface_curte.data),
        etaj=etaj_val if etaj_val and form.property_type.data != "casa" else None,
        nr_etaje_cladire=form.nr_etaje_cladire.data or None,
        nr_locuri_parcare=form.nr_locuri_parcare.data or None,
        offers_commission=bool(form.offers_commission.data),
        commission_value=(form.commission_value.data or "").strip() or None,
        description=(form.description.data or "").strip() or None,
        contact_phone=contact_phone,
        owner_name_private=(form.owner_name_private.data or "").strip() or None,
    )
    db.session.add(offer)
    db.session.flush()
    for zid in zone_ids:
        db.session.add(OfferZones(offer_id=offer.id, zone_id=zid))
    db.session.commit()

    run_matching_for_new_offer(offer.id)

    flash("Anunțul a fost creat.", "success")
    return redirect(url_for("marketplace.detail_offer", id=offer.id))


@marketplace_bp.get("/oferte/<int:id>")
@login_required
def detail_offer(id):
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    offer = SellerOffer.query.get_or_404(id)
    has_active_access = current_user.is_active_account()
    can_view_contact_phone = has_active_access and bool(offer.contact_phone)
    contact_phone = offer.contact_phone if can_view_contact_phone else None
    contact_phone_digits = "".join(c for c in (offer.contact_phone or "") if c.isdigit()) if can_view_contact_phone else None
    is_owner = offer.user_id == current_user.id
    wa_phone = _whatsapp_support_phone()
    return render_template(
        "marketplace/offer_detail.html",
        offer=offer,
        has_active_access=has_active_access,
        can_view_contact_phone=can_view_contact_phone,
        contact_phone=contact_phone,
        contact_phone_digits=contact_phone_digits,
        is_owner=is_owner,
        wa_phone=wa_phone,
    )


@marketplace_bp.route("/oferte/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_offer(id):
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    offer = SellerOffer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    form = SellerOfferForm()
    form.request_type.choices = REQUEST_TYPE_ANUNT_CHOICES
    form.property_type.choices = PROPERTY_TYPE_ANUNT_CHOICES
    form.zone_ids.choices = [(z.id, z.name) for z in zones]

    if request.method == "GET":
        form.request_type.data = offer.request_type
        form.property_type.data = offer.property_type
        form.zone_ids.data = [z.id for z in offer.zones]
        form.price.data = (offer.price or offer.budget_min) if (offer.price or offer.budget_min) else None
        form.price_negotiable.data = getattr(offer, "price_negotiable", False)
        form.plus_tva.data = getattr(offer, "plus_tva", False)
        form.rooms.data = offer.rooms
        form.surface_utila.data = _format_surface(offer.surface_utila)
        form.surface_totala.data = _format_surface(offer.surface_totala)
        form.surface_balcon.data = _format_surface(offer.surface_balcon)
        form.surface_terasa.data = _format_surface(offer.surface_terasa)
        form.surface_curte.data = _format_surface(offer.surface_curte)
        form.anul_constructiei.data = offer.anul_constructiei
        form.nr_etaje_cladire.data = offer.nr_etaje_cladire
        form.nr_locuri_parcare.data = offer.nr_locuri_parcare
        form.offers_commission.data = offer.offers_commission
        form.commission_value.data = offer.commission_value or ""
        form.description.data = offer.description or ""
        form.contact_phone.data = offer.contact_phone or ""
        form.owner_name_private.data = getattr(offer, "owner_name_private", None) or ""
        offer_etaj_list = [x.strip() for x in (offer.etaj or "").replace("P", "Parter").split(",") if x.strip()]
        return render_template(
            "marketplace/offer_form_edit.html",
            form=form,
            offer=offer,
            offer_etaj_list=offer_etaj_list,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    if not form.validate_on_submit():
        if form.zone_ids.errors:
            flash("Trebuie să selectezi cel puțin o zonă.", "error")
        offer_etaj_list = [x.strip() for x in (offer.etaj or "").replace("P", "Parter").split(",") if x.strip()]
        return render_template(
            "marketplace/offer_form_edit.html",
            form=form,
            offer=offer,
            offer_etaj_list=offer_etaj_list,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    zone_ids = [z for z in (form.zone_ids.data or []) if z is not None]
    if not zone_ids:
        offer_etaj_list = [x.strip() for x in (offer.etaj or "").replace("P", "Parter").split(",") if x.strip()]
        flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "marketplace/offer_form_edit.html",
            form=form,
            offer=offer,
            offer_etaj_list=offer_etaj_list,
            zones=zones,
            zones_by_group=zones_by_group,
        )

    contact_phone = _normalize_phone_display(request.form.get("contact_phone") or (form.contact_phone.data or ""))
    price_val = form.price.data
    etaj_val = _etaj_from_request() if form.property_type.data != "casa" else None

    offer.request_type = form.request_type.data
    offer.property_type = form.property_type.data
    offer.price = price_val
    offer.budget_min = price_val
    offer.budget_max = price_val
    offer.price_negotiable = bool(form.price_negotiable.data)
    offer.plus_tva = bool(form.plus_tva.data)
    offer.rooms = form.rooms.data or None
    offer.anul_constructiei = form.anul_constructiei.data or None
    offer.surface_utila = _parse_surface(form.surface_utila.data)
    offer.surface_totala = _parse_surface(form.surface_totala.data)
    offer.surface_balcon = _parse_surface(form.surface_balcon.data)
    offer.surface_terasa = _parse_surface(form.surface_terasa.data)
    offer.surface_curte = _parse_surface(form.surface_curte.data)
    offer.etaj = etaj_val
    offer.nr_etaje_cladire = form.nr_etaje_cladire.data or None
    offer.nr_locuri_parcare = form.nr_locuri_parcare.data or None
    offer.offers_commission = bool(form.offers_commission.data)
    offer.commission_value = (form.commission_value.data or "").strip() or None
    offer.description = (form.description.data or "").strip() or None
    offer.contact_phone = contact_phone
    offer.owner_name_private = (form.owner_name_private.data or "").strip() or None
    OfferZones.query.filter_by(offer_id=offer.id).delete()
    for zid in zone_ids:
        db.session.add(OfferZones(offer_id=offer.id, zone_id=zid))
    db.session.commit()

    run_matching_for_new_offer(offer.id)

    flash("Anunțul a fost actualizat.", "success")
    return redirect(url_for("marketplace.detail_offer", id=offer.id))


@marketplace_bp.post("/oferte/<int:id>/delete")
@login_required
def delete_offer(id):
    redirect_response = _require_active_account()
    if redirect_response:
        return redirect_response
    offer = SellerOffer.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(offer)
    db.session.commit()
    flash("Anunțul a fost șters. Slotul este liber — poți adăuga alt anunț.", "success")
    return redirect(url_for("marketplace.profile_page"))
