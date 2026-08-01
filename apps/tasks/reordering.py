from django.core.exceptions import (
    ValidationError,
)
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.utils import timezone

from .models import (
    Task,
    TaskActivity,
)
from .services import (
    TaskActivityService,
    TaskScopeService,
    TaskTouchService,
)


class TaskReorderingService:
    TEMPORARY_POSITION_GAP = 1024

    @staticmethod
    def _lock_active_tasks(
        *,
        column_ids,
    ):
        return list(
            Task.objects
            .select_for_update()
            .active()
            .filter(
                column_id__in=column_ids,
            )
            .select_related("column")
            .order_by(
                "column_id",
                "position",
                "pk",
            )
        )

    @staticmethod
    def _group_tasks(
        *,
        locked_tasks,
        column_ids,
    ):
        grouped_tasks = {
            column_id: []
            for column_id in column_ids
        }

        for task in locked_tasks:
            grouped_tasks[
                task.column_id
            ].append(task)

        return grouped_tasks

    @classmethod
    def _stage_locked_tasks(
        cls,
        *,
        tasks_by_column,
    ):
        for tasks in tasks_by_column.values():
            if not tasks:
                continue

            maximum_position = max(
                task.position
                for task in tasks
            )

            temporary_offset = (
                maximum_position
                + len(tasks)
                + cls.TEMPORARY_POSITION_GAP
            )

            Task.objects.filter(
                pk__in=[
                    task.pk
                    for task in tasks
                ],
            ).update(
                position=(
                    F("position")
                    + temporary_offset
                ),
            )

    @staticmethod
    def _persist_orders(
        *,
        orders,
    ):
        now = timezone.now()
        tasks_to_update = []

        for column, ordered_tasks in orders:
            for position, task in enumerate(
                ordered_tasks
            ):
                task.column = column
                task.position = position
                task.updated_at = now

                tasks_to_update.append(task)

        if not tasks_to_update:
            return

        Task.objects.bulk_update(
            tasks_to_update,
            fields=[
                "column",
                "position",
                "updated_at",
            ],
        )

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
                        "از محدوده ستون است."
                    ),
                }
            )

    @classmethod
    def _perform_reorder(
        cls,
        *,
        board,
        columns,
        locked_tasks,
        source_column_pk,
        target_column_pk,
        task_pk,
        target_position,
        actor=None,
    ):
        source_column = columns[
            source_column_pk
        ]
        target_column = columns[
            target_column_pk
        ]

        tasks_by_column = cls._group_tasks(
            locked_tasks=locked_tasks,
            column_ids=columns,
        )

        source_tasks = tasks_by_column[
            source_column_pk
        ]
        target_tasks = tasks_by_column[
            target_column_pk
        ]

        moving_task = next(
            (
                task
                for task in source_tasks
                if task.pk == task_pk
            ),
            None,
        )

        if moving_task is None:
            raise Http404

        old_position = moving_task.position

        same_column = (
            source_column_pk
            == target_column_pk
        )

        if same_column:
            current_position = (
                source_tasks.index(
                    moving_task
                )
            )

            maximum_position = (
                len(source_tasks) - 1
            )

            if target_position is None:
                target_position = (
                    maximum_position
                )

            cls._validate_target_position(
                target_position=target_position,
                maximum_position=maximum_position,
            )

            if (
                current_position
                == target_position
            ):
                return (
                    moving_task,
                    board,
                    source_column,
                    target_column,
                )

            final_tasks = [
                task
                for task in source_tasks
                if task.pk != moving_task.pk
            ]

            final_tasks.insert(
                target_position,
                moving_task,
            )

            final_orders = (
                (
                    source_column,
                    final_tasks,
                ),
            )

        else:
            maximum_position = len(
                target_tasks
            )

            if target_position is None:
                target_position = (
                    maximum_position
                )

            cls._validate_target_position(
                target_position=target_position,
                maximum_position=maximum_position,
            )

            final_source_tasks = [
                task
                for task in source_tasks
                if task.pk != moving_task.pk
            ]

            final_target_tasks = list(
                target_tasks
            )

            final_target_tasks.insert(
                target_position,
                moving_task,
            )

            final_orders = (
                (
                    source_column,
                    final_source_tasks,
                ),
                (
                    target_column,
                    final_target_tasks,
                ),
            )

        cls._stage_locked_tasks(
            tasks_by_column=tasks_by_column,
        )

        cls._persist_orders(
            orders=final_orders,
        )

        TaskTouchService.touch(
            board=board,
            columns=(
                source_column,
                target_column,
            ),
        )

        if same_column:
            TaskActivityService.record(
                task=moving_task,
                actor=actor,
                action=(
                    TaskActivity
                    .Action
                    .REORDERED
                ),
                metadata={
                    "column_id": (
                        source_column.pk
                    ),
                    "column_title": (
                        source_column.title
                    ),
                    "old_position": (
                        old_position
                    ),
                    "new_position": (
                        moving_task.position
                    ),
                },
            )

        else:
            TaskActivityService.record(
                task=moving_task,
                actor=actor,
                action=TaskActivity.Action.MOVED,
                metadata={
                    "source_column_id": (
                        source_column.pk
                    ),
                    "source_column_title": (
                        source_column.title
                    ),
                    "target_column_id": (
                        target_column.pk
                    ),
                    "target_column_title": (
                        target_column.title
                    ),
                    "old_position": (
                        old_position
                    ),
                    "new_position": (
                        moving_task.position
                    ),
                },
            )

        return (
            moving_task,
            board,
            source_column,
            target_column,
        )

    @classmethod
    @transaction.atomic
    def reorder(
        cls,
        *,
        workspace,
        board_pk,
        source_column_pk,
        target_column_pk,
        task_pk,
        target_position,
        actor=None,
    ):
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

        locked_tasks = (
            cls._lock_active_tasks(
                column_ids=columns,
            )
        )

        return cls._perform_reorder(
            board=board,
            columns=columns,
            locked_tasks=locked_tasks,
            source_column_pk=(
                source_column_pk
            ),
            target_column_pk=(
                target_column_pk
            ),
            task_pk=task_pk,
            target_position=target_position,
            actor=actor,
        )

    @classmethod
    def move_to_column(
        cls,
        *,
        workspace,
        board_pk,
        source_column_pk,
        target_column_pk,
        task_pk,
        actor=None,
    ):
        if (
            source_column_pk
            == target_column_pk
        ):
            raise Http404

        return cls.reorder(
            workspace=workspace,
            board_pk=board_pk,
            source_column_pk=(
                source_column_pk
            ),
            target_column_pk=(
                target_column_pk
            ),
            task_pk=task_pk,
            target_position=None,
            actor=actor,
        )

    @classmethod
    @transaction.atomic
    def shift(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        offset,
        actor=None,
    ):
        if offset not in (-1, 1):
            raise ValueError(
                "offset must be -1 or 1"
            )

        board = TaskScopeService.lock_board(
            workspace=workspace,
            board_pk=board_pk,
        )

        columns = TaskScopeService.lock_columns(
            board=board,
            column_ids=(column_pk,),
        )

        locked_tasks = (
            cls._lock_active_tasks(
                column_ids=columns,
            )
        )

        column_tasks = [
            task
            for task in locked_tasks
            if task.column_id == column_pk
        ]

        moving_task = next(
            (
                task
                for task in column_tasks
                if task.pk == task_pk
            ),
            None,
        )

        if moving_task is None:
            raise Http404

        current_position = (
            column_tasks.index(
                moving_task
            )
        )

        target_position = max(
            0,
            min(
                len(column_tasks) - 1,
                current_position + offset,
            ),
        )

        return cls._perform_reorder(
            board=board,
            columns=columns,
            locked_tasks=locked_tasks,
            source_column_pk=column_pk,
            target_column_pk=column_pk,
            task_pk=task_pk,
            target_position=target_position,
            actor=actor,
        )

    @classmethod
    def move_up(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        actor=None,
    ):
        return cls.shift(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
            offset=-1,
            actor=actor,
        )

    @classmethod
    def move_down(
        cls,
        *,
        workspace,
        board_pk,
        column_pk,
        task_pk,
        actor=None,
    ):
        return cls.shift(
            workspace=workspace,
            board_pk=board_pk,
            column_pk=column_pk,
            task_pk=task_pk,
            offset=1,
            actor=actor,
        )