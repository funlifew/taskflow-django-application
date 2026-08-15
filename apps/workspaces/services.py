import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from apps.notifications.services import (
    WorkspaceNotificationService,
)

from apps.dashboard.cache import (
    schedule_dashboard_cache_invalidation,
)

from .models import(
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)

from apps.core.emailing import (
    EmailDeliveryError,
    TemplatedEmail,
    send_templated_email,
)

logger = logging.getLogger(
    __name__
)

WORKSPACE_INVITATION_LIFETIME = timedelta(days=3)

@transaction.atomic
def create_workspace(
    *,
    owner,
    name,
    description="",
):
    workspace = Workspace.objects.create(
        owner=owner,
        name=name,
        description=description,
        is_archived=False,
    )
    
    WorkspaceMembership.objects.create(
        workspace=workspace,
        user=owner,
        role=WorkspaceMembership.Role.OWNER,
    )
    
    schedule_dashboard_cache_invalidation(
        user_ids=(
            owner.pk,
        ),
    )
    
    return workspace

@transaction.atomic
def create_workspace_invitation(
    *,
    request,
    workspace,
    invited_by,
    email,
    role,
):
    if role == WorkspaceMembership.Role.OWNER:
        raise ValueError(
            "نمی‌توان کاربر را با نقش مالک دعوت کرد."
        )
    
    invitation = WorkspaceInvitation.objects.create(
        workspace=workspace,
        invited_by=invited_by,
        email=email.strip().lower(),
        role=role,
        status=WorkspaceInvitation.Status.PENDING,
        expires_at=(
            timezone.now()
            + WORKSPACE_INVITATION_LIFETIME
        ),
    )
    
    WorkspaceNotificationService.notify_invitation(
        invitation=invitation,
        actor=invited_by,
    )
    
    transaction.on_commit(
    lambda invitation_id=invitation.pk: (
        send_workspace_invitation_email_safely(
            request=request,
            invitation_id=(
                invitation_id
            ),
        )
    )
)
    
    return invitation

@transaction.atomic
def update_workspace_membership_role(
    *,
    workspace,
    membership,
    requester_role,
    new_role,
    actor=None,
):
    locked_membership = (
        WorkspaceMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "workspace",
        )
        .get(
            pk=membership.pk,
            workspace=workspace,
        )
    )

    if (
        locked_membership.role
        == WorkspaceMembership.Role.OWNER
    ):
        raise PermissionError(
            "نقش مالک از این بخش "
            "قابل تغییر نیست."
        )

    if (
        new_role
        == WorkspaceMembership.Role.OWNER
    ):
        raise PermissionError(
            "انتقال مالکیت باید "
            "از بخش جداگانه انجام شود."
        )

    if (
        requester_role
        == WorkspaceMembership.Role.ADMIN
    ):
        if (
            locked_membership.role
            == WorkspaceMembership.Role.ADMIN
        ):
            raise PermissionError(
                "مدیر نمی‌تواند نقش "
                "مدیر دیگری را تغییر دهد."
            )

        if (
            new_role
            == WorkspaceMembership.Role.ADMIN
        ):
            raise PermissionError(
                "فقط مالک Workspace "
                "می‌تواند نقش مدیر بدهد."
            )

    if (
        locked_membership.role
        == new_role
    ):
        return locked_membership

    old_role = locked_membership.role

    locked_membership.role = new_role

    locked_membership.save(
        update_fields=[
            "role",
            "updated_at",
        ]
    )

    (
        WorkspaceNotificationService
        .notify_role_change(
            membership=locked_membership,
            actor=actor,
            old_role=old_role,
        )
    )

    return locked_membership

@transaction.atomic
def remove_workspace_membership(
    *,
    workspace,
    membership,
    requester_role,
    actor=None,
):
    locked_membership = (
        WorkspaceMembership.objects
        .select_for_update()
        .select_related(
            "user",
            "workspace",
        )
        .get(
            pk=membership.pk,
            workspace=workspace,
        )
    )

    if (
        locked_membership.role
        == WorkspaceMembership.Role.OWNER
    ):
        raise PermissionError(
            "مالک Workspace قابل حذف نیست."
        )

    if (
        requester_role
        == WorkspaceMembership.Role.ADMIN
        and locked_membership.role
        == WorkspaceMembership.Role.ADMIN
    ):
        raise PermissionError(
            "مدیر نمی‌تواند "
            "مدیر دیگری را حذف کند."
        )

    recipient = locked_membership.user
    old_role = locked_membership.role

    member_name = (
        recipient.get_full_name()
        or recipient.username
    )

    locked_membership.delete()

    (
        WorkspaceNotificationService
        .notify_removal(
            recipient=recipient,
            workspace=workspace,
            actor=actor,
            old_role=old_role,
        )
    )

    schedule_dashboard_cache_invalidation(
        user_ids=(
            recipient.pk,
        ),
    )
    
    return member_name

def send_workspace_invitation_email(
    request,
    invitation,
) -> None:
    invitation_path = reverse(
        (
            "workspaces:"
            "invitation_detail"
        ),
        kwargs={
            "token": (
                invitation.token
            ),
        },
    )

    invitation_url = (
        request.build_absolute_uri(
            invitation_path
        )
    )

    context = {
        "invitation": (
            invitation
        ),
        "workspace": (
            invitation.workspace
        ),
        "invited_by": (
            invitation.invited_by
        ),
        "invitation_url": (
            invitation_url
        ),
    }

    send_templated_email(
        TemplatedEmail(
            category=(
                "workspace_invitation"
            ),
            subject_template=(
                "workspaces/emails/"
                "invitation_subject.txt"
            ),
            text_template=(
                "workspaces/emails/"
                "invitation_email.txt"
            ),
            html_template=(
                "workspaces/emails/"
                "invitation_email.html"
            ),
            recipients=(
                invitation.email,
            ),
            context=context,
        )
    )


def send_workspace_invitation_email_safely(
    *,
    request,
    invitation_id,
) -> bool:
    invitation = (
        WorkspaceInvitation.objects
        .select_related(
            "workspace",
            "invited_by",
        )
        .filter(
            pk=invitation_id
        )
        .first()
    )

    if invitation is None:
        logger.warning(
            (
                "Workspace invitation "
                "email skipped because "
                "invitation no longer "
                "exists. invitation_id=%s"
            ),
            invitation_id,
        )

        return False

    try:
        send_workspace_invitation_email(
            request,
            invitation,
        )

    except EmailDeliveryError:
        # Already logged by the
        # central email gateway.
        return False

    except Exception:
        logger.exception(
            (
                "Unexpected workspace "
                "invitation email failure. "
                "invitation_id=%s"
            ),
            invitation_id,
        )

        return False

    return True

def expire_stale_workspace_invitations(
    *,
    workspace=None,
    email=None
) -> int:
    invitations = WorkspaceInvitation.objects.filter(
        status=WorkspaceInvitation.Status.PENDING,
        expires_at__lte=timezone.now(),
    )
    
    if workspace is not None:
        invitations = invitations.filter(
            workspace=workspace,
        )
    
    if email:
        invitations = invitations.filter(
            email__iexact=email.strip(),
        )
        
    return invitations.update(
        status=WorkspaceInvitation.Status.EXPIRED
    )

def accept_workspace_invitation(
    *,
    invitation,
    user,
):
    membership = None
    created = False
    invitation_expired = False

    with transaction.atomic():
        locked_invitation = (
            WorkspaceInvitation.objects
            .select_for_update()
            .select_related("workspace")
            .get(pk=invitation.pk)
        )

        if (
            locked_invitation.status
            != WorkspaceInvitation.Status.PENDING
        ):
            raise ValueError(
                "این دعوت دیگر معتبر نیست."
            )

        if locked_invitation.workspace.is_archived:
            raise ValueError(
                "Workspace مربوط به این دعوت آرشیو شده است."
            )

        if (
            locked_invitation.email.casefold()
            != user.email.casefold()
        ):
            raise PermissionError(
                "این دعوت برای ایمیل حساب شما ارسال نشده است."
            )

        if locked_invitation.expires_at <= timezone.now():
            locked_invitation.status = (
                WorkspaceInvitation.Status.EXPIRED
            )
            locked_invitation.save(
                update_fields=["status"],
            )

            invitation_expired = True

        else:
            membership, created = (
                WorkspaceMembership.objects.get_or_create(
                    workspace=locked_invitation.workspace,
                    user=user,
                    defaults={
                        "role": locked_invitation.role,
                    },
                )
            )

            locked_invitation.status = (
                WorkspaceInvitation.Status.ACCEPTED
            )
            locked_invitation.save(
                update_fields=["status"],
            )
    if invitation_expired:
        raise ValueError(
            "این دعوت منقضی شده است."
        )

    if created:
        schedule_dashboard_cache_invalidation(
            user_ids=(
                user.pk,
            ),
        )
    
    return membership, created

def decline_workspace_invitation(
    *,
    invitation,
    user,
):
    invitation_expired = False

    with transaction.atomic():
        locked_invitation = (
            WorkspaceInvitation.objects
            .select_for_update()
            .select_related("workspace")
            .get(pk=invitation.pk)
        )

        if (
            locked_invitation.status
            != WorkspaceInvitation.Status.PENDING
        ):
            raise ValueError(
                "این دعوت دیگر معتبر نیست."
            )

        if (
            locked_invitation.email.casefold()
            != user.email.casefold()
        ):
            raise PermissionError(
                "این دعوت برای ایمیل حساب شما ارسال نشده است."
            )

        if locked_invitation.expires_at <= timezone.now():
            locked_invitation.status = (
                WorkspaceInvitation.Status.EXPIRED
            )
            locked_invitation.save(
                update_fields=["status"],
            )

            invitation_expired = True

        else:
            locked_invitation.status = (
                WorkspaceInvitation.Status.DECLINED
            )
            locked_invitation.save(
                update_fields=["status"],
            )

    if invitation_expired:
        raise ValueError(
            "این دعوت منقضی شده است."
        )

    return locked_invitation