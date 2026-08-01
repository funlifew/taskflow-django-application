from django.http import Http404

from apps.tasks.models import (
    Task,
    TaskActivity,
)
from apps.tasks.reordering import (
    TaskReorderingService,
)
from apps.tasks.services import (
    TaskLifecycleService,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)


class TaskLifecycleActivityTests(
    TaskTestBase
):
    def test_create_records_activity(self):
        task, _board, _column = (
            TaskLifecycleService.create(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                actor=self.owner,
                title="Activity Task",
                description="Created",
                priority=Task.Priority.HIGH,
                assignee=self.member,
                due_at=None,
            )
        )

        activity = task.activities.get(
            action=(
                TaskActivity
                .Action
                .CREATED
            )
        )

        self.assertEqual(
            activity.actor,
            self.owner,
        )
        self.assertEqual(
            activity.metadata[
                "column_id"
            ],
            self.column.pk,
        )
        self.assertIsInstance(
            activity.metadata,
            dict,
        )

    def test_update_records_changed_fields(
        self,
    ):
        TaskLifecycleService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            title="عنوان جدید",
            description=(
                self.task.description
            ),
            priority=self.task.priority,
            assignee=self.task.assignee,
            due_at=self.task.due_at,
            actor=self.owner,
        )

        activity = self.task.activities.get(
            action=(
                TaskActivity
                .Action
                .UPDATED
            )
        )

        self.assertEqual(
            activity.metadata[
                "changed_fields"
            ],
            ["title"],
        )

    def test_noop_update_records_nothing(
        self,
    ):
        TaskLifecycleService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            title=self.task.title,
            description=(
                self.task.description
            ),
            priority=self.task.priority,
            assignee=self.task.assignee,
            due_at=self.task.due_at,
            actor=self.owner,
        )

        self.assertFalse(
            self.task.activities.exists()
        )

    def test_assignee_change_records_activity(
        self,
    ):
        TaskLifecycleService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            title=self.task.title,
            description=(
                self.task.description
            ),
            priority=self.task.priority,
            assignee=self.admin,
            due_at=self.task.due_at,
            actor=self.owner,
        )

        activity = self.task.activities.get(
            action=(
                TaskActivity
                .Action
                .ASSIGNEE_CHANGED
            )
        )

        self.assertEqual(
            activity.metadata[
                "old_assignee_id"
            ],
            self.member.pk,
        )
        self.assertEqual(
            activity.metadata[
                "new_assignee_id"
            ],
            self.admin.pk,
        )

    def test_status_change_records_labels(
        self,
    ):
        TaskLifecycleService.update_status(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            status=Task.Status.DONE,
            actor=self.admin,
        )

        activity = self.task.activities.get(
            action=(
                TaskActivity
                .Action
                .STATUS_CHANGED
            )
        )

        self.assertEqual(
            activity.metadata[
                "old_status"
            ],
            Task.Status.TODO,
        )
        self.assertEqual(
            activity.metadata[
                "new_status"
            ],
            Task.Status.DONE,
        )
        self.assertEqual(
            activity.actor,
            self.admin,
        )
        self.assertIn(
            "old_status_label",
            activity.metadata,
        )
        self.assertIn(
            "new_status_label",
            activity.metadata,
        )

    def test_noop_status_records_nothing(
        self,
    ):
        TaskLifecycleService.update_status(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            status=self.task.status,
            actor=self.owner,
        )

        self.assertFalse(
            self.task.activities.exists()
        )

    def test_archive_records_activity(self):
        TaskLifecycleService.archive(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            actor=self.owner,
        )

        activity = self.task.activities.get(
            action=(
                TaskActivity
                .Action
                .ARCHIVED
            )
        )

        self.assertEqual(
            activity.metadata[
                "position"
            ],
            0,
        )

    def test_restore_records_activity(self):
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        TaskLifecycleService.restore(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=archived.pk,
            actor=self.owner,
        )

        activity = archived.activities.get(
            action=(
                TaskActivity
                .Action
                .RESTORED
            )
        )

        self.assertEqual(
            activity.metadata[
                "column_id"
            ],
            self.column.pk,
        )


class TaskReorderingActivityTests(
    TaskTestBase
):
    def test_cross_column_move_records_moved(
        self,
    ):
        target_column = self.create_column(
            title="در حال انجام",
            position=1,
        )

        (
            task,
            _board,
            _source_column,
            _target_column,
        ) = (
            TaskReorderingService
            .move_to_column(
                workspace=self.workspace,
                board_pk=self.board.pk,
                source_column_pk=(
                    self.column.pk
                ),
                target_column_pk=(
                    target_column.pk
                ),
                task_pk=self.task.pk,
                actor=self.owner,
            )
        )

        activity = task.activities.get(
            action=(
                TaskActivity
                .Action
                .MOVED
            )
        )

        self.assertEqual(
            activity.metadata[
                "source_column_title"
            ],
            self.column.title,
        )
        self.assertEqual(
            activity.metadata[
                "target_column_title"
            ],
            target_column.title,
        )

    def test_same_column_reorder_records_activity(
        self,
    ):
        self.create_task(
            title="Second",
            position=1,
        )

        (
            task,
            _board,
            _source_column,
            _target_column,
        ) = TaskReorderingService.reorder(
            workspace=self.workspace,
            board_pk=self.board.pk,
            source_column_pk=(
                self.column.pk
            ),
            target_column_pk=(
                self.column.pk
            ),
            task_pk=self.task.pk,
            target_position=1,
            actor=self.owner,
        )

        activity = task.activities.get(
            action=(
                TaskActivity
                .Action
                .REORDERED
            )
        )

        self.assertEqual(
            activity.metadata[
                "old_position"
            ],
            0,
        )
        self.assertEqual(
            activity.metadata[
                "new_position"
            ],
            1,
        )

    def test_move_down_records_activity(self):
        self.create_task(
            title="Second",
            position=1,
        )

        TaskReorderingService.move_down(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            actor=self.owner,
        )

        self.assertTrue(
            self.task.activities.filter(
                action=(
                    TaskActivity
                    .Action
                    .REORDERED
                )
            ).exists()
        )

    def test_boundary_move_up_is_noop(
        self,
    ):
        TaskReorderingService.move_up(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            actor=self.owner,
        )

        self.assertFalse(
            self.task.activities.exists()
        )

    def test_same_column_quick_move_is_rejected(
        self,
    ):
        with self.assertRaises(Http404):
            (
                TaskReorderingService
                .move_to_column(
                    workspace=self.workspace,
                    board_pk=self.board.pk,
                    source_column_pk=(
                        self.column.pk
                    ),
                    target_column_pk=(
                        self.column.pk
                    ),
                    task_pk=self.task.pk,
                    actor=self.owner,
                )
            )

        self.assertFalse(
            self.task.activities.exists()
        )

    def test_failed_move_does_not_record_activity(
        self,
    ):
        other_board = self.create_board(
            title="Other Board",
        )

        other_column = self.create_column(
            board=other_board,
            title="Other Column",
            position=0,
        )

        with self.assertRaises(Http404):
            (
                TaskReorderingService
                .move_to_column(
                    workspace=self.workspace,
                    board_pk=self.board.pk,
                    source_column_pk=(
                        self.column.pk
                    ),
                    target_column_pk=(
                        other_column.pk
                    ),
                    task_pk=self.task.pk,
                    actor=self.owner,
                )
            )

        self.assertFalse(
            self.task.activities.exists()
        )