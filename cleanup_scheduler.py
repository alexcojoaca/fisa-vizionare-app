# cleanup_scheduler.py – Auto-cleanup zilnic + failsafe
"""
- Auto-cleanup la 03:00 UTC (APScheduler)
- Failsafe: dacă nu s-a rulat cu succes de 180 zile, rulează la primul request al zilei
"""
import logging
from datetime import datetime, timedelta, timezone

_log = logging.getLogger(__name__)

FAILSAFE_DAYS = 180
_failsafe_checked_today = None  # date string "YYYY-MM-DD" când am făcut ultima verificare


def _today_utc():
    return datetime.now(timezone.utc).date().isoformat()


def run_scheduled_cleanup(app):
    """Rulează curățarea completă (toate categoriile). Folosit de auto și failsafe."""
    with app.app_context():
        try:
            from admin.cleanup import run_cleanup, save_cleanup_run, get_last_successful_run_at

            toggles = {
                "remote_expired": True,
                "buyer_request": True,
                "assistant_reminder": True,
                "task_completed": True,
                "assistant_usage": True,
                "user_device": True,
                "device_trial": False,
                "team_task_assignment_done": True,
                "daily_activity": True,
            }
            result = run_cleanup(dry_run=False, toggles=toggles, mode="auto", ran_by_user_id=None)
            save_cleanup_run(
                mode="auto",
                ok=result["ok"],
                details=result.get("details", {}),
                error_text=result.get("error"),
                ran_by_user_id=None,
            )
            if result["ok"]:
                _log.info("Auto-cleanup finalizat: %s rânduri șterse", result.get("total_deleted", 0))
            else:
                _log.warning("Auto-cleanup eroare: %s", result.get("error", "necunoscut"))
        except Exception as e:
            _log.exception("Eroare la auto-cleanup: %s", e)


def maybe_run_failsafe(app):
    """
    Verificare failsafe: dacă nu s-a rulat cu succes în ultimele 180 zile,
    rulează cleanup o singură dată (la primul request al zilei).
    """
    global _failsafe_checked_today
    today = _today_utc()
    if _failsafe_checked_today == today:
        return
    _failsafe_checked_today = today

    with app.app_context():
        try:
            from admin.cleanup import get_last_successful_run_at, run_cleanup, save_cleanup_run

            last = get_last_successful_run_at()
            if last is None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            else:
                cutoff = datetime.now(timezone.utc) - timedelta(days=FAILSAFE_DAYS)

            if last is not None and last >= cutoff:
                return  # totul ok, nu e nevoie de failsafe

            _log.info("Failsafe: ultima curățare reușită %s zile în urmă. Rulez cleanup.", FAILSAFE_DAYS)

            toggles = {
                "remote_expired": True,
                "buyer_request": True,
                "assistant_reminder": True,
                "task_completed": True,
                "assistant_usage": True,
                "user_device": True,
                "device_trial": False,
                "team_task_assignment_done": True,
                "daily_activity": True,
            }
            result = run_cleanup(
                dry_run=False,
                toggles=toggles,
                mode="auto_failsafe",
                ran_by_user_id=None,
            )
            save_cleanup_run(
                mode="auto_failsafe",
                ok=result["ok"],
                details=result.get("details", {}),
                error_text=result.get("error"),
                ran_by_user_id=None,
            )
        except Exception as e:
            _log.exception("Eroare failsafe cleanup: %s", e)


def init_scheduler(app):
    """Inițializează APScheduler pentru 03:00 UTC zilnic."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            func=lambda: run_scheduled_cleanup(app),
            trigger="cron",
            hour=3,
            minute=0,
            id="cleanup_daily",
        )
        scheduler.start()
        _log.info("Scheduler cleanup: programat 03:00 UTC zilnic")
    except ImportError:
        _log.info("APScheduler nu e instalat. Auto-cleanup la 03:00 nu rulează. Folosește cron extern sau failsafe.")
    except Exception as e:
        _log.warning("Nu s-a putut porni scheduler: %s", e)
