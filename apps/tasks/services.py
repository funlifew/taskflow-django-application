from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column

from .models import (
    Task,
    TaskActivity,
)


class TaskScopeService:
    @staticmethod
    def lock_board(
        *,
        workspace,
        board_pk,
    ):
        return get_object_or_404(
            Board.objects
            .select_for_update()
            .select_related(
                "workspace",
                "created_by",
            ),
            pk=board_pk,
            workspace=workspace,
            is_archived=False,
        )

    @staticmethod
    def lock_column(
        *,
        board,
        column_pk,
        is_archived=False,
    ):
        return get_object_or_404(
            Column.objects
            .select_for_update()
            .select_related(
                "board",
                "created_by",
            ),
            pk=column_pk,
            board=board,
            is_archived=is_archived,
        )

    @staticmethod
    def lock_columns(
        *,
        board,
        column_ids,
    ):
        requested_ids = set(column_ids)

        if not requested_ids:
            return {}

        columns = {
            column.pk: column
            for column in (
                Column.objects
                .select_for_update()
                .filter(
                    board=board,
                    is_archived=False,
                    pk__in=requested_ids,
                )
                .select_related(
                    "board",
                    "created_by",
                )
                .order_by("pk")
            )
        }

        if set(columns) != requested_ids:
            raise Http404

        return columns

    @staticmethod
    def lock_task(
        *,
        column,
        task_pk,
        is_archived=False,
    ):
        return get_object_or_404(
            Task.objects
            .select_for_update()
            .select_related(
                "column",
                "assignee",
                "created_by",
            ),
            pk=task_pk,
            column=column,
            is_archived=is_archived,
        )

    @classmethod
    def lock_task_scope(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        task_is_archived=False,
    ):
        board = cls.lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )

        column = cls.lock_column(
            board=board,
            column_pk=column_pk,
        )

        task = cls.lock_task(
            column=column,
            task_pk=task_pk,
            is_archived=task_is_archived,
        )

        return board, column, task


