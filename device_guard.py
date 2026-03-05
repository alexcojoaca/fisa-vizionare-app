# device_guard.py
import hashlib
from datetime import datetime, timezone

from flask import request, current_app, flash, redirect, url_for
from flask_login import current_user, logout_user

from extensions import db
from models import UserDevice


MAX_DEVICES = 3  # tu ai zis 3 ✅

def get_device_id() -> str:
    """
    Returnează device_id din cookie (stabil).
    Dacă nu există, întoarce string gol.
    """
    return (request.cookies.get("device_id") or "").strip()



def _utcnow():
    return datetime.now(timezone.utc)


def _fingerprint() -> str:
    """
    Fingerprint stabil-ish pentru device.
    Nu e perfect (browser privacy etc.), dar suficient pentru anti-sharing basic.
    """
    ua = request.headers.get("User-Agent", "")[:300]
    lang = request.headers.get("Accept-Language", "")[:120]
    # nu folosim IP ca “device id”, se schimbă des; dar îl băgăm ușor în hash ca sare
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()

    raw = f"{ua}|{lang}|{ip}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _label() -> str:
    ua = (request.headers.get("User-Agent") or "")
    if "iPhone" in ua:
        return "iPhone"
    if "Android" in ua:
        return "Android"
    if "Windows" in ua:
        return "Windows"
    if "Macintosh" in ua:
        return "Mac"
    return "Device"


def enforce_device_limit() -> bool:
    """
    Se cheamă după login. Marchează device-ul ca 'seen' sau blochează login-ul dacă e peste limită.
    Returnează True dacă e ok, False dacă a blocat (și a făcut redirect).
    """
    if not current_user.is_authenticated:
        return True

    device_id = _fingerprint()

    # există device-ul deja?
    existing = (
        UserDevice.query
        .filter_by(user_id=current_user.id, device_id=device_id)
        .first()
    )
    if existing:
        existing.last_seen_at = _utcnow()
        if not existing.label:
            existing.label = _label()
        db.session.commit()
        return True

    # device nou -> verificăm câte are
    count = UserDevice.query.filter_by(user_id=current_user.id).count()
    if count >= MAX_DEVICES:
        # prea multe device-uri: scoatem userul din login și îl trimitem la login cu mesaj
        logout_user()
        flash(
            f"Contul este folosit pe prea multe device-uri. Limită: {MAX_DEVICES}. "
            f"Te rog deconectează un device vechi sau contactează suportul.",
            "error",
        )
        return False

    # ok, îl adăugăm
    d = UserDevice(
        user_id=current_user.id,
        device_id=device_id,
        label=_label(),
        last_seen_at=_utcnow(),
    )
    db.session.add(d)
    db.session.commit()
    return True
