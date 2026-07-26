import json
from unittest.mock import patch

from django.core.exceptions import (
    ValidationError,
)
from django.urls import reverse

from apps.tasks.models import Task
from apps.tasks.tests.base import (
    TaskTestBase,
)


class TaskDragReorderingTests(
    TaskTestBase,
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

        self.target_first = (
            self.create_task(
                column=(
                    self.target_column
                ),
                title="Target First",
                position=0,
            )
        )

    def drag_url(
        self,
        *,
        task=None,
        column=None,
    ):
        task = task or self.task
        column = column or task.column

        return reverse(
            "tasks:drag_reorder",
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

    def board_url(self):
        return reverse(
            "boards:detail",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
            },
        )

    def post_drag(
        self,
        *,
        task=None,
        column=None,
        payload=None,
        raw_data=None,
    ):
        if raw_data is None:
            raw_data = json.dumps(
                payload or {}
            )

        return self.client.post(
            self.drag_url(
                task=task,
                column=column,
            ),
            data=raw_data,
            content_type=(
                "application/json"
            ),
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

    def test_endpoint_only_accepts_post(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.drag_url(
                task=self.second,
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_owner_admin_and_member_can_drag(
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

                response = (
                    self.post_drag(
                        task=self.task,
                        payload={
                            "target_column": (
                                self.column.pk
                            ),
                            "target_position": 0,
                        },
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.assertTrue(
                    response.json()[
                        "ok"
                    ]
                )

                self.client.logout()

    def test_viewer_cannot_drag_task(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_drag_task(
        self,
    ):
        self.client.force_login(
            self.outsider
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_malformed_json_is_rejected(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            raw_data="{invalid-json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            response.json()["ok"]
        )

    def test_json_array_is_rejected(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            raw_data=json.dumps(
                [
                    self.target_column.pk,
                    0,
                ]
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_missing_fields_are_rejected(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={},
        )

        response_payload = (
            response.json()
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "target_column",
            response_payload[
                "errors"
            ],
        )

        self.assertIn(
            "target_position",
            response_payload[
                "errors"
            ],
        )

    def test_cross_column_exact_position(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 1,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.second.refresh_from_db()

        self.assertEqual(
            self.second.column,
            self.target_column,
        )

        self.assertEqual(
            self.second.position,
            1,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                self.task.title,
                "Third",
            ],
        )

        self.assertEqual(
            self.ordered_positions(
                self.column
            ),
            [0, 1],
        )

        self.assertEqual(
            self.ordered_titles(
                self.target_column
            ),
            [
                "Target First",
                "Second",
            ],
        )

        payload = response.json()

        self.assertEqual(
            payload["task"][
                "column_id"
            ],
            self.target_column.pk,
        )

        self.assertEqual(
            payload["task"][
                "position"
            ],
            1,
        )

        self.assertEqual(
            payload["task"][
                "reorder_url"
            ],
            self.drag_url(
                task=self.second,
                column=(
                    self.target_column
                ),
            ),
        )

    def test_same_column_reordering(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.third,
            payload={
                "target_column": (
                    self.column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self.ordered_titles(
                self.column
            ),
            [
                "Third",
                self.task.title,
                "Second",
            ],
        )

        self.assertEqual(
            self.ordered_positions(
                self.column
            ),
            [0, 1, 2],
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

        self.client.force_login(
            self.admin
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    empty_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.second.refresh_from_db()

        self.assertEqual(
            self.second.column,
            empty_column,
        )

        self.assertEqual(
            self.second.position,
            0,
        )

    def test_negative_position_is_rejected(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": -1,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "target_position",
            response.json()[
                "errors"
            ],
        )

    def test_boolean_position_is_rejected(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": True,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_out_of_range_position_is_rejected(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 99,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.second.refresh_from_db()

        self.assertEqual(
            self.second.column,
            self.column,
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

        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    archived_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "target_column",
            response.json()[
                "errors"
            ],
        )

    def test_other_board_column_is_rejected(
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

        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    other_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_archived_task_is_not_available(
        self,
    ):
        archived_task = (
            self.create_task(
                title="Archived Task",
                position=50,
                is_archived=True,
            )
        )

        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=archived_task,
            column=self.column,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    @patch(
        "apps.tasks.views."
        "TaskReorderingService.reorder"
    )
    def test_service_validation_error_is_json(
        self,
        mocked_reorder,
    ):
        mocked_reorder.side_effect = (
            ValidationError(
                {
                    "target_position": [
                        (
                            "جایگاه مقصد "
                            "معتبر نیست."
                        ),
                    ],
                }
            )
        )

        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.json()[
                "errors"
            ][
                "target_position"
            ],
            [
                (
                    "جایگاه مقصد "
                    "معتبر نیست."
                ),
            ],
        )

    def test_response_contains_affected_column_order(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.post_drag(
            task=self.second,
            payload={
                "target_column": (
                    self.target_column.pk
                ),
                "target_position": 0,
            },
        )

        columns = {
            column["id"]: column
            for column in (
                response.json()[
                    "columns"
                ]
            )
        }

        self.assertEqual(
            columns[
                self.column.pk
            ][
                "task_ids"
            ],
            [
                self.task.pk,
                self.third.pk,
            ],
        )

        self.assertEqual(
            columns[
                self.target_column.pk
            ][
                "task_ids"
            ],
            [
                self.second.pk,
                self.target_first.pk,
            ],
        )

    def test_writer_sees_drag_controls(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.board_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.context[
                "can_drag_tasks"
            ]
        )

        self.assertContains(
            response,
            "data-task-board",
        )

        self.assertContains(
            response,
            "data-drag-handle",
        )

        self.assertContains(
            response,
            "sortablejs@1.15.7",
        )

        self.assertContains(
            response,
            "task-drag-drop.js",
        )

    def test_viewer_does_not_receive_drag_controls(
        self,
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.board_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.context[
                "can_drag_tasks"
            ]
        )

        self.assertNotContains(
            response,
            "data-drag-handle",
        )

        self.assertNotContains(
            response,
            "sortablejs@1.15.7",
        )

        self.assertNotContains(
            response,
            "task-drag-drop.js",
        )