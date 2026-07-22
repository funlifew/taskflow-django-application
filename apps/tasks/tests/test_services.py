from datetime import timedelta

from django.http import Http404
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.tasks.models import Task
from apps.tasks.services import (
    TaskLifecycleService,
    TaskPositionService,
)
from apps.tasks.tests.base import TaskTestBase


class TaskPositionServiceTests(TaskTestBase):
    def test_normalize_can_run_without_outer_transaction(
        self,
    ):
        second = self.create_task(
            title="Second",
            position=4,
        )

        TaskPositionService.normalize(
            column=self.column,
        )

        second.refresh_from_db()

        self.assertEqual(
            second.position,
            1,
        )

    def test_normalize_closes_position_gaps(self):
        second = self.create_task(
            title="Second",
            position=3,
        )
        third = self.create_task(
            title="Third",
            position=8,
        )

        TaskPositionService.normalize(
            column=self.column,
        )

        second.refresh_from_db()
        third.refresh_from_db()

        self.assertEqual(
            second.position,
            1,
        )
        self.assertEqual(
            third.position,
            2,
        )
        self.assertEqual(
            list(
                Task.objects
                .active()
                .for_column(self.column)
                .values_list(
                    "position",
                    flat=True,
                )
            ),
            [0, 1, 2],
        )

    def test_normalize_ignores_archived_tasks(
        self,
    ):
        active = self.create_task(
            title="Active",
            position=5,
        )
        archived = self.create_task(
            title="Archived",
            position=99,
            is_archived=True,
        )

        TaskPositionService.normalize(
            column=self.column,
        )

        active.refresh_from_db()
        archived.refresh_from_db()

        self.assertEqual(
            active.position,
            1,
        )
        self.assertEqual(
            archived.position,
            99,
        )

    def test_normalize_only_changes_requested_column(
        self,
    ):
        other_column = self.create_column(
            title="Other",
            position=1,
        )
        other_task = self.create_task(
            column=other_column,
            title="Other task",
            position=8,
        )
        self.create_task(
            title="Source gap",
            position=4,
        )

        TaskPositionService.normalize(
            column=self.column,
        )

        other_task.refresh_from_db()

        self.assertEqual(
            other_task.position,
            8,
        )

    def test_normalize_archived_column_returns_404(
        self,
    ):
        archived_column = self.create_column(
            title="Archived Column",
            position=50,
            is_archived=True,
        )

        with self.assertRaises(Http404):
            TaskPositionService.normalize(
                column=archived_column,
            )


class TaskLifecycleServiceArchiveTests(
    TaskTestBase
):
    def test_archive_sets_archive_timestamp(self):
        before = timezone.now()

        task, board, column = (
            TaskLifecycleService.archive(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
            )
        )

        task.refresh_from_db()

        self.assertTrue(
            task.is_archived
        )
        self.assertIsNotNone(
            task.archived_at
        )
        self.assertGreaterEqual(
            task.archived_at,
            before,
        )
        self.assertEqual(
            board,
            self.board,
        )
        self.assertEqual(
            column,
            self.column,
        )

    def test_archive_normalizes_remaining_positions(
        self,
    ):
        middle = self.create_task(
            title="Middle",
            position=1,
        )
        final = self.create_task(
            title="Final",
            position=2,
        )

        TaskLifecycleService.archive(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=middle.pk,
        )

        middle.refresh_from_db()
        final.refresh_from_db()

        self.assertTrue(
            middle.is_archived
        )
        self.assertEqual(
            final.position,
            1,
        )
        self.assertEqual(
            list(
                Task.objects
                .active()
                .for_column(self.column)
                .values_list(
                    "position",
                    flat=True,
                )
            ),
            [0, 1],
        )

    def test_archived_task_cannot_be_archived_again(
        self,
    ):
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        with self.assertRaises(Http404):
            TaskLifecycleService.archive(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=archived.pk,
            )

    def test_archive_touches_parent_timestamps(
        self,
    ):
        old_time = (
            timezone.now()
            - timedelta(days=1)
        )

        Board.objects.filter(
            pk=self.board.pk,
        ).update(
            updated_at=old_time,
        )
        Column.objects.filter(
            pk=self.column.pk,
        ).update(
            updated_at=old_time,
        )

        TaskLifecycleService.archive(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
        )

        self.board.refresh_from_db()
        self.column.refresh_from_db()

        self.assertGreater(
            self.board.updated_at,
            old_time,
        )
        self.assertGreater(
            self.column.updated_at,
            old_time,
        )


