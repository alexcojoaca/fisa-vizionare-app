"""
Echipă & Performanță – Modul pentru manageri de agenții.
Manager: creează echipă, dă task-uri, urmărește performanța.
Agent: primește task-uri în To-Do, raportează activitate zilnică.
"""
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from sqlalchemy import func, or_

from access_control import access_required, agent_required
from extensions import db
from models import (
    User,
    Team,
    TeamMember,
    TeamTask,
    TeamTaskAssignment,
    DailyActivity,
    utcnow,
)

from .forms import TeamCreateForm, TeamTaskForm


team_bp = Blueprint("team", __name__, url_prefix="/team")


def _today_utc():
    return date.today()


def _get_team_for_manager():
    """Returnează echipa pe care o gestionează current_user (manager). None dacă nu e manager."""
    if not current_user.is_authenticated:
        return None
    team = Team.query.filter_by(manager_user_id=current_user.id).first()
    return team


def _get_team_membership():
    """Returnează TeamMember dacă current_user face parte dintr-o echipă (pending sau confirmed)."""
    if not current_user.is_authenticated:
        return None
    return TeamMember.query.filter_by(user_id=current_user.id).first()


def _get_confirmed_team_membership():
    """Returnează TeamMember confirmat (agent în echipă)."""
    m = _get_team_membership()
    return m if m and m.status == "confirmed" else None


