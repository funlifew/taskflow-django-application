from django.urls import reverse

from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
)

from apps.boards.tests.base import BoardTestBase


class BoardLifecycleTestBase(BoardTestBase):
    def create_archived_board(
        self,
        *,
        title="Archived Board",
        workspace=None,
        created_by=None,
    ):
        return self.create_board(
            workspace=workspace,
            title=title,
            created_by=created_by,
            is_archived=True,
        )

    def get_archived_list_url(self):
        return reverse(
            "boards:archived_list",
            kwargs={
                "workspace_pk": self.workspace.pk,
            },
        )


class ArchivedBoardListViewTests(
    BoardLifecycleTestBase
):
    def test_anonymous_user_is_redirected(self):
        response = self.client.get(
            self.get_archived_list_url()
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_all_workspace_roles_can_view_archive(
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
                    self.get_archived_list_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_outsider_cannot_view_archive(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            self.get_archived_list_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_archive_contains_only_archived_boards(
        self
    ):
        archived_board = (
            self.create_archived_board()
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_archived_list_url()
        )

        self.assertContains(
            response,
            archived_board.title,
        )
        self.assertNotContains(
            response,
            self.board.title,
        )

    def test_other_workspace_boards_are_hidden(self):
        other_workspace = Workspace.objects.create(
            name="Shelly Workspace",
            owner=self.outsider,
        )

        other_board = self.create_archived_board(
            workspace=other_workspace,
            title="Shelly Archived Board",
            created_by=self.outsider,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_archived_list_url()
        )

        self.assertNotContains(
            response,
            other_board.title,
        )

    def test_member_can_restore_but_not_delete(self):
        self.client.force_login(self.member)

        response = self.client.get(
            self.get_archived_list_url()
        )

        self.assertTrue(
            response.context[
                "can_restore_boards"
            ]
        )
        self.assertFalse(
            response.context[
                "can_delete_boards"
            ]
        )

    def test_viewer_cannot_restore_or_delete(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            self.get_archived_list_url()
        )

        self.assertFalse(
            response.context[
                "can_restore_boards"
            ]
        )
        self.assertFalse(
            response.context[
                "can_delete_boards"
            ]
        )


class BoardArchiveViewTests(
    BoardLifecycleTestBase
):
    def get_url(self, board=None):
        return reverse(
            "boards:archive",
            kwargs={
                "workspace_pk": self.workspace.pk,
                "board_pk": (
                    board or self.board
                ).pk,
            },
        )

    def test_owner_admin_and_member_can_archive(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
        ]

        for index, user in enumerate(
            allowed_users,
            start=1,
        ):
            board = self.create_board(
                title=f"Board {index}"
            )

            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.post(
                    self.get_url(board)
                )

                board.refresh_from_db()

                self.assertTrue(
                    board.is_archived
                )
                self.assertEqual(
                    response.status_code,
                    302,
                )

                self.client.logout()

    def test_viewer_cannot_archive(self):
        self.client.force_login(self.viewer)

        response = self.client.post(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_archive(self):
        self.client.force_login(self.outsider)

        response = self.client.post(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_archive_does_not_accept_get(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_archived_board_cannot_be_archived_again(
        self
    ):
        board = self.create_archived_board()

        self.client.force_login(self.owner)

        response = self.client.post(
            self.get_url(board)
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class BoardRestoreViewTests(
    BoardLifecycleTestBase
):
    def get_url(self, board):
        return reverse(
            "boards:restore",
            kwargs={
                "workspace_pk": self.workspace.pk,
                "board_pk": board.pk,
            },
        )

    def test_owner_admin_and_member_can_restore(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
        ]

        for index, user in enumerate(
            allowed_users,
            start=1,
        ):
            board = self.create_archived_board(
                title=f"Archived Board {index}"
            )

            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.post(
                    self.get_url(board)
                )

                board.refresh_from_db()

                self.assertFalse(
                    board.is_archived
                )

                self.assertRedirects(
                    response,
                    reverse(
                        "boards:detail",
                        kwargs={
                            "workspace_pk": (
                                self.workspace.pk
                            ),
                            "board_pk": board.pk,
                        },
                    ),
                )

                self.client.logout()

    def test_viewer_cannot_restore(self):
        board = self.create_archived_board()

        self.client.force_login(self.viewer)

        response = self.client.post(
            self.get_url(board)
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_restore_does_not_accept_get(self):
        board = self.create_archived_board()

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_url(board)
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_active_board_cannot_be_restored(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.get_url(self.board)
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class BoardDeleteViewTests(
    BoardLifecycleTestBase
):
    def get_url(self, board):
        return reverse(
            "boards:delete",
            kwargs={
                "workspace_pk": self.workspace.pk,
                "board_pk": board.pk,
            },
        )

    def test_owner_and_admin_can_open_confirmation(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
        ]

        for index, user in enumerate(
            allowed_users,
            start=1,
        ):
            board = self.create_archived_board(
                title=f"Delete Board {index}"
            )

            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(
                    self.get_url(board)
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.assertContains(
                    response,
                    board.title,
                )

                self.client.logout()

    def test_owner_and_admin_can_delete_permanently(
        self
    ):
        allowed_users = [
            self.owner,
            self.admin,
        ]

        for index, user in enumerate(
            allowed_users,
            start=1,
        ):
            board = self.create_archived_board(
                title=f"Permanent Delete {index}"
            )
            board_pk = board.pk

            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.post(
                    self.get_url(board)
                )

                self.assertFalse(
                    type(board).objects.filter(
                        pk=board_pk
                    ).exists()
                )

                self.assertRedirects(
                    response,
                    self.get_archived_list_url(),
                )

                self.client.logout()

    def test_member_cannot_delete(self):
        board = self.create_archived_board()

        self.client.force_login(self.member)

        response = self.client.post(
            self.get_url(board)
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_viewer_cannot_delete(self):
        board = self.create_archived_board()

        self.client.force_login(self.viewer)

        response = self.client.post(
            self.get_url(board)
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_active_board_cannot_be_deleted(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.get_url(self.board)
        )

        self.assertEqual(
            response.status_code,
            404,
        )