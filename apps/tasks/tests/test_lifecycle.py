from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.tasks.models import Task
from apps.tasks.tests.base import TaskTestBase


class TaskLifecycleTestBase(TaskTestBase):
    def task_url(
        self,
        name,
        *,
        task=None,
        column=None,
        board=None,
        workspace=None,
    ):
        task = task or self.task
        column = column or task.column
        board = board or column.board
        workspace = (
            workspace
            or board.workspace
        )

        return reverse(
            f"tasks:{name}",
            kwargs={
                "workspace_pk": workspace.pk,
                "board_pk": board.pk,
                "column_pk": column.pk,
                "task_pk": task.pk,
            },
        )

    def detail_url(self, **kwargs):
        return self.task_url(
            "detail",
            **kwargs,
        )

    def update_url(self, **kwargs):
        return self.task_url(
            "update",
            **kwargs,
        )

    def status_url(self, **kwargs):
        return self.task_url(
            "status",
            **kwargs,
        )

    def move_url(self, **kwargs):
        return self.task_url(
            "move",
            **kwargs,
        )

    def archive_url(self, **kwargs):
        return self.task_url(
            "archive",
            **kwargs,
        )

    def restore_url(self, **kwargs):
        return self.task_url(
            "restore",
            **kwargs,
        )

    def delete_url(self, **kwargs):
        return self.task_url(
            "delete",
            **kwargs,
        )

    def archived_list_url(
        self,
        *,
        column=None,
        board=None,
        workspace=None,
    ):
        column = column or self.column
        board = board or column.board
        workspace = (
            workspace
            or board.workspace
        )

        return reverse(
            "tasks:archived_list",
            kwargs={
                "workspace_pk": workspace.pk,
                "board_pk": board.pk,
                "column_pk": column.pk,
            },
        )

    def get_update_data(self):
        return {
            "title": "عنوان ویرایش‌شده",
            "description": (
                "توضیحات ویرایش‌شده"
            ),
            "priority": Task.Priority.URGENT,
            "assignee": self.admin.pk,
            "due_at": "2031-02-03T11:45",
        }


