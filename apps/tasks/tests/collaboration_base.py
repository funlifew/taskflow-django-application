from django.urls import reverse
from django.utils import timezone

from apps.tasks.models import (
    TaskActivity,
    TaskComment,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)


class TaskCollaborationTestBase(
    TaskTestBase
):
    def create_comment(
        self,
        *,
        task=None,
        author=None,
        body="دیدگاه آزمایشی",
        is_deleted=False,
        deleted_at=None,
        deleted_by=None,
    ):
        task = task or self.task

        if author is None:
            author = self.member

        if is_deleted:
            deleted_at = (
                deleted_at
                or timezone.now()
            )
        else:
            deleted_at = None
            deleted_by = None

        return (
            TaskComment.objects.create(
                task=task,
                author=author,
                body=body,
                is_deleted=is_deleted,
                deleted_at=deleted_at,
                deleted_by=deleted_by,
            )
        )

    def create_activity(
        self,
        *,
        task=None,
        actor=None,
        action=None,
        metadata=None,
    ):
        task = task or self.task
        actor = actor or self.owner

        if action is None:
            action = (
                TaskActivity
                .Action
                .UPDATED
            )

        if metadata is None:
            metadata = {}

        return (
            TaskActivity.objects.create(
                task=task,
                actor=actor,
                action=action,
                metadata=metadata,
            )
        )

    def task_detail_url(
        self,
        *,
        task=None,
        column=None,
    ):
        task = task or self.task
        column = column or task.column

        return reverse(
            "tasks:detail",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    column.pk
                ),
                "task_pk": task.pk,
            },
        )

    def comment_create_url(
        self,
        *,
        task=None,
        column=None,
    ):
        task = task or self.task
        column = column or task.column

        return reverse(
            "tasks:comment_create",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    column.pk
                ),
                "task_pk": task.pk,
            },
        )

    def comment_update_url(
        self,
        comment,
    ):
        return reverse(
            "tasks:comment_update",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    comment.task.column_id
                ),
                "task_pk": (
                    comment.task_id
                ),
                "comment_pk": (
                    comment.pk
                ),
            },
        )

    def comment_delete_url(
        self,
        comment,
    ):
        return reverse(
            "tasks:comment_delete",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    comment.task.column_id
                ),
                "task_pk": (
                    comment.task_id
                ),
                "comment_pk": (
                    comment.pk
                ),
            },
        )