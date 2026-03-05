# assistant/routes.py – Asistent: ghid pagină, FAQ, notificări (anunțuri admin, expirare trial/paid), posibile colaborări.
import logging
import os
from datetime import date, datetime, timedelta, timezone

from flask import request, jsonify, current_app, url_for
from flask_login import login_required, current_user

from access_control import access_required
from extensions import db
from models import (
    Announcement,
    UserAnnouncementRead,
    Task,
    utcnow,
    PossibleCollaboration,
    CollaborationSeen,
    SellerOffer,
    BuyerRequest,
)

from . import assistant_bp
from .content import get_page_guide, get_faq_items
from .page_registry import get_page_id

_log = logging.getLogger(__name__)


def _wa_phone():
    return current_app.config.get("WHATSAPP_SUPPORT_PHONE", "40764381795")


def _inject_wa_in_faq_item(item):
    """Replace {{WHATSAPP}} placeholder with actual WhatsApp number in answer."""
    item = dict(item)
    a = item.get("a", "")
    item["a"] = a.replace("{{WHATSAPP}}", _wa_phone())
    return item


# --- Page guide (Ghid pagină) ---
@assistant_bp.get("/context")
@login_required
@access_required
def get_context():
    """Return page guide: title (Ești în: <name>), intro, bullets, tip."""
    page_id = request.args.get("page_id") or get_page_id(request)
    guide = get_page_guide(page_id)
    return jsonify({
        "ok": True,
        "page_id": page_id,
        "title": "Ești în: " + guide.get("name", ""),
        "intro": guide.get("intro", ""),
        "bullets": guide.get("bullets", []),
        "tip": guide.get("tip"),
    })


# --- FAQ (Întreabă) ---
@assistant_bp.get("/faq")
@login_required
@access_required
def get_faq():
    """Return all FAQ items (with WhatsApp number injected)."""
    items = get_faq_items("")
    out = [_inject_wa_in_faq_item(it) for it in items]
    return jsonify({"ok": True, "items": out, "wa_phone": _wa_phone()})


@assistant_bp.get("/faq/search")
@login_required
@access_required
def get_faq_search():
    """Search FAQ. Query: ?q= """
    q = request.args.get("q", "").strip()
    items = get_faq_items(q)
    out = [_inject_wa_in_faq_item(it) for it in items]
    return jsonify({"ok": True, "items": out, "wa_phone": _wa_phone()})


# --- Notificări: anunțuri admin + expirare trial/paid ---

