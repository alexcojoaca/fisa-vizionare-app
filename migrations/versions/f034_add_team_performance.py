"""Add team, team_member, team_task, team_task_assignment, daily_activity tables.

Revision ID: f034_team
Revises: e7afc645651b
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = "f034_team"
down_revision = "e7afc645651b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "team",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("manager_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["manager_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_manager_user_id", "team", ["manager_user_id"])

    op.create_table(
        "team_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="agent"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_team_member_user"),
    )
    op.create_index("ix_team_member_team_id", "team_member", ["team_id"])
    op.create_index("ix_team_member_user_id", "team_member", ["user_id"])

    op.create_table(
        "team_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_task_team_id", "team_task", ["team_id"])
    op.create_index("ix_team_task_created_by_user_id", "team_task", ["created_by_user_id"])

    op.create_table(
        "team_task_assignment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("assignee_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["team_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "assignee_user_id", name="uq_team_task_assignment"),
    )
    op.create_index("ix_team_task_assignment_task_id", "team_task_assignment", ["task_id"])
    op.create_index("ix_team_task_assignment_assignee_user_id", "team_task_assignment", ["assignee_user_id"])
    op.create_index("ix_team_task_assignment_status", "team_task_assignment", ["status"])

    op.create_table(
        "daily_activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("viewings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_closed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_activity_user_date"),
    )
    op.create_index("ix_daily_activity_user_id", "daily_activity", ["user_id"])
    op.create_index("ix_daily_activity_date", "daily_activity", ["date"])
    op.create_index("ix_daily_activity_user_date", "daily_activity", ["user_id", "date"])


def downgrade():
    op.drop_table("daily_activity")
    op.drop_table("team_task_assignment")
    op.drop_table("team_task")
    op.drop_table("team_member")
    op.drop_table("team")
