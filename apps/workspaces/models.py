from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import TimeStampedModel

import uuid

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

class WorkspaceInvitation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        ACCEPTED = 'accepted', 'پذیرفته‌شده'
        DECLINED = 'declined', 'ردشده'
        EXPIRED = 'expired', 'منقضی‌شده'

    workspace = models.ForeignKey(
        "Workspace",
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_workspace_invitations',
    )
    
    email = models.EmailField()
    
    role = models.CharField(
        max_length=20,
        choices=WorkspaceMembership.Role.choices,
        default=WorkspaceMembership.Role.MEMBER,
    )
    
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    
    expires_at = models.DateTimeField()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('workspace', 'email'),
                condition=models.Q(status="pending"),
                name='unique_pending_workspace_invitation',
            ),
        ]
    
    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
    
    def __str__(self):
        return f"{self.email} → {self.workspace.name}"