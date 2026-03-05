# admin/cleanup.py – Service curățare bază de date
"""
Logica centrală pentru Admin Cleaner:
- Curățare per categorie (toggle)
- Dry-run vs run real
- Lock anti-dublu
- Raport JSON
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from extensions import db
from models import (
    AssistantDailyUsage,
    BuyerRequest,
    ChirieRemoteSigning,
    DailyActivity,
    DeviceTrial,
    Task,
    TeamTask,
    TeamTaskAssignment,
    UserDevice,
    VanzareRemoteSigning,
    CleanupRun,
    utcnow,
)

_log = logging.getLogger(__name__)

# Categorii cu chei și etichete
CATEGORIES = {
    "remote_expired": "Remote expirate (chirie + vânzare)",
    "buyer_request": "Cereri marketplace > 30 zile",
    "task_completed": "Task-uri completate > 30 zile",
    "assistant_usage": "Assistant usage (mai vechi decât azi)",
    "user_device": "Device-uri inactive > 180 zile",
    "device_trial": "Device trial vechi > 365 zile",
    "team_task_assignment_done": "TeamTaskAssignment DONE > 90 zile",
    "daily_activity": "DailyActivity > 90 zile",
    "team_task_old_7_days": "TeamTask mai vechi de 7 zile (rulează la fiecare 6 zile)",
}

# Retention în zile (configurabil)
REMOTE_BUFFER_DAYS = 1  # expires_at < now - 1 zi
BUYER_REQUEST_DAYS = 30
TASK_COMPLETED_DAYS = 30
ASSISTANT_USAGE_RETENTION_DAYS = 1  # păstrăm doar azi (env: ASSISTANT_USAGE_RETENTION_DAYS)
USER_DEVICE_DAYS = 180
DEVICE_TRIAL_DAYS = 365
TEAM_TASK_ASSIGNMENT_DONE_DAYS = 90
DAILY_ACTIVITY_DAYS = 90
TEAM_TASK_OLD_DAYS = 7

# Lock: nume advisory lock Postgres (sau None dacă SQLite)
ADVISORY_LOCK_ID = 0x5F31A1  # hex: 6234529


def _get_tmp_dir():
    """Director static/tmp pentru PDF-uri remote."""
    return Path(current_app.root_path) / "static" / "tmp"


def _safe_table_exists(table_name: str) -> bool:
    """Verifică dacă tabelul există (Postgres)."""
    try:
        with db.engine.connect() as conn:
            r = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :t"
                ),
                {"t": table_name},
            )
            return r.fetchone() is not None
    except Exception:
        return False


def _safe_column_exists(table_name: str, column_name: str) -> bool:
    """Verifică dacă coloana există."""
    try:
        with db.engine.connect() as conn:
            r = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
                ),
                {"t": table_name, "c": column_name},
            )
            return r.fetchone() is not None
    except Exception:
        return False


def _acquire_lock() -> bool:
    """Advisory lock Postgres. Returnează True dacă am luat lock-ul."""
    if "postgresql" not in str(db.engine.url):
        return True  # SQLite: fără lock (single-writer)
    try:
        with db.engine.connect() as conn:
            r = conn.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": ADVISORY_LOCK_ID})
            row = r.fetchone()
            return row and row[0] is True
    except Exception:
        return False


def _release_lock():
    """Eliberează advisory lock (la închiderea sesiunii)."""
    if "postgresql" not in str(db.engine.url):
        return
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": ADVISORY_LOCK_ID})
    except Exception:
        pass


def _run_category_remote_expired(dry_run: bool, details: dict) -> int:
    """Remote signing expirate + 1 zi buffer. Șterge și PDF-uri."""
    details["remote_expired"] = {"chirie": 0, "vanzare": 0, "warnings": []}
    total = 0
    cutoff = utcnow() - timedelta(days=REMOTE_BUFFER_DAYS)

    if not _safe_table_exists("chirie_remote_signing"):
        details["remote_expired"]["warnings"].append("Tabel chirie_remote_signing lipsă")
        return 0
    if not _safe_table_exists("vanzare_remote_signing"):
        details["remote_expired"]["warnings"].append("Tabel vanzare_remote_signing lipsă")
        return 0

    try:
        # Chirie
        q = ChirieRemoteSigning.query.filter(
            ChirieRemoteSigning.expires_at.isnot(None),
            ChirieRemoteSigning.expires_at < cutoff,
        )
        count = q.count()
        details["remote_expired"]["chirie"] = count
        if not dry_run and count > 0:
            tmp_dir = _get_tmp_dir()
            for rec in q.all():
                if rec.pdf_doc_id:
                    pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
                    try:
                        if pdf_path.exists():
                            pdf_path.unlink()
                    except Exception:
                        pass
                db.session.delete(rec)
            db.session.commit()
        total += count
    except ProgrammingError as e:
        details["remote_expired"]["warnings"].append(f"Eroare chirie: {str(e)[:200]}")
    except Exception as e:
        details["remote_expired"]["warnings"].append(f"Eroare chirie: {str(e)[:200]}")

    try:
        # Vanzare
        q = VanzareRemoteSigning.query.filter(
            VanzareRemoteSigning.expires_at.isnot(None),
            VanzareRemoteSigning.expires_at < cutoff,
        )
        count = q.count()
        details["remote_expired"]["vanzare"] = count
        if not dry_run and count > 0:
            tmp_dir = _get_tmp_dir()
            for rec in q.all():
                if rec.pdf_doc_id:
                    pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
                    try:
                        if pdf_path.exists():
                            pdf_path.unlink()
                    except Exception:
                        pass
                db.session.delete(rec)
            db.session.commit()
        total += count
    except ProgrammingError as e:
        details["remote_expired"]["warnings"].append(f"Eroare vanzare: {str(e)[:200]}")
    except Exception as e:
        details["remote_expired"]["warnings"].append(f"Eroare vanzare: {str(e)[:200]}")

    return total


def _run_category_buyer_request(dry_run: bool, details: dict) -> int:
    """Cereri marketplace created_at < now - 30 zile. RequestZones CASCADE."""
    details["buyer_request"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("buyer_request"):
        details["buyer_request"]["warnings"].append("Tabel buyer_request lipsă")
        return 0
    try:
        cutoff = utcnow() - timedelta(days=BUYER_REQUEST_DAYS)
        q = BuyerRequest.query.filter(BuyerRequest.created_at < cutoff)
        count = q.count()
        details["buyer_request"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["buyer_request"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_task_completed(dry_run: bool, details: dict) -> int:
    """Task-uri cu completed_at NOT NULL și completed_at < now - 30 zile."""
    details["task_completed"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("task"):
        details["task_completed"]["warnings"].append("Tabel task lipsă")
        return 0
    try:
        cutoff = utcnow() - timedelta(days=TASK_COMPLETED_DAYS)
        q = Task.query.filter(
            Task.completed_at.isnot(None),
            Task.completed_at < cutoff,
        )
        count = q.count()
        details["task_completed"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["task_completed"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_assistant_usage(dry_run: bool, details: dict) -> int:
    """Assistant daily usage: usage_date < azi (sau retention din env)."""
    details["assistant_usage"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("assistant_daily_usage"):
        details["assistant_usage"]["warnings"].append("Tabel assistant_daily_usage lipsă")
        return 0
    try:
        import os
        days = int(os.getenv("ASSISTANT_USAGE_RETENTION_DAYS", "1"))
        cutoff_date = (utcnow() - timedelta(days=days)).date()
        q = AssistantDailyUsage.query.filter(AssistantDailyUsage.usage_date < cutoff_date)
        count = q.count()
        details["assistant_usage"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["assistant_usage"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_user_device(dry_run: bool, details: dict) -> int:
    """user_device: last_seen_at < now - 180 zile."""
    details["user_device"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("user_device"):
        details["user_device"]["warnings"].append("Tabel user_device lipsă")
        return 0
    if not _safe_column_exists("user_device", "last_seen_at"):
        details["user_device"]["warnings"].append("Coloana last_seen_at lipsă")
        return 0
    try:
        cutoff = utcnow() - timedelta(days=USER_DEVICE_DAYS)
        q = UserDevice.query.filter(UserDevice.last_seen_at < cutoff)
        count = q.count()
        details["user_device"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["user_device"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_team_task_assignment_done(dry_run: bool, details: dict) -> int:
    """TeamTaskAssignment cu status=done și completed_at < now - 90 zile."""
    details["team_task_assignment_done"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("team_task_assignment"):
        details["team_task_assignment_done"]["warnings"].append("Tabel team_task_assignment lipsă")
        return 0
    try:
        cutoff = utcnow() - timedelta(days=TEAM_TASK_ASSIGNMENT_DONE_DAYS)
        q = TeamTaskAssignment.query.filter(
            TeamTaskAssignment.status == "done",
            TeamTaskAssignment.completed_at.isnot(None),
            TeamTaskAssignment.completed_at < cutoff,
        )
        count = q.count()
        details["team_task_assignment_done"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["team_task_assignment_done"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_team_task_old_7_days(dry_run: bool, details: dict) -> int:
    """TeamTask cu created_at < now - 7 zile (păstrează doar ultimele 7 zile)."""
    details["team_task_old_7_days"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("team_task"):
        details["team_task_old_7_days"]["warnings"].append("Tabel team_task lipsă")
        return 0
    try:
        cutoff = utcnow() - timedelta(days=TEAM_TASK_OLD_DAYS)
        q = TeamTask.query.filter(TeamTask.created_at < cutoff)
        count = q.count()
        details["team_task_old_7_days"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["team_task_old_7_days"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_daily_activity(dry_run: bool, details: dict) -> int:
    """DailyActivity cu date < now - 90 zile."""
    details["daily_activity"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("daily_activity"):
        details["daily_activity"]["warnings"].append("Tabel daily_activity lipsă")
        return 0
    try:
        cutoff_date = (utcnow() - timedelta(days=DAILY_ACTIVITY_DAYS)).date()
        q = DailyActivity.query.filter(DailyActivity.date < cutoff_date)
        count = q.count()
        details["daily_activity"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["daily_activity"]["warnings"].append(str(e)[:200])
        return 0


def _run_category_device_trial(dry_run: bool, details: dict) -> int:
    """device_trial: updated_at < now - 365 zile ȘI device_id nu e în user_device."""
    details["device_trial"] = {"count": 0, "warnings": []}
    if not _safe_table_exists("device_trial"):
        details["device_trial"]["warnings"].append("Tabel device_trial lipsă")
        return 0
    if not _safe_column_exists("device_trial", "updated_at"):
        details["device_trial"]["warnings"].append("Coloana updated_at lipsă")
        return 0
    try:
        cutoff = utcnow() - timedelta(days=DEVICE_TRIAL_DAYS)
        # device_id care mai există în user_device
        active_subq = db.session.query(UserDevice.device_id).distinct()
        q = DeviceTrial.query.filter(
            DeviceTrial.updated_at < cutoff,
            ~DeviceTrial.device_id.in_(active_subq),
        )
        count = q.count()
        details["device_trial"]["count"] = count
        if not dry_run and count > 0:
            q.delete(synchronize_session=False)
            db.session.commit()
        return count
    except Exception as e:
        details["device_trial"]["warnings"].append(str(e)[:200])
        return 0


def run_cleanup(
    dry_run: bool,
    toggles: dict,
    mode: str,
    ran_by_user_id: int | None = None,
) -> dict:
    """
    Execută curățarea conform toggle-urilor.
    Returnează: {
        "ok": bool,
        "locked": bool,  # True dacă nu am putut lua lock
        "details": {...},
        "total_deleted": int,
        "error": str | None,
    }
    """
    result = {
        "ok": True,
        "locked": False,
        "details": {},
        "total_deleted": 0,
        "error": None,
    }

    if not dry_run and not _acquire_lock():
        result["locked"] = True
        result["ok"] = False
        result["error"] = "Curățarea este deja în curs."
        return result

    details = result["details"]
    total = 0

    try:
        if toggles.get("remote_expired", True):
            total += _run_category_remote_expired(dry_run, details)
        if toggles.get("buyer_request", True):
            total += _run_category_buyer_request(dry_run, details)
        if toggles.get("task_completed", True):
            total += _run_category_task_completed(dry_run, details)
        if toggles.get("assistant_usage", True):
            total += _run_category_assistant_usage(dry_run, details)
        if toggles.get("user_device", True):
            total += _run_category_user_device(dry_run, details)
        if toggles.get("device_trial", False):  # opțional, default off
            total += _run_category_device_trial(dry_run, details)
        if toggles.get("team_task_assignment_done", True):
            total += _run_category_team_task_assignment_done(dry_run, details)
        if toggles.get("daily_activity", True):
            total += _run_category_daily_activity(dry_run, details)
        if toggles.get("team_task_old_7_days", True):
            total += _run_category_team_task_old_7_days(dry_run, details)

        result["total_deleted"] = total
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)[:500]
        _log.exception("Cleanup error")
    finally:
        if not dry_run:
            _release_lock()

    return result


def save_cleanup_run(mode: str, ok: bool, details: dict, error_text: str | None, ran_by_user_id: int | None = None):
    """Salvează în cleanup_run."""
    if not _safe_table_exists("cleanup_run"):
        return
    try:
        r = CleanupRun(
            ran_at=utcnow(),
            ran_by_user_id=ran_by_user_id,
            mode=mode,
            ok=ok,
            details_json=json.dumps(details, ensure_ascii=False) if details else None,
            error_text=error_text,
        )
        db.session.add(r)
        db.session.commit()
    except Exception as e:
        _log.warning("Nu s-a putut salva cleanup_run: %s", e)
        db.session.rollback()


def get_last_successful_run_at() -> datetime | None:
    """Data ultimei rulări reușite (ok=True)."""
    if not _safe_table_exists("cleanup_run"):
        return None
    try:
        r = CleanupRun.query.filter_by(ok=True).order_by(CleanupRun.ran_at.desc()).first()
        return r.ran_at if r else None
    except Exception:
        return None


def get_recent_runs(limit: int = 20):
    """Ultimele N rulări pentru istoric."""
    if not _safe_table_exists("cleanup_run"):
        return []
    try:
        return (
            CleanupRun.query
            .order_by(CleanupRun.ran_at.desc())
            .limit(limit)
            .all()
        )
    except Exception:
        return []
