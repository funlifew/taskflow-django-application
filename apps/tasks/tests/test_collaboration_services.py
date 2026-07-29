from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import (
    PermissionDenied,
)
from django.http import Http404
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.tasks.collaboration import (
    TaskActivityService,
    TaskCommentService,
)
from apps.tasks.models import (
    Task,
    TaskActivity,
    TaskComment,
)

from apps.tasks.tests.collaboration_base import (
    TaskCollaborationTestBase,
)


class TaskActivityServiceTests(
    TaskCollaborationTestBase
):
    def test_record_creates_activity(
        self,
    ):
        activity = (
            TaskActivityService.record(
                task=self.task,
                actor=self.owner,
                action=(
                    TaskActivity
                    .Action
                    .UPDATED
                ),
                metadata={
                    "field": "title",
                },
            )
        )

        self.assertEqual(
            activity.task,
            self.task,
        )

        self.assertEqual(
            activity.actor,
            self.owner,
        )

        self.assertEqual(
            activity.metadata,
            {
                "field": "title",
            },
        )

    def test_record_rejects_non_dict_metadata(
        self,
    ):
        from django.core.exceptions import (
            ValidationError,
        )

        with self.assertRaises(
            ValidationError
        ):
            TaskActivityService.record(
                task=self.task,
                actor=self.owner,
                action=(
                    TaskActivity
                    .Action
                    .UPDATED
                ),
                metadata=[],
            )

        self.assertFalse(
            TaskActivity.objects.exists()
        )


class TaskCommentServiceTests(
    TaskCollaborationTestBase
):
    def create_via_service(
        self,
        *,
        actor=None,
        body="Comment body",
    ):
        return (
            TaskCommentService.create(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
                actor=actor or self.member,
                body=body,
            )
        )

    def test_create_persists_comment_and_activity(
        self,
    ):
        (
            comment,
            task,
            board,
            column,
        ) = self.create_via_service(
            body="  گزارش پیشرفت  ",
        )

        self.assertEqual(
            comment.body,
            "گزارش پیشرفت",
        )

        self.assertEqual(
            comment.task,
            self.task,
        )

        self.assertEqual(
            comment.author,
            self.member,
        )

        activity = (
            TaskActivity.objects.get()
        )

        self.assertEqual(
            activity.action,
            (
                TaskActivity
                .Action
                .COMMENTED
            ),
        )

        self.assertEqual(
            activity.metadata[
                "comment_id"
            ],
            comment.pk,
        )

        self.assertEqual(
            task,
            self.task,
        )

        self.assertEqual(
            board,
            self.board,
        )

        self.assertEqual(
            column,
            self.column,
        )

    def test_create_touches_task_column_and_board(
        self,
    ):
        past = (
            timezone.now()
            - timedelta(days=1)
        )

        Task.objects.filter(
            pk=self.task.pk,
        ).update(
            updated_at=past,
        )

        Column.objects.filter(
            pk=self.column.pk,
        ).update(
            updated_at=past,
        )

        Board.objects.filter(
            pk=self.board.pk,
        ).update(
            updated_at=past,
        )

        self.create_via_service()

        self.task.refresh_from_db()
        self.column.refresh_from_db()
        self.board.refresh_from_db()

        self.assertGreater(
            self.task.updated_at,
            past,
        )

        self.assertGreater(
            self.column.updated_at,
            past,
        )

        self.assertGreater(
            self.board.updated_at,
            past,
        )

    def test_create_rejects_archived_task(
        self,
    ):
        self.task.is_archived = True
        self.task.archived_at = (
            timezone.now()
        )

        self.task.save(
            update_fields=[
                "is_archived",
                "archived_at",
                "updated_at",
            ]
        )

        with self.assertRaises(
            Http404
        ):
            self.create_via_service()

    @patch(
        "apps.tasks.collaboration."
        "TaskActivityService.record"
    )
    def test_create_rolls_back_when_activity_fails(
        self,
        mocked_record,
    ):
        mocked_record.side_effect = (
            RuntimeError(
                "Activity failed"
            )
        )

        with self.assertRaises(
            RuntimeError
        ):
            self.create_via_service()

        self.assertFalse(
            TaskComment.objects.exists()
        )

    def test_author_can_update_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
            body="Old body",
        )

        (
            updated_comment,
            task,
            board,
            column,
        ) = TaskCommentService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            comment_pk=comment.pk,
            actor=self.member,
            body="  New body  ",
        )

        self.assertEqual(
            updated_comment.body,
            "New body",
        )

        activity = (
            TaskActivity.objects.get()
        )

        self.assertEqual(
            activity.action,
            (
                TaskActivity
                .Action
                .COMMENT_UPDATED
            ),
        )

        self.assertEqual(
            activity.metadata,
            {
                "comment_id": (
                    comment.pk
                ),
            },
        )

    def test_update_same_body_is_no_op(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
            body="Same body",
        )

        TaskCommentService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            comment_pk=comment.pk,
            actor=self.member,
            body="Same body",
        )

        self.assertFalse(
            TaskActivity.objects.exists()
        )

    def test_non_author_cannot_update_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.admin,
        )

        with self.assertRaises(
            PermissionDenied
        ):
            TaskCommentService.update(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
                comment_pk=comment.pk,
                actor=self.member,
                body="Unauthorized",
            )

        comment.refresh_from_db()

        self.assertEqual(
            comment.body,
            "دیدگاه آزمایشی",
        )

    def test_author_can_soft_delete_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        (
            deleted_comment,
            task,
            board,
            column,
        ) = TaskCommentService.delete(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            comment_pk=comment.pk,
            actor=self.member,
        )

        self.assertTrue(
            deleted_comment.is_deleted
        )

        self.assertIsNotNone(
            deleted_comment.deleted_at
        )

        self.assertEqual(
            deleted_comment.deleted_by,
            self.member,
        )

        self.assertTrue(
            TaskComment.objects.filter(
                pk=comment.pk,
            ).exists()
        )

        activity = (
            TaskActivity.objects.get()
        )

        self.assertEqual(
            activity.action,
            (
                TaskActivity
                .Action
                .COMMENT_DELETED
            ),
        )

    def test_admin_can_delete_another_users_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        TaskCommentService.delete(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            comment_pk=comment.pk,
            actor=self.admin,
        )

        comment.refresh_from_db()

        self.assertTrue(
            comment.is_deleted
        )

        self.assertEqual(
            comment.deleted_by,
            self.admin,
        )

    def test_owner_can_delete_another_users_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        TaskCommentService.delete(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            comment_pk=comment.pk,
            actor=self.owner,
        )

        comment.refresh_from_db()

        self.assertTrue(
            comment.is_deleted
        )

    def test_member_cannot_delete_another_users_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.admin,
        )

        with self.assertRaises(
            PermissionDenied
        ):
            TaskCommentService.delete(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
                comment_pk=comment.pk,
                actor=self.member,
            )

        comment.refresh_from_db()

        self.assertFalse(
            comment.is_deleted
        )

    @patch(
        "apps.tasks.collaboration."
        "TaskActivityService.record"
    )
    def test_delete_rolls_back_when_activity_fails(
        self,
        mocked_record,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        mocked_record.side_effect = (
            RuntimeError(
                "Activity failed"
            )
        )

        with self.assertRaises(
            RuntimeError
        ):
            TaskCommentService.delete(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                task_pk=self.task.pk,
                comment_pk=comment.pk,
                actor=self.member,
            )

        comment.refresh_from_db()

        self.assertFalse(
            comment.is_deleted
        )

        self.assertIsNone(
            comment.deleted_at
        )

        self.assertIsNone(
            comment.deleted_by
        )