from django.core.exceptions import (
    ValidationError,
)

from apps.tasks.models import (
    TaskActivity,
    TaskComment,
)

from apps.tasks.tests.collaboration_base import (
    TaskCollaborationTestBase,
)


class TaskCommentModelTests(
    TaskCollaborationTestBase
):
    def test_visible_queryset_excludes_deleted(
        self,
    ):
        visible_comment = (
            self.create_comment(
                body="Visible",
            )
        )

        self.create_comment(
            body="Deleted",
            is_deleted=True,
            deleted_by=self.admin,
        )

        self.assertQuerySetEqual(
            TaskComment.objects.visible(),
            [visible_comment],
        )

    def test_deleted_queryset_only_returns_deleted(
        self,
    ):
        self.create_comment(
            body="Visible",
        )

        deleted_comment = (
            self.create_comment(
                body="Deleted",
                is_deleted=True,
                deleted_by=self.admin,
            )
        )

        self.assertQuerySetEqual(
            TaskComment.objects.deleted(),
            [deleted_comment],
        )

    def test_for_task_scopes_comments(
        self,
    ):
        another_task = self.create_task(
            title="Another Task",
        )

        expected_comment = (
            self.create_comment(
                task=self.task,
            )
        )

        self.create_comment(
            task=another_task,
        )

        self.assertQuerySetEqual(
            (
                TaskComment.objects
                .for_task(self.task)
            ),
            [expected_comment],
        )

    def test_comment_body_is_trimmed(
        self,
    ):
        comment = TaskComment(
            task=self.task,
            author=self.member,
            body="  متن دیدگاه  ",
        )

        comment.full_clean()

        self.assertEqual(
            comment.body,
            "متن دیدگاه",
        )

    def test_active_comment_cannot_have_blank_body(
        self,
    ):
        comment = TaskComment(
            task=self.task,
            author=self.member,
            body="   ",
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            comment.full_clean()

        self.assertIn(
            "body",
            context.exception.message_dict,
        )

    def test_active_comment_cannot_have_deleted_at(
        self,
    ):
        from django.utils import timezone

        comment = TaskComment(
            task=self.task,
            author=self.member,
            body="Comment",
            is_deleted=False,
            deleted_at=timezone.now(),
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            comment.full_clean()

        self.assertIn(
            "is_deleted",
            context.exception.message_dict,
        )

    def test_deleted_comment_requires_deleted_at(
        self,
    ):
        comment = TaskComment(
            task=self.task,
            author=self.member,
            body="Comment",
            is_deleted=True,
            deleted_at=None,
            deleted_by=self.admin,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            comment.full_clean()

        self.assertIn(
            "is_deleted",
            context.exception.message_dict,
        )

    def test_comment_string_contains_task_and_body(
        self,
    ):
        comment = self.create_comment(
            body="یک دیدگاه مهم",
        )

        representation = str(comment)

        self.assertIn(
            self.task.title,
            representation,
        )

        self.assertIn(
            "یک دیدگاه مهم",
            representation,
        )


class TaskActivityModelTests(
    TaskCollaborationTestBase
):
    def test_activity_requires_dict_metadata(
        self,
    ):
        activity = TaskActivity(
            task=self.task,
            actor=self.owner,
            action=(
                TaskActivity
                .Action
                .UPDATED
            ),
            metadata=[],
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            activity.full_clean()

        self.assertIn(
            "metadata",
            context.exception.message_dict,
        )

    def test_activity_accepts_empty_dict_metadata(
        self,
    ):
        activity = TaskActivity(
            task=self.task,
            actor=self.owner,
            action=(
                TaskActivity
                .Action
                .CREATED
            ),
            metadata={},
        )

        activity.full_clean()

    def test_activities_are_newest_first(
        self,
    ):
        first = self.create_activity(
            action=(
                TaskActivity
                .Action
                .CREATED
            ),
        )

        second = self.create_activity(
            action=(
                TaskActivity
                .Action
                .UPDATED
            ),
        )

        self.assertQuerySetEqual(
            TaskActivity.objects.all(),
            [
                second,
                first,
            ],
        )

    def test_activity_string_contains_display_name(
        self,
    ):
        activity = self.create_activity(
            action=(
                TaskActivity
                .Action
                .COMMENTED
            ),
        )

        representation = str(activity)

        self.assertIn(
            self.task.title,
            representation,
        )

        self.assertIn(
            activity.get_action_display(),
            representation,
        )

    def test_deleting_task_cascades_collaboration_data(
        self,
    ):
        self.create_comment()
        self.create_activity()

        self.task.delete()

        self.assertFalse(
            TaskComment.objects.exists()
        )

        self.assertFalse(
            TaskActivity.objects.exists()
        )