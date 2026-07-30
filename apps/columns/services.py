from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.boards.models import Board

from .models import Column

class ColumnLifecycleService:
    @staticmethod
    def _lock_board(
        *,
        workspace,
        board,
    ):
        return get_object_or_404(
            Board.objects
            .select_for_update()
            .select_related(
                'workspace',
                'created_by',
            ),
            pk=board.pk,
            workspace=workspace,
            is_archived=False,
        )
    
    @staticmethod
    def _lock_column(
        *,
        board,
        column,
        is_archived,
    ):
        return get_object_or_404(
            Column.objects
            .select_for_update()
            .select_related(
                'board',
                'created_by',
            ),
            pk=column.pk,
            board=board,
            is_archived=is_archived,
        )
    
    @staticmethod
    def _touch_board(
        *,
        board,
    ):
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        workspace,
        board,
        actor,
        title,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
        )
        
        column = Column(
            board=locked_board,
            title=title,
            position=(
                Column.objects.next_position(
                    board=locked_board,
                )
            ),
            created_by=actor,
            is_archived=False,
        )
        
        column.full_clean()
        column.save()

        cls._touch_board(
            board=locked_board,
        )
        
        return (
            column,
            locked_board,
        )
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        workspace,
        board,
        column,
        title,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
        )
        
        locked_column = cls._lock_column(
            board=locked_board,
            column=column,
            is_archived=False,
        )
        
        locked_column.title = title
        locked_column.full_clean()
        locked_column.save(
            update_fields=[
                'title',
                'updated_at',
            ]
        )
        
        cls._touch_board(
            board=locked_board,
        )
        
        return (
            locked_column,
            locked_board,
        )
    
    @classmethod
    @transaction.atomic
    def archive(
        cls,
        *,
        workspace,
        board,
        column,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
        )
        
        locked_column = cls._lock_column(
            board=locked_board,
            column=column,
            is_archived=False,
        )
        
        locked_column.is_archived = True
        locked_column.save(
            update_fields=[
                'is_archived',
                'updated_at',
            ]
        )
        
        Column.objects.normalize_positions(
            board=locked_board,
        )
        
        cls._touch_board(
            board=locked_board,
        )
        
        return (
            locked_column,
            locked_board,
        )
    
    @classmethod
    @transaction.atomic
    def restore(
        cls,
        *,
        workspace,
        board,
        column,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
        )
        
        locked_column = cls._lock_column(
            board=locked_board,
            column=column,
            is_archived=True,
        )
        
        locked_column.position = (
            Column.objects.next_position(
                board=locked_board,
            )
        )
        
        locked_column.is_archived = False
        locked_column.save(
            update_fields=[
                'position',
                'is_archived',
                'updated_at',
            ]
        )
        
        cls._touch_board(
            board=locked_board,
        )
        
        return (
            locked_column,
            locked_board,
        )
        
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        *,
        workspace,
        board,
        column,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
        )
        
        locked_column = cls._lock_column(
            board=locked_board,
            column=column,
            is_archived=True,
        )
        
        column_title = locked_column.title
        board_id = locked_board.pk
        workspace_id = locked_board.workspace_id
        
        locked_column.delete()

        cls._touch_board(
            board=locked_board,
        )
        
        return (
            column_title,
            workspace_id,
            board_id,
        )