from django.contrib.auth import (
    get_user_model,
)
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
)
from django.urls import reverse
from django.utils import timezone

from .models import Notification

User = get_user_model()

class NotificationService:
    @staticmethod
    def create(
        *,
        recipient,
        actor,
        notification_type,
        title,
        message="",
        target_url="",
        metadata=None,
    ):
        if recipient is None:
            return None
        
        if (
            actor is not None
            and actor.pk == recipient.pk
        ):
            return None
        
        if metadata is None:
            metadata = {}

        notification = Notification(
            recipient=recipient,
            actor=actor,
            notification_type=notification_type,
            title=title,
            message=message,
            target_url=target_url,
            metadata=metadata,
            is_read=False,
            read_at=None,
        )
        
        notification.full_clean()

        notification.save(
            force_insert=True,
        )
        
        return notification
    
    @classmethod
    def create_for_recipients(
        cls,
        *,
        recipients,
        actor,
        notification_type,
        title,
        message="",
        target_url="",
        metadata=None,
    ):
        unique_recipients = {}

        for recipient in recipients:
            if (
                recipient is None
                or recipient.pk is None
            ):
                continue
            
            unique_recipients[recipient.pk] = recipient
        
        notifications = []

        for recipient in (
            unique_recipients.values()
        ):
            notification = cls.create(
                recipient=recipient,
                actor=actor,
                notification_type=notification_type,
                title=title,
                message=message,
                target_url=target_url,
                metadata=metadata,
            )
            
            if notification is not None:
                notifications.append(
                    notification
                )
        
        return notifications
    
    @staticmethod
    @transaction.atomic
    def mark_as_read(
        *,
        recipient,
        notification_pk,
    ):
        notification = get_object_or_404(
            Notification.objects
            .select_for_update()
            .select_related(
                'recipient',
                'actor',
            ),
            pk=notification_pk,
            recipient=recipient,
        )
        
        if notification.is_read:
            return notification, False
        
        now = timezone.now()

        notification.is_read = True
        notification.read_at = now
        notification.updated_at = now
        
        notification.full_clean()

        notification.save(
            update_fields=[
                'is_read',
                'read_at',
                'updated_at',
            ]
        )
        
        return notification, True
    
    @staticmethod
    @transaction.atomic
    def mark_all_as_read(
        *,
        recipient,
    ):
        now = timezone.now()

        return (
            Notification.objects
            .for_recipient(recipient)
            .unread()
            .update(
                is_read=True,
                read_at=now,
                updated_at=now,
            )
        )

class TaskNotificationService:
    @staticmethod
    def _get_task_target_url(
        task,
    ):
        column = task.column
        board = column.board
        
        return reverse(
            'tasks:detail',
            kwargs={
                'workspace_pk': board.workspace_id,
                'board_pk': board.pk,
                'column_pk': column.pk,
                'task_pk': task.pk,
            },
        )
    
    @staticmethod
    def _get_user_label(user):
        if user is None:
            return 'سیستم'
        
        full_name = user.get_full_name().strip()

        return (
            full_name
            or user.username
        )
    
    @classmethod
    def notify_assignment(
        cls,
        *,
        task,
        actor,
        previous_assignee,
    ):
        if task.assignee is None:
            return None
        
        is_reassignment = previous_assignee is not None
        
        if is_reassignment:
            notification_type = (
                Notification.Type
                .TASK_REASSIGNED
            )
            
            title = (
                "مسئولیت یک Task "
                "به شما منتقل شد"
            )
        else:
            notification_type = (
                Notification.Type
                .TASK_ASSIGNED
            )

            title = (
                "یک Task به شما "
                "واگذار شد"
            )
        
        actor_label = cls._get_user_label(actor)

        return (
            NotificationService.create(
                recipient=task.assignee,
                actor=actor,
                notification_type=notification_type,
                title=title,
                message=(
                    f"{actor_label}، Task "
                    f"«{task.title}» را "
                    "به شما واگذار کرد."
                ),
                target_url=cls._get_task_target_url(task),
                metadata={
                    "workspace_id": (
                        task
                        .column
                        .board
                        .workspace_id
                    ),
                    "board_id": (
                        task.column.board_id
                    ),
                    "column_id": (
                        task.column_id
                    ),
                    "task_id": task.pk,
                    "previous_assignee_id": (
                        previous_assignee.pk
                        if (
                            previous_assignee
                            is not None
                        )
                        else None
                    ),
                    "new_assignee_id": (
                        task.assignee_id
                    ),
                },
            )
        )
    
    @classmethod
    def notify_status_change(
        cls,
        *,
        task,
        actor,
        old_status,
        old_status_label,
        new_status_label,
    ):
        if task.assignee is None:
            return None
        
        actor_label = cls._get_user_label(actor)

        return (
            NotificationService.create(
                recipient=task.assignee,
                actor=actor,
                notification_type=(
                    Notification.Type
                    .TASK_STATUS_CHANGED
                ),
                title=(
                    "وضعیت Task تغییر کرد"
                ),
                message=(
                    f"{actor_label} وضعیت "
                    f"Task «{task.title}» را "
                    f"از «{old_status_label}» "
                    f"به «{new_status_label}» "
                    "تغییر داد."
                ),
                target_url=(
                    cls._get_task_target_url(
                        task
                    )
                ),
                metadata={
                    "workspace_id": (
                        task
                        .column
                        .board
                        .workspace_id
                    ),
                    "board_id": (
                        task.column.board_id
                    ),
                    "column_id": (
                        task.column_id
                    ),
                    "task_id": task.pk,
                    "old_status": old_status,
                    "new_status": task.status,
                    "old_status_label": (
                        old_status_label
                    ),
                    "new_status_label": (
                        new_status_label
                    ),
                },
            )
        )
    
    @classmethod
    def notify_comment(
        cls,
        *,
        task,
        comment,
        actor,
    ):
        recipients = (
            task.assignee,
            task.created_by,
        )
        
        actor_label = cls._get_user_label(actor)

        return (
            NotificationService
            .create_for_recipients(
                recipients=recipients,
                actor=actor,
                notification_type=(
                    Notification.Type
                    .TASK_COMMENTED
                ),
                title=(
                    "دیدگاه جدید روی Task"
                ),
                message=(
                    f"{actor_label} روی Task "
                    f"«{task.title}» "
                    "دیدگاه جدیدی ثبت کرد."
                ),
                target_url=(
                    cls._get_task_target_url(
                        task
                    )
                ),
                metadata={
                    "workspace_id": (
                        task
                        .column
                        .board
                        .workspace_id
                    ),
                    "board_id": (
                        task.column.board_id
                    ),
                    "column_id": (
                        task.column_id
                    ),
                    "task_id": task.pk,
                    "comment_id": (
                        comment.pk
                    ),
                },
            )
        )
    

