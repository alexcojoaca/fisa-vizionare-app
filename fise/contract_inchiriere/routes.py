import json
import uuid
from pathlib import Path
from datetime import datetime
from flask_login import login_required, current_user
from access_control import access_required, agent_required

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

from .form import ContractForm
from pdf.contract_pdf import render_contract_pdf_bytes


contract_bp = Blueprint(
    "contract",
    __name__,
    url_prefix="/contract-inchiriere",
)

BASE_DIR = Path(__file__).resolve().parents[2]
PROFILE_PATH = BASE_DIR / "db" / "profile.json"


def _default_profile() -> dict:
    return {
        "agency": {
            "name": "__________ SRL",
            "hq_address": "__________",
            "orc_number": "__________",
            "cui": "__________",
            "iban": "__________",
            "bank": "__________",
            "administrator": "__________",
        },
        "agent": {"name": "__________"},
    }


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return _default_profile()

    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        fixed = _default_profile()
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(
            json.dumps(fixed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return fixed


def get_tmp_dir() -> Path:
    tmp_dir = Path(current_app.root_path) / "static" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


def _s(key: str) -> str:
    # For checkboxes, getlist returns a list - take first checked value
    val = request.form.getlist(key)
    if val:
        return val[0].strip() if isinstance(val[0], str) else ""
    return (request.form.get(key) or "").strip()


def _build_contract_from_request() -> dict:
    """
    Construim contract dict din form.
    IMPORTANT: ținem cheile identice cu ce folosește PDF-ul.
    """
    return {
        # Proprietar
        "owner_name": _s("owner_name"),
        "owner_address": _s("owner_address"),
        "owner_phone": _s("owner_phone"),
        "owner_email": _s("owner_email"),
        "owner_id_type": _s("owner_id_type") or "",
        "owner_cnp": _s("owner_cnp"),
        "owner_ci_series": _s("owner_ci_series"),
        "owner_passport_no": _s("owner_passport_no"),
        "owner_citizenship": _s("owner_citizenship"),

        # Chiriaș
        "tenant_name": _s("tenant_name"),
        "tenant_address": _s("tenant_address"),
        "tenant_phone": _s("tenant_phone"),
        "tenant_email": _s("tenant_email"),
        "tenant_id_type": _s("tenant_id_type") or "",
        "tenant_cnp": _s("tenant_cnp"),
        "tenant_ci_series": _s("tenant_ci_series"),
        "tenant_passport_no": _s("tenant_passport_no"),
        "tenant_citizenship": _s("tenant_citizenship"),

        # Imobil
        "property_type": _s("property_type"),
        "property_rooms": _s("property_rooms"),
        "property_mp": _s("property_mp"),
        "property_address": _s("property_address"),

        # Durată
        "date_signed": _s("date_signed"),   # <-- era în template dar lipsea din routes
        "start_date": _s("start_date"),
        "end_date": _s("end_date"),
        "duration_months": _s("duration_months"),
        "pay_day": _s("pay_day"),
        "notice_days": _s("notice_days"),

        # Plăți
        "rent_amount": _s("rent_amount"),
        "rent_currency": _s("rent_currency") or "EUR",
        "deposit_amount": _s("deposit_amount"),
        "paid_today_total": _s("paid_today_total"),  # <-- corect, nu rent_paid_today

        # Bancă (opțional)
        "bank_name": _s("bank_name"),
        "bank_iban": _s("bank_iban"),
        "bank_swift": _s("bank_swift"),

        # Opțiuni
        "pets_allowed": _s("pets_allowed") or "",  # Empty string means not specified (won't appear in PDF)
        "notes": _s("notes"),
    }


# -----------------------------
# PREVIEW (fără semnături)
# POST /contract-inchiriere/preview
# -----------------------------
@contract_bp.route("/preview", methods=["POST"])
@login_required
@agent_required
@access_required
def preview_pdf():
    profile = load_profile()

    contract_data = _build_contract_from_request()

    payload = {
        "agency": profile.get("agency", {}),
        "agent": profile.get("agent", {}),
        "contract": contract_data,
        "signature_owner_dataurl": "",
        "signature_tenant_dataurl": "",
    }

    pdf_bytes = render_contract_pdf_bytes(payload)

    tmp_dir = get_tmp_dir()
    doc_id = uuid.uuid4().hex[:12]
    pdf_path = tmp_dir / f"preview-contract-{doc_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name="preview-contract-inchiriere.pdf",
        conditional=True,
        max_age=0,
    )
    return _no_cache(resp)


# -----------------------------
# FORM
# GET/POST /contract-inchiriere/
# -----------------------------
@contract_bp.route("/", methods=["GET", "POST"])
@login_required
@agent_required
@access_required
def form_page():
    form = ContractForm()
    profile = load_profile()

    # Blochează contractele de închiriere pentru utilizatorii neplătiți
    if not current_user.is_active_account():
        flash("Contractele de închiriere sunt disponibile doar pentru conturi active. Activează abonamentul ca să continui.", "error")
        return redirect(url_for("menu.menu_home"))

    if request.method == "POST":
        signature_owner = _s("signature_owner")
        signature_tenant = _s("signature_tenant")

        contract_data = _build_contract_from_request()

        payload = {
            "agency": profile.get("agency", {}),
            "agent": profile.get("agent", {}),
            "contract": contract_data,
            "signature_owner_dataurl": signature_owner,
            "signature_tenant_dataurl": signature_tenant,
        }

        pdf_bytes = render_contract_pdf_bytes(payload)

        tmp_dir = get_tmp_dir()
        doc_id = uuid.uuid4().hex[:12]
        pdf_path = tmp_dir / f"{doc_id}.pdf"
        meta_path = tmp_dir / f"{doc_id}.json"

        pdf_path.write_bytes(pdf_bytes)

        c = payload["contract"]
        meta_path.write_text(
            json.dumps(
                {
                    "client": c.get("tenant_name", ""),
                    "telefon": c.get("tenant_phone", ""),
                    "adresa": c.get("property_address", ""),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return redirect(url_for("contract.done_page", doc_id=doc_id))

    return render_template("contract_form.html", form=form)


@contract_bp.route("/done/<doc_id>")
@login_required
@agent_required
@access_required
def done_page(doc_id):
    tmp_dir = get_tmp_dir()
    meta_path = tmp_dir / f"{doc_id}.json"
    if not meta_path.exists():
        flash("Contractul nu a fost găsit.", "error")
        return redirect(url_for("contract.form_page"))

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return render_template("contract_done.html", doc_id=doc_id, meta=meta)


@contract_bp.route("/pdf/<doc_id>")
@login_required
@agent_required
@access_required
def download_pdf(doc_id):
    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"{doc_id}.pdf"
    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect(url_for("contract.form_page"))

    response = send_file(
        pdf_path,
        as_attachment=True,
        download_name="contract-inchiriere.pdf",
        mimetype="application/octet-stream",
        conditional=False,
    )
    response.headers["Content-Disposition"] = 'attachment; filename="contract-inchiriere.pdf"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@contract_bp.route("/view/<doc_id>")
@login_required
@agent_required
@access_required
def view_pdf(doc_id):
    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"{doc_id}.pdf"
    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect(url_for("contract.form_page"))

    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name="contract-inchiriere.pdf",
        conditional=True,
        max_age=0,
    )
    return _no_cache(resp)
