from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from .models import(
    WorkspaceInvitation,
    WorkspaceMembership,
)

def send_workspace_invitation_email(
    request,
    invitation
) -> None:
    invitation_path = reverse(
        'workspaces:invitation_detail',
        kwargs={
            'token': invitation.token,
        },
    )
    
    invitation_url = request.build_absolute_uri(
        invitation_path
    )
    
    context = {
        "invitation": invitation,
        "workspace": invitation.workspace,
        'invited_by': invitation.invited_by,
        "invitation_url": invitation_url,
    }
    
    text_body = render_to_string(
        "workspaces/emails/invitation_email.txt",
        context,
    )
    
    html_body = render_to_string(
        'workspaces/emails/invitation_email.html',
        context,
    )
    
    email = EmailMultiAlternatives(
        subject=f"دعوت به Workspace {invitation.workspace.name}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.email],
    )
    
    email.attach_alternative(
        html_body,
        'text/html',
    )
    
    email.send()

@transaction.atomic
def accept_workspace_invitation(
    *,
    invitation,
    user
):
    if invitation.status != WorkspaceInvitation.Status.PENDING:
        raise ValueError("این دعوت دیگر معتبر نیست.")
    
    if invitation.expires_at <= timezone.now():
        invitation.status = WorkspaceInvitation.Status.EXPIRED
        invitation.save(update_fields=['status'])
        raise ValueError('این دعوت منقضی شده است.')
    
    if invitation.email.lower() != user.email.lower():
        raise PermissionError(
            'این دعوت برای ایمیل حساب شما ارسال نشده است.'
        )
    
    membership, created = (
        WorkspaceMembership.objects.get_or_create(
            workspace=invitation.workspace,
            user=user,
            defaults={
                'role': invitation.role,
            },
        )
    )
    
    invitation.status = (
        WorkspaceInvitation.Status.ACCEPTED
    )
    invitation.save(update_fields=['status'])
    return membership, created