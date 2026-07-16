from datetime import timedelta

from django.utils import timezone

from apps.workspaces.forms import (
    WorkspaceForm,
    WorkspaceInviteForm,
    WorkspaceMembershipUpdateForm,
)
from apps.workspaces.models import WorkspaceMembership

from apps.workspaces.tests.base import WorkspaceTestBase


class WorkspaceFormTests(WorkspaceTestBase):
    def test_workspace_form_strips_name(self):
        form = WorkspaceForm(
            data={
                "name": "   My Workspace   ",
                "description": "Description",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["name"],
            "My Workspace",
        )

    def test_workspace_form_rejects_short_name(self):
        form = WorkspaceForm(
            data={
                "name": "ab",
                "description": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


class WorkspaceInviteFormTests(WorkspaceTestBase):
    def build_form(
        self,
        *,
        data,
        workspace=None,
        request_user=None,
    ):
        return WorkspaceInviteForm(
            data=data,
            workspace=workspace or self.workspace,
            request_user=request_user or self.owner,
        )

    def test_owner_role_is_not_in_role_choices(self):
        form = WorkspaceInviteForm(
            workspace=self.workspace,
            request_user=self.owner,
        )

        role_values = [
            value
            for value, _label
            in form.fields["role"].choices
        ]

        self.assertNotIn(
            WorkspaceMembership.Role.OWNER,
            role_values,
        )

    def test_valid_invitation_normalizes_email(self):
        form = self.build_form(
            data={
                "email": "  NEW.USER@EXAMPLE.COM ",
                "role": WorkspaceMembership.Role.MEMBER,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["email"],
            "new.user@example.com",
        )

    def test_inviting_yourself_is_invalid(self):
        form = self.build_form(
            data={
                "email": self.owner.email.upper(),
                "role": WorkspaceMembership.Role.MEMBER,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_inviting_existing_member_is_invalid(self):
        form = self.build_form(
            data={
                "email": self.member.email,
                "role": WorkspaceMembership.Role.MEMBER,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_active_pending_invitation_is_invalid(self):
        self.create_invitation(
            email="new-user@example.com",
        )

        form = self.build_form(
            data={
                "email": "new-user@example.com",
                "role": WorkspaceMembership.Role.MEMBER,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_expired_pending_invitation_is_ignored(self):
        self.create_invitation(
            email="new-user@example.com",
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
        )

        form = self.build_form(
            data={
                "email": "new-user@example.com",
                "role": WorkspaceMembership.Role.MEMBER,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_owner_role_submitted_manually_is_invalid(self):
        form = self.build_form(
            data={
                "email": "new-user@example.com",
                "role": WorkspaceMembership.Role.OWNER,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_missing_workspace_context_is_invalid(self):
        form = WorkspaceInviteForm(
            data={
                "email": "new-user@example.com",
                "role": WorkspaceMembership.Role.MEMBER,
            },
            workspace=None,
            request_user=self.owner,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_missing_request_user_context_is_invalid(self):
        form = WorkspaceInviteForm(
            data={
                "email": "new-user@example.com",
                "role": WorkspaceMembership.Role.MEMBER,
            },
            workspace=self.workspace,
            request_user=None,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class WorkspaceMembershipUpdateFormTests(
    WorkspaceTestBase
):
    def test_admin_only_sees_member_and_viewer_roles(self):
        form = WorkspaceMembershipUpdateForm(
            instance=self.member_membership,
            requester_role=WorkspaceMembership.Role.ADMIN,
        )

        role_values = {
            value
            for value, _label
            in form.fields["role"].choices
        }

        self.assertEqual(
            role_values,
            {
                WorkspaceMembership.Role.MEMBER,
                WorkspaceMembership.Role.VIEWER,
            },
        )

    def test_admin_cannot_promote_member_to_admin(self):
        form = WorkspaceMembershipUpdateForm(
            data={
                "role": WorkspaceMembership.Role.ADMIN,
            },
            instance=self.member_membership,
            requester_role=WorkspaceMembership.Role.ADMIN,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_admin_can_change_member_to_viewer(self):
        form = WorkspaceMembershipUpdateForm(
            data={
                "role": WorkspaceMembership.Role.VIEWER,
            },
            instance=self.member_membership,
            requester_role=WorkspaceMembership.Role.ADMIN,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_owner_can_promote_member_to_admin(self):
        form = WorkspaceMembershipUpdateForm(
            data={
                "role": WorkspaceMembership.Role.ADMIN,
            },
            instance=self.member_membership,
            requester_role=WorkspaceMembership.Role.OWNER,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_owner_role_cannot_be_assigned(self):
        form = WorkspaceMembershipUpdateForm(
            data={
                "role": WorkspaceMembership.Role.OWNER,
            },
            instance=self.member_membership,
            requester_role=WorkspaceMembership.Role.OWNER,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)