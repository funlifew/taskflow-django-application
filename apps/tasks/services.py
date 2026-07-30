from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column

from .models import Task


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
    EDITABLE_FIELDS = (
        "title",
        "description",
        "priority",
        "assignee",
        "due_at",
    )

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

        task.title = title
        task.description = description
        task.priority = priority
        task.assignee = assignee
        task.due_at = due_at

        task.full_clean()
        task.save(
            update_fields=[
                *cls.EDITABLE_FIELDS,
                "updated_at",
            ]
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

        task.status = status
        task.full_clean()
        task.save(
            update_fields=[
                "status",
                "updated_at",
            ]
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

        task.is_archived = True
        task.archived_at = timezone.now()
        task.save(
            update_fields=[
                "is_archived",
                "archived_at",
                "updated_at",
            ]
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

        TaskTouchService.touch(
            board=board,
            columns=(column,),
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
        if source_column_pk == target_column_pk:
            raise Http404

        board = TaskScopeService.lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )

        columns = TaskScopeService.lock_columns(
            board=board,
            column_ids=(
                source_column_pk,
                target_column_pk,
            ),
        )

        source_column = columns[
            source_column_pk
        ]
        target_column = columns[
            target_column_pk
        ]

        task = TaskScopeService.lock_task(
            column=source_column,
            task_pk=task_pk,
        )

        task.column = target_column
        task.position = (
            Task.objects.next_position(
                column=target_column,
            )
        )

        task.save(
            update_fields=[
                "column",
                "position",
                "updated_at",
            ]
        )

        TaskPositionService._normalize_locked(
            column=source_column,
        )

        TaskTouchService.touch(
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