from django.urls import reverse

from apps.columns.models import Column

from apps.columns.tests.base import ColumnTestBase


class ColumnLifecycleTestBase(
    ColumnTestBase
):
    def update_url(self, column):
        return reverse(
            "columns:update",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def archive_url(self, column):
        return reverse(
            "columns:archive",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def restore_url(self, column):
        return reverse(
            "columns:restore",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def delete_url(self, column):
        return reverse(
            "columns:delete",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def archived_list_url(self):
        return reverse(
            "columns:archived_list",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
            },
        )

class ColumnUpdateViewTests(
    ColumnLifecycleTestBase
):
    def test_owner_admin_and_member_can_update(
        self
    ):
        for user in (
            self.owner,
            self.admin,
            self.member,
        ):
            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.get(
                    self.update_url(
                        self.column
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_viewer_cannot_update(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.update_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_valid_post_updates_title(self):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.update_url(
                self.column
            ),
            data={
                "title": "عنوان جدید",
            },
        )

        self.column.refresh_from_db()

        self.assertEqual(
            self.column.title,
            "عنوان جدید",
        )
        self.assertEqual(
            self.column.position,
            0,
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

    def test_archived_column_cannot_be_updated(
        self
    ):
        archived_column = self.create_column(
            title="Archived",
            position=8,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.update_url(
                archived_column
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

class ColumnArchiveViewTests(
    ColumnLifecycleTestBase
):
    def test_archive_only_accepts_post(self):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.archive_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_owner_admin_and_member_can_archive(
        self
    ):
        for index, user in enumerate(
            (
                self.owner,
                self.admin,
                self.member,
            ),
            start=1,
        ):
            column = self.create_column(
                title=f"Column {index}",
                position=index,
            )

            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.post(
                    self.archive_url(
                        column
                    )
                )

                column.refresh_from_db()

                self.assertTrue(
                    column.is_archived
                )
                self.assertEqual(
                    response.status_code,
                    302,
                )

                self.client.logout()

    def test_viewer_cannot_archive(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.archive_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_archiving_normalizes_positions(
        self
    ):
        middle_column = self.create_column(
            title="Doing",
            position=1,
        )

        final_column = self.create_column(
            title="Done",
            position=2,
        )

        self.client.force_login(
            self.owner
        )

        self.client.post(
            self.archive_url(
                middle_column
            )
        )

        final_column.refresh_from_db()

        self.assertEqual(
            final_column.position,
            1,
        )

        active_positions = list(
            Column.objects
            .active()
            .for_board(self.board)
            .values_list(
                "position",
                flat=True,
            )
        )

        self.assertEqual(
            active_positions,
            [
                0,
                1,
            ],
        )

class ArchivedColumnListViewTests(
    ColumnLifecycleTestBase
):
    def test_all_workspace_roles_can_view_archive(
        self
    ):
        for user in (
            self.owner,
            self.admin,
            self.member,
            self.viewer,
        ):
            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.get(
                    self.archived_list_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_outsider_cannot_view_archive(self):
        self.client.force_login(
            self.outsider
        )

        response = self.client.get(
            self.archived_list_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_only_archived_columns_are_listed(
        self
    ):
        archived_column = self.create_column(
            title="Archived Column",
            position=9,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.archived_list_url()
        )

        self.assertContains(
            response,
            archived_column.title,
        )
        self.assertNotContains(
            response,
            self.column.title,
        )

class ColumnRestoreViewTests(
    ColumnLifecycleTestBase
):
    def test_restore_only_accepts_post(self):
        column = self.create_column(
            title="Archived",
            position=8,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.restore_url(
                column
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_restore_appends_column_to_end(
        self
    ):
        self.create_column(
            title="Doing",
            position=1,
        )

        archived_column = self.create_column(
            title="Archived",
            position=0,
            is_archived=True,
        )

        self.client.force_login(
            self.member
        )

        self.client.post(
            self.restore_url(
                archived_column
            )
        )

        archived_column.refresh_from_db()

        self.assertFalse(
            archived_column.is_archived
        )
        self.assertEqual(
            archived_column.position,
            2,
        )

    def test_viewer_cannot_restore(self):
        archived_column = self.create_column(
            title="Archived",
            position=8,
            is_archived=True,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.restore_url(
                archived_column
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_active_column_cannot_be_restored(
        self
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.restore_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

class ColumnDeleteViewTests(
    ColumnLifecycleTestBase
):
    def test_owner_and_admin_can_open_confirmation(
        self
    ):
        for index, user in enumerate(
            (
                self.owner,
                self.admin,
            ),
            start=1,
        ):
            column = self.create_column(
                title=f"Archived {index}",
                position=index,
                is_archived=True,
            )

            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.get(
                    self.delete_url(
                        column
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_member_cannot_delete(self):
        column = self.create_column(
            title="Archived",
            position=8,
            is_archived=True,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.delete_url(
                column
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_permanently_delete(
        self
    ):
        column = self.create_column(
            title="Archived",
            position=8,
            is_archived=True,
        )

        column_pk = column.pk

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.delete_url(
                column
            )
        )

        self.assertFalse(
            Column.objects.filter(
                pk=column_pk,
            ).exists()
        )

        self.assertRedirects(
            response,
            self.archived_list_url(),
        )

    def test_active_column_cannot_be_deleted(
        self
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.delete_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )