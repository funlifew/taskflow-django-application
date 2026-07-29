from django.core.exceptions import (
    PermissionDenied,
)
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
)
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.workspaces.models import (
    WorkspaceMembership,
)

from .models import (
    Task,
    TaskActivity,
    TaskComment,
)

COMMENT_MODERATOR_ROLES = (
    WorkspaceMembership.Role.OWNER,
    WorkspaceMembership.Role.ADMIN,
)

class TaskActivityService:
    @staticmethod
    def record(
        *,
        task,
        actor,
        action,
        metadata=None,
    ):
        if metadata is None:
            metadata = {}
        
        activity = TaskActivity(
            task=task,
            actor=actor,
            action=action,
            metadata=metadata,
        )
        
        activity.full_clean()
        
        activity.save(
            force_insert=True,
        )
        
        return activity

class TaskCommentService:
    @staticmethod
    def _lock_scope(
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
    ):
        board = get_object_or_404(
            Board.objects.select_for_update(),
            pk=board_pk,
            workspace=workspace,
            is_archived=False,
        )
        column = get_object_or_404(
            Column.objects.select_for_update(),
            pk=column_pk,
            board=board,
            is_archived=False,
        )
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=task_pk,
            column=column,
            is_archived=False,
        )
        
        return (
            board,
            column,
            task,
        )
        
    @staticmethod
    def _get_actor_role(
        *,
        workspace,
        actor,
    ):
        if (
            workspace.owner_id
            == actor.pk
        ):
            return (
                WorkspaceMembership.Role.OWNER
            )
        
        membership = (
            WorkspaceMembership
            .objects
            .filter(
                workspace=workspace,
                user=actor,
            )
            .only(
                'role'
            )
            .first()
        )
        
        if membership is None:
            return None
        
        return membership.role
    
    @staticmethod
    def _touch_scope(
        *,
        board,
        column,
        task,
    ):
        now = timezone.now()

        Task.objects.filter(
            pk=task.pk
        ).update(
            updated_at=now,
        )
        
        Column.objects.filter(
            pk=column.pk,
        ).update(
            updated_at=now,
        )
        
        Board.objects.filter(
            pk=board.pk,
        ).update(
            updated_at=now,
        )
        
        task.updated_at = now
        column.updated_at = now
        board.updated_at = now
    
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        actor,
        body,
    ):
        (
            board,
            column,
            task
        ) = cls._lock_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
        )
        
        comment = TaskComment(
            task=task,
            author=actor,
            body=body,
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
        
        comment.full_clean()
        comment.save()

        TaskActivityService.record(
            task=task,
            actor=actor,
            action=(
                TaskActivity
                .Action
                .COMMENTED
            ),
            metadata={
                'comment_id': comment.pk,
            },
        )
        
        cls._touch_scope(
            board=board,
            column=column,
            task=task,
        )
        
        return (
            comment,
            task,
            board,
            column,
        )
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        comment_pk,
        actor,
        body,
    ):
        (
            board,
            column,
            task,
        ) = cls._lock_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
        )
        
        comment = get_object_or_404(
            TaskComment.objects
            .select_for_update(),
            pk=comment_pk,
            task=task,
            is_deleted=False,
        )
        
        if (
            comment.author_id
            != actor.pk
        ):
            raise PermissionDenied(
                "فقط نویسنده دیدگاه "
                "می‌تواند آن را ویرایش کند."
            )
        
        
        normalized_body = (
            body.strip()
        )
        
        if (
            comment.body
            == normalized_body
        ):
            return (
                comment,
                task,
                board,
                column,
            )
        
        comment.body = normalized_body
        
        comment.full_clean()

        comment.save(
            update_fields=[
                'body',
                'updated_at',
            ]
        )
        
        TaskActivityService.record(
            task=task,
            actor=actor,
            action=(
                TaskActivity
                .Action
                .COMMENT_UPDATED
            ),
            metadata={
                'comment_id': comment.pk,
            },
        )
        
        cls._touch_scope(
            board=board,
            column=column,
            task=task,
        )
        
        return (
            comment,
            task,
            board,
            column,
        )
    
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        comment_pk,
        actor,
    ):
        (
            board,
            column,
            task,
        ) = cls._lock_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
        )
        
        comment = get_object_or_404(
            TaskComment.objects
            .select_for_update(),
            pk=comment_pk,
            task=task,
            is_deleted=False,
        )
        
        actor_role = (
            cls._get_actor_role(
                workspace=workspace,
                actor=actor,
            )
        )
        
        is_author = (
            comment.author_id
            == actor.pk
        )
        
        is_moderator = (
            actor_role
            in COMMENT_MODERATOR_ROLES
        )
        
        if not (
            is_author
            or is_moderator
        ):
            raise PermissionDenied(
                "اجازه حذف این دیدگاه "
                "را ندارید."
            )
        
        comment.is_deleted = True
        comment.deleted_at = (
            timezone.now()
        )
        comment.deleted_by = actor
        
        comment.full_clean()

        comment.save(
            update_fields=[
                'is_deleted',
                'deleted_at',
                'deleted_by',
                'updated_at',
            ]
        )
        
        TaskActivityService.record(
            task=task,
            actor=actor,
            action=(
                TaskActivity
                .Action
                .COMMENT_DELETED
            ),
            metadata={
                'comment_id': comment.pk,
                'comment_author_id': comment.author_id,
            }
        )
        
        
        cls._touch_scope(
            board=board,
            column=column,
            task=task,
        )
        
        return (
            comment,
            task,
            board,
            column,
        )