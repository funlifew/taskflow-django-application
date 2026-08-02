from datetime import timedelta

from django.core.exceptions import (
    ValidationError,
)
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import (
    ValidationError,
)
from django.urls import reverse
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.columns.reordering import (
    ColumnReorderingService,
)
from apps.columns.tests.base import (
    ColumnTestBase,
)
from apps.tasks.models import Task


class ColumnReorderingServiceTests(
    ColumnTestBase
):
    def setUp(self):
        super().setUp()

        self.second = self.create_column(
            title="در حال انجام",
            position=1,
        )

        self.third = self.create_column(
            title="انجام‌شده",
            position=2,
        )

    def get_order(self):
        return list(
            Column.objects
            .active()
            .for_board(self.board)
            .order_by(
                "position",
                "pk",
            )
            .values_list(
                "pk",
                flat=True,
            )
        )

    def reorder(
        self,
        column,
        target_position,
    ):
        return (
            ColumnReorderingService
            .reorder(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=column.pk,
                target_position=(
                    target_position
                ),
            )
        )

    def test_first_column_can_move_to_end(
        self,
    ):
        (
            column,
            board,
            changed,
        ) = self.reorder(
            self.column,
            2,
        )

        column.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(
            board,
            self.board,
        )
        self.assertEqual(
            column.position,
            2,
        )
        self.assertEqual(
            self.get_order(),
            [
                self.second.pk,
                self.third.pk,
                self.column.pk,
            ],
        )

    def test_last_column_can_move_to_start(
        self,
    ):
        (
            column,
            _board,
            changed,
        ) = self.reorder(
            self.third,
            0,
        )

        column.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(
            column.position,
            0,
        )
        self.assertEqual(
            self.get_order(),
            [
                self.third.pk,
                self.column.pk,
                self.second.pk,
            ],
        )

    def test_middle_column_can_move_right(
        self,
    ):
        self.reorder(
            self.second,
            2,
        )

        self.assertEqual(
            self.get_order(),
            [
                self.column.pk,
                self.third.pk,
                self.second.pk,
            ],
        )

    def test_middle_column_can_move_left(
        self,
    ):
        self.reorder(
            self.second,
            0,
        )

        self.assertEqual(
            self.get_order(),
            [
                self.second.pk,
                self.column.pk,
                self.third.pk,
            ],
        )

    def test_positions_remain_contiguous(
        self,
    ):
        self.reorder(
            self.third,
            0,
        )

        positions = list(
            Column.objects
            .active()
            .for_board(self.board)
            .order_by("position")
            .values_list(
                "position",
                flat=True,
            )
        )

        self.assertEqual(
            positions,
            [0, 1, 2],
        )

    def test_noop_reorder_reports_unchanged(
        self,
    ):
        (
            column,
            _board,
            changed,
        ) = self.reorder(
            self.second,
            1,
        )

        self.assertFalse(changed)
        self.assertEqual(
            column.pk,
            self.second.pk,
        )
        self.assertEqual(
            self.get_order(),
            [
                self.column.pk,
                self.second.pk,
                self.third.pk,
            ],
        )

    def test_noop_does_not_touch_board(
        self,
    ):
        old_time = (
            timezone.now()
            - timedelta(days=1)
        )

        Board.objects.filter(
            pk=self.board.pk,
        ).update(
            updated_at=old_time,
        )

        self.reorder(
            self.second,
            1,
        )

        self.board.refresh_from_db()

        self.assertEqual(
            self.board.updated_at,
            old_time,
        )

    def test_successful_reorder_touches_board(
        self,
    ):
        old_time = (
            timezone.now()
            - timedelta(days=1)
        )

        Board.objects.filter(
            pk=self.board.pk,
        ).update(
            updated_at=old_time,
        )

        self.reorder(
            self.second,
            0,
        )

        self.board.refresh_from_db()

        self.assertGreater(
            self.board.updated_at,
            old_time,
        )

    def test_move_left_swaps_columns(self):
        (
            column,
            _board,
            changed,
        ) = (
            ColumnReorderingService
            .move_left(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.second.pk,
            )
        )

        column.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(
            column.position,
            0,
        )
        self.assertEqual(
            self.get_order(),
            [
                self.second.pk,
                self.column.pk,
                self.third.pk,
            ],
        )

    def test_move_right_swaps_columns(self):
        (
            column,
            _board,
            changed,
        ) = (
            ColumnReorderingService
            .move_right(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
            )
        )

        column.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(
            column.position,
            1,
        )
        self.assertEqual(
            self.get_order(),
            [
                self.second.pk,
                self.column.pk,
                self.third.pk,
            ],
        )

    def test_first_column_move_left_is_noop(
        self,
    ):
        (
            _column,
            _board,
            changed,
        ) = (
            ColumnReorderingService
            .move_left(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
            )
        )

        self.assertFalse(changed)

    def test_last_column_move_right_is_noop(
        self,
    ):
        (
            _column,
            _board,
            changed,
        ) = (
            ColumnReorderingService
            .move_right(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.third.pk,
            )
        )

        self.assertFalse(changed)

    def test_boolean_position_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.column,
                True,
            )

    def test_string_position_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.column,
                "1",
            )

    def test_negative_position_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.column,
                -1,
            )

    def test_out_of_range_position_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.column,
                3,
            )

    def test_archived_column_cannot_be_reordered(
        self,
    ):
        archived = self.create_column(
            title="Archived",
            position=20,
            is_archived=True,
        )

        with self.assertRaises(Http404):
            self.reorder(
                archived,
                0,
            )

    def test_column_from_other_board_is_rejected(
        self,
    ):
        other_board = self.create_board(
            title="Other Board",
        )

        other_column = self.create_column(
            board=other_board,
            title="Other Column",
            position=0,
        )

        with self.assertRaises(Http404):
            (
                ColumnReorderingService
                .reorder(
                    workspace=self.workspace,
                    board_pk=self.board.pk,
                    column_pk=other_column.pk,
                    target_position=0,
                )
            )

    def test_column_fields_are_preserved(
        self,
    ):
        original_title = self.second.title
        original_creator = (
            self.second.created_by
        )

        self.reorder(
            self.second,
            0,
        )

        self.second.refresh_from_db()

        self.assertEqual(
            self.second.title,
            original_title,
        )
        self.assertEqual(
            self.second.created_by,
            original_creator,
        )
        self.assertFalse(
            self.second.is_archived
        )

    def test_tasks_remain_in_original_column(
        self,
    ):
        task = Task.objects.create(
            column=self.second,
            title="Task",
            description="",
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
            position=0,
            created_by=self.owner,
            is_archived=False,
            archived_at=None,
        )

        self.reorder(
            self.second,
            0,
        )

        task.refresh_from_db()

        self.assertEqual(
            task.column,
            self.second,
        )


