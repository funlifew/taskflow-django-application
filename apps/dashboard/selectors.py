from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.boards.models import Board
from apps.tasks.models import (
    Task,
    TaskActivity,
)
from apps.workspaces.models import Workspace


UNFINISHED_TASK_STATUSES = (
    Task.Status.TODO,
    Task.Status.IN_PROGRESS,
    Task.Status.BLOCKED,
)

def get_accessible_workspaces(
    *,
    user,
):
    return (
        Workspace.objects
        .filter(
            Q(owner=user)
            | Q(
                memberships__user=user,
            ),
            is_archived=False,
        )
        .select_related(
            'owner',
        )
        .distinct()
    )
    
def get_accessible_boards(
    *,
    user,
):
    accessible_workspace_ids = (
        get_accessible_workspaces(
            user=user,
        )
        .values("pk")
    )

    return (
        Board.objects
        .filter(
            workspace_id__in=(
                accessible_workspace_ids
            ),
            workspace__is_archived=False,
            is_archived=False,
        )
        .select_related(
            "workspace",
            "workspace__owner",
            "created_by",
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
    )


def get_accessible_active_tasks(
    *,
    user,
):
    accessible_workspace_ids = (
        get_accessible_workspaces(
            user=user,
        )
        .values("pk")
    )

    return (
        Task.objects
        .filter(
            column__board__workspace_id__in=(
                accessible_workspace_ids
            ),
            column__board__workspace__is_archived=False,
            column__board__is_archived=False,
            column__is_archived=False,
            is_archived=False,
        )
        .select_related(
            "assignee",
            "created_by",
            "column",
            "column__board",
            "column__board__workspace",
        )
    )


def get_user_assigned_tasks(
    *,
    user,
):
    return (
        get_accessible_active_tasks(
            user=user,
        )
        .filter(
            assignee=user,
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
    )


def get_user_overdue_tasks(
    *,
    user,
    now=None,
):
    if now is None:
        now = timezone.now()

    return (
        get_user_assigned_tasks(
            user=user,
        )
        .filter(
            due_at__lt=now,
            status__in=(
                UNFINISHED_TASK_STATUSES
            ),
        )
        .order_by(
            "due_at",
            "pk",
        )
    )


def get_user_due_soon_tasks(
    *,
    user,
    now=None,
    days=7,
):
    if now is None:
        now = timezone.now()

    due_until = (
        now
        + timedelta(days=days)
    )

    return (
        get_user_assigned_tasks(
            user=user,
        )
        .filter(
            due_at__gte=now,
            due_at__lte=due_until,
            status__in=(
                UNFINISHED_TASK_STATUSES
            ),
        )
        .order_by(
            "due_at",
            "pk",
        )
    )


def get_user_completed_tasks(
    *,
    user,
):
    return (
        get_user_assigned_tasks(
            user=user,
        )
        .filter(
            status=Task.Status.DONE,
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
    )


def get_user_recent_tasks(
    *,
    user,
    limit=6,
):
    queryset = (
        get_user_assigned_tasks(
            user=user,
        )
    )

    if limit is None:
        return queryset

    return queryset[:limit]


def get_user_recent_task_activities(
    *,
    user,
    limit=10,
):
    accessible_workspace_ids = (
        get_accessible_workspaces(
            user=user,
        )
        .values("pk")
    )

    queryset = (
        TaskActivity.objects
        .filter(
            task__column__board__workspace_id__in=(
                accessible_workspace_ids
            ),
            task__column__board__workspace__is_archived=False,
            task__column__board__is_archived=False,
        )
        .select_related(
            "actor",
            "task",
            "task__assignee",
            "task__created_by",
            "task__column",
            "task__column__board",
            (
                "task__column__board__"
                "workspace"
            ),
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )

    if limit is None:
        return queryset

    return queryset[:limit]