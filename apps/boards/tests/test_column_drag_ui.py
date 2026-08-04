from django.urls import reverse

from apps.columns.tests.base import (
    ColumnTestBase,
)


class ColumnDragDropTemplateTests(
    ColumnTestBase
):
    def setUp(self):
        super().setUp()

        self.second_column = (
            self.create_column(
                title="در حال انجام",
                position=1,
            )
        )

    def detail_url(self):
        return reverse(
            "boards:detail",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
            },
        )

    def drag_url(self, column):
        return reverse(
            "columns:drag_reorder",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def move_previous_url(
        self,
        column,
    ):
        return reverse(
            "columns:move_left",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def move_next_url(
        self,
        column,
    ):
        return reverse(
            "columns:move_right",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )

    def test_owner_receives_column_drag_markup(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "data-column-board",
        )

        self.assertContains(
            response,
            (
                'data-column-drag-enabled='
                '"true"'
            ),
        )

        self.assertContains(
            response,
            "data-column-card",
            count=2,
        )

        self.assertContains(
            response,
            "data-column-drag-handle",
            count=2,
        )

        self.assertContains(
            response,
            self.drag_url(
                self.column
            ),
        )

        self.assertContains(
            response,
            self.drag_url(
                self.second_column
            ),
        )

    def test_writer_receives_relative_move_controls(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertContains(
            response,
            self.move_previous_url(
                self.column
            ),
        )

        self.assertContains(
            response,
            self.move_next_url(
                self.column
            ),
        )

        self.assertContains(
            response,
            self.move_previous_url(
                self.second_column
            ),
        )

        self.assertContains(
            response,
            self.move_next_url(
                self.second_column
            ),
        )

    def test_viewer_has_read_only_column_board(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            (
                'data-column-drag-enabled='
                '"false"'
            ),
        )

        self.assertNotContains(
            response,
            "data-column-drag-handle",
        )

        self.assertNotContains(
            response,
            "data-reorder-url=",
        )

        self.assertNotContains(
            response,
            "data-column-move-previous",
        )

        self.assertNotContains(
            response,
            "data-column-move-next",
        )

    def test_writer_loads_drag_scripts(
        self,
    ):
        self.client.force_login(
            self.admin
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertContains(
            response,
            "Sortable.min.js",
        )

        self.assertContains(
            response,
            "js/task-drag-drop.js",
        )

        self.assertContains(
            response,
            "js/column-drag-drop.js",
        )

        self.assertContains(
            response,
            "css/column-drag-drop.css",
        )

    def test_viewer_does_not_load_drag_scripts(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertNotContains(
            response,
            "Sortable.min.js",
        )

        self.assertNotContains(
            response,
            "js/task-drag-drop.js",
        )

        self.assertNotContains(
            response,
            "js/column-drag-drop.js",
        )

        self.assertContains(
            response,
            "css/column-drag-drop.css",
        )

    def test_columns_keep_position_order(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertEqual(
            [
                column.pk
                for column
                in response.context[
                    "columns"
                ]
            ],
            [
                self.column.pk,
                self.second_column.pk,
            ],
        )

    def test_column_position_metadata_is_rendered(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertContains(
            response,
            (
                f'data-column-id="'
                f'{self.column.pk}"'
            ),
        )

        self.assertContains(
            response,
            'data-position="0"',
        )

        self.assertContains(
            response,
            'data-position="1"',
        )