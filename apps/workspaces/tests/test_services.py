from datetime import timedelta

from django.core import mail
from django.test import (
    RequestFactory,
    override_settings,
)
from django.utils import timezone

from apps.workspaces.models import (
    WorkspaceInvitation,
    WorkspaceMembership,
)
from apps.workspaces.services import (
    accept_workspace_invitation,
    decline_workspace_invitation,
    expire_stale_workspace_invitations,
    send_workspace_invitation_email,
)

from apps.workspaces.tests.base import WorkspaceTestBase


class ExpireInvitationServiceTests(
    WorkspaceTestBase
):
    def test_only_expired_pending_invitations_are_updated(
        self,
    ):
        stale = self.create_invitation(
            email="stale@example.com",
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
        )
        active = self.create_invitation(
            email="active@example.com",
            expires_at=(
                timezone.now()
                + timedelta(days=1)
            ),
        )
        accepted = self.create_invitation(
            email="accepted@example.com",
            status=WorkspaceInvitation.Status.ACCEPTED,
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
        )

        updated_count = (
            expire_stale_workspace_invitations(
                workspace=self.workspace,
            )
        )

        stale.refresh_from_db()
        active.refresh_from_db()
        accepted.refresh_from_db()

        self.assertEqual(updated_count, 1)

        self.assertEqual(
            stale.status,
            WorkspaceInvitation.Status.EXPIRED,
        )
        self.assertEqual(
            active.status,
            WorkspaceInvitation.Status.PENDING,
        )
        self.assertEqual(
            accepted.status,
            WorkspaceInvitation.Status.ACCEPTED,
        )

    def test_expire_service_can_filter_by_email(self):
        target = self.create_invitation(
            email="target@example.com",
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
        )
        untouched = self.create_invitation(
            email="other@example.com",
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
        )

        updated_count = (
            expire_stale_workspace_invitations(
                workspace=self.workspace,
                email=" TARGET@EXAMPLE.COM ",
            )
        )

        target.refresh_from_db()
        untouched.refresh_from_db()

        self.assertEqual(updated_count, 1)
        self.assertEqual(
            target.status,
            WorkspaceInvitation.Status.EXPIRED,
        )
        self.assertEqual(
            untouched.status,
            WorkspaceInvitation.Status.PENDING,
        )


class AcceptInvitationServiceTests(
    WorkspaceTestBase
):
    def test_accept_creates_membership_with_invited_role(
        self,
    ):
        invitation = self.create_invitation(
            role=WorkspaceMembership.Role.VIEWER,
        )

        membership, created = (
            accept_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )
        )

        invitation.refresh_from_db()

        self.assertTrue(created)
        self.assertEqual(
            membership.workspace,
            self.workspace,
        )
        self.assertEqual(
            membership.user,
            self.invited_user,
        )
        self.assertEqual(
            membership.role,
            WorkspaceMembership.Role.VIEWER,
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.ACCEPTED,
        )

    def test_email_comparison_is_case_insensitive(self):
        invitation = self.create_invitation(
            email=self.invited_user.email.upper(),
        )

        membership, created = (
            accept_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )
        )

        self.assertTrue(created)
        self.assertEqual(
            membership.user,
            self.invited_user,
        )

    def test_existing_membership_is_not_duplicated(self):
        invitation = self.create_invitation(
            email=self.member.email,
            role=WorkspaceMembership.Role.VIEWER,
        )

        membership, created = (
            accept_workspace_invitation(
                invitation=invitation,
                user=self.member,
            )
        )

        invitation.refresh_from_db()

        self.assertFalse(created)
        self.assertEqual(
            membership.pk,
            self.member_membership.pk,
        )

        # نقش عضویت موجود نباید بی‌اجازه تغییر کند.
        self.assertEqual(
            membership.role,
            WorkspaceMembership.Role.MEMBER,
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.ACCEPTED,
        )
        self.assertEqual(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=self.member,
            ).count(),
            1,
        )

    def test_wrong_user_cannot_accept_invitation(self):
        invitation = self.create_invitation()

        with self.assertRaises(PermissionError):
            accept_workspace_invitation(
                invitation=invitation,
                user=self.outsider,
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.PENDING,
        )
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=self.outsider,
            ).exists()
        )

    def test_expired_invitation_is_persisted_as_expired(
        self,
    ):
        invitation = self.create_invitation(
            expires_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

        with self.assertRaisesMessage(
            ValueError,
            "این دعوت منقضی شده است.",
        ):
            accept_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.EXPIRED,
        )
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=self.invited_user,
            ).exists()
        )

    def test_archived_workspace_invitation_cannot_be_accepted(
        self,
    ):
        self.workspace.is_archived = True
        self.workspace.save(
            update_fields=["is_archived"],
        )

        invitation = self.create_invitation()

        with self.assertRaisesMessage(
            ValueError,
            "Workspace مربوط به این دعوت آرشیو شده است.",
        ):
            accept_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.PENDING,
        )

    def test_non_pending_invitation_cannot_be_accepted(
        self,
    ):
        invitation = self.create_invitation(
            status=WorkspaceInvitation.Status.DECLINED,
        )

        with self.assertRaisesMessage(
            ValueError,
            "این دعوت دیگر معتبر نیست.",
        ):
            accept_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )


class DeclineInvitationServiceTests(
    WorkspaceTestBase
):
    def test_recipient_can_decline_invitation(self):
        invitation = self.create_invitation()

        returned_invitation = (
            decline_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )
        )

        invitation.refresh_from_db()

        self.assertEqual(
            returned_invitation.pk,
            invitation.pk,
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.DECLINED,
        )

    def test_wrong_user_cannot_decline_invitation(self):
        invitation = self.create_invitation()

        with self.assertRaises(PermissionError):
            decline_workspace_invitation(
                invitation=invitation,
                user=self.outsider,
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.PENDING,
        )

    def test_expired_invitation_is_persisted_as_expired(
        self,
    ):
        invitation = self.create_invitation(
            expires_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

        with self.assertRaisesMessage(
            ValueError,
            "این دعوت منقضی شده است.",
        ):
            decline_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )

        invitation.refresh_from_db()

        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.EXPIRED,
        )

    def test_non_pending_invitation_cannot_be_declined(
        self,
    ):
        invitation = self.create_invitation(
            status=WorkspaceInvitation.Status.ACCEPTED,
        )

        with self.assertRaisesMessage(
            ValueError,
            "این دعوت دیگر معتبر نیست.",
        ):
            decline_workspace_invitation(
                invitation=invitation,
                user=self.invited_user,
            )


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    ALLOWED_HOSTS=["testserver"],
)
class InvitationEmailServiceTests(
    WorkspaceTestBase
):
    def test_send_workspace_invitation_email(self):
        invitation = self.create_invitation()

        request = RequestFactory().get(
            "/",
            HTTP_HOST="testserver",
        )

        send_workspace_invitation_email(
            request,
            invitation,
        )

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            [self.invited_user.email],
        )
        self.assertIn(
            self.workspace.name,
            email.subject,
        )
        self.assertIn(
            str(invitation.token),
            email.body,
        )
        self.assertEqual(
            len(email.alternatives),
            1,
        )