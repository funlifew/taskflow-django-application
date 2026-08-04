from django.contrib.auth.models import (
    AnonymousUser,
)
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.notifications.context_processors import (
    HEADER_NOTIFICATIONS_LIMIT,
    notifications_context,
)
from apps.notifications.tests.base import (
    NotificationTestBase,
)


class NotificationContextProcessorTests(
    NotificationTestBase
):
    def setUp(self):
        super().setUp()

        self.request_factory = (
            RequestFactory()
        )

    def get_request(self, user):
        request = (
            self.request_factory.get(
                "/dashboard/"
            )
        )

        request.user = user

        return request

    def test_anonymous_context_is_empty(
        self,
    ):
        context = notifications_context(
            self.get_request(
                AnonymousUser()
            )
        )

        self.assertEqual(
            context[
                "unread_notifications_count"
            ],
            0,
        )

        self.assertEqual(
            context[
                "header_notifications"
            ],
            (),
        )

    def test_unread_count_is_integer(
        self,
    ):
        self.create_notification(
            title="Unread one",
        )

        self.create_notification(
            title="Unread two",
        )

        self.create_notification(
            title="Read",
            is_read=True,
            read_at=timezone.now(),
        )

        context = notifications_context(
            self.get_request(
                self.member
            )
        )

        self.assertIsInstance(
            context[
                "unread_notifications_count"
            ],
            int,
        )

        self.assertEqual(
            context[
                "unread_notifications_count"
            ],
            2,
        )

    def test_header_notifications_are_limited(
        self,
    ):
        notifications = [
            self.create_notification(
                title=f"Notification {index}",
            )
            for index in range(
                HEADER_NOTIFICATIONS_LIMIT
                + 3
            )
        ]

        context = notifications_context(
            self.get_request(
                self.member
            )
        )

        header_notifications = (
            context[
                "header_notifications"
            ]
        )

        expected_ids = [
            notification.pk
            for notification in reversed(
                notifications[
                    -HEADER_NOTIFICATIONS_LIMIT:
                ]
            )
        ]

        self.assertEqual(
            [
                notification.pk
                for notification
                in header_notifications
            ],
            expected_ids,
        )

    def test_other_users_notifications_are_excluded(
        self,
    ):
        own = self.create_notification(
            recipient=self.member,
            title="Own",
        )

        self.create_notification(
            recipient=self.admin,
            title="Other",
        )

        context = notifications_context(
            self.get_request(
                self.member
            )
        )

        self.assertEqual(
            [
                notification.pk
                for notification
                in context[
                    "header_notifications"
                ]
            ],
            [
                own.pk,
            ],
        )


class NotificationHeaderTemplateTests(
    NotificationTestBase
):
    def setUp(self):
        super().setUp()

        self.client.force_login(
            self.member
        )

    def test_header_contains_notification_menu(
        self,
    ):
        response = self.client.get(
            reverse(
                "dashboard:dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "data-notification-menu",
        )

        self.assertContains(
            response,
            "data-notification-toggle",
        )

        self.assertContains(
            response,
            "data-notification-panel",
        )

    def test_unread_notification_appears_in_header(
        self,
    ):
        notification = (
            self.create_notification(
                title="Task assigned",
            )
        )

        response = self.client.get(
            reverse(
                "dashboard:dashboard"
            )
        )

        self.assertContains(
            response,
            (
                'data-notification-count="1"'
            ),
        )

        self.assertContains(
            response,
            notification.title,
        )

        self.assertContains(
            response,
            reverse(
                "notifications:mark_read",
                kwargs={
                    "notification_pk": (
                        notification.pk
                    ),
                },
            ),
        )

    def test_read_notification_has_no_unread_count(
        self,
    ):
        self.create_notification(
            title="Read notification",
            is_read=True,
            read_at=timezone.now(),
        )

        response = self.client.get(
            reverse(
                "dashboard:dashboard"
            )
        )

        self.assertNotContains(
            response,
            "data-notification-count=",
        )