class WorkspaceNotificationService:
    @staticmethod
    def _get_user_label(user):
        if user is None:
            return 'سیستم'
        
        full_name = user.get_full_name().strip()

        return (
            full_name
            or user.username
        )
    
    @staticmethod
    def _get_workspace_target_url(
        workspace,
    ):
        return reverse(
            'workspaces:detail',
            kwargs={
                'pk': workspace.pk,
            },
        )
    
    @classmethod
    def notify_invitation(
        cls,
        *,
        invitation,
        actor,
    ):
        recipient = (
            User.objects
            .filter(
                email__iexact=invitation.email,
                is_active=True,
            )
            .first()
        )
        
        if recipient is None:
            return None
        
        actor_label = cls._get_user_label(actor)

        return (
            NotificationService.create(
                recipient=recipient,
                actor=actor,
                notification_type=(
                    Notification.Type
                    .WORKSPACE_INVITED
                ),
                title=(
                    "دعوت جدید به Workspace"
                ),
                message=(
                    f"{actor_label} شما را "
                    f"به Workspace "
                    f"«{invitation.workspace.name}» "
                    "دعوت کرد."
                ),
                target_url=reverse(
                    (
                        "workspaces:"
                        "invitation_detail"
                    ),
                    kwargs={
                        "token": (
                            invitation.token
                        ),
                    },
                ),
                metadata={
                    "workspace_id": (
                        invitation.workspace_id
                    ),
                    "invitation_id": (
                        invitation.pk
                    ),
                    "invitation_token": str(
                        invitation.token
                    ),
                    "role": invitation.role,
                },
            )
        )
    
    @classmethod
    def notify_role_change(
        cls,
        *,
        membership,
        actor,
        old_role,
    ):
        actor_label = cls._get_user_label(actor)

        return (
            NotificationService.create(
                recipient=membership.user,
                actor=actor,
                notification_type=(
                    Notification.Type
                    .WORKSPACE_ROLE_CHANGED
                ),
                title=(
                    "نقش شما تغییر کرد"
                ),
                message=(
                    f"{actor_label} نقش شما "
                    f"در Workspace "
                    f"«{membership.workspace.name}» "
                    "را تغییر داد."
                ),
                target_url=(
                    cls
                    ._get_workspace_target_url(
                        membership.workspace
                    )
                ),
                metadata={
                    "workspace_id": (
                        membership.workspace_id
                    ),
                    "membership_id": (
                        membership.pk
                    ),
                    "old_role": old_role,
                    "new_role": (
                        membership.role
                    ),
                    "new_role_label": str(
                        membership
                        .get_role_display()
                    ),
                },
            )
        )
    
    @classmethod
    def notify_removal(
        cls,
        *,
        recipient,
        workspace,
        actor,
        old_role,
    ):
        actor_label = (
            cls._get_user_label(actor)
        )

        return (
            NotificationService.create(
                recipient=recipient,
                actor=actor,
                notification_type=(
                    Notification.Type
                    .WORKSPACE_REMOVED
                ),
                title=(
                    "عضویت شما حذف شد"
                ),
                message=(
                    f"{actor_label} عضویت شما "
                    f"در Workspace "
                    f"«{workspace.name}» "
                    "را حذف کرد."
                ),
                target_url=reverse(
                    "workspaces:list",
                ),
                metadata={
                    "workspace_id": (
                        workspace.pk
                    ),
                    "workspace_name": (
                        workspace.name
                    ),
                    "old_role": old_role,
                },
            )
        )