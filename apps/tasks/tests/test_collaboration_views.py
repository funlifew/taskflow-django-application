from django.urls import reverse

from apps.tasks.models import (
    TaskActivity,
    TaskComment,
)

from .collaboration_base import (
    TaskCollaborationTestBase,
)


class TaskCollaborationViewTests(
    TaskCollaborationTestBase
):
    def test_writer_sees_comment_form(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.task_detail_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.context[
                "can_comment"
            ]
        )

        self.assertContains(
            response,
            self.comment_create_url(),
        )

        self.assertContains(
            response,
            'name="body"',
        )

    def test_viewer_sees_comments_but_not_form(
        self,
    ):
        comment = self.create_comment(
            body="Visible comment",
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.task_detail_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.context[
                "can_comment"
            ]
        )

        self.assertContains(
            response,
            comment.body,
        )

        self.assertNotContains(
            response,
            self.comment_create_url(),
        )

    def test_deleted_comment_uses_placeholder(
        self,
    ):
        self.create_comment(
            body="Secret deleted text",
            is_deleted=True,
            deleted_by=self.admin,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.task_detail_url()
        )

        self.assertContains(
            response,
            "این دیدگاه حذف شده است.",
        )

        self.assertNotContains(
            response,
            "Secret deleted text",
        )

    def test_detail_shows_activity_timeline(
        self,
    ):
        activity = self.create_activity(
            actor=self.owner,
            action=(
                TaskActivity
                .Action
                .UPDATED
            ),
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.task_detail_url()
        )

        self.assertContains(
            response,
            activity.get_action_display(),
        )

        self.assertContains(
            response,
            self.owner.get_full_name(),
        )

    def test_member_can_create_comment(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.comment_create_url(),
            data={
                "body": (
                    "گزارش پیشرفت Task"
                ),
            },
        )

        self.assertRedirects(
            response,
            self.task_detail_url(),
        )

        comment = (
            TaskComment.objects.get()
        )

        self.assertEqual(
            comment.author,
            self.member,
        )

        self.assertEqual(
            comment.body,
            "گزارش پیشرفت Task",
        )

        self.assertTrue(
            TaskActivity.objects.filter(
                action=(
                    TaskActivity
                    .Action
                    .COMMENTED
                ),
            ).exists()
        )

    def test_viewer_cannot_create_comment(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.comment_create_url(),
            data={
                "body": "Unauthorized",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            TaskComment.objects.exists()
        )

    def test_outsider_cannot_create_comment(
        self,
    ):
        self.client.force_login(
            self.outsider
        )

        response = self.client.post(
            self.comment_create_url(),
            data={
                "body": "Unauthorized",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_blank_comment_is_not_created(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.comment_create_url(),
            data={
                "body": "   ",
            },
        )

        self.assertRedirects(
            response,
            self.task_detail_url(),
        )

        self.assertFalse(
            TaskComment.objects.exists()
        )

        self.assertFalse(
            TaskActivity.objects.exists()
        )

    def test_author_can_open_comment_update_page(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.comment_update_url(
                comment
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            comment.body,
        )

    def test_non_author_cannot_open_update_page(
        self,
    ):
        comment = self.create_comment(
            author=self.admin,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.comment_update_url(
                comment
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_viewer_cannot_open_update_page(
        self,
    ):
        comment = self.create_comment(
            author=self.viewer,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.comment_update_url(
                comment
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_author_can_update_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
            body="Old body",
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.comment_update_url(
                comment
            ),
            data={
                "body": "New body",
            },
        )

        self.assertRedirects(
            response,
            self.task_detail_url(),
        )

        comment.refresh_from_db()

        self.assertEqual(
            comment.body,
            "New body",
        )

    def test_non_author_cannot_update_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.admin,
            body="Protected",
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.comment_update_url(
                comment
            ),
            data={
                "body": "Unauthorized",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        comment.refresh_from_db()

        self.assertEqual(
            comment.body,
            "Protected",
        )

    def test_author_can_delete_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.comment_delete_url(
                comment
            )
        )

        self.assertRedirects(
            response,
            self.task_detail_url(),
        )

        comment.refresh_from_db()

        self.assertTrue(
            comment.is_deleted
        )

    def test_admin_can_delete_another_users_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.member,
        )

        self.client.force_login(
            self.admin
        )

        response = self.client.post(
            self.comment_delete_url(
                comment
            )
        )

        self.assertRedirects(
            response,
            self.task_detail_url(),
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

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.comment_delete_url(
                comment
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        comment.refresh_from_db()

        self.assertFalse(
            comment.is_deleted
        )

    def test_viewer_cannot_delete_own_comment(
        self,
    ):
        comment = self.create_comment(
            author=self.viewer,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.comment_delete_url(
                comment
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        comment.refresh_from_db()

        self.assertFalse(
            comment.is_deleted
        )

    def test_deleted_comments_not_counted_as_active(
        self,
    ):
        self.create_comment(
            body="Visible",
        )

        self.create_comment(
            body="Deleted",
            is_deleted=True,
            deleted_by=self.admin,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.task_detail_url()
        )

        self.assertEqual(
            response.context[
                "comments_count"
            ],
            1,
        )

    def test_comment_routes_are_task_scoped(
        self,
    ):
        another_task = self.create_task(
            title="Another Task",
        )

        comment = self.create_comment(
            task=another_task,
            author=self.member,
        )

        incorrect_url = reverse(
            "tasks:comment_update",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    self.column.pk
                ),
                "task_pk": (
                    self.task.pk
                ),
                "comment_pk": (
                    comment.pk
                ),
            },
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            incorrect_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )