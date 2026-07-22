from django.db import transaction
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
)
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column

from .models import Task

class TaskPositionService:
    @classmethod
    def _normalize_locked(
        cls,
        *,
        column,
    ):
        tasks = list(
            Task.objects
            .select_for_update()
            .active()
            .for_column(column)
            .order_by(
                'position',
                'pk',
            )
        )
        
        for expected_position, task in enumerate(tasks):
            if(
                task.position
                == expected_position
            ):
                continue
            
            task.position = expected_position
            
            task.save(
                update_fields=[
                    'position',
                    'updated_at',
                ]
            )
    
    @classmethod
    @transaction.atomic
    def normalize(
        cls,
        *,
        column,
    ):
        locked_column = get_object_or_404(
            Column.objects.select_for_update(),
            pk=column.pk,
            is_archived=False,
            board__is_archived=False,
        )
        
        cls._normalize_locked(
            column=locked_column,
        )

class TaskLifecycleService:
    @staticmethod
    def _lock_board(
        *,
        workspace,
        board_pk,
    ):
        return get_object_or_404(
            Board.objects.select_for_update(),
            pk=board_pk,
            workspace=workspace,
            is_archived=False,
        )
    
    @staticmethod
    def _lock_column(
        *,
        board,
        column_pk,
    ):
        return get_object_or_404(
            Column.objects.select_for_update(),
            pk=column_pk,
            board=board,
            is_archived=False,
        )
    
    @staticmethod
    def _touch_parents(
        *,
        board,
        columns,
    ):
        now = timezone.now()
        
        Board.objects.filter(
            pk=board.pk
        ).update(
            updated_at=now,
        )
        
        Column.objects.filter(
            pk__in=[
                column.pk
                for column in columns
            ],
        ).update(
            updated_at=now,
        )
        
        board.updated_at = now
        
        for column in columns:
            column.updated_at = now
    
    
    @classmethod
    @transaction.atomic
    def archive(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
    ):
        board = cls._lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )
        
        column = cls._lock_column(
            board=board,
            column_pk=column_pk,
        )
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=task_pk,
            column=column,
            is_archived=False,
        )
        
        task.is_archived = True
        task.archived_at = timezone.now()
        
        task.save(
            update_fields=[
                'is_archived',
                'archived_at',
                'updated_at',
            ]
        )
        
        TaskPositionService._normalize_locked(
            column=column,
        )
        
        cls._touch_parents(
            board=board,
            columns=(column, ),
        )
        
        return task, board, column
    
    @classmethod
    @transaction.atomic
    def restore(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
    ):
        board = cls._lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )
        
        column = cls._lock_column(
            board=board,
            column_pk=column_pk,
        )
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=task_pk,
            column=column,
            is_archived=True,
        )
        
        task.position = (
            Task.objects.next_position(
                column=column,
            )
        )
        
        task.is_archived = False
        task.archived_at = None
        
        task.save(
            update_fields=[
                'position',
                'is_archived',
                'archived_at',
                'updated_at',
            ]
        )
        
        cls._touch_parents(
            board=board,
            columns=(column, ),
        )
        
        return task, board, column
    
    
    @classmethod
    @transaction.atomic
    def move(
        cls,
        *,
        workspace,
        board_pk,
        source_column_pk,
        target_column_pk,
        task_pk,
    ):
        if (
            source_column_pk
            == target_column_pk
        ):
            raise Http404
        
        board = cls._lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )
        
        locked_columns = {
            column.pk: column
            for column in (
                Column.objects
                .select_for_update()
                .filter(
                    board=board,
                    is_archived=False,
                    pk__in=[
                        source_column_pk,
                        target_column_pk,
                    ],
                )
                .order_by('pk')
            )
        }
        
        if (
            source_column_pk
            not in locked_columns
            or target_column_pk
            not in locked_columns
        ):
            raise Http404
        
        source_column = locked_columns[source_column_pk]
        target_column = locked_columns[target_column_pk]
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=task_pk,
            column=source_column,
            is_archived=False,
        )
        
        task.column = target_column
        task.position = (
            Task.objects.next_position(column=target_column)
        )
        
        task.save(
            update_fields=[
                'column',
                'position',
                'updated_at',
            ]
        )
        
        TaskPositionService._normalize_locked(column=source_column)
        cls._touch_parents(
            board=board,
            columns=(
                source_column,
                target_column,
            ),
        )
        
        return (
            task,
            board,
            source_column,
            target_column,
        )
    
    
    @classmethod
    @transaction.atomic
    def delete_archived(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
    ):
        board = cls._lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )
        
        column = cls._lock_column(
            board=board,
            column_pk=column_pk,
        )
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=task_pk,
            column=column,
            is_archived=True,
        )
        
        task_title = task.title
        task.delete()
        
        cls._touch_parents(
            board=board,
            columns=(column, ),
        )
        
        return task_title, board, column