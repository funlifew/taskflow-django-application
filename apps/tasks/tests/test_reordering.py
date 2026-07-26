from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import (
    ValidationError,
)
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.tasks.forms import (
    TaskReorderForm,
)
from apps.tasks.models import Task
from apps.tasks.reordering import (
    TaskReorderingService,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)


class TaskReorderingTestBase(
    TaskTestBase,
):
    def task_url(
        self,
        name,
        *,
        task=None,
        column=None,
    ):
        task = task or self.task
        column = column or task.column

        return reverse(
            f"tasks:{name}",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    column.pk
                ),
                "task_pk": task.pk,
            },
        )

    def ordered_tasks(
        self,
        column,
    ):
        return list(
            Task.objects
            .active()
            .for_column(column)
            .order_by(
                "position",
                "pk",
            )
        )

    def ordered_titles(
        self,
        column,
    ):
        return [
            task.title
            for task in (
                self.ordered_tasks(
                    column
                )
            )
        ]

    def ordered_positions(
        self,
        column,
    ):
        return [
            task.position
            for task in (
                self.ordered_tasks(
                    column
                )
            )
        ]


class TaskReorderFormTests(
    TaskReorderingTestBase,
):
    def setUp(self):
        super().setUp()

        self.target_column = (
            self.create_column(
                title="Target",
                position=1,
            )
        )

        self.archived_column = (
            self.create_column(
                title="Archived",
                position=50,
                is_archived=True,
            )
        )

        self.other_board = (
            self.create_board(
                title="Other Board",
            )
        )

        self.other_board_column = (
            self.create_column(
                board=self.other_board,
                title="Other Board Column",
                position=0,
            )
        )

    def test_current_and_other_active_columns_are_available(
        self,
    ):
        form = TaskReorderForm(
            board=self.board,
            task=self.task,
        )

        queryset = (
            form.fields[
                "target_column"
            ].queryset
        )

        self.assertIn(
            self.column,
            queryset,
        )

        self.assertIn(
            self.target_column,
            queryset,
        )

        self.assertNotIn(
            self.archived_column,
            queryset,
        )

        self.assertNotIn(
            self.other_board_column,
            queryset,
        )

    def test_initial_values_use_current_location(
        self,
    ):
        form = TaskReorderForm(
            board=self.board,
            task=self.task,
        )

        self.assertEqual(
            form.initial[
                "target_column"
            ],
            self.column,
        )

        self.assertEqual(
            form.initial[
                "target_position"
            ],
            1,
        )

    def test_user_position_is_converted_to_zero_based_position(
        self,
    ):
        self.create_task(
            title="Second",
            position=1,
        )

        form = TaskReorderForm(
            data={
                "target_column": (
                    self.column.pk
                ),
                "target_position": 2,
            },
            board=self.board,
            task=self.task,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data[
                "target_position"
            ],
            1,
        )

    def test_cross_column_end_position_is_valid(
        self,
    ):
        self.create_task(
            column=self.target_column,
            title="Target Existing",
            position=0,
        )

        form = TaskReorderForm(
            data={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 2,
            },
            board=self.board,
            task=self.task,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data[
                "target_position"
            ],
            1,
        )

    def test_zero_position_is_rejected(
        self,
    ):
        form = TaskReorderForm(
            data={
                "target_column": (
                    self.column.pk
                ),
                "target_position": 0,
            },
            board=self.board,
            task=self.task,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "target_position",
            form.errors,
        )

    def test_position_beyond_same_column_length_is_rejected(
        self,
    ):
        form = TaskReorderForm(
            data={
                "target_column": (
                    self.column.pk
                ),
                "target_position": 2,
            },
            board=self.board,
            task=self.task,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "target_position",
            form.errors,
        )

    def test_position_beyond_empty_target_range_is_rejected(
        self,
    ):
        form = TaskReorderForm(
            data={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 2,
            },
            board=self.board,
            task=self.task,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "target_position",
            form.errors,
        )


