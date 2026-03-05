import uuid
import logging
from datetime import datetime, timedelta, timezone
from flask import render_template, request, redirect, url_for, flash, make_response, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func

from extensions import db
from models import User, BuyerRequest, Zone, RequestZones, utcnow
from access_control import client_required
from marketplace.forms import BuyerRequestForm, REQUEST_TYPE_CHOICES, PROPERTY_TYPE_CHOICES
from marketplace.routes import _normalize_budget, _normalize_phone_display, _zones_by_group
from . import client_bp

from device_guard import enforce_device_limit, get_device_id

_log = logging.getLogger(__name__)

COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2  # 2 ani


def _set_device_cookie(resp, device_id: str):
    """Setează cookie-ul device_id pe response."""
    resp.set_cookie(
        "device_id",
        device_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=True,
    )
    return resp


@client_bp.route("/")
def landing():
    """Landing page dedicat pentru clienți."""
    if current_user.is_authenticated:
        if current_user.is_client:
            return redirect(url_for("client.home"))
        else:
            return redirect(url_for("home"))
    return render_template("client/landing.html")


@client_bp.route("/register", methods=["GET", "POST"])
def register():
    """Înregistrare cont client."""
    if current_user.is_authenticated:
        if current_user.is_client:
            return redirect(url_for("client.home"))
        else:
            return redirect(url_for("home"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        password = (request.form.get("password") or "").strip()

        # Acceptare termeni
        accept_terms = request.form.get("accept_terms")
        if not accept_terms:
            flash("Trebuie să accepți termenii și condițiile.", "error")
            return render_template("client/register.html", full_name=full_name, email=email, phone=phone)

        # Validări
        if not full_name or not email or not password or not phone:
            flash("Completează toate câmpurile obligatorii.", "error")
            return render_template("client/register.html", full_name=full_name, email=email, phone=phone)

        # Validare telefon
        import re
        phone_digits = re.sub(r"\D", "", phone)
        if len(phone_digits) < 10:
            flash("Introdu un număr de telefon valid (minim 10 cifre).", "error")
            return render_template("client/register.html", full_name=full_name, email=email, phone=phone)

        # Permite același email pentru conturi diferite (agent vs client)
        # Verifică doar dacă există deja un cont client cu același email
        existing_client = User.query.filter_by(email=email, role="client").first()
        if existing_client:
            flash("Există deja un cont client cu email-ul ăsta.", "error")
            return render_template("client/register.html", full_name=full_name, email=email, phone=phone)

        # Creează user client
        u = User(
            full_name=full_name,
            email=email,
            phone=phone,
            role="client",
            free_rental_viewing_used=True,  # Clienții nu au acces la fișe de vizionare
            free_sale_viewing_used=True,
            trial_ends_at=None,
            paid_ends_at=None
        )
        u.set_password(password)

        # Clienții nu au profil de agent
        # Nu creăm UserProfile pentru clienți

        db.session.add(u)
        db.session.commit()

        login_user(u, remember=True)

        # Limită device-uri (3)
        ok = enforce_device_limit()
        if not ok:
            return redirect(url_for("client.login"))

        device_id = get_device_id()
        if not device_id:
            device_id = uuid.uuid4().hex

        resp = make_response(redirect(url_for("client.home")))
        return _set_device_cookie(resp, device_id)

    return render_template("client/register.html")


@client_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login pentru clienți."""
    if current_user.is_authenticated:
        if current_user.is_client:
            return redirect(url_for("client.home"))
        else:
            return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash("Email sau parolă greșite.", "error")
            return render_template("client/login.html", email=email)

        # Verifică dacă e client
        if u.is_agent:
            flash("Acest cont este pentru agenți. Folosește pagina de login pentru agenți.", "error")
            return redirect(url_for("auth.login"))

        # Actualizăm last_login_at
        if hasattr(u, "last_login_at"):
            u.last_login_at = utcnow()
            db.session.commit()

        login_user(u, remember=True)
        session["session_version"] = getattr(u, "session_version", 1)

        # Limită device-uri
        ok = enforce_device_limit()
        if not ok:
            return redirect(url_for("client.login"))

        device_id = get_device_id()
        if not device_id:
            device_id = uuid.uuid4().hex

        next_url = request.args.get("next")
        if not next_url:
            next_url = url_for("client.home")
        resp = make_response(redirect(next_url))
        return _set_device_cookie(resp, device_id)

    return render_template("client/login.html")


@client_bp.route("/home")
@login_required
@client_required
def home():
    """Home page pentru clienți - lista cererilor."""
    # Obține cererile active ale clientului (mai noi de 30 zile)
    cutoff = utcnow() - timedelta(days=30)
    requests = BuyerRequest.query.filter(
        BuyerRequest.user_id == current_user.id,
        BuyerRequest.created_at >= cutoff
    ).order_by(BuyerRequest.created_at.desc()).all()

    # Verifică câte cereri poate mai crea în luna curentă
    now = utcnow()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    requests_this_month = BuyerRequest.query.filter(
        BuyerRequest.user_id == current_user.id,
        BuyerRequest.created_at >= month_start
    ).count()
    can_create_more = requests_this_month < 2

    return render_template("client/home.html", requests=requests, can_create_more=can_create_more, requests_this_month=requests_this_month)


@client_bp.route("/termeni")
def terms():
    """Termeni și condiții pentru clienți."""
    return render_template("client/terms.html", last_updated=datetime.now().strftime("%d.%m.%Y"))


@client_bp.route("/logout", methods=["GET"])
@login_required
@client_required
def logout():
    """Logout pentru clienți."""
    logout_user()
    return redirect(url_for("client.landing"))


@client_bp.route("/account", methods=["GET", "POST"])
@login_required
@client_required
def account_settings():
    """Setări cont client."""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_profile":
            full_name = (request.form.get("full_name") or "").strip()
            phone = (request.form.get("phone") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            
            if not full_name or not phone or not email:
                flash("Completează toate câmpurile.", "error")
                return redirect(url_for("client.account_settings"))
            
            # Validare telefon
            import re
            phone_digits = re.sub(r"\D", "", phone)
            if len(phone_digits) < 10:
                flash("Introdu un număr de telefon valid.", "error")
                return redirect(url_for("client.account_settings"))
            
            # Verifică dacă email-ul este deja folosit de alt user
            existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_user:
                flash("Există deja un cont cu acest email.", "error")
                return redirect(url_for("client.account_settings"))
            
            current_user.full_name = full_name
            current_user.phone = phone
            current_user.email = email
            db.session.commit()
            flash("Datele au fost actualizate.", "success")
            return redirect(url_for("client.account_settings"))
        
        elif action == "change_password":
            current_password = request.form.get("current_password", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()
            
            if not current_user.check_password(current_password):
                flash("Parola curentă este greșită.", "error")
                return redirect(url_for("client.account_settings"))
            
            if not new_password or len(new_password) < 6:
                flash("Parola nouă trebuie să aibă minim 6 caractere.", "error")
                return redirect(url_for("client.account_settings"))
            
            if new_password != confirm_password:
                flash("Parolele nu coincid.", "error")
                return redirect(url_for("client.account_settings"))
            
            current_user.set_password(new_password)
            db.session.commit()
            flash("Parola a fost schimbată.", "success")
            return redirect(url_for("client.account_settings"))
        
        elif action == "delete_account":
            # Șterge toate cererile clientului
            BuyerRequest.query.filter_by(user_id=current_user.id).delete()
            
            # Șterge user-ul
            db.session.delete(current_user)
            db.session.commit()
            
            logout_user()
            flash("Contul tău a fost șters.", "success")
            return redirect(url_for("client.landing"))
    
    return render_template("client/account_settings.html")


def _check_request_quota():
    """Verifică dacă clientul poate crea o cerere nouă (max 2 pe lună)."""
    now = utcnow()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    count = BuyerRequest.query.filter(
        BuyerRequest.user_id == current_user.id,
        BuyerRequest.created_at >= month_start
    ).count()
    
    return count < 2


@client_bp.route("/cereri/new", methods=["GET", "POST"])
@login_required
@client_required
def new_request():
    """Formular pentru crearea unei cereri noi de către client."""
    if not _check_request_quota():
        flash("Ai atins limita de 2 cereri pe lună. Poți publica o cerere nouă luna viitoare sau șterge una dintre cererile existente.", "error")
        return redirect(url_for("client.home"))
    
    zones = Zone.query.order_by(Zone.group, Zone.name).all()
    zones_by_group = _zones_by_group(zones)
    form = BuyerRequestForm()
    form.request_type.choices = REQUEST_TYPE_CHOICES
    form.property_type.choices = PROPERTY_TYPE_CHOICES
    form.zone_ids.choices = [(z.id, z.name) for z in zones]
    
    if request.method == "GET":
        return render_template(
            "client/request_form.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            client_request=None,
        )
    
    if not form.validate_on_submit():
        if form.zone_ids.errors:
            flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "client/request_form.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            client_request=None,
        )
    
    # Verifică quota din nou înainte de creare
    if not _check_request_quota():
        flash("Ai atins limita de 2 cereri pe lună.", "error")
        return redirect(url_for("client.home"))
    
    # Procesează zonele din formular (pot veni din modal)
    zone_ids = request.form.getlist("zone_ids")
    zone_ids = [int(z) for z in zone_ids if z and z.isdigit()]
    if not zone_ids:
        flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "client/request_form.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            client_request=None,
        )
    
    # Normalizează bugetul
    budget_min = form.budget_min.data
    budget_max = form.budget_max.data
    if not isinstance(budget_min, int) and budget_min is not None:
        budget_min = _normalize_budget(str(budget_min).strip()) if str(budget_min).strip() else None
    if not isinstance(budget_max, int) and budget_max is not None:
        budget_max = _normalize_budget(str(budget_max).strip()) if str(budget_max).strip() else None
    
    # Procesează comisionul - verifică explicit dacă valoarea este "1"
    commission_option = request.form.get("commission_option", "").strip()
    if commission_option == "offers":
        client_offers_commission = True
        client_no_commission = False
        client_commission_value = (request.form.get("client_commission_value") or "").strip() or None
    elif commission_option == "none":
        client_offers_commission = False
        client_no_commission = True
        client_commission_value = None
    else:
        # Fallback la valorile hidden (pentru compatibilitate)
        client_offers_commission = request.form.get("client_offers_commission") == "1"
        client_no_commission = request.form.get("client_no_commission") == "1"
        client_commission_value = (request.form.get("client_commission_value") or "").strip() or None
        if client_no_commission:
            client_commission_value = None
    
    # Procesează etajele
    etaj_values = request.form.getlist("etaj_values")
    etaj_str = ",".join([v.strip() for v in etaj_values if v.strip()]) or None
    
    # Creează cererea
    br = BuyerRequest(
        user_id=current_user.id,
        request_type=form.request_type.data,
        property_type=form.property_type.data,
        budget_min=budget_min,
        budget_max=budget_max,
        rooms=form.rooms.data or None,
        year_min=form.year_min.data or None,
        year_max=None,  # Nu mai folosim year_max pentru clienți
        etaj=etaj_str,
        description=(form.description.data or "").strip() or None,
        urgent=bool(form.urgent.data),
        plus_tva=bool(form.plus_tva.data),
        contact_phone=_normalize_phone_display(current_user.phone),  # Folosește telefonul din cont
        posted_by_role="client",
        client_offers_commission=client_offers_commission,
        client_commission_value=client_commission_value,
        client_no_commission=client_no_commission,
        view_count=0,
    )
    db.session.add(br)
    db.session.flush()
    
    # Adaugă zonele
    for zone_id in zone_ids:
        rz = RequestZones(request_id=br.id, zone_id=zone_id)
        db.session.add(rz)
    
    db.session.commit()
    
    # Rulează matching pentru a găsi potriviri cu anunțurile agenților
    from marketplace.matching import run_matching_for_new_request
    run_matching_for_new_request(br.id)
    
    flash("Cererea ta a fost publicată cu succes!", "success")
    return redirect(url_for("client.home"))


@client_bp.route("/cereri/<int:request_id>/edit", methods=["GET", "POST"])
@login_required
@client_required
def edit_request(request_id):
    """Editare cerere client."""
    req = BuyerRequest.query.filter_by(id=request_id, user_id=current_user.id).first_or_404()
    
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
        form.budget_min.data = req.budget_min
        form.budget_max.data = req.budget_max
        form.rooms.data = req.rooms
        form.year_min.data = req.year_min
        form.year_max.data = None  # Nu mai folosim year_max
        form.description.data = req.description
        # Etajele vor fi procesate din request.form.getlist("etaj_values")
        form.urgent.data = req.urgent
        form.plus_tva.data = req.plus_tva
        return render_template(
            "client/request_form.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            client_request=req,
        )
    
    if not form.validate_on_submit():
        if form.zone_ids.errors:
            flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "client/request_form.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            client_request=req,
        )
    
    # Procesează zonele din formular (pot veni din modal)
    zone_ids = request.form.getlist("zone_ids")
    zone_ids = [int(z) for z in zone_ids if z and z.isdigit()]
    if not zone_ids:
        flash("Trebuie să selectezi cel puțin o zonă.", "error")
        return render_template(
            "client/request_form.html",
            form=form,
            zones=zones,
            zones_by_group=zones_by_group,
            client_request=req,
        )
    
    # Actualizează cererea
    budget_min = form.budget_min.data
    budget_max = form.budget_max.data
    if not isinstance(budget_min, int) and budget_min is not None:
        budget_min = _normalize_budget(str(budget_min).strip()) if str(budget_min).strip() else None
    if not isinstance(budget_max, int) and budget_max is not None:
        budget_max = _normalize_budget(str(budget_max).strip()) if str(budget_max).strip() else None
    
    # Procesează comisionul - verifică explicit dacă valoarea este "1"
    commission_option = request.form.get("commission_option", "").strip()
    if commission_option == "offers":
        client_offers_commission = True
        client_no_commission = False
        client_commission_value = (request.form.get("client_commission_value") or "").strip() or None
    elif commission_option == "none":
        client_offers_commission = False
        client_no_commission = True
        client_commission_value = None
    else:
        # Fallback la valorile hidden (pentru compatibilitate)
        client_offers_commission = request.form.get("client_offers_commission") == "1"
        client_no_commission = request.form.get("client_no_commission") == "1"
        client_commission_value = (request.form.get("client_commission_value") or "").strip() or None
        if client_no_commission:
            client_commission_value = None
    
    # Procesează etajele
    etaj_values = request.form.getlist("etaj_values")
    etaj_str = ",".join([v.strip() for v in etaj_values if v.strip()]) or None
    
    req.request_type = form.request_type.data
    req.property_type = form.property_type.data
    req.budget_min = budget_min
    req.budget_max = budget_max
    req.rooms = form.rooms.data or None
    req.year_min = form.year_min.data or None
    req.year_max = None  # Nu mai folosim year_max pentru clienți
    req.etaj = etaj_str
    req.description = (form.description.data or "").strip() or None
    req.urgent = bool(form.urgent.data)
    req.plus_tva = bool(form.plus_tva.data)
    req.client_offers_commission = client_offers_commission
    req.client_commission_value = client_commission_value
    req.client_no_commission = client_no_commission
    
    # Actualizează zonele - ștergem doar dacă există, folosind query care nu verifică numărul de rânduri
    # Folosim query direct cu synchronize_session=False pentru a evita StaleDataError
    existing_zones = RequestZones.query.filter_by(request_id=req.id).all()
    if existing_zones:
        # Ștergem doar dacă există zone existente
        for rz in existing_zones:
            db.session.delete(rz)
    
    # Adăugăm noile zone
    for zone_id in zone_ids:
        rz = RequestZones(request_id=req.id, zone_id=zone_id)
        db.session.add(rz)
    
    db.session.commit()
    
    # Rulează matching pentru a actualiza potrivirile cu anunțurile agenților
    from marketplace.matching import run_matching_for_new_request
    run_matching_for_new_request(req.id)
    
    flash("Cererea a fost actualizată cu succes!", "success")
    return redirect(url_for("client.home"))


@client_bp.route("/cereri/<int:request_id>/delete", methods=["POST"])
@login_required
@client_required
def delete_request(request_id):
    """Ștergere cerere client."""
    req = BuyerRequest.query.filter_by(id=request_id, user_id=current_user.id).first_or_404()
    req_id = req.id  # Salvează ID-ul înainte de a șterge
    
    # Șterge potrivirile asociate (PossibleCollaboration) - trebuie șterse manual
    from models import PossibleCollaboration
    from sqlalchemy import text
    try:
        db.session.execute(text("DELETE FROM possible_collaboration WHERE request_id = :req_id"), {"req_id": req_id})
    except Exception:
        pass  # Ignoră dacă nu există rânduri de șters
    
    # Șterge cererea - RequestZones se șterge automat prin CASCADE
    # Nu ștergem manual RequestZones pentru că are ondelete="CASCADE" în model
    db.session.delete(req)
    db.session.commit()
    
    flash("Cererea a fost ștearsă.", "success")
    return redirect(url_for("client.home"))
