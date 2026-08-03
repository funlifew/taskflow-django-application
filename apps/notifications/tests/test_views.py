from django.urls import reverse

from apps.notifications.tests.base import (
    NotificationTestBase,
)


class NotificationViewTests(
    NotificationTestBase
):
    def list_url(self):
        return reverse(
            "notifications:list"
        )

    def mark_read_url(
        self,
        notification,
    ):
        return reverse(
            "notifications:mark_read",
            kwargs={
                "notification_pk": (
                    notification.pk
                ),
            },
        )

    def mark_all_url(self):
        return reverse(
            "notifications:mark_all_read"
        )

    def test_anonymous_user_is_redirected(
        self,
    ):
        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_user_only_sees_own_notifications(
        self,
    ):
        own = self.create_notification()

        other = self.create_notification(
            recipient=self.admin,
            title="Other",
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.list_url()
        )

        notifications = list(
            response.context[
                "notifications"
            ]
        )

        self.assertIn(
            own,
            notifications,
        )
        self.assertNotIn(
            other,
            notifications,
        )

    def test_unread_count_is_available(
        self,
    ):
        self.create_notification()
        self.create_notification(
            title="Second",
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.context[
                "unread_count"
            ],
            2,
        )

    def test_mark_read_only_accepts_post(
        self,
    ):
        notification = (
            self.create_notification()
        )

        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.mark_read_url(
                notification
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_valid_post_marks_notification_read(
        self,
    ):
        notification = (
            self.create_notification()
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.mark_read_url(
                notification
            ),
            data={
                "next": self.list_url(),
            },
        )

        notification.refresh_from_db()

        self.assertTrue(
            notification.is_read
        )
        self.assertIsNotNone(
            notification.read_at
        )
        self.assertRedirects(
            response,
            self.list_url(),
        )

    def test_other_users_notification_returns_404(
        self,
    ):
        notification = (
            self.create_notification(
                recipient=self.admin,
            )
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.mark_read_url(
                notification
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_mark_all_only_accepts_post(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.mark_all_url()
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_mark_all_marks_all_user_notifications(
        self,
    ):
        first = self.create_notification()
        second = self.create_notification(
            title="Second",
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.mark_all_url(),
            data={
                "next": self.list_url(),
            },
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertTrue(first.is_read)
        self.assertTrue(second.is_read)
        self.assertRedirects(
            response,
            self.list_url(),
        )

    def test_external_next_url_is_rejected(
        self,
    ):
        notification = (
            self.create_notification()
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.mark_read_url(
                notification
            ),
            data={
                "next": (
                    "https://example.com/"
                ),
            },
        )

        self.assertRedirects(
            response,
            self.list_url(),
        )