class SameColumnReorderingTests(
    TaskReorderingTestBase,
):
    def setUp(self):
        super().setUp()

        self.second = self.create_task(
            title="Second",
            position=1,
        )

        self.third = self.create_task(
            title="Third",
            position=2,
        )

        self.fourth = self.create_task(
            title="Fourth",
            position=3,
        )

    def reorder(
        self,
        task,
        target_position,
    ):
        return (
            TaskReorderingService
            .reorder(
                workspace=(
                    self.workspace
                ),
                board_pk=self.board.pk,
                source_column_pk=(
                    self.column.pk
                ),
                target_column_pk=(
                    self.column.pk
                ),
                task_pk=task.pk,
                target_position=(
                    target_position
                ),
            )
        )

    def test_last_task_can_move_to_first(
        self,
    ):
        self.reorder(
            self.fourth,
            0,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                "Fourth",
                self.task.title,
                "Second",
                "Third",
            ],
        )

        self.assertEqual(
            self.ordered_positions(
                self.column
            ),
            [0, 1, 2, 3],
        )

    def test_first_task_can_move_to_last(
        self,
    ):
        self.reorder(
            self.task,
            3,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                "Second",
                "Third",
                "Fourth",
                self.task.title,
            ],
        )

    def test_middle_task_can_move_upward(
        self,
    ):
        self.reorder(
            self.third,
            1,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Third",
                "Second",
                "Fourth",
            ],
        )

    def test_middle_task_can_move_downward(
        self,
    ):
        self.reorder(
            self.second,
            2,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Third",
                "Second",
                "Fourth",
            ],
        )

    def test_same_position_is_noop(
        self,
    ):
        old_board_updated_at = (
            self.board.updated_at
        )

        old_column_updated_at = (
            self.column.updated_at
        )

        self.reorder(
            self.second,
            1,
        )

        self.board.refresh_from_db()
        self.column.refresh_from_db()

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Second",
                "Third",
                "Fourth",
            ],
        )

        self.assertEqual(
            self.board.updated_at,
            old_board_updated_at,
        )

        self.assertEqual(
            self.column.updated_at,
            old_column_updated_at,
        )

    def test_negative_position_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.second,
                -1,
            )

    def test_position_beyond_end_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.second,
                4,
            )

    def test_non_integer_position_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                self.second,
                "1",
            )

    def test_task_metadata_is_preserved(
        self,
    ):
        original_status = (
            self.third.status
        )

        original_priority = (
            self.third.priority
        )

        original_assignee = (
            self.third.assignee
        )

        original_creator = (
            self.third.created_by
        )

        self.reorder(
            self.third,
            0,
        )

        self.third.refresh_from_db()

        self.assertEqual(
            self.third.status,
            original_status,
        )

        self.assertEqual(
            self.third.priority,
            original_priority,
        )

        self.assertEqual(
            self.third.assignee,
            original_assignee,
        )

        self.assertEqual(
            self.third.created_by,
            original_creator,
        )


