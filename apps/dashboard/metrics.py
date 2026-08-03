from datetime import timedelta

from django.db.models import (
    Case,
    CharField,
    Count,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.utils import timezone

from apps.notifications.selectors import (
    get_unread_notifications_count,
)

from apps.tasks.models import Task
from apps.workspaces.models import (
    WorkspaceMembership,
)

from .selectors import (
    get_accessible_active_tasks,
    get_accessible_boards,
    get_accessible_workspaces,
    get_user_assigned_tasks,
)

DASHBOARD_DUE_SOON_DAYS = 7

PROGRESS_ELIGIBLE_STATUSES = (
    Task.Status.TODO,
    Task.Status.IN_PROGRESS,
    Task.Status.BLOCKED,
    Task.Status.DONE,
)

UNFINISHED_TASK_STATUSES = (
    Task.Status.TODO,
    Task.Status.IN_PROGRESS,
    Task.Status.BLOCKED,
)

def calculate_progress_percentage(
    *,
    completed,
    total,
):
    if total <= 0:
        return 0
    
    return int(
        round(
            (
                completed
                / total
            )
            * 100
        )
    )

def build_progress_payload(
    *,
    total,
    completed,
    todo,
    in_progress,
    blocked,
):
    return {
        'total': total,
        'completed': completed,
        'todo': todo,
        'in_progress': in_progress,
        'blocked': blocked,
        'progress_percentage': calculate_progress_percentage(
            completed=completed,
            total=total,
        ),
    }
    
def get_task_queryset_progress(
    *,
    queryset,
):
    counts = (
        queryset
        .filter(
            status__in=(
                PROGRESS_ELIGIBLE_STATUSES
            ),
        )
        .aggregate(
            total=Count("pk"),
            completed=Count(
                "pk",
                filter=Q(
                    status=Task.Status.DONE,
                ),
            ),
            todo=Count(
                "pk",
                filter=Q(
                    status=Task.Status.TODO,
                ),
            ),
            in_progress=Count(
                "pk",
                filter=Q(
                    status=(
                        Task.Status
                        .IN_PROGRESS
                    ),
                ),
            ),
            blocked=Count(
                "pk",
                filter=Q(
                    status=Task.Status.BLOCKED,
                ),
            ),
        )
    )

    return build_progress_payload(
        total=counts["total"],
        completed=counts["completed"],
        todo=counts["todo"],
        in_progress=(
            counts["in_progress"]
        ),
        blocked=counts["blocked"],
    )

def get_user_task_progress(
    *,
    user,
):
    return get_task_queryset_progress(
        queryset=(
            get_user_assigned_tasks(
                user=user,
            )
        ),
    )

def get_workspace_progress(
    *,
    user,
    workspace,
):
    queryset = (
        get_accessible_active_tasks(
            user=user,
        )
        .filter(
            column__board__workspace=workspace,
        )
    )
    
    return get_task_queryset_progress(
        queryset=queryset,
    )
    
def get_board_progress(
    *,
    user,
    board,
):
    queryset = (
        get_accessible_active_tasks(
            user=user,
        )
        .filter(
            column__board=board,
        )
    )

    return get_task_queryset_progress(
        queryset=queryset,
    )


def get_user_dashboard_summary(
    *,
    user,
    now=None,
    due_soon_days=(
        DASHBOARD_DUE_SOON_DAYS
    ),
):
    if now is None:
        now = timezone.now()

    due_until = (
        now
        + timedelta(
            days=due_soon_days,
        )
    )

    assigned_tasks = (
        get_user_assigned_tasks(
            user=user,
        )
    )

    task_counts = (
        assigned_tasks.aggregate(
            assigned_tasks_count=(
                Count("pk")
            ),
            overdue_tasks_count=Count(
                "pk",
                filter=Q(
                    due_at__lt=now,
                    status__in=(
                        UNFINISHED_TASK_STATUSES
                    ),
                ),
            ),
            due_soon_tasks_count=Count(
                "pk",
                filter=Q(
                    due_at__gte=now,
                    due_at__lte=due_until,
                    status__in=(
                        UNFINISHED_TASK_STATUSES
                    ),
                ),
            ),
            completed_tasks_count=Count(
                "pk",
                filter=Q(
                    status=Task.Status.DONE,
                ),
            ),
        )
    )

    return {
        "workspaces_count": (
            get_accessible_workspaces(
                user=user,
            )
            .count()
        ),
        "boards_count": (
            get_accessible_boards(
                user=user,
            )
            .count()
        ),
        **task_counts,
        "unread_notifications_count": (
            get_unread_notifications_count(
                user=user,
            )
        ),
    }


def get_user_workspace_summaries(
    *,
    user,
    now=None,
    limit=6,
):
    if now is None:
        now = timezone.now()

    membership_role = (
        WorkspaceMembership.objects
        .filter(
            workspace=OuterRef("pk"),
            user=user,
        )
        .values("role")[:1]
    )

    active_task_filter = Q(
        boards__is_archived=False,
        boards__columns__is_archived=False,
        boards__columns__tasks__is_archived=False,
    )

    eligible_task_filter = (
        active_task_filter
        & Q(
            boards__columns__tasks__status__in=(
                PROGRESS_ELIGIBLE_STATUSES
            ),
        )
    )

    queryset = (
        get_accessible_workspaces(
            user=user,
        )
        .annotate(
            current_user_role=Case(
                When(
                    owner=user,
                    then=Value(
                        WorkspaceMembership
                        .Role
                        .OWNER
                    ),
                ),
                default=Subquery(
                    membership_role
                ),
                output_field=(
                    CharField()
                ),
            ),
            boards_count=Count(
                "boards",
                filter=Q(
                    boards__is_archived=False,
                ),
                distinct=True,
            ),
            tasks_count=Count(
                "boards__columns__tasks",
                filter=(
                    active_task_filter
                ),
                distinct=True,
            ),
            progress_total=Count(
                "boards__columns__tasks",
                filter=(
                    eligible_task_filter
                ),
                distinct=True,
            ),
            completed_tasks_count=Count(
                "boards__columns__tasks",
                filter=(
                    active_task_filter
                    & Q(
                        boards__columns__tasks__status=(
                            Task.Status.DONE
                        ),
                    )
                ),
                distinct=True,
            ),
            overdue_tasks_count=Count(
                "boards__columns__tasks",
                filter=(
                    active_task_filter
                    & Q(
                        boards__columns__tasks__due_at__lt=now,
                        boards__columns__tasks__status__in=(
                            UNFINISHED_TASK_STATUSES
                        ),
                    )
                ),
                distinct=True,
            ),
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
    )

    if limit is not None:
        queryset = queryset[:limit]

    summaries = []

    for workspace in queryset:
        summaries.append(
            {
                "workspace": workspace,
                "current_user_role": (
                    workspace
                    .current_user_role
                ),
                "boards_count": (
                    workspace
                    .boards_count
                ),
                "tasks_count": (
                    workspace
                    .tasks_count
                ),
                "progress_total": (
                    workspace
                    .progress_total
                ),
                "completed_tasks_count": (
                    workspace
                    .completed_tasks_count
                ),
                "overdue_tasks_count": (
                    workspace
                    .overdue_tasks_count
                ),
                "progress_percentage": (
                    calculate_progress_percentage(
                        completed=(
                            workspace
                            .completed_tasks_count
                        ),
                        total=(
                            workspace
                            .progress_total
                        ),
                    )
                ),
            }
        )

    return summaries


def get_user_board_summaries(
    *,
    user,
    now=None,
    limit=6,
):
    if now is None:
        now = timezone.now()

    membership_role = (
        WorkspaceMembership.objects
        .filter(
            workspace_id=(
                OuterRef("workspace_id")
            ),
            user=user,
        )
        .values("role")[:1]
    )

    active_task_filter = Q(
        columns__is_archived=False,
        columns__tasks__is_archived=False,
    )

    eligible_task_filter = (
        active_task_filter
        & Q(
            columns__tasks__status__in=(
                PROGRESS_ELIGIBLE_STATUSES
            ),
        )
    )

    queryset = (
        get_accessible_boards(
            user=user,
        )
        .annotate(
            current_user_role=Case(
                When(
                    workspace__owner=user,
                    then=Value(
                        WorkspaceMembership
                        .Role
                        .OWNER
                    ),
                ),
                default=Subquery(
                    membership_role
                ),
                output_field=(
                    CharField()
                ),
            ),
            columns_count=Count(
                "columns",
                filter=Q(
                    columns__is_archived=False,
                ),
                distinct=True,
            ),
            tasks_count=Count(
                "columns__tasks",
                filter=(
                    active_task_filter
                ),
                distinct=True,
            ),
            progress_total=Count(
                "columns__tasks",
                filter=(
                    eligible_task_filter
                ),
                distinct=True,
            ),
            completed_tasks_count=Count(
                "columns__tasks",
                filter=(
                    active_task_filter
                    & Q(
                        columns__tasks__status=(
                            Task.Status.DONE
                        ),
                    )
                ),
                distinct=True,
            ),
            overdue_tasks_count=Count(
                "columns__tasks",
                filter=(
                    active_task_filter
                    & Q(
                        columns__tasks__due_at__lt=now,
                        columns__tasks__status__in=(
                            UNFINISHED_TASK_STATUSES
                        ),
                    )
                ),
                distinct=True,
            ),
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
    )

    if limit is not None:
        queryset = queryset[:limit]

    summaries = []

    for board in queryset:
        summaries.append(
            {
                "board": board,
                "workspace": (
                    board.workspace
                ),
                "current_user_role": (
                    board.current_user_role
                ),
                "columns_count": (
                    board.columns_count
                ),
                "tasks_count": (
                    board.tasks_count
                ),
                "progress_total": (
                    board.progress_total
                ),
                "completed_tasks_count": (
                    board
                    .completed_tasks_count
                ),
                "overdue_tasks_count": (
                    board
                    .overdue_tasks_count
                ),
                "progress_percentage": (
                    calculate_progress_percentage(
                        completed=(
                            board
                            .completed_tasks_count
                        ),
                        total=(
                            board
                            .progress_total
                        ),
                    )
                ),
            }
        )

    return summaries