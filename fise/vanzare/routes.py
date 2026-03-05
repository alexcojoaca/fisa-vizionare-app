import json
import uuid
import secrets
from pathlib import Path
from datetime import timedelta, datetime
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
    jsonify,
)
from flask_login import login_required, current_user

from access_control import access_required, agent_required
from extensions import db
from models import UserProfile, VanzareRemoteSigning, utcnow

from .form import ChirieForm  # TEMP: folosești același form ca la chirie

try:
    from pdf.vanzare_pdf import render_vanzare_pdf_bytes  # recomandat
except Exception:
    from pdf.vanzare_pdf import render_chirie_pdf_bytes as render_vanzare_pdf_bytes  # fallback


vanzare_bp = Blueprint("vanzare", __name__, url_prefix="/vanzare")


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
    return {
        "agent": {
            "name": p.agent_name or "",
            "phone": p.agent_phone or "",
            "signature_dataurl": p.agent_signature_dataurl or "",
        },
        "agency": {
            "name": p.agency_name or "",
            "hq_address": p.agency_hq_address or "",
            "orc_number": p.agency_orc_number or "",
            "cui": p.agency_cui or "",
            "iban": p.agency_iban or "",
            "bank": p.agency_bank or "",
            "administrator": p.agency_administrator or "",
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


def _token() -> str:
    return secrets.token_urlsafe(32)


def _default_expiry():
    return utcnow() + timedelta(days=3)


def cleanup_expired_remote_vanzare():
    """
    Șterge automat remote-urile expirate (vânzare):
    - DB record
    - PDF din static/tmp dacă există
    """
    tmp_dir = get_tmp_dir()
    now = utcnow()

    expired = (
        VanzareRemoteSigning.query
        .filter(VanzareRemoteSigning.expires_at.isnot(None))
        .filter(VanzareRemoteSigning.expires_at < now)
        .all()
    )

    for rec in expired:
        if rec.pdf_doc_id:
            pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
            try:
                if pdf_path.exists():
                    pdf_path.unlink()
            except Exception:
                pass

        db.session.delete(rec)

    if expired:
        db.session.commit()


def _get_client_ip(req) -> str:
    xff = (req.headers.get("X-Forwarded-For") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    xri = (req.headers.get("X-Real-IP") or "").strip()
    if xri:
        return xri
    return (req.remote_addr or "").strip()


def _signed_at_ro_str() -> str:
    return datetime.now(ZoneInfo("Europe/Bucharest")).strftime("%d.%m.%Y %H:%M:%S")


def _looks_like_dataurl(sig: str) -> bool:
    return (sig or "").strip().startswith("data:image/")


# ============================================================
# VARIANTA 1 — On-site
# ============================================================

@vanzare_bp.route("/preview", methods=["POST"])
@login_required
@agent_required
@access_required
def preview_pdf():
    """
    Preview DRAFT (fără semnături).
    IMPORTANT: aici trebuie să citim datele din request.form (WTForms),
    altfel rămâne tot gol.
    """
    form = ChirieForm()
    form.process(formdata=request.form)  # ✅ fix: citește POST

    p = get_or_create_profile()
    profile = _profile_to_dict(p)

    payload = {
        "vizionare": {
            "data": form.data_vizionarii.data.strftime("%d.%m.%Y") if form.data_vizionarii.data else "",
            "ora": form.ora_vizionarii.data.strftime("%H:%M") if form.ora_vizionarii.data else "",
        },
        "agency": profile.get("agency", {}),
        "agent": profile.get("agent", {}),
        "vizitator": {
            "nume": _safe_strip(form.nume.data),
            "telefon": _safe_strip(form.telefon.data),
            "email": _safe_strip(form.email.data),
            "ci_serie": _safe_strip(request.form.get("ci_serie")),
            "ci_numar": _safe_strip(request.form.get("ci_numar")),
        },
        "imobil": {
            "tip": _safe_strip(form.tip_imobil.data),
            "adresa": _safe_strip(form.adresa_locuintei.data),
        },
        "comision_procent": _safe_strip(form.comision_procent.data),
        "signature_agent_dataurl": "",
        "signature_visitor_dataurl": "",
        "signature_meta": {
            "mode": "onsite-preview",
            "generated_at_local": _signed_at_ro_str(),
            "timezone": "Europe/Bucharest",
        },
    }

    pdf_bytes = render_vanzare_pdf_bytes(payload)

    tmp_dir = get_tmp_dir()
    doc_id = uuid.uuid4().hex[:12]
    pdf_path = tmp_dir / f"preview-vanzare-{doc_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name="preview-fisa-vizionare-vanzare.pdf",
        conditional=True,
        max_age=0,
    )
    return _no_cache(resp)


@vanzare_bp.route("/", methods=["GET", "POST"])
@login_required
@agent_required
@access_required
def form_page():
    form = ChirieForm()
    
    # Verifică dacă utilizatorul a folosit deja accesul gratuit (doar pentru afișare mesaj, nu pentru blocare)
    # Permitem generarea PDF-ului chiar dacă a folosit deja accesul gratuit, pentru a permite descărcarea
    show_activate_modal_on_load = False
    if request.method == "GET" and not current_user.can_create_sale_viewing():
        show_activate_modal_on_load = True

    if form.validate_on_submit():
        p = get_or_create_profile()
        profile = _profile_to_dict(p)

        signature_agent = (request.form.get("signature_agent") or "").strip()
        signature_visitor = (request.form.get("signature_visitor") or "").strip()

        ci_serie = (request.form.get("ci_serie") or "").strip()
        ci_numar = (request.form.get("ci_numar") or "").strip()

        # dacă tu vrei obligatoriu semnături la generare finală:
        if not _looks_like_dataurl(signature_agent) or not _looks_like_dataurl(signature_visitor):
            flash("Semnăturile (agent + client) sunt obligatorii pentru generarea PDF-ului final.", "error")
            return render_template("vanzare_form.html", form=form)

        payload = {
            "vizionare": {
                "data": form.data_vizionarii.data.strftime("%d.%m.%Y"),
                "ora": form.ora_vizionarii.data.strftime("%H:%M"),
            },
            "agency": profile.get("agency", {}),
            "agent": profile.get("agent", {}),
            "vizitator": {
                "nume": (form.nume.data or "").strip(),
                "telefon": (form.telefon.data or "").strip(),
                "email": (form.email.data or "").strip(),
                "ci_serie": ci_serie,
                "ci_numar": ci_numar,
            },
            "imobil": {
                "tip": (form.tip_imobil.data or "").strip(),
                "adresa": (form.adresa_locuintei.data or "").strip(),
            },
            "comision_procent": (form.comision_procent.data or "").strip(),
            "signature_agent_dataurl": signature_agent,
            "signature_visitor_dataurl": signature_visitor,
            "signature_meta": {
                "mode": "onsite",
                "signed_at_local": _signed_at_ro_str(),
                "timezone": "Europe/Bucharest",
            },
        }

        pdf_bytes = render_vanzare_pdf_bytes(payload)

        tmp_dir = get_tmp_dir()
        doc_id = uuid.uuid4().hex[:12]

        pdf_path = tmp_dir / f"vanzare-{doc_id}.pdf"
        meta_path = tmp_dir / f"vanzare-{doc_id}.json"

        pdf_path.write_bytes(pdf_bytes)
        meta_path.write_text(
            json.dumps(
                {
                    "client": payload["vizitator"]["nume"],
                    "telefon": payload["vizitator"]["telefon"],
                    "adresa": payload["imobil"]["adresa"],
                    "ci": f'{payload["vizitator"]["ci_serie"]} {payload["vizitator"]["ci_numar"]}'.strip(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # Marchează că a folosit accesul gratuit pentru fișă vânzare (doar dacă nu e plătit și nu a folosit deja)
        # Permitem generarea PDF-ului chiar dacă a folosit deja accesul gratuit, dar marcăm doar dacă nu a folosit încă
        if current_user.can_create_sale_viewing():
            current_user.mark_sale_viewing_used()
            db.session.commit()

        return redirect(url_for("vanzare.done_page", doc_id=doc_id))

    if request.method == "POST":
        flash("Completează câmpurile obligatorii.", "error")

    return render_template("vanzare_form.html", form=form, show_activate_modal=show_activate_modal_on_load)


@vanzare_bp.route("/done/<doc_id>")
@login_required
@agent_required
@access_required
def done_page(doc_id):
    tmp_dir = get_tmp_dir()
    meta_path = tmp_dir / f"vanzare-{doc_id}.json"

    if not meta_path.exists():
        flash("Fișa nu a fost găsită.", "error")
        return redirect(url_for("vanzare.form_page"))

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return render_template("vanzare_done.html", doc_id=doc_id, meta=meta)


@vanzare_bp.route("/pdf/<doc_id>")
@login_required
@agent_required
def download_pdf(doc_id):
    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"vanzare-{doc_id}.pdf"

    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect(url_for("vanzare.form_page"))

    response = send_file(
        pdf_path,
        as_attachment=True,
        download_name="fisa-vizionare-vanzare.pdf",
        mimetype="application/octet-stream",
        conditional=False,
    )
    response.headers["Content-Disposition"] = 'attachment; filename="fisa-vizionare-vanzare.pdf"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@vanzare_bp.route("/view/<doc_id>")
@login_required
@agent_required
@access_required
def view_pdf(doc_id):
    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"vanzare-{doc_id}.pdf"

    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect(url_for("vanzare.form_page"))

    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name="fisa-vizionare-vanzare.pdf",
        conditional=True,
        max_age=0,
    )
    return _no_cache(resp)


# ============================================================
# VARIANTA 2 — Remote signing (VÂNZARE)
# ============================================================

@vanzare_bp.route("/remote", methods=["GET"])
@login_required
@agent_required
@access_required
def remote_agent_page():
    cleanup_expired_remote_vanzare()
    p = get_or_create_profile()
    profile = _profile_to_dict(p)
    return render_template("vanzare_remote_agent.html", profile=profile)


@vanzare_bp.route("/remote/create", methods=["POST"])
@login_required
@agent_required
@access_required
def remote_create():
    cleanup_expired_remote_vanzare()

    # Verifică dacă user neplătit poate crea fișă vânzare (trial pe acțiuni)
    if not current_user.can_create_sale_viewing():
        return jsonify({
            "ok": False,
            "error": "Acces limitat atins",
            "message": "Ai folosit deja accesul gratuit pentru fișă de vizionare vânzare. Activează abonamentul ca să continui.",
            "requires_activation": True,
        }), 403

    data_viz = (request.form.get("data_vizionarii") or "").strip()
    ora_viz = (request.form.get("ora_vizionarii") or "").strip()
    tip = (request.form.get("tip_imobil") or "").strip()
    adresa_full = (request.form.get("adresa_locuintei") or request.form.get("adresa_full") or "").strip()
    adresa_public = (request.form.get("adresa_public") or "").strip()
    comision = (request.form.get("comision_procent") or "").strip()
    sig_agent = (request.form.get("signature_agent") or "").strip()

    if not (data_viz and ora_viz and tip and adresa_full and adresa_public and comision):
        return jsonify({"ok": False, "error": "Completează toate câmpurile obligatorii."}), 400

    # ✅ semnătura agent obligatorie (cum zice UI)
    if not _looks_like_dataurl(sig_agent):
        return jsonify({"ok": False, "error": "Semnătura agentului este obligatorie."}), 400

    rec = VanzareRemoteSigning(
        public_token=_token(),
        user_id=current_user.id,
        created_at=utcnow(),
        expires_at=_default_expiry(),
        status="pending",
        data_vizionarii=data_viz,
        ora_vizionarii=ora_viz,
        tip_imobil=tip,
        adresa_full=adresa_full,
        adresa_public=adresa_public,
        comision_procent=comision,
        signature_agent_dataurl=sig_agent,
    )
    db.session.add(rec)
    
    # Marchează că a folosit accesul gratuit pentru fișă vânzare (doar dacă nu e plătit)
    current_user.mark_sale_viewing_used()
    db.session.commit()

    link = url_for("vanzare.remote_public_page", token=rec.public_token, _external=True)
    return jsonify({"ok": True, "link": link})


@vanzare_bp.route("/s/<token>", methods=["GET"])
def remote_public_page(token):
    cleanup_expired_remote_vanzare()

    rec = VanzareRemoteSigning.query.filter_by(public_token=token).first()
    if not rec:
        return render_template("remote_invalid.html", message="Link invalid sau expirat."), 404

    if rec.status == "signed":
        return render_template("remote_invalid.html", message="Fișa este deja semnată. Mulțumim!")

    # edge case: record rămas dar expirat
    if rec.expires_at and utcnow() > rec.expires_at:
        return render_template("remote_invalid.html", message="Link expirat."), 410

    public_data = {
        "data_vizionarii": rec.data_vizionarii,
        "ora_vizionarii": rec.ora_vizionarii,
        "tip_imobil": rec.tip_imobil,
        "adresa_public": rec.adresa_public,
        "comision_procent": rec.comision_procent,
    }

    p = UserProfile.query.filter_by(user_id=rec.user_id).first()

    agent_name = ""
    agency_text = ""
    if p:
        agent_name = (p.agent_name or "").strip()

        parts = []
        if p.agency_name:
            parts.append(f"{p.agency_name}")
        if p.agency_hq_address:
            parts.append(f"cu sediul social în {p.agency_hq_address}")
        if p.agency_orc_number:
            parts.append(f"înregistrată la ORC sub nr. {p.agency_orc_number}")
        if p.agency_cui:
            parts.append(f"CUI {p.agency_cui}")
        if p.agency_iban:
            parts.append(f"IBAN {p.agency_iban}")
        if p.agency_bank:
            parts.append(f"Banca {p.agency_bank}")
        if p.agency_administrator:
            parts.append(f"reprezentată legal prin {p.agency_administrator}, în calitate de Administrator")

        agency_text = ", ".join([x for x in parts if x])

    return render_template(
        "vanzare_remote_public.html",
        token=token,
        info=public_data,
        agent_name=agent_name,
        agency_text=agency_text,
    )


@vanzare_bp.route("/s/<token>/submit", methods=["POST"])
def remote_submit(token):
    cleanup_expired_remote_vanzare()

    rec = VanzareRemoteSigning.query.filter_by(public_token=token).first()
    if not rec:
        return "Link invalid sau expirat.", 404

    if rec.status == "signed":
        return "Fișa este deja semnată.", 409

    if rec.expires_at and utcnow() > rec.expires_at:
        return "Link expirat.", 410

    viz_nume = (request.form.get("nume") or "").strip()
    viz_tel = (request.form.get("telefon") or "").strip()
    viz_email = (request.form.get("email") or "").strip()
    sig_visitor = (request.form.get("signature_visitor") or "").strip()

    ci_serie = (request.form.get("ci_serie") or "").strip()
    ci_numar = (request.form.get("ci_numar") or "").strip()

    if not viz_nume:
        flash("Numele este obligatoriu.", "error")
        return redirect(url_for("vanzare.remote_public_page", token=token))

    if not _looks_like_dataurl(sig_visitor):
        flash("Semnătura este obligatorie.", "error")
        return redirect(url_for("vanzare.remote_public_page", token=token))

    p = UserProfile.query.filter_by(user_id=rec.user_id).first()
    if not p:
        return "Agent profile missing.", 500

    profile = _profile_to_dict(p)

    payload = {
        "vizionare": {"data": rec.data_vizionarii, "ora": rec.ora_vizionarii},
        "agency": profile.get("agency", {}),
        "agent": profile.get("agent", {}),
        "vizitator": {
            "nume": viz_nume,
            "telefon": viz_tel,
            "email": viz_email,
            "ci_serie": ci_serie,
            "ci_numar": ci_numar,
        },
        "imobil": {
            "tip": rec.tip_imobil,
            "adresa": rec.adresa_full,
        },
        "comision_procent": rec.comision_procent,
        "signature_agent_dataurl": rec.signature_agent_dataurl or "",
        "signature_visitor_dataurl": sig_visitor,
        "signature_meta": {
            "mode": "remote",
            "signed_at_local": _signed_at_ro_str(),
            "timezone": "Europe/Bucharest",
            "ip": _get_client_ip(request),
            "token": rec.public_token,
        },
    }

    pdf_bytes = render_vanzare_pdf_bytes(payload)

    tmp_dir = get_tmp_dir()
    doc_id = uuid.uuid4().hex[:12]
    pdf_path = tmp_dir / f"remote-vanzare-{doc_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    rec.viz_nume = viz_nume
    rec.viz_telefon = viz_tel
    rec.viz_email = viz_email
    rec.signature_visitor_dataurl = sig_visitor
    rec.status = "signed"
    rec.signed_at = utcnow()
    rec.pdf_doc_id = f"remote-vanzare-{doc_id}"
    db.session.commit()

    resp = send_file(
        pdf_path,
        as_attachment=True,
        download_name="fisa-vizionare-vanzare.pdf",
        mimetype="application/octet-stream",
        conditional=False,
    )
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@vanzare_bp.route("/remote/pdf/<token>", methods=["GET"])
@login_required
@agent_required
@access_required
def remote_download_pdf(token):
    cleanup_expired_remote_vanzare()

    rec = VanzareRemoteSigning.query.filter_by(public_token=token, user_id=current_user.id).first()
    if not rec or not rec.pdf_doc_id:
        flash("PDF inexistent.", "error")
        return redirect("/chirie/remote/list")  # ✅ redirect safe la lista comună

    tmp_dir = get_tmp_dir()
    pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
    if not pdf_path.exists():
        flash("PDF inexistent.", "error")
        return redirect("/chirie/remote/list")

    resp = send_file(
        pdf_path,
        as_attachment=True,
        download_name="fisa-vizionare-vanzare.pdf",
        mimetype="application/octet-stream",
        conditional=False,
    )
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