class TaskTouchService:
    @staticmethod
    def touch(
        *,
        board,
        columns=(),
        tasks=(),
    ):
        now = timezone.now()

        unique_columns = {
            column.pk: column
            for column in columns
        }

        unique_tasks = {
            task.pk: task
            for task in tasks
        }

        Board.objects.filter(
            pk=board.pk,
        ).update(
            updated_at=now,
        )

        if unique_columns:
            Column.objects.filter(
                pk__in=unique_columns,
            ).update(
                updated_at=now,
            )

        if unique_tasks:
            Task.objects.filter(
                pk__in=unique_tasks,
            ).update(
                updated_at=now,
            )

        board.updated_at = now

        for column in unique_columns.values():
            column.updated_at = now

        for task in unique_tasks.values():
            task.updated_at = now


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
                "position",
                "pk",
            )
        )

        for expected_position, task in enumerate(
            tasks
        ):
            if task.position == expected_position:
                continue

            task.position = expected_position

            task.save(
                update_fields=[
                    "position",
                    "updated_at",
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
    def _get_user_label(user):
        if user is None:
            return "بدون مسئول"

        full_name = user.get_full_name().strip()

        return full_name or user.username

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        actor,
        title,
        description,
        priority,
        assignee,
        due_at,
    ):
        board = TaskScopeService.lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )

        column = TaskScopeService.lock_column(
            board=board,
            column_pk=column_pk,
        )

        task = Task(
            column=column,
            title=title,
            description=description,
            priority=priority,
            assignee=assignee,
            due_at=due_at,
            position=(
                Task.objects.next_position(
                    column=column,
                )
            ),
            status=Task.Status.TODO,
            created_by=actor,
            is_archived=False,
            archived_at=None,
        )

        task.full_clean()
        task.save()

        TaskActivityService.record(
            task=task,
            actor=actor,
            action=TaskActivity.Action.CREATED,
            metadata={
                "column_id": column.pk,
                "column_title": column.title,
                "assignee_id": task.assignee_id,
                "status": task.status,
                "status_label": str(
                    task.get_status_display()
                ),
            },
        )

        TaskTouchService.touch(
            board=board,
            columns=(column,),
        )

        return task, board, column

    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        title,
        description,
        priority,
        assignee,
        due_at,
        actor=None,
    ):
        (
            board,
            column,
            task,
        ) = TaskScopeService.lock_task_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
        )

        old_assignee = task.assignee
        old_assignee_id = task.assignee_id
        new_assignee_id = (
            assignee.pk
            if assignee is not None
            else None
        )

        changed_fields = []
        update_fields = []

        if task.title != title:
            task.title = title
            changed_fields.append("title")
            update_fields.append("title")

        if task.description != description:
            task.description = description
            changed_fields.append("description")
            update_fields.append("description")

        if task.priority != priority:
            task.priority = priority
            changed_fields.append("priority")
            update_fields.append("priority")

        if task.due_at != due_at:
            task.due_at = due_at
            changed_fields.append("due_at")
            update_fields.append("due_at")

        assignee_changed = (
            old_assignee_id
            != new_assignee_id
        )

        if assignee_changed:
            task.assignee = assignee
            update_fields.append("assignee")

        if not update_fields:
            return task, board, column

        task.full_clean()

        task.save(
            update_fields=[
                *update_fields,
                "updated_at",
            ]
        )

        if changed_fields:
            TaskActivityService.record(
                task=task,
                actor=actor,
                action=TaskActivity.Action.UPDATED,
                metadata={
                    "changed_fields": changed_fields,
                },
            )

        if assignee_changed:
            TaskActivityService.record(
                task=task,
                actor=actor,
                action=(
                    TaskActivity
                    .Action
                    .ASSIGNEE_CHANGED
                ),
                metadata={
                    "old_assignee_id": (
                        old_assignee_id
                    ),
                    "new_assignee_id": (
                        task.assignee_id
                    ),
                    "old_assignee_label": (
                        cls._get_user_label(
                            old_assignee
                        )
                    ),
                    "new_assignee_label": (
                        cls._get_user_label(
                            task.assignee
                        )
                    ),
                },
            )

        TaskTouchService.touch(
            board=board,
            columns=(column,),
        )

        return task, board, column

    @classmethod
    @transaction.atomic
    def update_status(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        status,
        actor=None,
    ):
        (
            board,
            column,
            task,
        ) = TaskScopeService.lock_task_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
        )

        old_status = task.status

        if old_status == status:
            return task, board, column

        task.status = status

        task.full_clean()

        task.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        TaskActivityService.record(
            task=task,
            actor=actor,
            action=(
                TaskActivity
                .Action
                .STATUS_CHANGED
            ),
            metadata={
                "old_status": old_status,
                "new_status": task.status,
                "old_status_label": str(
                    Task.Status(
                        old_status
                    ).label
                ),
                "new_status_label": str(
                    task.get_status_display()
                ),
            },
        )

        TaskTouchService.touch(
            board=board,
            columns=(column,),
        )

        return task, board, column

    @classmethod
    @transaction.atomic
    def archive(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        actor=None,
    ):
        (
            board,
            column,
            task,
        ) = TaskScopeService.lock_task_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
        )

        old_position = task.position

        task.is_archived = True
        task.archived_at = timezone.now()

        task.save(
            update_fields=[
                "is_archived",
                "archived_at",
                "updated_at",
            ]
        )

        TaskActivityService.record(
            task=task,
            actor=actor,
            action=TaskActivity.Action.ARCHIVED,
            metadata={
                "column_id": column.pk,
                "column_title": column.title,
                "position": old_position,
            },
        )

        TaskPositionService._normalize_locked(
            column=column,
        )

        TaskTouchService.touch(
            board=board,
            columns=(column,),
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
        actor=None,
    ):
        (
            board,
            column,
            task,
        ) = TaskScopeService.lock_task_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
            task_is_archived=True,
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
                "position",
                "is_archived",
                "archived_at",
                "updated_at",
            ]
        )

        TaskActivityService.record(
            task=task,
            actor=actor,
            action=TaskActivity.Action.RESTORED,
            metadata={
                "column_id": column.pk,
                "column_title": column.title,
                "position": task.position,
            },
        )

        TaskTouchService.touch(
            board=board,
            columns=(column,),
        )

        return task, board, column

    @classmethod
    def move(
        cls,
        *,
        workspace,
        board_pk,
        source_column_pk,
        target_column_pk,
        task_pk,
        actor=None,
    ):
        """
        Backward-compatible delegator.

        New code should call
        TaskReorderingService.move_to_column().
        """
        from .reordering import (
            TaskReorderingService,
        )

        return (
            TaskReorderingService
            .move_to_column(
                workspace=workspace,
                board_pk=board_pk,
                source_column_pk=(
                    source_column_pk
                ),
                target_column_pk=(
                    target_column_pk
                ),
                task_pk=task_pk,
                actor=actor,
            )
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
        (
            board,
            column,
            task,
        ) = TaskScopeService.lock_task_scope(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
            task_is_archived=True,
        )

        task_title = task.title

        task.delete()

        TaskTouchService.touch(
            board=board,
            columns=(column,),
        )

        return task_title, board, column