class ColumnReorderingViewTests(
    ColumnTestBase
):
    def setUp(self):
        super().setUp()

        self.second = self.create_column(
            title="در حال انجام",
            position=1,
        )

        self.third = self.create_column(
            title="انجام‌شده",
            position=2,
        )

    def move_left_url(self, column):
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

    def move_right_url(self, column):
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

    def get_order(self):
        return list(
            Column.objects
            .active()
            .for_board(self.board)
            .order_by(
                "position",
                "pk",
            )
            .values_list(
                "pk",
                flat=True,
            )
        )

    def test_anonymous_user_is_redirected(
        self,
    ):
        response = self.client.post(
            self.move_right_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_owner_admin_and_member_can_reorder(
        self,
    ):
        for user in (
            self.owner,
            self.admin,
            self.member,
        ):
            with self.subTest(
                user=user.username
            ):
                self.client.force_login(user)

                response = self.client.post(
                    self.move_left_url(
                        self.column
                    )
                )

                self.assertEqual(
                    response.status_code,
                    302,
                )

                self.client.logout()

    def test_viewer_cannot_reorder(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.move_right_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_reorder(self):
        self.client.force_login(
            self.outsider
        )

        response = self.client.post(
            self.move_right_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_move_endpoint_only_accepts_post(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.move_right_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_drag_endpoint_only_accepts_post(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.drag_url(
                self.column
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_move_right_changes_order(self):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.move_right_url(
                self.column
            )
        )

        self.assertEqual(
            self.get_order(),
            [
                self.second.pk,
                self.column.pk,
                self.third.pk,
            ],
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

    def test_move_left_changes_order(self):
        self.client.force_login(
            self.admin
        )

        self.client.post(
            self.move_left_url(
                self.second
            )
        )

        self.assertEqual(
            self.get_order(),
            [
                self.second.pk,
                self.column.pk,
                self.third.pk,
            ],
        )

    def test_valid_drag_reorders_column(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                self.column
            ),
            data={
                "target_position": 2,
            },
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["ok"]
        )
        self.assertTrue(
            payload["changed"]
        )
        self.assertEqual(
            payload["column"]["id"],
            self.column.pk,
        )
        self.assertEqual(
            payload["column"][
                "position"
            ],
            2,
        )
        self.assertEqual(
            [
                column["id"]
                for column
                in payload["columns"]
            ],
            [
                self.second.pk,
                self.third.pk,
                self.column.pk,
            ],
        )

    def test_same_position_drag_is_noop(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                self.second
            ),
            data={
                "target_position": 1,
            },
            content_type=(
                "application/json"
            ),
        )

        payload = response.json()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTrue(
            payload["ok"]
        )
        self.assertFalse(
            payload["changed"]
        )

    def test_invalid_json_returns_400(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                self.column
            ),
            data="{",
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertFalse(
            response.json()["ok"]
        )

    def test_non_object_json_returns_400(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                self.column
            ),
            data=[0],
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_boolean_position_returns_400(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                self.column
            ),
            data={
                "target_position": True,
            },
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_out_of_range_position_returns_400(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                self.column
            ),
            data={
                "target_position": 3,
            },
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "target_position",
            response.json()["errors"],
        )

    def test_archived_column_returns_404(
        self,
    ):
        archived = self.create_column(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.drag_url(
                archived
            ),
            data={
                "target_position": 0,
            },
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class BoardDetailColumnReorderingContextTests(
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

    def test_member_can_reorder_columns(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertTrue(
            response.context[
                "can_reorder_columns"
            ]
        )
        self.assertTrue(
            response.context[
                "can_drag_columns"
            ]
        )

    def test_viewer_cannot_reorder_columns(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertFalse(
            response.context[
                "can_reorder_columns"
            ]
        )
        self.assertFalse(
            response.context[
                "can_drag_columns"
            ]
        )