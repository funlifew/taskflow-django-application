from django.urls import reverse

from apps.boards.models import Board
from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
)

from apps.boards.tests.base import BoardTestBase


class BoardListViewTests(BoardTestBase):
    def get_url(self):
        return reverse(
            "boards:list",
            kwargs={
                "workspace_pk": self.workspace.pk,
            },
        )

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_workspace_members_can_view_board_list(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
            self.viewer,
        ]

        for user in allowed_users:
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(
                    self.get_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_outsider_cannot_view_board_list(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_list_contains_active_board(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url()
        )

        self.assertContains(
            response,
            self.board.title,
        )

    def test_archived_board_is_not_displayed(self):
        archived_board = self.create_board(
            title="Archived Secret Board",
            is_archived=True,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url()
        )

        self.assertNotContains(
            response,
            archived_board.title,
        )

    def test_board_from_other_workspace_is_not_displayed(
        self
    ):
        other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=self.outsider,
        )

        WorkspaceMembership.objects.create(
            workspace=other_workspace,
            user=self.outsider,
            role=WorkspaceMembership.Role.OWNER,
        )

        other_board = self.create_board(
            workspace=other_workspace,
            title="Other Workspace Board",
            created_by=self.outsider,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url()
        )

        self.assertNotContains(
            response,
            other_board.title,
        )

    def test_member_can_create_board_context(self):
        self.client.force_login(self.member)

        response = self.client.get(
            self.get_url()
        )

        self.assertTrue(
            response.context["can_create_board"]
        )

    def test_viewer_cannot_create_board_context(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            self.get_url()
        )

        self.assertFalse(
            response.context["can_create_board"]
        )

    def test_archived_workspace_returns_404(self):
        self.workspace.is_archived = True
        self.workspace.save(
            update_fields=[
                "is_archived",
                "updated_at",
            ]
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class BoardCreateViewTests(BoardTestBase):
    def get_url(self):
        return reverse(
            "boards:create",
            kwargs={
                "workspace_pk": self.workspace.pk,
            },
        )

    def test_owner_admin_and_member_can_open_create_page(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
        ]

        for user in allowed_users:
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(
                    self.get_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_viewer_cannot_open_create_page(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_open_create_page(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_valid_post_creates_board(self):
        self.client.force_login(self.member)

        response = self.client.post(
            self.get_url(),
            data={
                "title": "API Development",
                "description": (
                    "Backend API tasks"
                ),
            },
        )

        board = Board.objects.get(
            title="API Development"
        )

        self.assertEqual(
            board.workspace,
            self.workspace,
        )
        self.assertEqual(
            board.created_by,
            self.member,
        )
        self.assertFalse(
            board.is_archived
        )

        self.assertRedirects(
            response,
            reverse(
                "boards:list",
                kwargs={
                    "workspace_pk": (
                        self.workspace.pk
                    ),
                },
            ),
        )

    def test_internal_fields_cannot_be_tampered_with(
        self
    ):
        other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=self.outsider,
        )

        self.client.force_login(self.member)

        self.client.post(
            self.get_url(),
            data={
                "title": "Secure Board",
                "description": "",
                "workspace": other_workspace.pk,
                "created_by": self.outsider.pk,
                "is_archived": True,
            },
        )

        board = Board.objects.get(
            title="Secure Board"
        )

        self.assertEqual(
            board.workspace,
            self.workspace,
        )
        self.assertEqual(
            board.created_by,
            self.member,
        )
        self.assertFalse(
            board.is_archived
        )

    def test_invalid_post_does_not_create_board(self):
        self.client.force_login(self.owner)

        initial_count = Board.objects.count()

        response = self.client.post(
            self.get_url(),
            data={
                "title": "ab",
                "description": "",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            Board.objects.count(),
            initial_count,
        )
        self.assertIn(
            "title",
            response.context["form"].errors,
        )

    def test_archived_workspace_returns_404(self):
        self.workspace.is_archived = True
        self.workspace.save(
            update_fields=[
                "is_archived",
                "updated_at",
            ]
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )