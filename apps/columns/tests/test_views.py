from django.urls import reverse

from apps.boards.models import Board
from apps.columns.models import Column
from apps.workspaces.models import Workspace

from apps.columns.tests.base import ColumnTestBase


class ColumnCreateViewTests(
    ColumnTestBase
):
    def get_url(
        self,
        *,
        workspace=None,
        board=None,
    ):
        return reverse(
            "columns:create",
            kwargs={
                "workspace_pk": (
                    workspace
                    or self.workspace
                ).pk,
                "board_pk": (
                    board
                    or self.board
                ).pk,
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

    def test_owner_admin_and_member_can_open_create(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
        ]

        for user in allowed_users:
            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.get(
                    self.get_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_viewer_cannot_open_create(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_open_create(self):
        self.client.force_login(
            self.outsider
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_valid_post_creates_column(self):
        initial_count = (
            Column.objects.count()
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.get_url(),
            data={
                "title": "در حال انجام",
            },
        )

        self.assertEqual(
            Column.objects.count(),
            initial_count + 1,
        )

        column = Column.objects.get(
            title="در حال انجام",
        )

        self.assertEqual(
            column.board,
            self.board,
        )
        self.assertEqual(
            column.created_by,
            self.member,
        )
        self.assertEqual(
            column.position,
            1,
        )
        self.assertFalse(
            column.is_archived
        )

        self.assertRedirects(
            response,
            reverse(
                "boards:detail",
                kwargs={
                    "workspace_pk": (
                        self.workspace.pk
                    ),
                    "board_pk": (
                        self.board.pk
                    ),
                },
            ),
        )

    def test_title_is_trimmed_when_created(
        self
    ):
        self.client.force_login(
            self.owner
        )

        self.client.post(
            self.get_url(),
            data={
                "title": "  تکمیل‌شده  ",
            },
        )

        self.assertTrue(
            Column.objects.filter(
                board=self.board,
                title="تکمیل‌شده",
            ).exists()
        )

    def test_position_is_assigned_automatically(
        self
    ):
        self.create_column(
            title="در حال انجام",
            position=1,
        )

        self.client.force_login(
            self.owner
        )

        self.client.post(
            self.get_url(),
            data={
                "title": "انجام‌شده",
            },
        )

        column = Column.objects.get(
            board=self.board,
            title="انجام‌شده",
        )

        self.assertEqual(
            column.position,
            2,
        )

    def test_internal_fields_cannot_be_tampered_with(
        self
    ):
        other_workspace = (
            Workspace.objects.create(
                name="Other Workspace",
                owner=self.outsider,
            )
        )

        other_board = Board.objects.create(
            workspace=other_workspace,
            title="Other Board",
            created_by=self.outsider,
        )

        self.client.force_login(
            self.member
        )

        self.client.post(
            self.get_url(),
            data={
                "title": "Secure Column",
                "board": other_board.pk,
                "position": 999,
                "created_by": (
                    self.outsider.pk
                ),
                "is_archived": True,
            },
        )

        column = Column.objects.get(
            title="Secure Column"
        )

        self.assertEqual(
            column.board,
            self.board,
        )
        self.assertEqual(
            column.position,
            1,
        )
        self.assertEqual(
            column.created_by,
            self.member,
        )
        self.assertFalse(
            column.is_archived
        )

    def test_invalid_post_does_not_create_column(
        self
    ):
        initial_count = (
            Column.objects.count()
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.get_url(),
            data={
                "title": "ا",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            Column.objects.count(),
            initial_count,
        )
        self.assertIn(
            "title",
            response.context[
                "form"
            ].errors,
        )

    def test_archived_board_returns_404(self):
        archived_board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url(
                board=archived_board,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_board_from_another_workspace_returns_404(
        self
    ):
        other_workspace = (
            Workspace.objects.create(
                name="Other Workspace",
                owner=self.outsider,
            )
        )

        other_board = Board.objects.create(
            workspace=other_workspace,
            title="Other Board",
            created_by=self.outsider,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url(
                workspace=self.workspace,
                board=other_board,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

class BoardDetailColumnIntegrationTests(
    ColumnTestBase
):
    def get_url(self):
        return reverse(
            "boards:detail",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
            },
        )

    def test_active_columns_are_displayed(self):
        second_column = self.create_column(
            title="در حال انجام",
            position=1,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertContains(
            response,
            self.column.title,
        )
        self.assertContains(
            response,
            second_column.title,
        )

    def test_archived_columns_are_hidden(self):
        archived_column = self.create_column(
            title="ستون آرشیوشده",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertNotContains(
            response,
            archived_column.title,
        )

    def test_columns_follow_position_order(self):
        second_column = self.create_column(
            title="در حال انجام",
            position=1,
        )

        third_column = self.create_column(
            title="انجام‌شده",
            position=2,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.context["columns"],
            [
                self.column,
                second_column,
                third_column,
            ],
        )

    def test_column_count_is_available(self):
        self.create_column(
            title="در حال انجام",
            position=1,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.context[
                "columns_count"
            ],
            2,
        )

    def test_member_sees_create_column_link(self):
        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.get_url()
        )

        create_url = reverse(
            "columns:create",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
            },
        )

        self.assertContains(
            response,
            create_url,
        )

    def test_viewer_does_not_see_create_link(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.get_url()
        )

        create_url = reverse(
            "columns:create",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
            },
        )

        self.assertNotContains(
            response,
            create_url,
        )
        self.assertFalse(
            response.context[
                "can_create_column"
            ]
        )