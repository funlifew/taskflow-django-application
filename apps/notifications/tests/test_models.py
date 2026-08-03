from django.core.exceptions import (
    ValidationError,
)
from django.utils import timezone

from apps.notifications.models import (
    Notification,
)
from apps.notifications.tests.base import (
    NotificationTestBase,
)


class NotificationModelTests(
    NotificationTestBase
):
    def test_notification_is_unread_by_default(
        self,
    ):
        notification = Notification(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="Assigned",
        )

        self.assertFalse(
            notification.is_read
        )
        self.assertIsNone(
            notification.read_at
        )

    def test_metadata_must_be_dict(self):
        notification = Notification(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="Assigned",
            metadata=[],
        )

        with self.assertRaises(
            ValidationError
        ):
            notification.full_clean()

    def test_unread_notification_cannot_have_read_at(
        self,
    ):
        notification = Notification(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="Assigned",
            is_read=False,
            read_at=timezone.now(),
        )

        with self.assertRaises(
            ValidationError
        ):
            notification.full_clean()

    def test_read_notification_requires_read_at(
        self,
    ):
        notification = Notification(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="Assigned",
            is_read=True,
            read_at=None,
        )

        with self.assertRaises(
            ValidationError
        ):
            notification.full_clean()

    def test_deleting_actor_preserves_notification(
        self,
    ):
        actor = self.create_user(
            username="deleted-actor",
            email=(
                "deleted-actor@example.com"
            ),
        )

        notification = (
            self.create_notification(
                actor=actor,
            )
        )

        actor.delete()

        notification.refresh_from_db()

        self.assertIsNone(
            notification.actor
        )

    def test_deleting_recipient_deletes_notification(
        self,
    ):
        recipient = self.create_user(
            username="deleted-recipient",
            email=(
                "deleted-recipient@example.com"
            ),
        )

        notification = (
            self.create_notification(
                recipient=recipient,
            )
        )

        notification_pk = notification.pk

        recipient.delete()

        self.assertFalse(
            Notification.objects.filter(
                pk=notification_pk,
            ).exists()
        )