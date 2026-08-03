from datetime import timedelta

from django.utils import timezone

from apps.dashboard.metrics import (
    calculate_progress_percentage,
    get_board_progress,
    get_user_board_summaries,
    get_user_dashboard_summary,
    get_user_task_progress,
    get_user_workspace_summaries,
    get_workspace_progress,
)
from apps.notifications.models import (
    Notification,
)
from apps.tasks.models import Task
from apps.tasks.tests.base import (
    TaskTestBase,
)


class DashboardProgressTests(
    TaskTestBase
):
    def test_empty_progress_is_zero(self):
        self.task.delete()

        progress = get_user_task_progress(
            user=self.member,
        )

        self.assertEqual(
            progress["total"],
            0,
        )
        self.assertEqual(
            progress[
                "progress_percentage"
            ],
            0,
        )

    def test_percentage_is_rounded(self):
        self.assertEqual(
            calculate_progress_percentage(
                completed=2,
                total=3,
            ),
            67,
        )

    def test_canceled_tasks_are_excluded_from_progress(
        self,
    ):
        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        self.create_task(
            title="Blocked",
            assignee=self.member,
            status=Task.Status.BLOCKED,
        )

        self.create_task(
            title="Canceled",
            assignee=self.member,
            status=Task.Status.CANCELED,
        )

        progress = get_user_task_progress(
            user=self.member,
        )

        self.assertEqual(
            progress["total"],
            3,
        )
        self.assertEqual(
            progress["completed"],
            1,
        )
        self.assertEqual(
            progress["todo"],
            1,
        )
        self.assertEqual(
            progress["blocked"],
            1,
        )
        self.assertEqual(
            progress[
                "progress_percentage"
            ],
            33,
        )

    def test_workspace_progress(self):
        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        progress = get_workspace_progress(
            user=self.member,
            workspace=self.workspace,
        )

        self.assertEqual(
            progress["total"],
            2,
        )
        self.assertEqual(
            progress["completed"],
            1,
        )
        self.assertEqual(
            progress[
                "progress_percentage"
            ],
            50,
        )

    def test_board_progress(self):
        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        progress = get_board_progress(
            user=self.member,
            board=self.board,
        )

        self.assertEqual(
            progress["total"],
            2,
        )
        self.assertEqual(
            progress["completed"],
            1,
        )


class DashboardSummaryTests(
    TaskTestBase
):
    def test_dashboard_summary(self):
        now = timezone.now()

        self.create_task(
            title="Overdue",
            assignee=self.member,
            due_at=(
                now
                - timedelta(days=1)
            ),
        )

        self.create_task(
            title="Due soon",
            assignee=self.member,
            status=(
                Task.Status.IN_PROGRESS
            ),
            due_at=(
                now
                + timedelta(days=2)
            ),
        )

        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
            due_at=(
                now
                - timedelta(days=2)
            ),
        )

        self.create_task(
            title="Canceled",
            assignee=self.member,
            status=Task.Status.CANCELED,
            due_at=(
                now
                - timedelta(days=3)
            ),
        )

        Notification.objects.create(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="Unread",
            is_read=False,
            read_at=None,
        )

        Notification.objects.create(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="Read",
            is_read=True,
            read_at=now,
        )

        summary = (
            get_user_dashboard_summary(
                user=self.member,
                now=now,
            )
        )

        self.assertEqual(
            summary[
                "workspaces_count"
            ],
            1,
        )
        self.assertEqual(
            summary["boards_count"],
            1,
        )
        self.assertEqual(
            summary[
                "assigned_tasks_count"
            ],
            5,
        )
        self.assertEqual(
            summary[
                "overdue_tasks_count"
            ],
            1,
        )
        self.assertEqual(
            summary[
                "due_soon_tasks_count"
            ],
            1,
        )
        self.assertEqual(
            summary[
                "completed_tasks_count"
            ],
            1,
        )
        self.assertEqual(
            summary[
                "unread_notifications_count"
            ],
            1,
        )

    def test_workspace_summary_calculates_progress(
        self,
    ):
        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        self.create_task(
            title="Canceled",
            assignee=self.member,
            status=Task.Status.CANCELED,
        )

        summaries = (
            get_user_workspace_summaries(
                user=self.member,
                limit=None,
            )
        )

        summary = next(
            item
            for item in summaries
            if (
                item["workspace"].pk
                == self.workspace.pk
            )
        )

        self.assertEqual(
            summary["boards_count"],
            1,
        )
        self.assertEqual(
            summary["tasks_count"],
            3,
        )
        self.assertEqual(
            summary["progress_total"],
            2,
        )
        self.assertEqual(
            summary[
                "completed_tasks_count"
            ],
            1,
        )
        self.assertEqual(
            summary[
                "progress_percentage"
            ],
            50,
        )

    def test_board_summary_calculates_progress(
        self,
    ):
        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        summaries = (
            get_user_board_summaries(
                user=self.member,
                limit=None,
            )
        )

        summary = next(
            item
            for item in summaries
            if (
                item["board"].pk
                == self.board.pk
            )
        )

        self.assertEqual(
            summary["columns_count"],
            1,
        )
        self.assertEqual(
            summary["tasks_count"],
            2,
        )
        self.assertEqual(
            summary[
                "completed_tasks_count"
            ],
            1,
        )
        self.assertEqual(
            summary[
                "progress_percentage"
            ],
            50,
        )