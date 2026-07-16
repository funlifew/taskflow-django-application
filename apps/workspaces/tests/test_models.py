from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.workspaces.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)

from apps.workspaces.tests.base import WorkspaceTestBase


class WorkspaceModelTests(WorkspaceTestBase):
    def test_workspace_string_representation(self):
        self.assertEqual(
            str(self.workspace),
            "TaskFlow",
        )

    def test_membership_string_representation(self):
        self.assertEqual(
            str(self.member_membership),
            "member - TaskFlow",
        )

    def test_invitation_string_representation(self):
        invitation = self.create_invitation()

        self.assertEqual(
            str(invitation),
            "invited@example.com → TaskFlow",
        )

    def test_workspace_membership_is_unique_per_user(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkspaceMembership.objects.create(
                    workspace=self.workspace,
                    user=self.member,
                    role=WorkspaceMembership.Role.VIEWER,
                )

    def test_pending_invitation_is_unique_per_workspace_and_email(
        self,
    ):
        self.create_invitation()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_invitation()

    def test_non_pending_invitation_does_not_block_new_pending(
        self,
    ):
        self.create_invitation(
            status=WorkspaceInvitation.Status.DECLINED,
        )

        pending_invitation = self.create_invitation()

        self.assertEqual(
            pending_invitation.status,
            WorkspaceInvitation.Status.PENDING,
        )

    def test_is_expired_returns_true_for_past_date(self):
        invitation = self.create_invitation(
            expires_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

        self.assertTrue(invitation.is_expired)

    def test_is_expired_returns_false_for_future_date(self):
        invitation = self.create_invitation(
            expires_at=(
                timezone.now()
                + timedelta(days=1)
            ),
        )

        self.assertFalse(invitation.is_expired)

    def test_membership_default_role_is_member(self):
        second_workspace = Workspace.objects.create(
            name="Second Workspace",
            owner=self.owner,
        )

        membership = WorkspaceMembership.objects.create(
            workspace=second_workspace,
            user=self.outsider,
        )

        self.assertEqual(
            membership.role,
            WorkspaceMembership.Role.MEMBER,
        )