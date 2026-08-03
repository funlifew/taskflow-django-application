from django.http import Http404
from django.utils import timezone

from apps.notifications.models import (
    Notification,
)
from apps.notifications.services import (
    NotificationService,
)
from apps.notifications.tests.base import (
    NotificationTestBase,
)


class NotificationServiceTests(
    NotificationTestBase
):
    def test_create_notification(self):
        notification = (
            NotificationService.create(
                recipient=self.member,
                actor=self.owner,
                notification_type=(
                    Notification.Type
                    .TASK_ASSIGNED
                ),
                title="Assigned",
                message="Message",
                target_url="/task/",
                metadata={
                    "task_id": self.task.pk,
                },
            )
        )

        self.assertIsNotNone(
            notification
        )
        self.assertEqual(
            notification.recipient,
            self.member,
        )
        self.assertFalse(
            notification.is_read
        )

    def test_actor_does_not_notify_self(
        self,
    ):
        notification = (
            NotificationService.create(
                recipient=self.owner,
                actor=self.owner,
                notification_type=(
                    Notification.Type
                    .TASK_ASSIGNED
                ),
                title="Assigned",
            )
        )

        self.assertIsNone(notification)
        self.assertFalse(
            Notification.objects.exists()
        )

    def test_none_recipient_is_ignored(
        self,
    ):
        notification = (
            NotificationService.create(
                recipient=None,
                actor=self.owner,
                notification_type=(
                    Notification.Type
                    .TASK_ASSIGNED
                ),
                title="Assigned",
            )
        )

        self.assertIsNone(notification)

    def test_multiple_recipients_are_deduplicated(
        self,
    ):
        notifications = (
            NotificationService
            .create_for_recipients(
                recipients=(
                    self.member,
                    self.member,
                    self.admin,
                ),
                actor=self.owner,
                notification_type=(
                    Notification.Type
                    .TASK_COMMENTED
                ),
                title="Comment",
            )
        )

        self.assertEqual(
            len(notifications),
            2,
        )

        self.assertEqual(
            set(
                Notification.objects
                .values_list(
                    "recipient_id",
                    flat=True,
                )
            ),
            {
                self.member.pk,
                self.admin.pk,
            },
        )

    def test_mark_as_read(self):
        notification = (
            self.create_notification()
        )

        (
            notification,
            changed,
        ) = (
            NotificationService
            .mark_as_read(
                recipient=self.member,
                notification_pk=(
                    notification.pk
                ),
            )
        )

        self.assertTrue(changed)
        self.assertTrue(
            notification.is_read
        )
        self.assertIsNotNone(
            notification.read_at
        )

    def test_marking_read_notification_is_noop(
        self,
    ):
        read_at = timezone.now()

        notification = (
            self.create_notification(
                is_read=True,
                read_at=read_at,
            )
        )

        (
            notification,
            changed,
        ) = (
            NotificationService
            .mark_as_read(
                recipient=self.member,
                notification_pk=(
                    notification.pk
                ),
            )
        )

        self.assertFalse(changed)
        self.assertEqual(
            notification.read_at,
            read_at,
        )

    def test_user_cannot_read_other_users_notification(
        self,
    ):
        notification = (
            self.create_notification(
                recipient=self.admin,
            )
        )

        with self.assertRaises(Http404):
            (
                NotificationService
                .mark_as_read(
                    recipient=self.member,
                    notification_pk=(
                        notification.pk
                    ),
                )
            )

    def test_mark_all_as_read_only_updates_recipient(
        self,
    ):
        first = self.create_notification()
        second = self.create_notification(
            title="Second",
        )

        other = self.create_notification(
            recipient=self.admin,
            title="Other",
        )

        updated_count = (
            NotificationService
            .mark_all_as_read(
                recipient=self.member,
            )
        )

        self.assertEqual(
            updated_count,
            2,
        )

        first.refresh_from_db()
        second.refresh_from_db()
        other.refresh_from_db()

        self.assertTrue(first.is_read)
        self.assertTrue(second.is_read)
        self.assertFalse(other.is_read)