def _expiry_reminder_for_user():
    """
    Returnează dict cu { show, message, days_left } dacă utilizatorul are trial/paid care expiră în ≤1 zi.
    Nu arată dacă a dat dismiss azi (expiry_reminder_dismissed_at.date == today).
    """
    until = current_user.access_until()
    if not until:
        return {"show": False, "message": "", "days_left": 0}
    now = utcnow()
    if until <= now:
        return {"show": False, "message": "", "days_left": 0}
    delta = until - now
    days_left = int((delta.total_seconds() + 86400 - 1) // 86400)
    if days_left > 1:
        return {"show": False, "message": "", "days_left": days_left}
    # 1 zi sau mai puțin
    dismissed = getattr(current_user, "expiry_reminder_dismissed_at", None)
    if dismissed:
        dismissed_date = dismissed.date() if hasattr(dismissed, "date") else dismissed
        now_date = now.date() if hasattr(now, "date") else now
        if dismissed_date == now_date:
            return {"show": False, "message": "", "days_left": days_left}
    source = current_user.access_source()
    label = "abonamentul plătit" if source == "paid" else "perioada de trial"
    until_str = until.strftime("%d.%m.%Y") if until else ""
    message = f"În maxim 1 zi îți expiră {label} (până la {until_str}). Poți prelungi sau contacta suportul."
    return {"show": True, "message": message, "days_left": days_left}


@assistant_bp.get("/notifications")
@login_required
@access_required
def get_notifications():
    """
    Returnează anunțurile necitite + eventual notificarea de expirare trial/paid.
    Verificat la fiecare încărcare (login/activitate).
    """
    # Anunțuri necitite: max 20 zile vechime, excluse cele deja citite.
    # Filtru global: dacă ANNOUNCEMENTS_VISIBLE_FROM=YYYY-MM-DD este setat, doar anunțurile de la acea dată înainte
    # sunt afișate (nimeni nu vede mesajele de test trimise înainte).
    # Opțional: doar anunțuri create după înregistrarea utilizatorului (created_at >= user.created_at).
    now = utcnow()
    cutoff = now - timedelta(days=20)
    read_ids = {
        r.announcement_id
        for r in UserAnnouncementRead.query.filter_by(user_id=current_user.id).all()
    }
    q = Announcement.query.filter(Announcement.created_at >= cutoff)
    visible_from = os.getenv("ANNOUNCEMENTS_VISIBLE_FROM", "").strip()
    if visible_from:
        try:
            limit_date = datetime.strptime(visible_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            q = q.filter(Announcement.created_at >= limit_date)
        except ValueError:
            pass
    q = q.filter(Announcement.created_at >= current_user.created_at)
    if read_ids:
        q = q.filter(~Announcement.id.in_(read_ids))
    unread = q.order_by(Announcement.created_at.desc()).limit(20).all()
    announcements = [
        {"id": a.id, "message": a.message, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in unread
    ]
    expiry = _expiry_reminder_for_user()
    has_unread_announcements = len(announcements) > 0

    # Posibile colaborări: potriviri necitite (fără CollaborationSeen pentru acest user)
    collab_unread_count, unread_collabs = _collaborations_unread_for_user(current_user.id)
    has_unread_collaborations = collab_unread_count > 0
    # Verifică dacă există potriviri cu clienți
    has_client_matches = False
    if unread_collabs:
        for collab in unread_collabs:
            if hasattr(collab, 'request') and collab.request and getattr(collab.request, 'posted_by_role', None) == 'client':
                has_client_matches = True
                break
    
    # Task-uri pentru astăzi (nefăcute)
    today = date.today()
    today_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date == today,
        Task.status != "done"
    ).order_by(
        Task.priority.desc(),
        Task.due_time.asc() if Task.due_time else None
    ).all()
    has_unread_tasks = len(today_tasks) > 0
    tasks_data = []
    if today_tasks:
        base_url = current_app.config.get("PUBLIC_BASE_URL") or request.url_root.rstrip("/")
        for task in today_tasks:
            if not task.completion_token:
                task.generate_completion_token()
                db.session.commit()
            completion_url = f"{base_url}/todo/complete/{task.completion_token}"
            tasks_data.append({
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "due_time": task.due_time.strftime("%H:%M") if task.due_time else None,
                "priority": task.priority,
                "completion_url": completion_url,
            })

    return jsonify({
        "ok": True,
        "announcements": announcements,
        "expiry_reminder": expiry,
        "has_unread": has_unread_announcements or expiry.get("show", False) or has_unread_collaborations or has_unread_tasks,
        "has_unread_announcements": has_unread_announcements,
        "has_unread_collaborations": has_unread_collaborations,
        "has_unread_tasks": has_unread_tasks,
        "today_tasks": tasks_data,
        "collaboration_unread_count": collab_unread_count,
        "has_client_matches": has_client_matches,
    })


def _collaborations_unread_for_user(user_id):
    """
    Returnează (count, listă de PossibleCollaboration) unde userul este fie owner al ofertei,
    fie owner al cererii, și nu a marcat potrivirea ca văzută (nu există CollaborationSeen).
    """
    from sqlalchemy import or_

    # Toate potrivirile care îl implică pe user (offer.user_id sau request.user_id)
    q = (
        PossibleCollaboration.query
        .join(SellerOffer, PossibleCollaboration.offer_id == SellerOffer.id)
        .join(BuyerRequest, PossibleCollaboration.request_id == BuyerRequest.id)
        .filter(or_(SellerOffer.user_id == user_id, BuyerRequest.user_id == user_id))
    )
    all_collab = q.all()
    seen_ids = {
        r.collaboration_id
        for r in CollaborationSeen.query.filter_by(user_id=user_id).all()
    }
    unread = [c for c in all_collab if c.id not in seen_ids]
    return len(unread), unread


# Etichete tip imobil pentru afișare în „Posibile colaborări”
_PROPERTY_TYPE_LABELS = {
    "apartament": "Apartament",
    "casa": "Casă",
    "teren": "Teren",
    "birou": "Birou",
    "spatiu_industrial": "Spațiu industrial",
    "spatiu_comercial": "Spațiu comercial",
}


def _request_short_label(request):
    """Titlu scurt pentru cerere: ex. 'Apartament 2 camere', 'Casă 4 camere'."""
    pt = (request.property_type or "").strip().lower()
    label = _PROPERTY_TYPE_LABELS.get(pt, pt.capitalize() if pt else "Cerere")
    rooms = getattr(request, "rooms", None)
    if rooms is not None:
        return f"{label} {rooms} camere"
    return label


def _offer_short_label(offer):
    """Titlu scurt pentru anunț: title dacă există, altfel ex. 'Apartament 2 camere'."""
    title = (offer.title or "").strip()
    if title:
        return title
    pt = (offer.property_type or "").strip().lower()
    label = _PROPERTY_TYPE_LABELS.get(pt, pt.capitalize() if pt else "Anunț")
    rooms = getattr(offer, "rooms", None)
    if rooms is not None:
        return f"{label} {rooms} camere"
    return label


def _request_full_label(request):
    """Etichetă completă pentru cerere: ex. 'Apartament 2 camere, buget 500-700 €'."""
    pt = (request.property_type or "").strip().lower()
    label = _PROPERTY_TYPE_LABELS.get(pt, pt.capitalize() if pt else "Cerere")
    rooms = getattr(request, "rooms", None)
    if rooms is not None:
        label = f"{label} {rooms} camere"
    parts = [label]
    if request.budget_min or request.budget_max:
        budget_str = ""
        if request.budget_min and request.budget_max:
            budget_str = f"{request.budget_min:,}-{request.budget_max:,} €".replace(",", ".")
        elif request.budget_min:
            budget_str = f"de la {request.budget_min:,} €".replace(",", ".")
        elif request.budget_max:
            budget_str = f"până la {request.budget_max:,} €".replace(",", ".")
        if budget_str:
            parts.append(f"buget {budget_str}")
    return ", ".join(parts)


def _offer_full_label(offer):
    """Etichetă completă pentru anunț: title sau 'Apartament 2 camere, preț X €'."""
    title = (offer.title or "").strip()
    if title:
        return title
    pt = (offer.property_type or "").strip().lower()
    label = _PROPERTY_TYPE_LABELS.get(pt, pt.capitalize() if pt else "Anunț")
    rooms = getattr(offer, "rooms", None)
    if rooms is not None:
        label = f"{label} {rooms} camere"
    parts = [label]
    price = offer.price
    if price:
        parts.append(f"preț {price:,} €".replace(",", "."))
    return ", ".join(parts)


def _collaborations_list_for_user(user_id, base_url=""):
    """
    Returnează potrivirile grupate per cerere/anunț al userului, în format chat.
    Structură: [
      {
        "type": "request" | "offer",
        "my_item": { "id": ..., "label": "...", "url": "..." },
        "matches": [
          { "id": ..., "label": "...", "url": "...", "collaboration_id": ..., "seen": bool }
        ]
      },
      ...
    ]
    """
    from sqlalchemy import or_
    from collections import defaultdict

    q = (
        PossibleCollaboration.query
        .options(
            db.joinedload(PossibleCollaboration.offer),
            db.joinedload(PossibleCollaboration.request),
        )
        .join(SellerOffer, PossibleCollaboration.offer_id == SellerOffer.id)
        .join(BuyerRequest, PossibleCollaboration.request_id == BuyerRequest.id)
        .filter(or_(SellerOffer.user_id == user_id, BuyerRequest.user_id == user_id))
        .order_by(PossibleCollaboration.created_at.desc())
    )
    all_collab = q.all()
    seen_ids = {
        r.collaboration_id
        for r in CollaborationSeen.query.filter_by(user_id=user_id).all()
    }
    
    # Grupăm potrivirile: per cerere al userului -> lista de anunțuri potrivite
    #                     per anunț al userului -> lista de cereri potrivite
    requests_dict = defaultdict(list)  # request_id -> [matches (offers)]
    offers_dict = defaultdict(list)    # offer_id -> [matches (requests)]
    
    for c in all_collab:
        if c.offer.user_id == user_id:
            # Userul are anunțul, potrivirea e cu cererea
            request_label = _request_full_label(c.request)
            # Dacă cererea e de la un client, adaugă indicator
            if getattr(c.request, 'posted_by_role', None) == 'client':
                request_label = "👤 Client: " + request_label
            request_url = (base_url.rstrip("/") + url_for("marketplace.detail", id=c.request_id)) if base_url else url_for("marketplace.detail", id=c.request_id)
            offers_dict[c.offer_id].append({
                "id": c.request_id,
                "label": request_label,
                "url": request_url,
                "collaboration_id": c.id,
                "seen": c.id in seen_ids,
                "is_client_request": getattr(c.request, 'posted_by_role', None) == 'client',
            })
        else:
            # Userul are cererea, potrivirea e cu anunțul
            offer_label = _offer_full_label(c.offer)
            offer_url = (base_url.rstrip("/") + url_for("marketplace.detail_offer", id=c.offer_id)) if base_url else url_for("marketplace.detail_offer", id=c.offer_id)
            requests_dict[c.request_id].append({
                "id": c.offer_id,
                "label": offer_label,
                "url": offer_url,
                "collaboration_id": c.id,
                "seen": c.id in seen_ids,
            })
    
    # Construim lista finală grupate
    out = []
    
    # Cererile userului cu potrivirile lor
    for request_id, matches in requests_dict.items():
        # Găsim cererea pentru label
        req_obj = BuyerRequest.query.get(request_id)
        if req_obj:
            out.append({
                "type": "request",
                "my_item": {
                    "id": request_id,
                    "label": _request_full_label(req_obj),
                    "url": (base_url.rstrip("/") + url_for("marketplace.detail", id=request_id)) if base_url else url_for("marketplace.detail", id=request_id),
                },
                "matches": matches,
            })
    
    # Anunțurile userului cu potrivirile lor
    for offer_id, matches in offers_dict.items():
        offer_obj = SellerOffer.query.get(offer_id)
        if offer_obj:
            out.append({
                "type": "offer",
                "my_item": {
                    "id": offer_id,
                    "label": _offer_full_label(offer_obj),
                    "url": (base_url.rstrip("/") + url_for("marketplace.detail_offer", id=offer_id)) if base_url else url_for("marketplace.detail_offer", id=offer_id),
                },
                "matches": matches,
            })
    
    # Sortăm după data celei mai recente potriviri (primul match din lista matches)
    def sort_key(item):
        if item["matches"]:
            # Găsim collaboration_id din primul match și sortăm după created_at
            collab_id = item["matches"][0]["collaboration_id"]
            collab = PossibleCollaboration.query.get(collab_id)
            return collab.created_at if collab else utcnow()
        return utcnow()
    
    out.sort(key=sort_key, reverse=True)
    return out


@assistant_bp.get("/collaborations")
@login_required
@access_required
def get_collaborations():
    """
    Listă posibile colaborări pentru utilizatorul curent: link direct către cerere sau anunț.
    """
    base = (request.url_root or "").rstrip("/")
    items = _collaborations_list_for_user(current_user.id, base)
    unread_count, _ = _collaborations_unread_for_user(current_user.id)
    # Verifică dacă există potriviri cu clienți pentru notificare
    has_client_matches = False
    for item in items:
        if item.get("matches"):
            for match in item["matches"]:
                if match.get("is_client_request"):
                    has_client_matches = True
                    break
        if has_client_matches:
            break
    # Statistică ultimele 3 luni (pentru viitor)
    from datetime import timedelta
    from models import PossibleCollaboration as PC
    cutoff = utcnow() - timedelta(days=90)
    stats_count = PC.query.filter(PC.created_at >= cutoff).count()
    return jsonify({
        "ok": True,
        "items": items,
        "unread_count": unread_count,
        "has_client_matches": has_client_matches,
        "collaborations": items,  # Pentru compatibilitate cu JS
        "stats_last_3_months": stats_count,
    })


@assistant_bp.post("/collaborations/seen")
@login_required
@access_required
def mark_collaborations_seen():
    """Marchează toate potrivirile utilizatorului ca văzute (când deschide secțiunea Posibile colaborări)."""
    from sqlalchemy import or_

    q = (
        PossibleCollaboration.query
        .join(SellerOffer, PossibleCollaboration.offer_id == SellerOffer.id)
        .join(BuyerRequest, PossibleCollaboration.request_id == BuyerRequest.id)
        .filter(or_(SellerOffer.user_id == current_user.id, BuyerRequest.user_id == current_user.id))
    )
    now = utcnow()
    for c in q.all():
        existing = CollaborationSeen.query.filter_by(
            collaboration_id=c.id, user_id=current_user.id
        ).first()
        if not existing:
            db.session.add(CollaborationSeen(
                collaboration_id=c.id,
                user_id=current_user.id,
                seen_at=now,
            ))
    db.session.commit()
    return jsonify({"ok": True})


@assistant_bp.post("/announcements/<int:aid>/read")
@login_required
@access_required
def mark_announcement_read(aid: int):
    """Marchează anunțul ca citit. Nu mai apare la acest utilizator."""
    a = Announcement.query.get(aid)
    if not a:
        return jsonify({"ok": False, "error": "not found"}), 404
    existing = UserAnnouncementRead.query.filter_by(
        user_id=current_user.id, announcement_id=aid
    ).first()
    if not existing:
        r = UserAnnouncementRead(user_id=current_user.id, announcement_id=aid)
        db.session.add(r)
        db.session.commit()
    return jsonify({"ok": True})


@assistant_bp.post("/expiry-reminder/dismiss")
@login_required
@access_required
def dismiss_expiry_reminder():
    """Utilizatorul a dat OK la notificarea de expirare. Nu o mai arătăm azi."""
    current_user.expiry_reminder_dismissed_at = utcnow()
    db.session.commit()
    return jsonify({"ok": True})


# --- Task-uri azi (pentru tooltip asistent: „Astăzi ai de făcut…”) ---

@assistant_bp.get("/today-tasks")
@login_required
@access_required
def get_today_tasks():
    """
    Returnează task-urile utilizatorului cu termen azi (due_date == azi), nefinalizate.
    Folosit de asistent pentru mesajul „Astăzi ai de făcut: …” în tooltip. Doar pentru conturi active.
    """
    if not current_user.is_active_account():
        return jsonify({"ok": True, "tasks": []})
    today = date.today()
    tasks = (
        Task.query.filter_by(user_id=current_user.id)
        .filter(Task.due_date == today, Task.status != "done")
        .order_by(Task.created_at.asc())
        .limit(20)
        .all()
    )
    return jsonify({
        "ok": True,
        "tasks": [{"id": t.id, "title": t.title or ""} for t in tasks],
    })
