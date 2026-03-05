import uuid
import logging
from flask import render_template, request, redirect, url_for, flash, make_response, session
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, UserProfile, DeviceTrial, utcnow
from . import auth_bp

from device_guard import enforce_device_limit, get_device_id

_log = logging.getLogger(__name__)


COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2  # 2 ani
MAX_TRIALS_PER_DEVICE = 2


def _set_device_cookie(resp, device_id: str):
    """
    Setează cookie-ul device_id pe response.
    NOTE: secure=True înseamnă că se setează doar pe HTTPS (Railway e ok).
    Dacă testezi local pe http://, cookie-ul poate să nu se seteze.
    """
    resp.set_cookie(
        "device_id",
        device_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=True,
    )
    return resp


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        # ✅ acceptare termeni
        accept_terms = request.form.get("accept_terms")
        if not accept_terms:
            flash("Trebuie să accepți termenii și condițiile.", "error")
            return render_template("register.html", full_name=full_name, email=email)

        # validări
        if not full_name or not email or not password:
            flash("Completează nume, email și parolă.", "error")
            return render_template("register.html", full_name=full_name, email=email)

        # Permite același email pentru conturi diferite (agent vs client)
        # Verifică doar dacă există deja un cont cu același email și același rol
        existing = User.query.filter_by(email=email, role="agent").first()
        if existing:
            flash("Există deja un cont de agent cu email-ul ăsta.", "error")
            return render_template("register.html", full_name=full_name, email=email)

        # ---- DEVICE ID (pentru max 2 trial-uri per device) ----
        device_id = get_device_id()
        if not device_id:
            device_id = uuid.uuid4().hex  # generăm noi dacă lipsește

        dt = DeviceTrial.query.filter_by(device_id=device_id).first()
        if not dt:
            dt = DeviceTrial(device_id=device_id, trial_count=0)
            db.session.add(dt)
            db.session.flush()

        # All users are agents (utilizator role removed)
        role = "agent"

        # ---- Creează user cu trial pe acțiuni (1× chirie, 1× vânzare) ----
        # NU mai dăm trial pe zile - doar trial pe acțiuni (1× chirie, 1× vânzare)
        # DAR: dacă device-ul a depășit limita (MAX_TRIALS_PER_DEVICE), nu mai dăm acțiuni gratuite
        has_exceeded_limit = dt.trial_count >= MAX_TRIALS_PER_DEVICE
        
        u = User(
            full_name=full_name, 
            email=email, 
            role=role,
            free_rental_viewing_used=has_exceeded_limit,  # Dacă a depășit limita, marchează ca folosit
            free_sale_viewing_used=has_exceeded_limit,     # Dacă a depășit limita, marchează ca folosit
            trial_ends_at=None,  # EXPLICIT: NU setăm trial pe zile
            paid_ends_at=None    # EXPLICIT: NU setăm paid
        )
        u.set_password(password)
        # NU mai apelăm u.start_trial(7) - utilizatorul nou nu primește trial pe zile
        
        # VERIFICARE EXPLICITĂ: asigură-te că trial_ends_at rămâne None
        assert u.trial_ends_at is None, "trial_ends_at trebuie să fie None pentru utilizatori noi"

        # profil separat per user (agent/agency + semnături)
        u.profile = UserProfile()

        db.session.add(u)

        # Incrementăm trial_count pentru tracking (chiar dacă a depășit limita, permitem contul dar fără acțiuni gratuite)
        dt.trial_count += 1
        
        # Mesaj informativ dacă a depășit limita
        if has_exceeded_limit:
            flash("Cont creat cu succes. Pentru acces gratuit, contactează suportul.", "info")

        db.session.commit()
        
        # VERIFICARE DUPĂ COMMIT: asigură-te că trial_ends_at nu a fost setat automat
        db.session.refresh(u)  # Reîncarcă din DB pentru a vedea valorile reale
        if u.trial_ends_at is not None:
            # Dacă trial_ends_at a fost setat automat (probabil trigger în DB), îl resetăm
            _log.warning(f"trial_ends_at a fost setat automat pentru user {u.id} ({u.email}), resetăm la None")
            u.trial_ends_at = None
            db.session.commit()
            db.session.refresh(u)  # Reîncarcă din nou pentru a confirma

        login_user(u, remember=True)

        # limită device-uri per user (3)
        # Important: asta poate face redirect/logout dacă depășește
        ok = enforce_device_limit()
        if not ok:
            return redirect(url_for("auth.login"))

        # All users redirect to home (utilizator role removed)
        resp = make_response(redirect(url_for("home")))
        return _set_device_cookie(resp, device_id)

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash("Email sau parolă greșite.", "error")
            return render_template("login.html", email=email)

        # dacă e user vechi și nu are profil, îl creăm acum
        if getattr(u, "profile", None) is None:
            u.profile = UserProfile()
            db.session.commit()

        # actualizăm last_login_at la autentificare
        if hasattr(u, "last_login_at"):
            u.last_login_at = utcnow()
            db.session.commit()

        login_user(u, remember=True)
        session["session_version"] = getattr(u, "session_version", 1)

        # limită device-uri (3). Dacă depășește, îl scoate din login.
        ok = enforce_device_limit()
        if not ok:
            return redirect(url_for("auth.login"))

        # asigurăm device_id cookie (util pt trial-limit logic / tracking)
        device_id = get_device_id()
        if not device_id:
            device_id = uuid.uuid4().hex

        next_url = request.args.get("next")
        if not next_url:
            next_url = url_for("home")
        resp = make_response(redirect(next_url))
        return _set_device_cookie(resp, device_id)

    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))
