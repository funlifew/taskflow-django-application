from django.urls import reverse

from apps.tasks.models import Task

from apps.tasks.tests.base import TaskTestBase


class TaskCreateViewTests(
    TaskTestBase
):
    def get_url(
        self,
        *,
        workspace=None,
        board=None,
        column=None,
    ):
        return reverse(
            "tasks:create",
            kwargs={
                "workspace_pk": (
                    workspace
                    or self.workspace
                ).pk,
                "board_pk": (
                    board
                    or self.board
                ).pk,
                "column_pk": (
                    column
                    or self.column
                ).pk,
            },
        )

    def get_valid_data(self):
        return {
            "title": "طراحی API",
            "description": (
                "پیاده‌سازی API اصلی"
            ),
            "priority": (
                Task.Priority.URGENT
            ),
            "assignee": self.admin.pk,
            "due_at": "2030-01-01T12:30",
        }

    def test_anonymous_user_is_redirected(
        self
    ):
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
                    self.get_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_viewer_cannot_open_create(
        self
    ):
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

    def test_outsider_cannot_open_create(
        self
    ):
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

    def test_valid_post_creates_task(self):
        initial_count = (
            Task.objects.count()
        )

        self.client.force_login(
            self.member
        )

        response = self.client.post(
            self.get_url(),
            data=self.get_valid_data(),
        )

        self.assertEqual(
            Task.objects.count(),
            initial_count + 1,
        )

        task = Task.objects.get(
            title="طراحی API",
        )

        self.assertEqual(
            task.column,
            self.column,
        )
        self.assertEqual(
            task.position,
            1,
        )
        self.assertEqual(
            task.priority,
            Task.Priority.URGENT,
        )
        self.assertEqual(
            task.status,
            Task.Status.TODO,
        )
        self.assertEqual(
            task.assignee,
            self.admin,
        )
        self.assertEqual(
            task.created_by,
            self.member,
        )
        self.assertFalse(
            task.is_archived
        )
        self.assertIsNotNone(
            task.due_at
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

    def test_internal_fields_cannot_be_tampered_with(
        self
    ):
        self.client.force_login(
            self.member
        )

        data = self.get_valid_data()

        data.update(
            {
                "column": 999999,
                "position": 500,
                "status": (
                    Task.Status.DONE
                ),
                "created_by": (
                    self.outsider.pk
                ),
                "is_archived": True,
            }
        )

        self.client.post(
            self.get_url(),
            data=data,
        )

        task = Task.objects.get(
            title="طراحی API",
        )

        self.assertEqual(
            task.column,
            self.column,
        )
        self.assertEqual(
            task.position,
            1,
        )
        self.assertEqual(
            task.status,
            Task.Status.TODO,
        )
        self.assertEqual(
            task.created_by,
            self.member,
        )
        self.assertFalse(
            task.is_archived
        )

    def test_outsider_cannot_be_assigned(
        self
    ):
        initial_count = (
            Task.objects.count()
        )

        self.client.force_login(
            self.owner
        )

        data = self.get_valid_data()

        data["assignee"] = (
            self.outsider.pk
        )

        response = self.client.post(
            self.get_url(),
            data=data,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            Task.objects.count(),
            initial_count,
        )

        self.assertIn(
            "assignee",
            response.context[
                "form"
            ].errors,
        )

    def test_invalid_title_does_not_create_task(
        self
    ):
        initial_count = (
            Task.objects.count()
        )

        self.client.force_login(
            self.owner
        )

        data = self.get_valid_data()
        data["title"] = "ت"

        response = self.client.post(
            self.get_url(),
            data=data,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            Task.objects.count(),
            initial_count,
        )

    def test_archived_column_returns_404(
        self
    ):
        archived_column = (
            self.create_column(
                title="Archived Column",
                position=8,
                is_archived=True,
            )
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url(
                column=archived_column,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_archived_board_returns_404(
        self
    ):
        archived_board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )

        archived_board_column = (
            self.create_column(
                board=archived_board,
                title="Archived Board Column",
                position=0,
            )
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url(
                board=archived_board,
                column=archived_board_column,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_column_from_another_board_returns_404(
        self
    ):
        other_board = self.create_board(
            title="Other Board",
        )

        other_column = self.create_column(
            board=other_board,
            title="Other Column",
            position=0,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_url(
                board=self.board,
                column=other_column,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

class BoardDetailTaskIntegrationTests(
    TaskTestBase
):
    def get_board_url(self):
        return reverse(
            "boards:detail",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
            },
        )

    def test_active_tasks_are_displayed(
        self
    ):
        second_task = self.create_task(
            title="Task دوم",
            position=1,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_board_url()
        )

        self.assertContains(
            response,
            self.task.title,
        )
        self.assertContains(
            response,
            second_task.title,
        )

    def test_archived_tasks_are_hidden(
        self
    ):
        archived_task = self.create_task(
            title="Task آرشیوشده",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_board_url()
        )

        self.assertNotContains(
            response,
            archived_task.title,
        )

    def test_tasks_follow_position_order(
        self
    ):
        second_task = self.create_task(
            title="Task دوم",
            position=1,
        )

        third_task = self.create_task(
            title="Task سوم",
            position=2,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_board_url()
        )

        first_column = (
            response.context[
                "columns"
            ][0]
        )

        self.assertEqual(
            first_column.active_tasks,
            [
                self.task,
                second_task,
                third_task,
            ],
        )

    def test_total_task_count_is_available(
        self
    ):
        self.create_task(
            title="Task دوم",
            position=1,
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.get_board_url()
        )

        self.assertEqual(
            response.context[
                "tasks_count"
            ],
            2,
        )

    def test_member_sees_create_task_link(
        self
    ):
        self.client.force_login(
            self.member
        )

        response = self.client.get(
            self.get_board_url()
        )

        create_url = reverse(
            "tasks:create",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": (
                    self.column.pk
                ),
            },
        )

        self.assertContains(
            response,
            create_url,
        )

    def test_viewer_does_not_see_create_task_link(
        self
    ):
        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.get_board_url()
        )

        create_url = reverse(
            "tasks:create",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": (
                    self.column.pk
                ),
            },
        )

        self.assertNotContains(
            response,
            create_url,
        )

        self.assertFalse(
            response.context[
                "can_create_tasks"
            ]
        )