class CrossColumnReorderingTests(
    TaskReorderingTestBase,
):
    def setUp(self):
        super().setUp()

        self.moving = self.create_task(
            title="Moving",
            position=1,
        )

        self.source_final = (
            self.create_task(
                title="Source Final",
                position=2,
            )
        )

        self.target_column = (
            self.create_column(
                title="Target",
                position=1,
            )
        )

        self.target_first = (
            self.create_task(
                column=self.target_column,
                title="Target First",
                position=0,
            )
        )

        self.target_second = (
            self.create_task(
                column=self.target_column,
                title="Target Second",
                position=1,
            )
        )

    def reorder(
        self,
        *,
        task=None,
        target_column=None,
        target_position,
    ):
        task = task or self.moving

        target_column = (
            target_column
            or self.target_column
        )

        return (
            TaskReorderingService
            .reorder(
                workspace=(
                    self.workspace
                ),
                board_pk=self.board.pk,
                source_column_pk=(
                    task.column_id
                ),
                target_column_pk=(
                    target_column.pk
                ),
                task_pk=task.pk,
                target_position=(
                    target_position
                ),
            )
        )

    def test_task_can_insert_at_exact_position(
        self,
    ):
        self.reorder(
            target_position=1,
        )

        self.moving.refresh_from_db()

        self.assertEqual(
            self.moving.column,
            self.target_column,
        )

        self.assertEqual(
            self.moving.position,
            1,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Source Final",
            ],
        )

        self.assertEqual(
            self.ordered_titles(
                self.target_column
            ),
            [
                "Target First",
                "Moving",
                "Target Second",
            ],
        )

        self.assertEqual(
            self.ordered_positions(
                self.column
            ),
            [0, 1],
        )

        self.assertEqual(
            self.ordered_positions(
                self.target_column
            ),
            [0, 1, 2],
        )

    def test_task_can_insert_at_start(
        self,
    ):
        self.reorder(
            target_position=0,
        )

        self.assertEqual(
            self.ordered_titles(
                self.target_column
            ),
            [
                "Moving",
                "Target First",
                "Target Second",
            ],
        )

    def test_task_can_append_to_end(
        self,
    ):
        self.reorder(
            target_position=2,
        )

        self.assertEqual(
            self.ordered_titles(
                self.target_column
            ),
            [
                "Target First",
                "Target Second",
                "Moving",
            ],
        )

    def test_task_can_move_to_empty_column(
        self,
    ):
        empty_column = (
            self.create_column(
                title="Empty",
                position=2,
            )
        )

        self.reorder(
            target_column=empty_column,
            target_position=0,
        )

        self.moving.refresh_from_db()

        self.assertEqual(
            self.moving.column,
            empty_column,
        )

        self.assertEqual(
            self.moving.position,
            0,
        )

    def test_target_position_beyond_range_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            self.reorder(
                target_position=3,
            )

    def test_archived_target_column_is_rejected(
        self,
    ):
        archived_column = (
            self.create_column(
                title="Archived",
                position=50,
                is_archived=True,
            )
        )

        with self.assertRaises(
            Http404
        ):
            self.reorder(
                target_column=(
                    archived_column
                ),
                target_position=0,
            )

    def test_other_board_target_is_rejected(
        self,
    ):
        other_board = (
            self.create_board(
                title="Other Board",
            )
        )

        other_column = (
            self.create_column(
                board=other_board,
                title="Other Column",
                position=0,
            )
        )

        with self.assertRaises(
            Http404
        ):
            self.reorder(
                target_column=(
                    other_column
                ),
                target_position=0,
            )

    def test_archived_task_is_rejected(
        self,
    ):
        archived_task = (
            self.create_task(
                title="Archived Task",
                position=50,
                is_archived=True,
            )
        )

        with self.assertRaises(
            Http404
        ):
            (
                TaskReorderingService
                .reorder(
                    workspace=(
                        self.workspace
                    ),
                    board_pk=(
                        self.board.pk
                    ),
                    source_column_pk=(
                        self.column.pk
                    ),
                    target_column_pk=(
                        self.target_column.pk
                    ),
                    task_pk=(
                        archived_task.pk
                    ),
                    target_position=0,
                )
            )

    def test_parent_timestamps_are_updated(
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

        Column.objects.filter(
            pk__in=[
                self.column.pk,
                self.target_column.pk,
            ],
        ).update(
            updated_at=old_time,
        )

        self.reorder(
            target_position=1,
        )

        self.board.refresh_from_db()
        self.column.refresh_from_db()
        self.target_column.refresh_from_db()

        self.assertGreater(
            self.board.updated_at,
            old_time,
        )

        self.assertGreater(
            self.column.updated_at,
            old_time,
        )

        self.assertGreater(
            self.target_column.updated_at,
            old_time,
        )

    def test_transaction_rolls_back_on_failure(
        self,
    ):
        original_source = (
            self.ordered_titles(
                self.column
            )
        )

        original_target = (
            self.ordered_titles(
                self.target_column
            )
        )

        with patch.object(
            Task.objects,
            "bulk_update",
            side_effect=RuntimeError(
                "Forced failure",
            ),
        ):
            with self.assertRaises(
                RuntimeError
            ):
                self.reorder(
                    target_position=1,
                )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            original_source,
        )

        self.assertEqual(
            self.ordered_titles(
                self.target_column
            ),
            original_target,
        )

        self.assertEqual(
            self.ordered_positions(
                self.column
            ),
            [0, 1, 2],
        )

        self.assertEqual(
            self.ordered_positions(
                self.target_column
            ),
            [0, 1],
        )


class RelativeTaskMovementTests(
    TaskReorderingTestBase,
):
    def setUp(self):
        super().setUp()

        self.second = self.create_task(
            title="Second",
            position=1,
        )

        self.third = self.create_task(
            title="Third",
            position=2,
        )

    def test_move_up_swaps_with_previous_task(
        self,
    ):
        TaskReorderingService.move_up(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.third.pk,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Third",
                "Second",
            ],
        )

    def test_move_down_swaps_with_next_task(
        self,
    ):
        (
            TaskReorderingService
            .move_down(
                workspace=(
                    self.workspace
                ),
                board_pk=(
                    self.board.pk
                ),
                column_pk=(
                    self.column.pk
                ),
                task_pk=self.task.pk,
            )
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                "Second",
                self.task.title,
                "Third",
            ],
        )

    def test_first_task_move_up_is_noop(
        self,
    ):
        TaskReorderingService.move_up(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Second",
                "Third",
            ],
        )

    def test_last_task_move_down_is_noop(
        self,
    ):
        (
            TaskReorderingService
            .move_down(
                workspace=(
                    self.workspace
                ),
                board_pk=(
                    self.board.pk
                ),
                column_pk=(
                    self.column.pk
                ),
                task_pk=self.third.pk,
            )
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Second",
                "Third",
            ],
        )

    def test_invalid_offset_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            (
                TaskReorderingService
                .shift(
                    workspace=(
                        self.workspace
                    ),
                    board_pk=(
                        self.board.pk
                    ),
                    column_pk=(
                        self.column.pk
                    ),
                    task_pk=(
                        self.second.pk
                    ),
                    offset=2,
                )
            )


