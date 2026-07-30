from django.db.models import Prefetch

from apps.columns.models import Column
from apps.tasks.models import Task

from .models import Board


def get_active_boards(
    *,
    workspace,
):
    return (
        Board.objects
        .filter(
            workspace=workspace,
            is_archived=False,
        )
        .select_related(
            'workspace',
            'created_by',
        )
        .order_by(
            '-updated_at',
            '-pk',
        )
    )

def get_archived_boards(
    *,
    workspace,
):
    return (
        Board.objects
        .filter(
            workspace=workspace,
            is_archived=True,
        )
        .select_related(
            'workspace',
            'created_by',
        )
        .order_by(
            '-updated_at',
            '-pk',
        )
    )

def get_board_detail_queryset(
    *,
    queryset,
):
    active_tasks = (
        Task.objects
        .active()
        .select_related(
            'assignee',
            'created_by',
        )
        .order_by(
            'position',
            'pk',
        )
    )
    
    active_columns = (
        Column.objects
        .active()
        .select_related(
            'created_by',
        )
        .prefetch_related(
            Prefetch(
                'tasks',
                queryset=active_tasks,
                to_attr='active_tasks',
            )
        )
        .order_by(
            'position',
            'pk',
        )
    )
    
    return queryset.prefetch_related(
        Prefetch(
            'columns',
            queryset=active_columns,
            to_attr='active_columns',
        )
    )

def get_archived_columns_count(
    *,
    board,
):
    return (
        Column.objects
        .archived()
        .for_board(board)
        .count()
    )