from datetime import date, datetime, timedelta, timezone
import secrets

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user
from sqlalchemy import or_, func

from access_control import access_required, agent_required
from extensions import db
from models import Task, utcnow, User

from .forms import TaskForm, QuickAddForm


todo_bp = Blueprint("todo", __name__, url_prefix="/todo")

# 30 days after completion -> remove task
AUTO_EXPIRE_DAYS = 30


def _run_cleanup():
    """Delete tasks completed more than AUTO_EXPIRE_DAYS ago (for current user)."""
    if not current_user.is_authenticated:
        return
    cutoff = utcnow() - timedelta(days=AUTO_EXPIRE_DAYS)
    deleted = (
        Task.query.filter_by(user_id=current_user.id)
        .filter(Task.completed_at.isnot(None), Task.completed_at < cutoff)
        .delete()
    )
    if deleted:
        db.session.commit()


def _today_utc():
    return date.today()


def _is_overdue(task):
    if not task.due_date:
        return False
    if task.status == "done":
        return False
    return task.due_date < _today_utc()


def _check_todo_access():
    """Verifică dacă utilizatorul are acces la To-Do (doar conturi active)."""
    if not current_user.is_active_account():
        flash("To-Do List este disponibil doar pentru conturi active. Activează contul pentru a accesa această funcție.", "error")
        return redirect(url_for("menu.menu_home"))
    return None


@todo_bp.get("/")
@agent_required
@access_required
def list_tasks():
    # To-Do este disponibil DOAR pentru conturi active (trial/paid)
    redirect_response = _check_todo_access()
    if redirect_response:
        return redirect_response
    # Cleanup task-uri vechi se face la 03:00 UTC (cleanup_scheduler + admin.cleanup)
    # Nu mai rulăm _run_cleanup() aici ca să păstrăm pagina rapidă.

    q = Task.query.filter_by(user_id=current_user.id)

    # Search (title, description, tags)
    search = (request.args.get("q") or "").strip()
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Task.title.ilike(term),
                Task.description.ilike(term),
                Task.tags.ilike(term),
            )
        )

    # Filter: status
    status_filter = request.args.get("status", "").strip()
    if status_filter in ("open", "in-progress", "done"):
        q = q.filter(Task.status == status_filter)

    # Filter: priority
    priority_filter = request.args.get("priority", "").strip()
    if priority_filter in ("low", "medium", "high"):
        q = q.filter(Task.priority == priority_filter)

    # Filter: due_today
    if request.args.get("due_today") == "1":
        q = q.filter(Task.due_date == _today_utc())

    # Filter: overdue
    if request.args.get("overdue") == "1":
        q = q.filter(
            Task.due_date.isnot(None),
            Task.due_date < _today_utc(),
            Task.status != "done",
        )

    # Filter: calendar day (day, month, year)
    day_filter = request.args.get("day")
    if day_filter:
        try:
            # expect YYYY-MM-DD
            parsed = datetime.strptime(day_filter, "%Y-%m-%d").date()
            q = q.filter(Task.due_date == parsed)
        except ValueError:
            pass

    # Limit pentru performanță
    TASKS_LIST_LIMIT = 500
    tasks = q.order_by(Task.created_at.desc()).limit(TASKS_LIST_LIMIT).all()

    today = _today_utc()
    week_end = today + timedelta(days=6)

    # Grupare în secțiuni pentru UX premium
    sections = {
        "today": [],      # Azi
        "overdue": [],    # Întârziate
        "this_week": [],  # Săptămâna asta
        "later": [],      # Mai târziu
        "no_date": [],    # Fără dată
        "done": [],       # Finalizate
    }
    for t in tasks:
        if t.status == "done":
            sections["done"].append(t)
        elif not t.due_date:
            sections["no_date"].append(t)
        elif t.due_date < today:
            sections["overdue"].append(t)
        elif t.due_date == today:
            sections["today"].append(t)
        elif t.due_date <= week_end:
            sections["this_week"].append(t)
        else:
            sections["later"].append(t)

    # Calendar: current month (or from ?year=&month=)
    try:
        year = int(request.args.get("year") or _today_utc().year)
        month = int(request.args.get("month") or _today_utc().month)
    except (TypeError, ValueError):
        year, month = _today_utc().year, _today_utc().month

    # Tasks per day for calendar: un singur query cu GROUP BY (mai rapid decât .all())
    from calendar import monthrange
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    calendar_counts = (
        db.session.query(Task.due_date, func.count(Task.id))
        .filter(
            Task.user_id == current_user.id,
            Task.due_date.isnot(None),
            Task.due_date >= first_day,
            Task.due_date <= last_day,
        )
        .group_by(Task.due_date)
        .all()
    )
    tasks_by_day = {d.isoformat(): count for d, count in calendar_counts}

    # weekday(): Monday=0, Sunday=6 (same as calendar grid Lun..Dum)
    first_weekday = first_day.weekday()
    month_names = (
        "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
        "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie",
    )
    month_name = month_names[month - 1]

    return render_template(
        "todo_list.html",
        tasks=tasks,
        sections=sections,
        year=year,
        month=month,
        first_day=first_day,
        last_day=last_day,
        first_weekday=first_weekday,
        month_name=month_name,
        tasks_by_day=tasks_by_day,
        is_overdue=_is_overdue,
        today=_today_utc(),
        search=search,
        status_filter=status_filter,
        priority_filter=priority_filter,
    )


# Template presets for quick-add (title, tags)
TASK_TEMPLATES = {
    "vizionare": ("Vizionare imobil", "vizionare"),
    "followup": ("Follow-up client", "follow-up, client"),
    "contract": ("Pregătire contract", "contract"),
}


