import json
import uuid
from pathlib import Path
from datetime import datetime

from zoneinfo import ZoneInfo

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    current_app,
)

from flask_login import login_required, current_user

from access_control import access_required, agent_required
from extensions import db
from models import UserProfile, utcnow

from .form import PrestariForm
from pdf.prestari_pdf import render_prestari_pdf_bytes


prestari_bp = Blueprint("prestari", __name__, url_prefix="/prestari-servicii")


# -----------------------------
# Helpers
# -----------------------------
def get_tmp_dir() -> Path:
    tmp_dir = Path(current_app.root_path) / "static" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


def _safe_strip(x):
    return (x or "").strip() if isinstance(x, str) else ""


def _profile_to_dict(p: UserProfile) -> dict:
    """Compatibil cu template/PDF existente: profile.agency, profile.agent (name + signature)."""
    return {
        "agency": {
            "name": p.agency_name or "",
            "hq_address": p.agency_hq_address or "",
            "orc_number": p.agency_orc_number or "",
            "cui": p.agency_cui or "",
            "iban": p.agency_iban or "",
            "bank": p.agency_bank or "",
            "administrator": p.agency_administrator or "",
        },
        "agent": {
            "name": p.agent_name or "",
            "phone": p.agent_phone or "",
            "signature_dataurl": p.agent_signature_dataurl or "",
        },
    }


def get_or_create_profile() -> UserProfile:
    p = UserProfile.query.filter_by(user_id=current_user.id).first()
    if p:
        return p
    p = UserProfile(user_id=current_user.id)
    db.session.add(p)
    db.session.commit()
    return p


def _signed_at_ro_str() -> str:
    """Momentul semnării în România (Europe/Bucharest)."""
    return datetime.now(ZoneInfo("Europe/Bucharest")).strftime("%d.%m.%Y %H:%M:%S")


# ============================================================
# Routes
# ============================================================

@prestari_bp.route("/preview", methods=["POST"])
@login_required
@agent_required
@access_required
def preview_pdf():
    # Prestări servicii este disponibil DOAR pentru conturi active (trial/paid)
    from flask_login import current_user
    if not current_user.is_active_account():
        from flask import jsonify
        return jsonify({"ok": False, "error": "Contract de prestări servicii este disponibil doar pentru conturi active."}), 403
    form = PrestariForm()

    p = get_or_create_profile()
    profile = _profile_to_dict(p)

    # Get beneficiary type and CNP/CUI
    beneficiar_tip = _safe_strip(form.beneficiar_tip.data)
    beneficiar_cnp = _safe_strip(form.beneficiar_cnp.data) if beneficiar_tip == "pf" else ""
    beneficiar_cui = _safe_strip(form.beneficiar_cui.data) if beneficiar_tip == "pj" else ""
    beneficiar_cnp_cui = beneficiar_cnp if beneficiar_tip == "pf" else beneficiar_cui

    # Agent name: profile (agent_name) else User full_name else email else "Agent"
    agent = profile.get("agent") or {}
    agent_name = (agent.get("name") or "").strip() or getattr(current_user, "full_name", None) or getattr(current_user, "email", None) or "Agent"
    
    # Capture signatures from form if present (for preview to show what will be signed)
    signature_beneficiar_preview = (request.form.get("signature_beneficiar") or "").strip()
    signature_agent_preview = (request.form.get("signature_agent") or "").strip()
    
    payload_agent = {"name": agent_name, "signature_dataurl": signature_agent_preview}

    payload = {
        "agency": profile.get("agency", {}),
        "agent": payload_agent,
        "beneficiar": {
            "tip": beneficiar_tip,
            "nume": _safe_strip(form.beneficiar_nume.data),
            "cnp": beneficiar_cnp,
            "cui": beneficiar_cui,
            "cnp_cui": beneficiar_cnp_cui,
            "adresa": _safe_strip(form.beneficiar_adresa.data),
            "telefon": _safe_strip(form.beneficiar_telefon.data),
            "email": _safe_strip(form.beneficiar_email.data),
        },
        "obiect": {
            "tip_tranzactie": _safe_strip(form.tip_tranzactie.data),
            "imobil_tip": _safe_strip(form.imobil_tip.data),
            "imobil_adresa": _safe_strip(form.imobil_adresa.data),
        },
        "currency": _safe_strip(form.currency.data) or "RON",
        "comision_tva": _safe_strip(form.comision_tva.data) or "fara",
        "comision": _safe_strip(form.comision.data) or "4570.00",  # Raw string, exactly as typed
        "nr_contract": _safe_strip(form.nr_contract.data),
        "data_contractului": form.data_contractului.data.strftime("%d.%m.%Y") if form.data_contractului.data else "",
        "signature_beneficiar_dataurl": signature_beneficiar_preview,
        "signature_prestator_dataurl": signature_agent_preview,
        "signature_meta": {
            "mode": "onsite",
            "signed_at_local": _signed_at_ro_str(),
            "timezone": "Europe/Bucharest",
        },
    }

    pdf_bytes = render_prestari_pdf_bytes(payload)

    tmp_dir = get_tmp_dir()
    doc_id = uuid.uuid4().hex[:12]
    pdf_path = tmp_dir / f"preview-prestari-{doc_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name="preview-contract-prestari-servicii.pdf",
        conditional=True,
        max_age=0,
    )
    return _no_cache(resp)