class TaskLifecycleServiceRestoreTests(
    TaskTestBase
):
    def test_restore_clears_archive_timestamp(
        self,
    ):
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        task, board, column = (
            TaskLifecycleService.restore(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=archived.pk,
            )
        )

        task.refresh_from_db()

        self.assertFalse(
            task.is_archived
        )
        self.assertIsNone(
            task.archived_at
        )
        self.assertEqual(
            board,
            self.board,
        )
        self.assertEqual(
            column,
            self.column,
        )

    def test_restore_appends_to_end(self):
        self.create_task(
            title="Second active",
            position=1,
        )
        archived = self.create_task(
            title="Archived",
            position=99,
            is_archived=True,
        )

        task, _board, _column = (
            TaskLifecycleService.restore(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=archived.pk,
            )
        )

        task.refresh_from_db()

        self.assertEqual(
            task.position,
            2,
        )

    def test_active_task_cannot_be_restored(
        self,
    ):
        with self.assertRaises(Http404):
            TaskLifecycleService.restore(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
            )


class TaskLifecycleServiceMoveTests(
    TaskTestBase
):
    def test_move_appends_to_target_and_normalizes_source(
        self,
    ):
        moving = self.create_task(
            title="Moving",
            position=1,
        )
        source_final = self.create_task(
            title="Source Final",
            position=2,
        )
        target = self.create_column(
            title="Target",
            position=1,
        )
        self.create_task(
            column=target,
            title="Target Existing",
            position=0,
        )

        (
            moved,
            board,
            source_column,
            target_column,
        ) = TaskLifecycleService.move(
            workspace=self.workspace,
            board_pk=self.board.pk,
            source_column_pk=self.column.pk,
            target_column_pk=target.pk,
            task_pk=moving.pk,
        )

        moved.refresh_from_db()
        source_final.refresh_from_db()

        self.assertEqual(
            moved.column,
            target,
        )
        self.assertEqual(
            moved.position,
            1,
        )
        self.assertEqual(
            source_final.position,
            1,
        )
        self.assertEqual(
            board,
            self.board,
        )
        self.assertEqual(
            source_column,
            self.column,
        )
        self.assertEqual(
            target_column,
            target,
        )

    def test_move_preserves_task_metadata(self):
        target = self.create_column(
            title="Target",
            position=1,
        )

        original_status = self.task.status
        original_priority = self.task.priority
        original_assignee = self.task.assignee
        original_creator = self.task.created_by

        moved, *_ = TaskLifecycleService.move(
            workspace=self.workspace,
            board_pk=self.board.pk,
            source_column_pk=self.column.pk,
            target_column_pk=target.pk,
            task_pk=self.task.pk,
        )

        moved.refresh_from_db()

        self.assertEqual(
            moved.status,
            original_status,
        )
        self.assertEqual(
            moved.priority,
            original_priority,
        )
        self.assertEqual(
            moved.assignee,
            original_assignee,
        )
        self.assertEqual(
            moved.created_by,
            original_creator,
        )

    def test_same_column_is_rejected(self):
        with self.assertRaises(Http404):
            TaskLifecycleService.move(
                workspace=self.workspace,
                board_pk=self.board.pk,
                source_column_pk=self.column.pk,
                target_column_pk=self.column.pk,
                task_pk=self.task.pk,
            )

    def test_archived_target_column_is_rejected(
        self,
    ):
        target = self.create_column(
            title="Archived Target",
            position=50,
            is_archived=True,
        )

        with self.assertRaises(Http404):
            TaskLifecycleService.move(
                workspace=self.workspace,
                board_pk=self.board.pk,
                source_column_pk=self.column.pk,
                target_column_pk=target.pk,
                task_pk=self.task.pk,
            )

    def test_other_board_target_is_rejected(self):
        other_board = self.create_board(
            title="Other Board",
        )
        target = self.create_column(
            board=other_board,
            title="Other Board Column",
            position=0,
        )

        with self.assertRaises(Http404):
            TaskLifecycleService.move(
                workspace=self.workspace,
                board_pk=self.board.pk,
                source_column_pk=self.column.pk,
                target_column_pk=target.pk,
                task_pk=self.task.pk,
            )

    def test_archived_task_cannot_be_moved(self):
        target = self.create_column(
            title="Target",
            position=1,
        )
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        with self.assertRaises(Http404):
            TaskLifecycleService.move(
                workspace=self.workspace,
                board_pk=self.board.pk,
                source_column_pk=self.column.pk,
                target_column_pk=target.pk,
                task_pk=archived.pk,
            )


class TaskLifecycleServiceDeleteTests(
    TaskTestBase
):
    def test_delete_archived_removes_task(self):
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )
        task_pk = archived.pk

        (
            task_title,
            board,
            column,
        ) = (
            TaskLifecycleService.delete_archived(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=archived.pk,
            )
        )

        self.assertEqual(
            task_title,
            archived.title,
        )
        self.assertEqual(
            board,
            self.board,
        )
        self.assertEqual(
            column,
            self.column,
        )
        self.assertFalse(
            Task.objects.filter(
                pk=task_pk,
            ).exists()
        )

    def test_active_task_cannot_be_deleted(
        self,
    ):
        with self.assertRaises(Http404):
            TaskLifecycleService.delete_archived(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
            )