class TaskDetailViewTests(
    TaskLifecycleTestBase
):
    def test_anonymous_user_is_redirected(self):
        response = self.client.get(
            self.detail_url()
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_all_workspace_roles_can_view_task(
        self,
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
                    self.detail_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.client.logout()

    def test_outsider_cannot_view_task(self):
        self.client.force_login(
            self.outsider
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_context_contains_correct_hierarchy(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertEqual(
            response.context["workspace"],
            self.workspace,
        )
        self.assertEqual(
            response.context["board"],
            self.board,
        )
        self.assertEqual(
            response.context["column"],
            self.column,
        )
        self.assertEqual(
            response.context["task"],
            self.task,
        )

    def test_viewer_has_read_only_context(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.detail_url()
        )

        self.assertFalse(
            response.context[
                "can_update_task"
            ]
        )
        self.assertFalse(
            response.context[
                "can_move_task"
            ]
        )
        self.assertFalse(
            response.context[
                "can_archive_task"
            ]
        )
        self.assertNotContains(
            response,
            self.update_url(),
        )
        self.assertNotContains(
            response,
            self.move_url(),
        )
        self.assertNotContains(
            response,
            self.archive_url(),
        )

    def test_archived_task_returns_404(self):
        archived_task = self.create_task(
            title="Archived",
            position=9,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_task_from_another_column_returns_404(
        self,
    ):
        other_column = self.create_column(
            title="Other Column",
            position=1,
        )
        other_task = self.create_task(
            column=other_column,
            title="Other Task",
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url(
                task=other_task,
                column=self.column,
                board=self.board,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_task_under_archived_column_returns_404(
        self,
    ):
        archived_column = (
            self.create_column(
                title="Archived Column",
                position=20,
                is_archived=True,
            )
        )
        task = self.create_task(
            column=archived_column,
            title="Hidden Task",
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url(
                task=task,
                column=archived_column,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_task_under_archived_board_returns_404(
        self,
    ):
        archived_board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )
        column = self.create_column(
            board=archived_board,
            title="Column",
            position=0,
        )
        task = self.create_task(
            column=column,
            title="Task",
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.detail_url(
                task=task,
                column=column,
                board=archived_board,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class TaskUpdateViewTests(
    TaskLifecycleTestBase
):
    def test_owner_admin_and_member_can_open_update(
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
                    self.update_url()
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
            self.update_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_update(self):
        self.client.force_login(
            self.outsider
        )

        response = self.client.get(
            self.update_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_valid_post_updates_editable_fields(
        self,
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.update_url(),
            data=self.get_update_data(),
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.title,
            "عنوان ویرایش‌شده",
        )
        self.assertEqual(
            self.task.description,
            "توضیحات ویرایش‌شده",
        )
        self.assertEqual(
            self.task.priority,
            Task.Priority.URGENT,
        )
        self.assertEqual(
            self.task.assignee,
            self.admin,
        )
        self.assertEqual(
            self.task.due_at.year,
            2031,
        )

        self.assertRedirects(
            response,
            self.detail_url(),
        )

    def test_update_preserves_protected_fields(
        self,
    ):
        original_column = self.task.column
        original_position = self.task.position
        original_status = self.task.status
        original_creator = self.task.created_by

        data = self.get_update_data()
        data.update(
            {
                "column": 999999,
                "position": 999,
                "status": Task.Status.DONE,
                "created_by": self.outsider.pk,
                "is_archived": True,
            }
        )

        self.client.force_login(
            self.owner
        )
        self.client.post(
            self.update_url(),
            data=data,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.column,
            original_column,
        )
        self.assertEqual(
            self.task.position,
            original_position,
        )
        self.assertEqual(
            self.task.status,
            original_status,
        )
        self.assertEqual(
            self.task.created_by,
            original_creator,
        )
        self.assertFalse(
            self.task.is_archived
        )

    def test_outsider_assignee_is_rejected(self):
        data = self.get_update_data()
        data["assignee"] = (
            self.outsider.pk
        )

        original_title = self.task.title

        self.client.force_login(
            self.owner
        )
        response = self.client.post(
            self.update_url(),
            data=data,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertIn(
            "assignee",
            response.context[
                "form"
            ].errors,
        )
        self.assertEqual(
            self.task.title,
            original_title,
        )

    def test_update_refreshes_parent_timestamps(
        self,
    ):
        old_time = (
            timezone.now()
            - timedelta(days=1)
        )

        Board.objects.filter(
            pk=self.board.pk
        ).update(updated_at=old_time)
        Column.objects.filter(
            pk=self.column.pk
        ).update(updated_at=old_time)

        self.client.force_login(
            self.owner
        )
        self.client.post(
            self.update_url(),
            data=self.get_update_data(),
        )

        self.board.refresh_from_db()
        self.column.refresh_from_db()

        self.assertGreater(
            self.board.updated_at,
            old_time,
        )
        self.assertGreater(
            self.column.updated_at,
            old_time,
        )

    def test_archived_task_cannot_be_updated(
        self,
    ):
        archived_task = self.create_task(
            title="Archived",
            position=9,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.update_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_wrong_column_returns_404(self):
        other_column = self.create_column(
            title="Other",
            position=1,
        )
        other_task = self.create_task(
            column=other_column,
            title="Other Task",
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.update_url(
                task=other_task,
                column=self.column,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class TaskStatusUpdateViewTests(
    TaskLifecycleTestBase
):
    def test_status_only_accepts_post(self):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.status_url()
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_owner_admin_and_member_can_update_status(
        self,
    ):
        for index, user in enumerate(
            (
                self.owner,
                self.admin,
                self.member,
            ),
            start=1,
        ):
            task = self.create_task(
                title=f"Status Task {index}",
            )

            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.post(
                    self.status_url(
                        task=task,
                    ),
                    data={
                        "status": (
                            Task.Status.DONE
                        ),
                    },
                )

                task.refresh_from_db()

                self.assertEqual(
                    task.status,
                    Task.Status.DONE,
                )
                self.assertEqual(
                    response.status_code,
                    302,
                )
                self.client.logout()

    def test_viewer_cannot_update_status(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.status_url(),
            data={
                "status": Task.Status.DONE,
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_invalid_status_does_not_change_task(
        self,
    ):
        original_status = self.task.status

        self.client.force_login(
            self.owner
        )
        response = self.client.post(
            self.status_url(),
            data={
                "status": "invalid",
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            original_status,
        )
        self.assertRedirects(
            response,
            self.detail_url(),
        )

    def test_status_update_preserves_other_fields(
        self,
    ):
        original_title = self.task.title
        original_column = self.task.column
        original_position = self.task.position
        original_creator = self.task.created_by

        self.client.force_login(
            self.owner
        )
        self.client.post(
            self.status_url(),
            data={
                "status": Task.Status.BLOCKED,
                "title": "Forged title",
                "column": 999999,
                "position": 999,
                "created_by": self.outsider.pk,
                "is_archived": True,
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            Task.Status.BLOCKED,
        )
        self.assertEqual(
            self.task.title,
            original_title,
        )
        self.assertEqual(
            self.task.column,
            original_column,
        )
        self.assertEqual(
            self.task.position,
            original_position,
        )
        self.assertEqual(
            self.task.created_by,
            original_creator,
        )
        self.assertFalse(
            self.task.is_archived
        )

    def test_archived_task_cannot_change_status(
        self,
    ):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.status_url(
                task=archived_task,
            ),
            data={
                "status": Task.Status.DONE,
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class TaskMoveViewTests(
    TaskLifecycleTestBase
):
    def test_owner_admin_and_member_can_open_move(
        self,
    ):
        self.create_column(
            title="Target",
            position=1,
        )

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
                    self.move_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.client.logout()

    def test_viewer_cannot_move(self):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.move_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_move_appends_to_target_and_normalizes_source(
        self,
    ):
        moving_task = self.create_task(
            title="Moving",
            position=1,
        )
        source_final = self.create_task(
            title="Source Final",
            position=2,
        )

        target_column = self.create_column(
            title="Target",
            position=1,
        )
        self.create_task(
            column=target_column,
            title="Target Existing",
            position=0,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.move_url(
                task=moving_task,
            ),
            data={
                "target_column": (
                    target_column.pk
                ),
            },
        )

        moving_task.refresh_from_db()
        source_final.refresh_from_db()

        self.assertEqual(
            moving_task.column,
            target_column,
        )
        self.assertEqual(
            moving_task.position,
            1,
        )
        self.assertEqual(
            source_final.position,
            1,
        )

        self.assertEqual(
            list(
                Task.objects
                .active()
                .for_column(self.column)
                .values_list(
                    "position",
                    flat=True,
                )
            ),
            [0, 1],
        )

        self.assertRedirects(
            response,
            self.detail_url(
                task=moving_task,
                column=target_column,
            ),
        )

    def test_move_preserves_task_metadata(self):
        target_column = self.create_column(
            title="Target",
            position=1,
        )

        original_status = self.task.status
        original_priority = (
            self.task.priority
        )
        original_assignee = (
            self.task.assignee
        )
        original_creator = (
            self.task.created_by
        )

        self.client.force_login(
            self.owner
        )
        self.client.post(
            self.move_url(),
            data={
                "target_column": (
                    target_column.pk
                ),
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            original_status,
        )
        self.assertEqual(
            self.task.priority,
            original_priority,
        )
        self.assertEqual(
            self.task.assignee,
            original_assignee,
        )
        self.assertEqual(
            self.task.created_by,
            original_creator,
        )

    def test_same_column_is_rejected(self):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.move_url(),
            data={
                "target_column": (
                    self.column.pk
                ),
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertIn(
            "target_column",
            response.context[
                "form"
            ].errors,
        )
        self.assertEqual(
            self.task.column,
            self.column,
        )

    def test_archived_target_column_is_rejected(
        self,
    ):
        target_column = self.create_column(
            title="Archived Target",
            position=8,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.move_url(),
            data={
                "target_column": (
                    target_column.pk
                ),
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertIn(
            "target_column",
            response.context[
                "form"
            ].errors,
        )
        self.assertEqual(
            self.task.column,
            self.column,
        )

    def test_other_board_target_is_rejected(self):
        other_board = self.create_board(
            title="Other Board",
        )
        target_column = self.create_column(
            board=other_board,
            title="Other Board Column",
            position=0,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.move_url(),
            data={
                "target_column": (
                    target_column.pk
                ),
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertIn(
            "target_column",
            response.context[
                "form"
            ].errors,
        )
        self.assertEqual(
            self.task.column,
            self.column,
        )

    def test_archived_task_cannot_be_moved(self):
        target_column = self.create_column(
            title="Target",
            position=1,
        )
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.move_url(
                task=archived_task,
            ),
            data={
                "target_column": (
                    target_column.pk
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class ArchivedTaskListViewTests(
    TaskLifecycleTestBase
):
    def test_all_workspace_roles_can_view_archive(
        self,
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

    def test_context_contains_correct_hierarchy(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.archived_list_url()
        )

        self.assertEqual(
            response.context["workspace"],
            self.workspace,
        )
        self.assertEqual(
            response.context["board"],
            self.board,
        )
        self.assertEqual(
            response.context["column"],
            self.column,
        )

    def test_only_archived_tasks_from_current_column_are_listed(
        self,
    ):
        archived_task = self.create_task(
            title="Archived Current",
            position=10,
            is_archived=True,
        )

        other_column = self.create_column(
            title="Other Column",
            position=1,
        )
        other_archived = self.create_task(
            column=other_column,
            title="Archived Other",
            position=10,
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
            archived_task.title,
        )
        self.assertNotContains(
            response,
            self.task.title,
        )
        self.assertNotContains(
            response,
            other_archived.title,
        )

    def test_permission_flags_match_roles(self):
        expectations = (
            (self.owner, True, True),
            (self.admin, True, True),
            (self.member, True, False),
            (self.viewer, False, False),
        )

        for (
            user,
            can_restore,
            can_delete,
        ) in expectations:
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
                    response.context[
                        "can_restore_tasks"
                    ],
                    can_restore,
                )
                self.assertEqual(
                    response.context[
                        "can_delete_tasks"
                    ],
                    can_delete,
                )
                self.client.logout()

    def test_archive_is_paginated_by_twelve(self):
        for index in range(13):
            self.create_task(
                title=f"Archived {index}",
                position=100,
                is_archived=True,
            )

        self.client.force_login(
            self.owner
        )

        first_page = self.client.get(
            self.archived_list_url()
        )
        second_page = self.client.get(
            self.archived_list_url()
            + "?page=2"
        )

        self.assertEqual(
            len(first_page.context["tasks"]),
            12,
        )
        self.assertEqual(
            len(second_page.context["tasks"]),
            1,
        )
        self.assertTrue(
            first_page.context[
                "is_paginated"
            ]
        )

    def test_viewer_does_not_see_restore_or_delete_actions(
        self,
    ):
        archived_task = self.create_task(
            title="Archived",
            position=10,
            is_archived=True,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.archived_list_url()
        )

        self.assertNotContains(
            response,
            self.restore_url(
                task=archived_task,
            ),
        )
        self.assertNotContains(
            response,
            self.delete_url(
                task=archived_task,
            ),
        )


class TaskArchiveViewTests(
    TaskLifecycleTestBase
):
    def test_archive_only_accepts_post(self):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.archive_url()
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_owner_admin_and_member_can_archive(
        self,
    ):
        for index, user in enumerate(
            (
                self.owner,
                self.admin,
                self.member,
            ),
            start=1,
        ):
            task = self.create_task(
                title=f"Archive {index}",
            )

            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.post(
                    self.archive_url(
                        task=task,
                    )
                )

                task.refresh_from_db()

                self.assertTrue(
                    task.is_archived
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
            self.archive_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_archiving_normalizes_positions(
        self,
    ):
        middle_task = self.create_task(
            title="Middle",
            position=1,
        )
        final_task = self.create_task(
            title="Final",
            position=2,
        )

        self.client.force_login(
            self.owner
        )
        self.client.post(
            self.archive_url(
                task=middle_task,
            )
        )

        middle_task.refresh_from_db()
        final_task.refresh_from_db()

        self.assertTrue(
            middle_task.is_archived
        )
        self.assertEqual(
            final_task.position,
            1,
        )
        self.assertEqual(
            list(
                Task.objects
                .active()
                .for_column(self.column)
                .values_list(
                    "position",
                    flat=True,
                )
            ),
            [0, 1],
        )

    def test_archived_task_cannot_be_archived_again(
        self,
    ):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.archive_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class TaskRestoreViewTests(
    TaskLifecycleTestBase
):
    def test_restore_only_accepts_post(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.restore_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_owner_admin_and_member_can_restore(
        self,
    ):
        for index, user in enumerate(
            (
                self.owner,
                self.admin,
                self.member,
            ),
            start=1,
        ):
            task = self.create_task(
                title=f"Restore {index}",
                position=50,
                is_archived=True,
            )

            with self.subTest(
                user=user.username
            ):
                self.client.force_login(
                    user
                )

                response = self.client.post(
                    self.restore_url(
                        task=task,
                    )
                )

                task.refresh_from_db()

                self.assertFalse(
                    task.is_archived
                )
                self.assertEqual(
                    response.status_code,
                    302,
                )
                self.client.logout()

    def test_restore_appends_task_to_end(self):
        self.create_task(
            title="Second Active",
            position=1,
        )
        archived_task = self.create_task(
            title="Archived",
            position=99,
            is_archived=True,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.restore_url(
                task=archived_task,
            )
        )

        archived_task.refresh_from_db()

        self.assertFalse(
            archived_task.is_archived
        )
        self.assertEqual(
            archived_task.position,
            2,
        )
        self.assertRedirects(
            response,
            self.detail_url(
                task=archived_task,
            ),
        )

    def test_viewer_cannot_restore(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.post(
            self.restore_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_active_task_cannot_be_restored(self):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.restore_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class TaskDeleteViewTests(
    TaskLifecycleTestBase
):
    def test_owner_and_admin_can_open_confirmation(
        self,
    ):
        for index, user in enumerate(
            (
                self.owner,
                self.admin,
            ),
            start=1,
        ):
            task = self.create_task(
                title=f"Delete {index}",
                position=50,
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
                        task=task,
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )
                self.assertEqual(
                    response.context[
                        "workspace"
                    ],
                    self.workspace,
                )
                self.assertEqual(
                    response.context[
                        "board"
                    ],
                    self.board,
                )
                self.assertEqual(
                    response.context[
                        "column"
                    ],
                    self.column,
                )
                self.client.logout()

    def test_member_cannot_delete(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.delete_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_viewer_cannot_delete(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.delete_url(
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_permanently_delete(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )
        task_pk = archived_task.pk

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.delete_url(
                task=archived_task,
            )
        )

        self.assertFalse(
            Task.objects.filter(
                pk=task_pk,
            ).exists()
        )
        self.assertRedirects(
            response,
            self.archived_list_url(),
        )

    def test_admin_can_permanently_delete(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )
        task_pk = archived_task.pk

        self.client.force_login(
            self.admin
        )

        self.client.post(
            self.delete_url(
                task=archived_task,
            )
        )

        self.assertFalse(
            Task.objects.filter(
                pk=task_pk,
            ).exists()
        )

    def test_active_task_cannot_be_deleted(self):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.delete_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_wrong_column_returns_404(self):
        archived_task = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )
        other_column = self.create_column(
            title="Other",
            position=1,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.delete_url(
                task=archived_task,
                column=other_column,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )
