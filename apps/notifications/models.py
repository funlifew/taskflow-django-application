from django.conf import settings
from django.core.exceptions import (
    ValidationError,
)


from django.db import models
from django.db.models import Q

from apps.core.models import (
    TimeStampedModel,
)

# Create your models here.

class NotificationQueryset(models.QuerySet):
    def for_recipient(
        self,
        recipient,
    ):
        return self.filter(
            recipient=recipient,
        )
    
    def unread(self):
        return self.filter(
            is_read=False,
        )
    
    def read(self):
        return self.filter(
            is_read=True,
        )

class NotificationManager(
    models.Manager.from_queryset(
        NotificationQueryset
    )
):
    pass

class Notification(TimeStampedModel):
    
    class Type(models.TextChoices):
        TASK_ASSIGNED = (
            "task_assigned",
            "واگذاری Task",
        )

        TASK_REASSIGNED = (
            "task_reassigned",
            "تغییر مسئول Task",
        )

        TASK_STATUS_CHANGED = (
            "task_status_changed",
            "تغییر وضعیت Task",
        )

        TASK_COMMENTED = (
            "task_commented",
            "دیدگاه جدید Task",
        )

        WORKSPACE_INVITED = (
            "workspace_invited",
            "دعوت به Workspace",
        )

        WORKSPACE_ROLE_CHANGED = (
            "workspace_role_changed",
            "تغییر نقش Workspace",
        )

        WORKSPACE_REMOVED = (
            "workspace_removed",
            "حذف از Workspace",
        )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            'created_notifications'
        ),
    )
    
    notification_type = (
        models.CharField(
            max_length=40,
            choices=Type.choices,
        )
    )
    
    title = models.CharField(
        max_length=200,
    )
    
    message = models.TextField(
        blank=True,
        default="",
    )
    
    target_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    
    is_read = models.BooleanField(
        default=False,
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    objects = NotificationManager()

    class Meta:
        ordering = (
            '-created_at',
            '-pk',
        )

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        is_read=False,
                        read_at__isnull=True,
                    )
                    | Q(
                        is_read=True,
                        read_at__isnull=False,
                    )
                ),
                name='notification_read_state_consistent',
            )
        ]
        
        indexes = [
            models.Index(
                fields=(
                    'recipient',
                    'is_read',
                    '-created_at',
                ),
                name='notif_rec_read_created_idx',
            ),
            models.Index(
                fields=(
                    'recipient',
                    'notification_type',
                    '-created_at',
                ),
                name='notif_rec_type_created_idx',
            ),
        ]
        
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
    
    
    def clean(self):
        super().clean()

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise ValidationError(
                {
                    "metadata": (
                        "Metadata اعلان باید "
                        "یک JSON object باشد."
                    ),
                }
            )
        
        read_state_is_invalid = (
            self.is_read
            != (
                self.read_at
                is not None
            )
        )
        
        if read_state_is_invalid:
            raise ValidationError(
                {
                    "is_read": (
                        "وضعیت خوانده‌شدن "
                        "و زمان خوانده‌شدن "
                        "با یکدیگر سازگار نیستند."
                    ),
                }
            )
    
    def __str__(self):
        return (
            f"{self.recipient.username}: "
            f"{self.title}"
        )