class TaskReorderingViewTests(
    TaskReorderingTestBase,
):
    def setUp(self):
        super().setUp()

        self.second = self.create_task(
            title="Second",
            position=1,
        )

        self.third = self.create_task(
            title="Third",
            position=2,
        )

        self.target_column = (
            self.create_column(
                title="Target",
                position=1,
            )
        )

    def test_writers_can_open_reorder_page(
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
                self.client.force_login(
                    user
                )

                response = self.client.get(
                    self.task_url(
                        "reorder",
                        task=self.second,
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_viewer_cannot_open_reorder_page(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.task_url(
                "reorder",
                task=self.second,
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_open_reorder_page(
        self,
    ):
        self.client.force_login(
            self.outsider
        )

        response = self.client.get(
            self.task_url(
                "reorder",
                task=self.second,
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_valid_post_reorders_task(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.task_url(
                "reorder",
                task=self.second,
            ),
            data={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 1,
            },
        )

        self.second.refresh_from_db()

        self.assertEqual(
            self.second.column,
            self.target_column,
        )

        self.assertEqual(
            self.second.position,
            0,
        )

        self.assertRedirects(
            response,
            self.task_url(
                "detail",
                task=self.second,
                column=self.target_column,
            ),
        )

    def test_invalid_post_rerenders_form(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.task_url(
                "reorder",
                task=self.second,
            ),
            data={
                "target_column": (
                    self.column.pk
                ),
                "target_position": 99,
            },
        )

        self.second.refresh_from_db()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "target_position",
            response.context[
                "form"
            ].errors,
        )

        self.assertEqual(
            self.second.column,
            self.column,
        )

        self.assertEqual(
            self.second.position,
            1,
        )

    def test_up_and_down_only_accept_post(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        for name in (
            "move_up",
            "move_down",
        ):
            with self.subTest(
                name=name
            ):
                response = self.client.get(
                    self.task_url(
                        name,
                        task=self.second,
                    )
                )

                self.assertEqual(
                    response.status_code,
                    405,
                )

    def test_move_up_view_changes_order(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.task_url(
                "move_up",
                task=self.second,
            )
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                "Second",
                self.task.title,
                "Third",
            ],
        )

        self.assertRedirects(
            response,
            self.task_url(
                "detail",
                task=self.second,
            ),
        )

    def test_move_down_view_changes_order(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.task_url(
                "move_down",
                task=self.second,
            )
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Third",
                "Second",
            ],
        )

        self.assertRedirects(
            response,
            self.task_url(
                "detail",
                task=self.second,
            ),
        )

    def test_viewer_cannot_move_up_or_down(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        for name in (
            "move_up",
            "move_down",
        ):
            with self.subTest(
                name=name
            ):
                response = (
                    self.client.post(
                        self.task_url(
                            name,
                            task=(
                                self.second
                            ),
                        )
                    )
                )

                self.assertEqual(
                    response.status_code,
                    403,
                )

    def test_archived_task_cannot_be_reordered(
        self,
    ):
        archived_task = (
            self.create_task(
                title="Archived",
                position=50,
                is_archived=True,
            )
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.task_url(
                "reorder",
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_detail_context_contains_reordering_flags(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.task_url(
                "detail",
                task=self.second,
            )
        )

        self.assertTrue(
            response.context[
                "can_reorder_task"
            ]
        )

        self.assertTrue(
            response.context[
                "can_move_up"
            ]
        )

        self.assertTrue(
            response.context[
                "can_move_down"
            ]
        )

    def test_viewer_does_not_see_reordering_actions(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.task_url(
                "detail",
                task=self.second,
            )
        )

        self.assertFalse(
            response.context[
                "can_reorder_task"
            ]
        )

        self.assertNotContains(
            response,
            self.task_url(
                "reorder",
                task=self.second,
            ),
        )

        self.assertNotContains(
            response,
            self.task_url(
                "move_up",
                task=self.second,
            ),
        )

        self.assertNotContains(
            response,
            self.task_url(
                "move_down",
                task=self.second,
            ),
        )