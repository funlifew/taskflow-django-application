from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.workspaces.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)

from apps.workspaces.tests.base import WorkspaceTestBase


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
)
class WorkspaceViewTests(WorkspaceTestBase):
    def test_guest_is_redirected_from_workspace_list(
        self,
    ):
        url = reverse("workspaces:list")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={url}",
        )

    def test_list_only_contains_accessible_workspaces(
        self,
    ):
        inaccessible = Workspace.objects.create(
            name="Inaccessible",
            owner=self.outsider,
        )
        archived = Workspace.objects.create(
            name="Archived",
            owner=self.owner,
            is_archived=True,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("workspaces:list")
        )

        workspaces = list(
            response.context["workspaces"]
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.workspace, workspaces)
        self.assertNotIn(inaccessible, workspaces)
        self.assertNotIn(archived, workspaces)

    def test_workspace_list_can_search_by_name(self):
        second_workspace = Workspace.objects.create(
            name="Galaxy Project",
            owner=self.owner,
        )
        WorkspaceMembership.objects.create(
            workspace=second_workspace,
            user=self.owner,
            role=WorkspaceMembership.Role.OWNER,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("workspaces:list"),
            {"q": "Galaxy"},
        )

        workspaces = list(
            response.context["workspaces"]
        )

        self.assertEqual(
            workspaces,
            [second_workspace],
        )

    def test_create_workspace_creates_owner_membership(
        self,
    ):
        self.client.force_login(self.outsider)

        response = self.client.post(
            reverse("workspaces:create"),
            {
                "name": "New Workspace",
                "description": "Created by test",
            },
        )

        workspace = Workspace.objects.get(
            name="New Workspace",
        )
        membership = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.outsider,
        )

        self.assertRedirects(
            response,
            reverse(
                "workspaces:detail",
                kwargs={"pk": workspace.pk},
            ),
        )
        self.assertEqual(
            workspace.owner,
            self.outsider,
        )
        self.assertEqual(
            membership.role,
            WorkspaceMembership.Role.OWNER,
        )

    def test_member_can_open_workspace_detail(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse(
                "workspaces:detail",
                kwargs={"pk": self.workspace.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["current_user_role"],
            WorkspaceMembership.Role.MEMBER,
        )

    def test_outsider_cannot_open_workspace_detail(
        self,
    ):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse(
                "workspaces:detail",
                kwargs={"pk": self.workspace.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_only_owner_can_update_workspace(self):
        url = reverse(
            "workspaces:update",
            kwargs={"pk": self.workspace.pk},
        )

        self.client.force_login(self.admin)

        denied_response = self.client.post(
            url,
            {
                "name": "Admin Edit",
                "description": "",
            },
        )

        self.assertEqual(
            denied_response.status_code,
            404,
        )

        self.client.force_login(self.owner)

        allowed_response = self.client.post(
            url,
            {
                "name": "Owner Edit",
                "description": "Updated",
            },
        )

        self.workspace.refresh_from_db()

        self.assertRedirects(
            allowed_response,
            reverse(
                "workspaces:detail",
                kwargs={"pk": self.workspace.pk},
            ),
        )
        self.assertEqual(
            self.workspace.name,
            "Owner Edit",
        )

    def test_only_owner_can_delete_workspace(self):
        url = reverse(
            "workspaces:delete",
            kwargs={"pk": self.workspace.pk},
        )

        self.client.force_login(self.admin)

        denied_response = self.client.post(url)

        self.assertEqual(
            denied_response.status_code,
            404,
        )
        self.assertTrue(
            Workspace.objects.filter(
                pk=self.workspace.pk,
            ).exists()
        )

        self.client.force_login(self.owner)

        allowed_response = self.client.post(url)

        self.assertRedirects(
            allowed_response,
            reverse("workspaces:list"),
        )
        self.assertFalse(
            Workspace.objects.filter(
                pk=self.workspace.pk,
            ).exists()
        )

    def test_member_and_viewer_can_open_members_page(
        self,
    ):
        url = reverse(
            "workspaces:members",
            kwargs={"pk": self.workspace.pk},
        )

        for user in (self.member, self.viewer):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)

                self.assertEqual(
                    response.status_code,
                    200,
                )

    def test_outsider_gets_forbidden_on_members_page(
        self,
    ):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse(
                "workspaces:members",
                kwargs={"pk": self.workspace.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_owner_and_admin_can_open_invite_form(
        self,
    ):
        url = reverse(
            "workspaces:member_invite",
            kwargs={"pk": self.workspace.pk},
        )

        for user in (self.owner, self.admin):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)

                self.assertEqual(
                    response.status_code,
                    200,
                )

    def test_member_cannot_open_invite_form(self):
        self.client.force_login(self.member)

        response = self.client.get(
            reverse(
                "workspaces:member_invite",
                kwargs={"pk": self.workspace.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_invite_post_creates_invitation_and_email(
        self,
    ):
        self.client.force_login(self.admin)

        url = reverse(
            "workspaces:member_invite",
            kwargs={"pk": self.workspace.pk},
        )

        before = timezone.now()

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            response = self.client.post(
                url,
                {
                    "email": self.invited_user.email,
                    "role": (
                        WorkspaceMembership.Role.VIEWER
                    ),
                },
            )

        invitation = (
            WorkspaceInvitation.objects.get(
                workspace=self.workspace,
                email=self.invited_user.email,
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "workspaces:members",
                kwargs={"pk": self.workspace.pk},
            ),
        )
        self.assertEqual(
            invitation.invited_by,
            self.admin,
        )
        self.assertEqual(
            invitation.role,
            WorkspaceMembership.Role.VIEWER,
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.PENDING,
        )
        self.assertGreaterEqual(
            invitation.expires_at,
            (
                before
                + timedelta(days=3)
                - timedelta(seconds=2)
            ),
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_invite_view_expires_stale_invitation(
        self,
    ):
        stale = self.create_invitation(
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
        )

        self.client.force_login(self.owner)

        url = reverse(
            "workspaces:member_invite",
            kwargs={"pk": self.workspace.pk},
        )

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            response = self.client.post(
                url,
                {
                    "email": self.invited_user.email,
                    "role": (
                        WorkspaceMembership.Role.MEMBER
                    ),
                },
            )

        stale.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            stale.status,
            WorkspaceInvitation.Status.EXPIRED,
        )
        self.assertEqual(
            WorkspaceInvitation.objects.filter(
                workspace=self.workspace,
                email=self.invited_user.email,
                status=(
                    WorkspaceInvitation.Status.PENDING
                ),
            ).count(),
            1,
        )

    def test_only_recipient_can_open_invitation_detail(
        self,
    ):
        invitation = self.create_invitation()

        url = reverse(
            "workspaces:invitation_detail",
            kwargs={"token": invitation.token},
        )

        self.client.force_login(self.outsider)
        denied_response = self.client.get(url)

        self.assertEqual(
            denied_response.status_code,
            404,
        )

        self.client.force_login(
            self.invited_user
        )
        allowed_response = self.client.get(url)

        self.assertEqual(
            allowed_response.status_code,
            200,
        )
        self.assertEqual(
            allowed_response.context["invitation"],
            invitation,
        )

    def test_recipient_can_accept_invitation(self):
        invitation = self.create_invitation()

        self.client.force_login(
            self.invited_user
        )

        response = self.client.post(
            reverse(
                "workspaces:invitation_accept",
                kwargs={"token": invitation.token},
            )
        )

        invitation.refresh_from_db()

        self.assertRedirects(
            response,
            reverse(
                "workspaces:detail",
                kwargs={"pk": self.workspace.pk},
            ),
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.ACCEPTED,
        )
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=self.invited_user,
            ).exists()
        )

    def test_wrong_user_cannot_accept_invitation(
        self,
    ):
        invitation = self.create_invitation()

        self.client.force_login(self.outsider)

        response = self.client.post(
            reverse(
                "workspaces:invitation_accept",
                kwargs={"token": invitation.token},
            )
        )

        invitation.refresh_from_db()

        self.assertRedirects(
            response,
            reverse(
                "workspaces:invitation_detail",
                kwargs={"token": invitation.token},
            ),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.PENDING,
        )

    def test_recipient_can_decline_invitation(self):
        invitation = self.create_invitation()

        self.client.force_login(
            self.invited_user
        )

        response = self.client.post(
            reverse(
                "workspaces:invitation_decline",
                kwargs={"token": invitation.token},
            )
        )

        invitation.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("dashboard:dashboard"),
        )
        self.assertEqual(
            invitation.status,
            WorkspaceInvitation.Status.DECLINED,
        )

    def test_owner_can_promote_member_to_admin(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse(
                "workspaces:member_update",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        self.member_membership.pk
                    ),
                },
            ),
            {
                "role": WorkspaceMembership.Role.ADMIN,
            },
        )

        self.member_membership.refresh_from_db()

        self.assertRedirects(
            response,
            reverse(
                "workspaces:members",
                kwargs={"pk": self.workspace.pk},
            ),
        )
        self.assertEqual(
            self.member_membership.role,
            WorkspaceMembership.Role.ADMIN,
        )

    def test_admin_can_change_member_to_viewer(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "workspaces:member_update",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        self.member_membership.pk
                    ),
                },
            ),
            {
                "role": WorkspaceMembership.Role.VIEWER,
            },
        )

        self.member_membership.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.member_membership.role,
            WorkspaceMembership.Role.VIEWER,
        )

    def test_admin_cannot_promote_member_to_admin(
        self,
    ):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "workspaces:member_update",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        self.member_membership.pk
                    ),
                },
            ),
            {
                "role": WorkspaceMembership.Role.ADMIN,
            },
        )

        self.member_membership.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "role",
            response.context["form"].errors,
        )
        self.assertEqual(
            self.member_membership.role,
            WorkspaceMembership.Role.MEMBER,
        )

    def test_admin_cannot_update_another_admin(self):
        second_admin = self.create_user(
            username="second-admin",
            email="second-admin@example.com",
        )
        second_admin_membership = (
            WorkspaceMembership.objects.create(
                workspace=self.workspace,
                user=second_admin,
                role=WorkspaceMembership.Role.ADMIN,
            )
        )

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "workspaces:member_update",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        second_admin_membership.pk
                    ),
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_remove_member(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse(
                "workspaces:member_remove",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        self.member_membership.pk
                    ),
                },
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "workspaces:members",
                kwargs={"pk": self.workspace.pk},
            ),
        )
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                pk=self.member_membership.pk,
            ).exists()
        )

    def test_admin_can_remove_member(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "workspaces:member_remove",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        self.member_membership.pk
                    ),
                },
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                pk=self.member_membership.pk,
            ).exists()
        )

    def test_admin_cannot_remove_another_admin(self):
        second_admin = self.create_user(
            username="remove-admin",
            email="remove-admin@example.com",
        )
        second_admin_membership = (
            WorkspaceMembership.objects.create(
                workspace=self.workspace,
                user=second_admin,
                role=WorkspaceMembership.Role.ADMIN,
            )
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "workspaces:member_remove",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        second_admin_membership.pk
                    ),
                },
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                pk=second_admin_membership.pk,
            ).exists()
        )

    def test_owner_membership_cannot_be_removed(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse(
                "workspaces:member_remove",
                kwargs={
                    "pk": self.workspace.pk,
                    "membership_pk": (
                        self.owner_membership.pk
                    ),
                },
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                pk=self.owner_membership.pk,
            ).exists()
        )

    def test_archived_workspace_is_not_accessible(
        self,
    ):
        self.workspace.is_archived = True
        self.workspace.save(
            update_fields=["is_archived"],
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            reverse(
                "workspaces:members",
                kwargs={"pk": self.workspace.pk},
            )
        )

        self.assertEqual(response.status_code, 404)