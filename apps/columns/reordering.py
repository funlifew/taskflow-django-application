from django.core.exceptions import (
    ValidationError,
)
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.boards.models import Board

from .models import Column

class ColumnReorderingService:
    TEMPORARY_POSITION_GAP = 1024
    
    @staticmethod
    def _lock_board(
        *,
        workspace,
        board_pk,
    ):
        return get_object_or_404(
            Board.objects
            .select_for_update()
            .select_related(
                'workspace',
                'created_by',
            ),
            pk=board_pk,
            workspace=workspace,
            is_archived=False,
        )
    
    @staticmethod
    def _lock_active_columns(
        *,
        board,
    ):
        return list(
            Column.objects
            .select_for_update()
            .active()
            .for_board(board)
            .select_related(
                'board',
                'created_by',
            )
            .order_by(
                'position',
                'pk',
            )
        )
    
    @classmethod
    def _stage_locked_columns(
        cls,
        *,
        columns,
    ):
        if not columns:
            return

        maximum_position = max(
            column.position
            for column in columns
        )

        temporary_offset = (
            maximum_position
            + len(columns)
            + cls.TEMPORARY_POSITION_GAP
        )

        Column.objects.filter(
            pk__in=[
                column.pk
                for column in columns
            ],
        ).update(
            position=(
                F("position")
                + temporary_offset
            ),
        )
    
    @staticmethod
    def _persist_order(
        *,
        board,
        ordered_columns,
    ):
        now = timezone.now()

        for position, column in enumerate(ordered_columns):
            column.position = position
            column.updated_at = now
        
        Column.objects.bulk_update(
            ordered_columns,
            fields=[
                'position',
                'updated_at',
            ],
        )
        
        Board.objects.filter(
            pk=board.pk
        ).update(
            updated_at=now,
        )
        
        board.updated_at = now
    
    @staticmethod
    def _validate_target_position(
        *,
        target_position,
        maximum_position,
    ):
        if (
            isinstance(target_position, bool)
            or not isinstance(
                target_position,
                int,
            )
        ):
            raise ValidationError(
                {
                    "target_position": (
                        "جایگاه مقصد باید "
                        "یک عدد صحیح باشد."
                    ),
                }
            )
        
        if target_position < 0:
            raise ValidationError(
                {
                    "target_position": (
                        "جایگاه مقصد "
                        "نمی‌تواند منفی باشد."
                    ),
                }
            )
        
        if target_position > maximum_position:
            raise ValidationError(
                {
                    "target_position": (
                        "جایگاه مقصد خارج "
                        "از محدوده Board است."
                    ),
                }
            )
    
    @classmethod
    def _perform_reorder(
        cls,
        *,
        board,
        locked_columns,
        column_pk,
        target_position,
    ):
        moving_column = next(
            (
                column
                for column in locked_columns
                if column.pk == column_pk
            ),
            None,
        )
        
        if moving_column is None:
            raise Http404
        
        current_position = (
            locked_columns.index(
                moving_column
            )
        )
        
        maximum_position = (
            len(locked_columns) - 1
        )
        
        cls._validate_target_position(
            target_position=target_position,
            maximum_position=maximum_position,
        )
        
        if current_position == target_position:
            return (
                moving_column,
                board,
                False,
            )
        
        final_columns = [
            column
            for column in locked_columns
            if column.pk != moving_column.pk
        ]
        
        final_columns.insert(
            target_position,
            moving_column,
        )
        
        cls._stage_locked_columns(
            columns=locked_columns,
        )
        
        cls._persist_order(
            board=board,
            ordered_columns=final_columns,
        )
        
        return (
            moving_column,
            board,
            True,
        )
    
    @classmethod
    @transaction.atomic
    def reorder(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        target_position,
    ):
        board = cls._lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )
        
        locked_columns = (
            cls._lock_active_columns(
                board=board,
            )
        )
        
        return cls._perform_reorder(
            board=board,
            locked_columns=locked_columns,
            column_pk=column_pk,
            target_position=target_position,
        )
    
    @classmethod
    @transaction.atomic
    def shift(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        offset,
    ):
        if offset not in (-1, 1):
            raise ValueError(
                "offset must be -1 or 1"
            )
        
        board = cls._lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )
        
        locked_columns = (
            cls._lock_active_columns(
                board=board,
            )
        )
        
        moving_column = next(
            (
                column
                for column in locked_columns
                if column.pk == column_pk
            ),
            None,
        )
        
        if moving_column is None:
            raise Http404
        
        current_position = (
            locked_columns.index(
                moving_column
            )
        )
        
        target_position = max(
            0,
            min(
                len(locked_columns) - 1,
                current_position + offset,
            ),
        )
        
        return cls._perform_reorder(
            board=board,
            locked_columns=locked_columns,
            column_pk=column_pk,
            target_position=target_position,
        )
    
    @classmethod
    def move_left(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
    ):
        return cls.shift(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            offset=-1,
        )
    
    @classmethod
    def move_right(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
    ):
        return cls.shift(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            offset=1,
        )