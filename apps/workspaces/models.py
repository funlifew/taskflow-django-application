from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel

# Create your models here.

class Workspace(TimeStampedModel):
    name = models.CharField(
        max_length=150,
    )
    description = models.TextField(
        blank=True,
        default='',
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_workspaces',
    )
    is_archived = models.BooleanField(
        default=False,
    )
    
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='WorkspaceMembership',
        related_name='workspaces',
    )
    
    def __str__(self):
        return self.name
    
class WorkspaceMembership(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = 'owner', 'مالک'
        ADMIN = 'admin', 'مدیر'
        MEMBER = 'member', 'عضو'
        VIEWER = 'viewer', 'مشاهده‌گر'
    
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('workspace', 'user'),
                name='unique_workspace_membership',
            ),
        ]
    
    def __str__(self):
        return (
            f'{self.user.username} - '
            f'{self.workspace.name}'
        )