@todo_bp.route("/quick-add", methods=["POST"])
@agent_required
@access_required
def quick_add():
    """Adaugă task rapid (doar titlu)."""
    redirect_response = _check_todo_access()
    if redirect_response:
        return redirect_response
    form = QuickAddForm()
    if form.validate_on_submit():
        task = Task(
            user_id=current_user.id,
            title=(form.title.data or "").strip(),
            priority="medium",
            status="open",
        )
        task.generate_completion_token()  # Generează token pentru notificări
        db.session.add(task)
        db.session.commit()
        flash("Task adăugat.", "success")
    return redirect(request.referrer or url_for("todo.list_tasks"))


@todo_bp.route("/new", methods=["GET", "POST"])
@agent_required
@access_required
def new_task():
    redirect_response = _check_todo_access()
    if redirect_response:
        return redirect_response
    template_key = request.args.get("template", "").strip().lower()
    preset = TASK_TEMPLATES.get(template_key)
    form = TaskForm()
    if preset and request.method == "GET":
        form.title.data = preset[0]
        form.tags.data = preset[1]
    if form.validate_on_submit():
        task = Task(
            user_id=current_user.id,
            title=(form.title.data or "").strip(),
            description=(form.description.data or "").strip() or None,
            due_date=form.due_date.data,
            priority=form.priority.data or "medium",
            status=form.status.data or "open",
            tags=(form.tags.data or "").strip() or None,
        )
        if task.status == "done":
            task.completed_at = utcnow()
        task.generate_completion_token()  # Generează token pentru notificări
        db.session.add(task)
        db.session.commit()
        flash("Task creat.", "success")
        return redirect(url_for("todo.list_tasks"))
    return render_template("todo_form.html", form=form, task=None)


def _get_task_or_404(task_id):
    t = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not t:
        from flask import abort
        abort(404)
    return t


@todo_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@agent_required
@access_required
def edit_task(task_id):
    redirect_response = _check_todo_access()
    if redirect_response:
        return redirect_response
    task = _get_task_or_404(task_id)
    form = TaskForm(
        title=task.title,
        description=task.description or "",
        due_date=task.due_date,
        priority=task.priority,
        status=task.status,
        tags=task.tags or "",
    )
    if form.validate_on_submit():
        task.title = (form.title.data or "").strip()
        task.description = (form.description.data or "").strip() or None
        task.due_date = form.due_date.data
        task.priority = form.priority.data or "medium"
        prev_status = task.status
        task.status = form.status.data or "open"
        task.tags = (form.tags.data or "").strip() or None
        if task.status == "done" and prev_status != "done":
            task.completed_at = utcnow()
        elif task.status != "done":
            task.completed_at = None
        db.session.commit()
        flash("Task actualizat.", "success")
        return redirect(url_for("todo.list_tasks"))
    return render_template("todo_form.html", form=form, task=task)


@todo_bp.post("/<int:task_id>/delete")
@agent_required
@access_required
def delete_task(task_id):
    redirect_response = _check_todo_access()
    if redirect_response:
        return redirect_response
    task = _get_task_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task șters.", "success")
    return redirect(url_for("todo.list_tasks"))


@todo_bp.post("/<int:task_id>/toggle")
@agent_required
@access_required
def toggle_task(task_id):
    redirect_response = _check_todo_access()
    if redirect_response:
        return redirect_response
    task = _get_task_or_404(task_id)
    if task.status == "done":
        task.status = "open"
        task.completed_at = None
        msg = "Task redeschis."
    else:
        task.status = "done"
        task.completed_at = utcnow()
        msg = "Task finalizat."
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return jsonify({"ok": True, "status": task.status, "message": msg})
    flash(msg, "success")
    return redirect(request.referrer or url_for("todo.list_tasks"))


@todo_bp.get("/complete/<token>")
def complete_task_by_token(token):
    """
    Marchează task-ul ca făcut prin token (pentru notificări).
    Nu necesită autentificare - token-ul este suficient pentru securitate.
    """
    task = Task.query.filter_by(completion_token=token, status="open").first()
    if not task:
        flash("Task-ul nu a fost găsit sau a fost deja finalizat.", "error")
        return redirect(url_for("home"))
    
    task.status = "done"
    task.completed_at = utcnow()
    db.session.commit()
    
    flash("Task finalizat cu succes! ✅", "success")
    return redirect(url_for("todo.list_tasks"))


def get_today_tasks_for_user(user_id):
    """Returnează toate task-urile pentru ziua de azi pentru un utilizator."""
    today = _today_utc()
    tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.due_date == today,
        Task.status != "done"
    ).order_by(
        Task.priority.desc(),  # high priority first
        Task.due_time.asc() if Task.due_time else None
    ).all()
    return tasks


def format_task_notification_message(tasks, user, base_url):
    """
    Formatează mesajul de notificare cu task-urile pentru ziua respectivă.
    Include link-uri pentru completare.
    """
    if not tasks:
        return None
    
    today_str = _today_utc().strftime("%d.%m.%Y")
    message_parts = [f"📋 *Task-uri pentru {today_str}*\n"]
    
    for idx, task in enumerate(tasks, 1):
        # Generează token dacă nu există
        if not task.completion_token:
            task.generate_completion_token()
            db.session.commit()
        
        completion_url = f"{base_url}/todo/complete/{task.completion_token}"
        
        task_line = f"\n*{idx}. {task.title}*"
        if task.description:
            task_line += f"\n   {task.description}"
        if task.due_time:
            time_str = task.due_time.strftime("%H:%M")
            task_line += f"\n   ⏰ {time_str}"
        
        # Link pentru completare
        task_line += f"\n   ✅ Bifează: {completion_url}"
        
        message_parts.append(task_line)
    
    message_parts.append(f"\n\n_Total: {len(tasks)} task-uri pentru astăzi_")
    return "\n".join(message_parts)
