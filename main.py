import os
from datetime import date

from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix

from flask_login import logout_user, current_user
from extensions import db, login_manager, migrate, csrf
from models import User

from auth import auth_bp
from account import account_bp
from menu.routes import menu_bp
from todo import todo_bp
from team import team_bp
from client import client_bp

from fise.chirie.routes import chirie_bp
from fise.vanzare.routes import vanzare_bp
from fise.contract_inchiriere.routes import contract_bp
from fise.prestari_servicii.routes import prestari_bp
from admin import admin_bp
from marketplace import marketplace_bp
from assistant import assistant_bp
from contract_templates import contract_templates_bp
from pdf_viewer import pdf_viewer_bp


def is_production_env() -> bool:
    # Railway de obicei nu setează FLASK_ENV by default; de asta mai punem heuristics.
    if os.getenv("FLASK_ENV") == "production":
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID") or os.getenv("RAILWAY_STATIC_URL"):
        return True
    return False


def create_app():
    # Load .env early so GEMINI_API_KEY and others are available (local dev; production uses host env)
    load_dotenv()

    app = Flask(__name__, static_folder="static")
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    # ✅ IMPORTANT pt Railway + domeniu (reverse proxy)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # DB URL: Railway / env -> fallback local sqlite
    db_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Connection pool settings pentru PostgreSQL (previne OperationalError când conexiunea se închide)
    if "postgresql" in db_url:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,  # Verifică conexiunea înainte de utilizare
            "pool_recycle": 3600,   # Recyclează conexiunile după 1 oră
            "pool_size": 10,        # Dimensiunea pool-ului
            "max_overflow": 20,     # Conexiuni suplimentare permise
            "connect_args": {
                "connect_timeout": 10,  # Timeout pentru conexiune inițială
            }
        }

    # ✅ Cookies ok pe domeniu/https
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Secure cookies doar pe producție
    is_production = is_production_env()
    app.config["SESSION_COOKIE_SECURE"] = is_production

    # ajută la url_for(..., _external=True)
    app.config["PREFERRED_URL_SCHEME"] = "https" if is_production else "http"

    # optional: util pt share links “fix”
    app.config["PUBLIC_BASE_URL"] = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")

    # Marketplace: WhatsApp suport (centralizat)
    app.config["WHATSAPP_SUPPORT_PHONE"] = os.getenv("WHATSAPP_SUPPORT_PHONE", "40764381795")

    # Page ID for assistant (page-aware help) – from assistant blueprint
    from assistant.page_registry import get_page_id as _get_page_id
    @app.context_processor
    def inject_page_id():
        return {"page_id": _get_page_id(request) if request else "generic"}

    # Pentru template-uri Jinja2 (ex.: getattr(obj, 'plus_tva', False))
    app.jinja_env.globals["getattr"] = getattr

    @app.context_processor
    def inject_team_context():
        """Injectează is_team_manager, has_team, unread_team_tasks pentru Echipă & Performanță."""
        if not current_user.is_authenticated:
            return {"is_team_manager": False, "has_team": False, "unread_team_tasks": 0}
        from models import Team, TeamMember, TeamTaskAssignment, TeamTask
        team = Team.query.filter_by(manager_user_id=current_user.id).first()
        membership = TeamMember.query.filter_by(user_id=current_user.id).first()
        has_team = membership is not None and membership.status == "confirmed"
        unread = 0
        if has_team and membership.role == "agent":
            unread = (
                TeamTaskAssignment.query.join(TeamTask, TeamTaskAssignment.task_id == TeamTask.id)
                .filter(
                    TeamTaskAssignment.assignee_user_id == current_user.id,
                    TeamTaskAssignment.status == "open",
                    TeamTaskAssignment.acknowledged_at.is_(None),
                    TeamTask.team_id == membership.team_id,
                )
                .count()
            )
        return {
            "is_team_manager": team is not None,
            "has_team": has_team,
            "unread_team_tasks": unread,
        }

    # Template filters: zone short name (neighborhood only), budget format
    @app.template_filter("zone_display_name")
    def zone_display_name(name):
        if not name:
            return ""
        if " - " in name:
            return name.split(" - ", 1)[-1].strip()
        return name

    @app.template_filter("format_budget")
    def format_budget(n):
        if n is None:
            return "–"
        return "{:,.0f}".format(int(n)).replace(",", ".")

    @app.template_filter("property_type_label")
    def property_type_label(value):
        """Etichetă tip imobil pentru cereri și anunțuri (apartament, casa, birou, etc.)."""
        if not value:
            return "Imobil"
        labels = {
            "apartament": "Apartament",
            "casa": "Casă/Vilă",
            "teren": "Teren",
            "spatiu_comercial": "Spațiu comercial",
            "birou": "Birou",
            "spatiu_industrial": "Spațiu industrial",
        }
        return labels.get(value, value.replace("_", " ").title())

    # init extensii
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Trebuie să te loghezi ca să continui."
    login_manager.login_message_category = "error"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(todo_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(chirie_bp)
    app.register_blueprint(vanzare_bp)
    app.register_blueprint(contract_bp)
    app.register_blueprint(prestari_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(contract_templates_bp)
    app.register_blueprint(pdf_viewer_bp)

    # -------------------------
    # Cleanup: failsafe + scheduler
    # -------------------------
    from cleanup_scheduler import maybe_run_failsafe, init_scheduler

    @app.before_request
    def _cleanup_failsafe_check():
        maybe_run_failsafe(app)

    @app.before_request
    def _check_session_version():
        """Dacă admin a apăsat 'Deconectează de pe alte dispozitive', invalidăm sesiunea la următoarea cerere."""
        if not current_user.is_authenticated:
            return
        try:
            u = db.session.get(User, current_user.id)
        except Exception:
            return
        if not u:
            return
        db_version = getattr(u, "session_version", 1)
        sess_version = session.get("session_version")
        # Sesiuni vechi (înainte de session_version): doar setăm cheia, nu delogăm
        if sess_version is None:
            session["session_version"] = db_version
            return
        if sess_version != db_version:
            logout_user()
            session.clear()
            flash("Ai fost deconectat de pe toate dispozitivele.", "info")
            return redirect(url_for("auth.login"))

    init_scheduler(app)

    # Endpoint pentru cron extern (Railway Cron / etc): GET /internal/cleanup-daily?token=SECRET
    @app.get("/internal/cleanup-daily")
    def internal_cleanup_daily():
        token = request.args.get("token", "")
        expected = os.getenv("CLEANUP_CRON_TOKEN", "")
        if not expected or token != expected:
            return {"ok": False, "error": "unauthorized"}, 403
        from cleanup_scheduler import run_scheduled_cleanup
        run_scheduled_cleanup(app)
        return {"ok": True}

    # pages
    @app.get("/")
    def home():
        return render_template("home.html")
    
    @app.get("/despre")
    def about():
        return render_template("about.html")


    @app.get("/termeni")
    def terms():
        return render_template(
            "terms.html",
            last_updated=date.today().strftime("%d.%m.%Y"),
            support_email="fisadevizionare@gmail.com",
        )

    @app.get("/confidentialitate")
    def privacy():
        return render_template(
            "privacy.html",
            last_updated=date.today().strftime("%d.%m.%Y"),
            support_email="fisadevizionare@gmail.com",
        )

    @app.get("/plati")
    def payments():
        return render_template(
            "payments.html",
            last_updated=date.today().strftime("%d.%m.%Y"),
            support_email="fisadevizionare@gmail.com",
        )

    return app


# ✅ Gunicorn va importa `app`
app = create_app()


# ✅ Doar pentru rulare locală (python main.py)
if __name__ == "__main__":
    # NU debug pe producție
    debug = (os.getenv("FLASK_DEBUG", "0") == "1") and (not is_production_env())
    port = int(os.getenv("PORT", "8080"))  # Railway îți dă PORT; fallback local
    app.run(host="0.0.0.0", port=port, debug=debug)
