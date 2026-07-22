from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q

from apps.columns.models import Column
from apps.core.models import TimeStampedModel
from apps.workspaces.models import (
    WorkspaceMembership,
)

from .constants import (
    TASK_ASSIGNABLE_ROLES,
)

# Create your models here.

class TaskQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            is_archived=False,
        )
    
    def archived(self):
        return self.filter(
            is_archived=True,
        )
    
    def for_column(self, column):
        return self.filter(
            column=column,
        )
    
    def assigned_to(self, user):
        return self.filter(
            assignee=user,
        )

class TaskManager(
    models.Manager.from_queryset(
        TaskQuerySet
    )
):
    def next_position(
        self,
        *,
        column,
    ):
        max_position = (
            self.get_queryset()
            .active()
            .for_column(column)
            .aggregate(
                value=Max('position')
            )['value']
        )
        
        if max_position is None:
            return 0
        
        return max_position + 1
    

class Task(TimeStampedModel):
    class Priority(models.TextChoices):
        LOW = 'low', 'کم'
        MEDIUM = 'medium', 'متوسط'
        HIGH = 'high', 'زیاد'
        URGENT = 'urgent', 'فوری'
    
    class Status(models.TextChoices):
        TODO = 'todo', 'برای انجام'
        IN_PROGRESS = 'in_progress', 'درحال انجام'
        BLOCKED = 'blocked', 'مسدود'
        DONE = 'done', 'انجام‌شده'
        CANCELED = 'canceled', 'لغوشده'
    
    column = models.ForeignKey(
        Column,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    
    title = models.CharField(
        max_length=200,
    )
    
    description = models.TextField(
        blank=True,
        default='',
    )
    
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    
    position = models.PositiveIntegerField()
    
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
    )
    
    due_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    is_archived = models.BooleanField(
        default=False,
    )
    
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    objects = TaskManager()
    
    class Meta:
        ordering = [
            'position',
            'pk',
        ]

        constraints = [
            models.UniqueConstraint(
                fields=(
                    'column',
                    'position',
                ),
                condition=Q(
                    is_archived=False,
                ),
                name='tasks_active_column_pos_unique'
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        is_archived=False,
                        archived_at__isnull=True,
                    )
                    | Q(
                        is_archived=True,
                        archived_at__isnull=False,
                    )
                ),
                name='tasks_archive_state_consistent',
            )
        ]
        
        indexes = [
            models.Index(
                fields=(
                    'column',
                    'is_archived',
                    'position',
                ),
                name='tasks_column_state_pos_idx'
            ),
            models.Index(
                fields=(
                    'assignee',
                    'status',
                    'due_at',
                ),
                name='tasks_assignee_status_due_idx',
            ),
        ]
        
        verbose_name = "وظیفه"
        verbose_name_plural = "وظایف"
    
    def clean(self):
        super().clean()
        
        archive_state_is_invalid = (
            (
                self.is_archived
                and self.archived_at is None
            )
            or (
                not self.is_archived
                and self.archived_at is not None
            )
        )
        
        if archive_state_is_invalid:
            raise ValidationError(
                {
                    'is_archived': (
                        "وضعیت Archive و زمان Archive "
                        "با یکدیگر سازگار نیستند."
                    ),
                }
            )
        
        if(
            not self.assignee_id
            or not self.column_id
        ):
            return
        
        workspace = (
            self.column
            .board
            .workspace
        )
        
        if (
            workspace.owner_id
            == self.assignee_id
        ):
            return
        
        is_assignable_member = (
            WorkspaceMembership.objects
            .filter(
                workspace=workspace,
                user_id=self.assignee_id,
                role__in=TASK_ASSIGNABLE_ROLES,
            )
            .exists()
        )
        
        if not is_assignable_member:
            raise ValidationError(
                {
                    "assignee": (
                        "مسئول Task باید مالک، مدیر "
                        "یا عضو Workspace باشد."
                    ),
                }
            )
    
    
    def __str__(self):
        return self.title