def _manager_required(fn):
    """Decorator: doar manager cu echipă."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        team = _get_team_for_manager()
        if not team:
            flash("Trebuie să ai o echipă creată pentru a accesa această pagină.", "error")
            return redirect(url_for("team.index"))
        return fn(team=team, *args, **kwargs)

    return wrapper


# --- Index: manager -> dashboard; agent confirmat -> agent_dashboard; agent pending -> invitation; else create_team ---
@team_bp.get("/")
@agent_required
@access_required
def index():
    team = _get_team_for_manager()
    if team:
        return redirect(url_for("team.dashboard"))
    membership = _get_team_membership()
    if membership and membership.status == "confirmed":
        return redirect(url_for("team.agent_dashboard"))
    if membership and membership.status == "pending":
        return redirect(url_for("team.invitation"))
    return render_template("team/create_team.html", form=TeamCreateForm())


@team_bp.post("/delete")
@agent_required
@access_required
@_manager_required
def delete_team(team):
    """Șterge echipa. Managerul și toți agenții sunt eliminați din echipă."""
    db.session.delete(team)
    db.session.commit()
    flash("Echipa a fost ștearsă.", "success")
    return redirect(url_for("team.index"))


@team_bp.route("/create", methods=["GET", "POST"])
@agent_required
@access_required
def create_team():
    if _get_team_for_manager():
        return redirect(url_for("team.dashboard"))
    form = TeamCreateForm()
    if form.validate_on_submit():
        name = (form.name.data or "").strip()
        team = Team(name=name, manager_user_id=current_user.id)
        db.session.add(team)
        db.session.flush()
        member = TeamMember(team_id=team.id, user_id=current_user.id, role="manager", status="confirmed")
        db.session.add(member)
        db.session.commit()
        flash("Echipa a fost creată.", "success")
        return redirect(url_for("team.dashboard"))
    return render_template("team/create_team.html", form=form)


# --- Dashboard Manager ---
@team_bp.get("/dashboard")
@agent_required
@access_required
@_manager_required
def dashboard(team):
    today = _today_utc()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)

    agent_user_ids = [
        m.user_id
        for m in TeamMember.query.filter_by(team_id=team.id, role="agent", status="confirmed").all()
    ]

    if not agent_user_ids:
        viewings_today = viewings_week = viewings_month = 0
        deals_today = deals_week = deals_month = 0
        amount_week = 0
        active_agents = 0
        weekly_data = []
        monthly_data = []
        max_weekly_viewings = 1
    else:
        # Vizionări: sum din DailyActivity
        q_today = (
            db.session.query(func.coalesce(func.sum(DailyActivity.viewings_count), 0))
            .filter(DailyActivity.user_id.in_(agent_user_ids), DailyActivity.date == today)
        ).scalar() or 0
        q_week = (
            db.session.query(func.coalesce(func.sum(DailyActivity.viewings_count), 0))
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= week_start,
                DailyActivity.date <= week_end,
            )
        ).scalar() or 0
        q_month = (
            db.session.query(func.coalesce(func.sum(DailyActivity.viewings_count), 0))
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= month_start,
                DailyActivity.date <= today,
            )
        ).scalar() or 0
        viewings_today = int(q_today)
        viewings_week = int(q_week)
        viewings_month = int(q_month)

        q_dt = (
            db.session.query(func.coalesce(func.sum(DailyActivity.deals_closed_count), 0))
            .filter(DailyActivity.user_id.in_(agent_user_ids), DailyActivity.date == today)
        ).scalar() or 0
        q_dw = (
            db.session.query(func.coalesce(func.sum(DailyActivity.deals_closed_count), 0))
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= week_start,
                DailyActivity.date <= week_end,
            )
        ).scalar() or 0
        q_dm = (
            db.session.query(func.coalesce(func.sum(DailyActivity.deals_closed_count), 0))
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= month_start,
                DailyActivity.date <= today,
            )
        ).scalar() or 0
        deals_today = int(q_dt)
        deals_week = int(q_dw)
        deals_month = int(q_dm)

        q_amt_week = (
            db.session.query(func.coalesce(func.sum(DailyActivity.total_amount), 0))
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= week_start,
                DailyActivity.date <= week_end,
            )
        ).scalar() or 0
        amount_week = float(q_amt_week)

        # Agenți activi (cu raport în ultimele 7 zile)
        cutoff_active = today - timedelta(days=7)
        active_agents = (
            db.session.query(DailyActivity.user_id)
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= cutoff_active,
            )
            .distinct()
            .count()
        )

        # Date săptămânale pentru grafic (ultimele 4 săptămâni)
        weekly_data = []
        for i in range(4):
            ws = week_start - timedelta(days=7 * (i + 1))
            we = ws + timedelta(days=6)
            v = (
                db.session.query(func.coalesce(func.sum(DailyActivity.viewings_count), 0))
                .filter(
                    DailyActivity.user_id.in_(agent_user_ids),
                    DailyActivity.date >= ws,
                    DailyActivity.date <= we,
                )
            ).scalar() or 0
            d = (
                db.session.query(func.coalesce(func.sum(DailyActivity.deals_closed_count), 0))
                .filter(
                    DailyActivity.user_id.in_(agent_user_ids),
                    DailyActivity.date >= ws,
                    DailyActivity.date <= we,
                )
            ).scalar() or 0
            amt = (
                db.session.query(func.coalesce(func.sum(DailyActivity.total_amount), 0))
                .filter(
                    DailyActivity.user_id.in_(agent_user_ids),
                    DailyActivity.date >= ws,
                    DailyActivity.date <= we,
                )
            ).scalar() or 0
            conv = round((int(d) / int(v) * 100), 1) if v else 0
            weekly_data.append({
                "week": f"S{4 - i}",
                "viewings": int(v),
                "deals": int(d),
                "amount": float(amt),
                "conv_rate": conv,
            })
        weekly_data.reverse()
        max_weekly_viewings = max(1, max((w["viewings"] for w in weekly_data), default=1))

        # Sumar lunar (ultimele 3 luni)
        from calendar import monthrange
        monthly_data = []
        for i in range(3):
            y, m = month_start.year, month_start.month
            m -= i
            while m <= 0:
                m += 12
                y -= 1
            ms = date(y, m, 1)
            last_day = date(y, m, monthrange(y, m)[1])
            if i == 0:
                last_day = min(last_day, today)
            v = (
                db.session.query(func.coalesce(func.sum(DailyActivity.viewings_count), 0))
                .filter(
                    DailyActivity.user_id.in_(agent_user_ids),
                    DailyActivity.date >= ms,
                    DailyActivity.date <= last_day,
                )
            ).scalar() or 0
            d = (
                db.session.query(func.coalesce(func.sum(DailyActivity.deals_closed_count), 0))
                .filter(
                    DailyActivity.user_id.in_(agent_user_ids),
                    DailyActivity.date >= ms,
                    DailyActivity.date <= last_day,
                )
            ).scalar() or 0
            amt = (
                db.session.query(func.coalesce(func.sum(DailyActivity.total_amount), 0))
                .filter(
                    DailyActivity.user_id.in_(agent_user_ids),
                    DailyActivity.date >= ms,
                    DailyActivity.date <= last_day,
                )
            ).scalar() or 0
            conv = round((int(d) / int(v) * 100), 1) if v else 0
            monthly_data.append({
                "month": ms.strftime("%b %Y"),
                "viewings": int(v),
                "deals": int(d),
                "amount": float(amt),
                "conv_rate": conv,
            })

    conv_rate = round((deals_week / viewings_week) * 100, 1) if viewings_week else 0

    amount_30 = 0
    if agent_user_ids:
        last_30 = today - timedelta(days=30)
        q_amt = (
            db.session.query(func.coalesce(func.sum(DailyActivity.total_amount), 0))
            .filter(
                DailyActivity.user_id.in_(agent_user_ids),
                DailyActivity.date >= last_30,
            )
        ).scalar() or 0
        amount_30 = float(q_amt)

    return render_template(
        "team/dashboard.html",
        team=team,
        active_agents=active_agents,
        total_agents=len(agent_user_ids),
        viewings_today=viewings_today,
        viewings_week=viewings_week,
        viewings_month=viewings_month,
        deals_today=deals_today,
        deals_week=deals_week,
        deals_month=deals_month,
        conv_rate=conv_rate,
        weekly_data=weekly_data,
        monthly_data=monthly_data,
        max_weekly_viewings=max_weekly_viewings if agent_user_ids else 1,
        amount_30=amount_30,
        amount_week=amount_week if agent_user_ids else 0,
    )


# --- Agenți ---
@team_bp.get("/agents")
@agent_required
@access_required
@_manager_required
def agents_list(team):
    members = (
        TeamMember.query.filter_by(team_id=team.id, role="agent", status="confirmed")
        .join(User, TeamMember.user_id == User.id)
        .add_columns(User.id, User.full_name, User.email)
        .all()
    )
    today = _today_utc()

    last_30 = today - timedelta(days=30)
    agents_data = []
    for m, uid, name, email in members:
        viewings_today = (
            db.session.query(func.coalesce(func.sum(DailyActivity.viewings_count), 0))
            .filter_by(user_id=uid, date=today)
        ).scalar() or 0
        deals_today = (
            db.session.query(func.coalesce(func.sum(DailyActivity.deals_closed_count), 0))
            .filter_by(user_id=uid, date=today)
        ).scalar() or 0
        amount_30 = (
            db.session.query(func.coalesce(func.sum(DailyActivity.total_amount), 0))
            .filter(
                DailyActivity.user_id == uid,
                DailyActivity.date >= last_30,
            )
        ).scalar() or 0
        tasks_open = (
            TeamTaskAssignment.query.join(TeamTask, TeamTaskAssignment.task_id == TeamTask.id)
            .filter(
                TeamTaskAssignment.assignee_user_id == uid,
                TeamTaskAssignment.status == "open",
                TeamTask.team_id == team.id,
            )
            .count()
        )
        agents_data.append({
            "user_id": uid,
            "full_name": name,
            "email": email,
            "viewings_today": int(viewings_today),
            "deals_today": int(deals_today),
            "amount_30": float(amount_30),
            "tasks_open": tasks_open,
        })

    return render_template("team/agents_list.html", team=team, agents=agents_data)


@team_bp.get("/agents/<int:user_id>")
@agent_required
@access_required
@_manager_required
def agent_detail(team, user_id):
    member = TeamMember.query.filter_by(team_id=team.id, user_id=user_id, role="agent").first()
    if not member:
        abort(404)
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    today = _today_utc()
    last_7 = today - timedelta(days=7)
    last_30 = today - timedelta(days=30)

    activities = (
        DailyActivity.query.filter_by(user_id=user_id)
        .filter(DailyActivity.date >= last_30)
        .order_by(DailyActivity.date.desc())
        .limit(31)
        .all()
    )
    viewings_7 = sum(a.viewings_count for a in activities if a.date >= last_7)
    viewings_30 = sum(a.viewings_count for a in activities)
    deals_7 = sum(a.deals_closed_count for a in activities if a.date >= last_7)
    deals_30 = sum(a.deals_closed_count for a in activities)
    amount_30 = sum(float(a.total_amount or 0) for a in activities)

    assignments = (
        TeamTaskAssignment.query.join(TeamTask, TeamTaskAssignment.task_id == TeamTask.id)
        .filter(
            TeamTaskAssignment.assignee_user_id == user_id,
            TeamTask.team_id == team.id,
        )
        .order_by(TeamTask.due_date.asc(), TeamTask.created_at.desc())
        .all()
    )

    return render_template(
        "team/agent_detail.html",
        team=team,
        agent=user,
        activities=activities,
        viewings_7=viewings_7,
        viewings_30=viewings_30,
        deals_7=deals_7,
        deals_30=deals_30,
        amount_30=amount_30,
        assignments=assignments,
        today=today,
    )


# --- Adăugare agent ---
@team_bp.route("/agents/add", methods=["GET", "POST"])
@agent_required
@access_required
@_manager_required
def add_agent(team):
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("Introdu email-ul agentului.", "error")
            return redirect(url_for("team.add_agent"))
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Nu am găsit niciun utilizator cu acest email.", "error")
            return redirect(url_for("team.add_agent"))
        if user.id == current_user.id:
            flash("Ești deja managerul echipei.", "error")
            return redirect(url_for("team.add_agent"))
        existing = TeamMember.query.filter_by(user_id=user.id).first()
        if existing:
            flash("Acest agent face deja parte dintr-o echipă sau are o invitație în așteptare.", "error")
            return redirect(url_for("team.add_agent"))
        member = TeamMember(team_id=team.id, user_id=user.id, role="agent", status="pending")
        db.session.add(member)
        db.session.commit()
        flash(f"Invitație trimisă către {user.full_name}. Agentul trebuie să confirme din aplicație.", "success")
        return redirect(url_for("team.agents_list"))
    return render_template("team/add_agent.html", team=team)


# --- Invitație (agent pending) ---
@team_bp.get("/invitation")
@agent_required
@access_required
def invitation():
    membership = _get_team_membership()
    if not membership or membership.status != "pending":
        return redirect(url_for("team.index"))
    team = Team.query.get(membership.team_id)
    return render_template("team/invitation.html", team=team, membership=membership)


@team_bp.post("/invitation/accept")
@agent_required
@access_required
def invitation_accept():
    membership = _get_team_membership()
    if not membership or membership.status != "pending":
        return redirect(url_for("team.index"))
    membership.status = "confirmed"
    db.session.commit()
    flash("Ai intrat în echipă.", "success")
    return redirect(url_for("team.agent_dashboard"))


@team_bp.post("/invitation/decline")
@agent_required
@access_required
def invitation_decline():
    membership = _get_team_membership()
    if not membership or membership.status != "pending":
        return redirect(url_for("team.index"))
    db.session.delete(membership)
    db.session.commit()
    flash("Ai refuzat invitația.", "info")
    return redirect(url_for("team.index"))


# --- Agent dashboard (echipa mea) ---
@team_bp.get("/my-dashboard")
@agent_required
@access_required
def agent_dashboard():
    membership = _get_confirmed_team_membership()
    if not membership:
        return redirect(url_for("team.index"))
    team = Team.query.get(membership.team_id)
    today = _today_utc()
    uid = current_user.id

    # Stats: today, week, month, 3 months
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    last_30 = today - timedelta(days=30)
    last_90 = today - timedelta(days=90)

    activities = DailyActivity.query.filter_by(user_id=uid).filter(DailyActivity.date >= last_90).all()
    viewings_today = next((a.viewings_count for a in activities if a.date == today), 0)
    deals_today = next((a.deals_closed_count for a in activities if a.date == today), 0)
    amount_today = next((float(a.total_amount or 0) for a in activities if a.date == today), 0)

    viewings_week = sum(a.viewings_count for a in activities if week_start <= a.date <= week_end)
    deals_week = sum(a.deals_closed_count for a in activities if week_start <= a.date <= week_end)
    amount_week = sum(float(a.total_amount or 0) for a in activities if week_start <= a.date <= week_end)

    viewings_month = sum(a.viewings_count for a in activities if a.date >= month_start)
    deals_month = sum(a.deals_closed_count for a in activities if a.date >= month_start)
    amount_month = sum(float(a.total_amount or 0) for a in activities if a.date >= month_start)

    viewings_3m = sum(a.viewings_count for a in activities if a.date >= last_90)
    deals_3m = sum(a.deals_closed_count for a in activities if a.date >= last_90)
    amount_3m = sum(float(a.total_amount or 0) for a in activities if a.date >= last_90)

    daily_activity_today = DailyActivity.query.filter_by(user_id=uid, date=today).first()

    assignments = (
        TeamTaskAssignment.query.join(TeamTask, TeamTaskAssignment.task_id == TeamTask.id)
        .filter(
            TeamTaskAssignment.assignee_user_id == uid,
            TeamTaskAssignment.status == "open",
            TeamTask.team_id == team.id,
        )
        .order_by(TeamTask.due_date.asc())
        .all()
    )
    new_tasks_count = sum(1 for a in assignments if not a.acknowledged_at)

    return render_template(
        "team/agent_dashboard.html",
        team=team,
        daily_activity_today=daily_activity_today,
        viewings_today=viewings_today,
        deals_today=deals_today,
        amount_today=amount_today,
        viewings_week=viewings_week,
        deals_week=deals_week,
        amount_week=amount_week,
        viewings_month=viewings_month,
        deals_month=deals_month,
        amount_month=amount_month,
        viewings_3m=viewings_3m,
        deals_3m=deals_3m,
        amount_3m=amount_3m,
        assignments=assignments,
        new_tasks_count=new_tasks_count,
        today=today,
    )


@team_bp.route("/my-dashboard/daily-activity", methods=["POST"])
@agent_required
@access_required
def agent_save_daily_activity():
    membership = _get_confirmed_team_membership()
    if not membership:
        return redirect(url_for("team.index"))
    today = _today_utc()
    viewings = int(request.form.get("viewings_count") or 0)
    deals = int(request.form.get("deals_closed_count") or 0)
    total_amount = request.form.get("total_amount")
    try:
        total_amount = float(total_amount.replace(",", ".").replace(" ", "")) if total_amount else None
    except (ValueError, AttributeError):
        total_amount = None
    if viewings < 0:
        viewings = 0
    if deals < 0:
        deals = 0
    existing = DailyActivity.query.filter_by(user_id=current_user.id, date=today).first()
    if existing:
        existing.viewings_count = viewings
        existing.deals_closed_count = deals
        existing.total_amount = total_amount
    else:
        existing = DailyActivity(
            user_id=current_user.id,
            date=today,
            viewings_count=viewings,
            deals_closed_count=deals,
            total_amount=total_amount,
        )
        db.session.add(existing)
    db.session.commit()
    flash("Raport salvat.", "success")
    return redirect(url_for("team.agent_dashboard"))


@team_bp.post("/my-dashboard/complete-task/<int:assignment_id>")
@agent_required
@access_required
def agent_complete_team_task(assignment_id):
    membership = _get_confirmed_team_membership()
    if not membership:
        return redirect(url_for("team.index"))
    assignment = TeamTaskAssignment.query.filter_by(
        id=assignment_id,
        assignee_user_id=current_user.id,
        status="open",
    ).first()
    if not assignment:
        abort(404)
    assignment.status = "done"
    assignment.completed_at = utcnow()
    assignment.acknowledged_at = utcnow()
    assignment.comment = (request.form.get("comment") or "").strip() or None
    db.session.commit()
    flash("Task finalizat.", "success")
    return redirect(url_for("team.agent_dashboard"))


@team_bp.post("/my-dashboard/acknowledge-tasks")
@agent_required
@access_required
def agent_acknowledge_tasks():
    """Marchează task-urile ca văzute (pentru a ascunde notificarea)."""
    membership = _get_confirmed_team_membership()
    if not membership:
        return redirect(url_for("team.index"))
    now = utcnow()
    assignments = (
        TeamTaskAssignment.query.join(TeamTask, TeamTaskAssignment.task_id == TeamTask.id)
        .filter(
            TeamTaskAssignment.assignee_user_id == current_user.id,
            TeamTask.team_id == membership.team_id,
            TeamTaskAssignment.acknowledged_at.is_(None),
        )
        .all()
    )
    for a in assignments:
        a.acknowledged_at = now
    db.session.commit()
    return redirect(request.referrer or url_for("team.agent_dashboard"))


@team_bp.post("/leave-team")
@agent_required
@access_required
def leave_team():
    membership = _get_confirmed_team_membership()
    if not membership:
        return redirect(url_for("team.index"))
    db.session.delete(membership)
    db.session.commit()
    flash("Ai ieșit din echipă.", "info")
    return redirect(url_for("team.index"))


@team_bp.post("/agents/<int:user_id>/remove")
@agent_required
@access_required
@_manager_required
def remove_agent(team, user_id):
    member = TeamMember.query.filter_by(team_id=team.id, user_id=user_id, role="agent").first()
    if not member:
        abort(404)
    if member.user_id == current_user.id:
        flash("Nu te poți elimina pe tine însuți.", "error")
        return redirect(url_for("team.agents_list"))
    db.session.delete(member)
    db.session.commit()
    flash("Agent eliminat din echipă.", "success")
    return redirect(url_for("team.agents_list"))


# --- Task-uri Echipă ---
@team_bp.get("/tasks")
@agent_required
@access_required
@_manager_required
def tasks_list(team):
    total_agents = TeamMember.query.filter_by(team_id=team.id, role="agent", status="confirmed").count()
    tasks = (
        TeamTask.query.filter_by(team_id=team.id)
        .order_by(TeamTask.due_date.asc(), TeamTask.created_at.desc())
        .all()
    )
    today = _today_utc()
    task_data = []
    for t in tasks:
        assignments = t.assignments.all()
        done = sum(1 for a in assignments if a.status == "done")
        total = len(assignments)
        overdue = t.due_date < today and done < total
        n = len(assignments)
        if n == total_agents and total_agents > 0:
            assignee_display = "Task-uri pentru toți"
        elif n == 1:
            assignee_display = assignments[0].assignee.full_name or "?"
        elif n > 2:
            names = [a.assignee.full_name or "?" for a in assignments[:2]]
            assignee_display = ", ".join(names) + ", ..."
        else:
            assignee_display = ", ".join(a.assignee.full_name or "?" for a in assignments) if assignments else ""
        task_data.append({
            "task": t,
            "done": done,
            "total": total,
            "overdue": overdue,
            "assignments": assignments,
            "assignee_display": assignee_display,
        })
    return render_template("team/tasks_list.html", team=team, task_data=task_data)


@team_bp.route("/tasks/new", methods=["GET", "POST"])
@agent_required
@access_required
@_manager_required
def task_new(team):
    form = TeamTaskForm()
    agents = (
        TeamMember.query.filter_by(team_id=team.id, role="agent", status="confirmed")
        .join(User, TeamMember.user_id == User.id)
        .add_columns(User.id, User.full_name)
        .all()
    )
    if form.validate_on_submit():
        title = (form.title.data or "").strip()
        description = (form.description.data or "").strip() or None
        due_date = form.due_date.data
        priority = form.priority.data or "medium"

        assign_type = request.form.get("assign_type", "all")
        assignee_ids = list(request.form.getlist("assignee_ids", type=int))
        single_id = request.form.get("assignee_single", type=int)
        if assign_type == "single" and single_id:
            assignee_ids = [single_id]

        task = TeamTask(
            team_id=team.id,
            created_by_user_id=current_user.id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
        )
        db.session.add(task)
        db.session.flush()

        valid_agent_ids = [row[1] for row in agents]
        if assign_type == "all":
            for uid in valid_agent_ids:
                a = TeamTaskAssignment(task_id=task.id, assignee_user_id=uid)
                db.session.add(a)
        elif assign_type in ("multiple", "single") and assignee_ids:
            for uid in assignee_ids:
                if uid in valid_agent_ids:
                    a = TeamTaskAssignment(task_id=task.id, assignee_user_id=uid)
                    db.session.add(a)

        db.session.commit()
        flash("Task creat.", "success")
        return redirect(url_for("team.tasks_list"))

    return render_template("team/task_form.html", team=team, form=form, agents=agents, task=None)


@team_bp.get("/tasks/<int:task_id>")
@agent_required
@access_required
@_manager_required
def task_detail(team, task_id):
    task = TeamTask.query.filter_by(id=task_id, team_id=team.id).first()
    if not task:
        abort(404)
    assignments = task.assignments.all()
    today = _today_utc()
    overdue = task.due_date < today
    return render_template(
        "team/task_detail.html",
        team=team,
        task=task,
        assignments=assignments,
        overdue=overdue,
    )
