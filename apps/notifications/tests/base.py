from apps.notifications.models import (
    Notification,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)


class NotificationTestBase(
    TaskTestBase
):
    def create_notification(
        self,
        *,
        recipient=None,
        actor=None,
        notification_type=(
            Notification.Type
            .TASK_ASSIGNED
        ),
        title="اعلان آزمایشی",
        message="متن اعلان",
        target_url="/dashboard/",
        metadata=None,
        is_read=False,
        read_at=None,
    ):
        if recipient is None:
            recipient = self.member

        if actor is None:
            actor = self.owner

        if metadata is None:
            metadata = {}

        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            notification_type=(
                notification_type
            ),
            title=title,
            message=message,
            target_url=target_url,
            metadata=metadata,
            is_read=is_read,
            read_at=read_at,
        )