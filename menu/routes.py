from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from .forms import AgentProfileForm, AgencyProfileForm
from models import UserProfile  # verifică importul la tine

menu_bp = Blueprint("menu", __name__, url_prefix="/menu")


def _profile_to_dict(p: UserProfile) -> dict:
    """Păstrăm compatibilitatea cu template-urile existente: profile.agent.name etc."""
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
    # 1) dacă ai relationship User.profile, ia direct de acolo
    p = getattr(current_user, "profile", None)
    if p:
        return p

    # 2) fallback: caută în DB
    p = UserProfile.query.filter_by(user_id=current_user.id).first()
    if p:
        # atașează-l pe current_user (nu e obligatoriu, dar ajută)
        try:
            current_user.profile = p
        except Exception:
            pass
        return p

    # 3) creează profil default pentru userul logat
    p = UserProfile(user_id=current_user.id)
    db.session.add(p)
    db.session.commit()

    try:
        current_user.profile = p
    except Exception:
        pass

    return p


@menu_bp.get("/")
@login_required
def menu_home():
    p = get_or_create_profile()
    profile = _profile_to_dict(p)
    return render_template("menu.html", profile=profile)


@menu_bp.route("/agent", methods=["GET", "POST"])
@login_required
def agent_profile():
    p = get_or_create_profile()
    form = AgentProfileForm(agent_name=p.agent_name or "", agent_phone=p.agent_phone or "")

    if form.validate_on_submit():
        p.agent_name = (form.agent_name.data or "").strip() or "__________"
        p.agent_phone = (form.agent_phone.data or "").strip() or ""
        db.session.commit()

        flash("Datele agentului au fost salvate.", "success")
        return redirect(url_for("menu.menu_home"))

    profile = _profile_to_dict(p)
    return render_template("agent_profile.html", form=form, profile=profile)


@menu_bp.route("/agency", methods=["GET", "POST"])
@login_required
def agency_profile():
    p = get_or_create_profile()

    form = AgencyProfileForm(
        name=p.agency_name or "",
        hq_address=p.agency_hq_address or "",
        orc_number=p.agency_orc_number or "",
        cui=p.agency_cui or "",
        iban=p.agency_iban or "",
        bank=p.agency_bank or "",
        administrator=p.agency_administrator or "",
    )

    if form.validate_on_submit():
        p.agency_name = (form.name.data or "").strip() or "__________ SRL"
        p.agency_hq_address = (form.hq_address.data or "").strip() or "__________"
        p.agency_orc_number = (form.orc_number.data or "").strip() or "__________"
        p.agency_cui = (form.cui.data or "").strip() or "__________"
        p.agency_iban = (form.iban.data or "").strip() or "__________"
        p.agency_bank = (form.bank.data or "").strip() or "__________"
        p.agency_administrator = (form.administrator.data or "").strip() or "__________"

        db.session.commit()

        flash("Datele agenției au fost salvate.", "success")
        return redirect(url_for("menu.menu_home"))

    profile = _profile_to_dict(p)
    return render_template("agency_profile.html", form=form, profile=profile)