@prestari_bp.route("/", methods=["GET", "POST"])
@login_required
@agent_required
@access_required
def form_page():
    # Prestări servicii este disponibil DOAR pentru conturi active (trial/paid)
    from flask_login import current_user
    if not current_user.is_active_account():
        from flask import flash, redirect, url_for
        from menu.routes import menu_bp
        flash("Contract de prestări servicii este disponibil doar pentru conturi active. Activează contul pentru a accesa această funcție.", "error")
        return redirect(url_for("menu.menu_home"))
    from datetime import date
    form = PrestariForm()
    if request.method == "GET":
        # Set default date to today
        form.data_contractului.data = date.today()

    if form.validate_on_submit():
        p = get_or_create_profile()
        profile = _profile_to_dict(p)

        signature_beneficiar = (request.form.get("signature_beneficiar") or "").strip()
        signature_agent = (request.form.get("signature_agent") or "").strip()
        # Agent name for PDF: profile.agent.name else current_user.full_name else email else "Agent"
        agent = profile.get("agent") or {}
        agent_name = (agent.get("name") or "").strip() or getattr(current_user, "full_name", None) or getattr(current_user, "email", None) or "Agent"
        payload_agent = {"name": agent_name, "signature_dataurl": signature_agent}

        # Get beneficiary type and CNP/CUI
        beneficiar_tip = (form.beneficiar_tip.data or "pf").strip()
        beneficiar_cnp = (form.beneficiar_cnp.data or "").strip() if beneficiar_tip == "pf" else ""
        beneficiar_cui = (form.beneficiar_cui.data or "").strip() if beneficiar_tip == "pj" else ""
        beneficiar_cnp_cui = beneficiar_cnp if beneficiar_tip == "pf" else beneficiar_cui

        payload = {
            "agency": profile.get("agency", {}),
            "agent": payload_agent,
            "beneficiar": {
                "tip": beneficiar_tip,
                "nume": (form.beneficiar_nume.data or "").strip(),
                "cnp": beneficiar_cnp,
                "cui": beneficiar_cui,
                "cnp_cui": beneficiar_cnp_cui,
                "adresa": (form.beneficiar_adresa.data or "").strip(),
                "telefon": (form.beneficiar_telefon.data or "").strip(),
                "email": (form.beneficiar_email.data or "").strip(),
            },
            "obiect": {
                "tip_tranzactie": (form.tip_tranzactie.data or "").strip(),
                "imobil_tip": (form.imobil_tip.data or "").strip(),
                "imobil_adresa": (form.imobil_adresa.data or "").strip(),
            },
            "currency": (form.currency.data or "RON").strip(),
            "comision_tva": (form.comision_tva.data or "fara").strip(),
            "comision": _safe_strip(form.comision.data) or "4570.00",  # Raw string, exactly as typed
            "nr_contract": (form.nr_contract.data or "").strip(),
            "data_contractului": form.data_contractului.data.strftime("%d.%m.%Y") if form.data_contractului.data else "",
            "signature_beneficiar_dataurl": signature_beneficiar,
            "signature_prestator_dataurl": signature_agent,
            "signature_meta": {
                "mode": "onsite",
                "signed_at_local": _signed_at_ro_str(),
                "timezone": "Europe/Bucharest",
            },
        }

        pdf_bytes = render_prestari_pdf_bytes(payload)

        tmp_dir = get_tmp_dir()
        doc_id = uuid.uuid4().hex[:12]
        pdf_path = tmp_dir / f"{doc_id}.pdf"
        meta_path = tmp_dir / f"{doc_id}.json"

        pdf_path.write_bytes(pdf_bytes)
        meta_path.write_text(
            json.dumps(
                {
                    "beneficiar": payload["beneficiar"]["nume"],
                    "telefon": payload["beneficiar"]["telefon"],
                    "adresa": payload["obiect"]["imobil_adresa"],
                    "nr_contract": payload["nr_contract"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return redirect(url_for("prestari.done_page", doc_id=doc_id))

    if request.method == "POST":
        flash("Completează câmpurile obligatorii.", "error")

    return render_template("prestari_form.html", form=form)


@prestari_bp.route("/done/<doc_id>")
@login_required
@agent_required
@access_required
def done_page(doc_id):
    tmp_dir = get_tmp_dir()
    meta_path = tmp_dir / f"{doc_id}.json"
    if not meta_path.exists():
        flash("Contractul nu a fost găsit.", "error")
        return redirect(url_for("prestari.form_page"))

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return render_template("prestari_done.html", doc_id=doc_id, meta=meta)


@prestari_bp.route("/pdf/<doc_id>")
@login_required
@agent_required
@access_required
def download_pdf(doc_id):
    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"{doc_id}.pdf"

    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect(url_for("prestari.form_page"))

    response = send_file(
        pdf_path,
        as_attachment=True,
        download_name="contract-prestari-servicii.pdf",
        mimetype="application/octet-stream",
        conditional=False,
    )

    response.headers["Content-Disposition"] = 'attachment; filename="contract-prestari-servicii.pdf"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@prestari_bp.route("/view/<doc_id>")
@login_required
@agent_required
@access_required
def view_pdf(doc_id):
    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"{doc_id}.pdf"
    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect(url_for("prestari.form_page"))

    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name="contract-prestari-servicii.pdf",
        conditional=True,
        max_age=0,
    )
    return _no_cache(resp)
