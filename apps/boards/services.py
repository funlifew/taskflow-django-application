from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.workspaces.models import Workspace

from .models import Board

class BoardLifecycleService:
    @staticmethod
    def _lock_workspace(
        *,
        workspace,
    ):
        return get_object_or_404(
            Workspace.objects.select_for_update(),
            pk=workspace.pk,
            is_archived=False,
        )
    
    @staticmethod
    def _lock_board(
        *,
        workspace,
        board,
        is_archived,
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
            is_archived=is_archived,
        )
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        workspace,
        actor,
        title,
        description="",
    ):
        locked_workspace = cls._lock_workspace(
            workspace=workspace,
        )
        
        board = Board(
            workspace=workspace,
            created_by=actor,
            title=title,
            description=description,
            is_archived=False,
        )
        
        board.full_clean()
        board.save()

        return board
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        workspace,
        board,
        title,
        description="",
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
            is_archived=False,
        )
        
        locked_board.title = title
        locked_board.description = description
        
        locked_board.full_clean()
        locked_board.save(
            update_fields=[
                'title',
                'description',
                'updated_at',
            ]
        )
        
        return locked_board
    
    @classmethod
    @transaction.atomic
    def archive(
        cls,
        *,
        workspace,
        board,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
            is_archived=False,
        )
        
        locked_board.is_archived = True
        locked_board.save(
            update_fields=[
                'is_archived',
                'updated_at',
            ]
        )
        
        return locked_board
    
    @classmethod
    @transaction.atomic
    def restore(
        cls,
        *,
        workspace,
        board,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
            is_archived=True,
        )

        locked_board.is_archived = False
        locked_board.save(
            update_fields=[
                "is_archived",
                "updated_at",
            ]
        )

        return locked_board
    
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        *,
        workspace,
        board,
    ):
        locked_board = cls._lock_board(
            workspace=workspace,
            board=board,
            is_archived=True,
        )

        board_title = locked_board.title
        workspace_id = locked_board.workspace_id

        locked_board.delete()

        return (
            board_title,
            workspace_id,
        )