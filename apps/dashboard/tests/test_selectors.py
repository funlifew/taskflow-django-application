from datetime import timedelta

from django.utils import timezone

from apps.boards.models import Board
from apps.columns.models import Column
from apps.dashboard.selectors import (
    get_accessible_workspaces,
    get_user_assigned_tasks,
    get_user_due_soon_tasks,
    get_user_overdue_tasks,
    get_user_recent_task_activities,
)
from apps.tasks.models import (
    Task,
    TaskActivity,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)
from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
)


class DashboardSelectorTests(
    TaskTestBase
):
    def test_accessible_workspaces_include_owned_and_joined(
        self,
    ):
        joined_workspace = (
            Workspace.objects.create(
                name="Joined",
                owner=self.outsider,
            )
        )

        WorkspaceMembership.objects.create(
            workspace=joined_workspace,
            user=self.member,
            role=(
                WorkspaceMembership
                .Role
                .MEMBER
            ),
        )

        inaccessible_workspace = (
            Workspace.objects.create(
                name="Inaccessible",
                owner=self.outsider,
            )
        )

        archived_workspace = (
            Workspace.objects.create(
                name="Archived",
                owner=self.outsider,
                is_archived=True,
            )
        )

        WorkspaceMembership.objects.create(
            workspace=archived_workspace,
            user=self.member,
            role=(
                WorkspaceMembership
                .Role
                .MEMBER
            ),
        )

        workspace_ids = set(
            get_accessible_workspaces(
                user=self.member,
            )
            .values_list(
                "pk",
                flat=True,
            )
        )

        self.assertIn(
            self.workspace.pk,
            workspace_ids,
        )
        self.assertIn(
            joined_workspace.pk,
            workspace_ids,
        )
        self.assertNotIn(
            inaccessible_workspace.pk,
            workspace_ids,
        )
        self.assertNotIn(
            archived_workspace.pk,
            workspace_ids,
        )

    def test_assigned_tasks_exclude_inactive_hierarchy(
        self,
    ):
        self.create_task(
            title="Other user",
            assignee=self.admin,
        )

        archived_task = self.create_task(
            title="Archived task",
            assignee=self.member,
            is_archived=True,
        )

        archived_board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )

        archived_board_column = (
            self.create_column(
                board=archived_board,
                title="Column",
                position=0,
            )
        )

        self.create_task(
            column=archived_board_column,
            title="Archived board task",
            assignee=self.member,
        )

        archived_column = self.create_column(
            title="Archived Column",
            position=50,
            is_archived=True,
        )

        self.create_task(
            column=archived_column,
            title="Archived column task",
            assignee=self.member,
        )

        task_ids = set(
            get_user_assigned_tasks(
                user=self.member,
            )
            .values_list(
                "pk",
                flat=True,
            )
        )

        self.assertIn(
            self.task.pk,
            task_ids,
        )
        self.assertNotIn(
            archived_task.pk,
            task_ids,
        )

        self.assertEqual(
            task_ids,
            {
                self.task.pk,
            },
        )

    def test_overdue_tasks_exclude_done_and_canceled(
        self,
    ):
        now = timezone.now()

        overdue = self.create_task(
            title="Overdue",
            assignee=self.member,
            due_at=(
                now
                - timedelta(days=1)
            ),
        )

        self.create_task(
            title="Done overdue",
            assignee=self.member,
            status=Task.Status.DONE,
            due_at=(
                now
                - timedelta(days=2)
            ),
        )

        self.create_task(
            title="Canceled overdue",
            assignee=self.member,
            status=Task.Status.CANCELED,
            due_at=(
                now
                - timedelta(days=3)
            ),
        )

        task_ids = set(
            get_user_overdue_tasks(
                user=self.member,
                now=now,
            )
            .values_list(
                "pk",
                flat=True,
            )
        )

        self.assertEqual(
            task_ids,
            {
                overdue.pk,
            },
        )

    def test_due_soon_uses_seven_day_window(
        self,
    ):
        now = timezone.now()

        due_soon = self.create_task(
            title="Due soon",
            assignee=self.member,
            due_at=(
                now
                + timedelta(days=3)
            ),
        )

        self.create_task(
            title="Too late",
            assignee=self.member,
            due_at=(
                now
                + timedelta(days=8)
            ),
        )

        self.create_task(
            title="Already overdue",
            assignee=self.member,
            due_at=(
                now
                - timedelta(hours=1)
            ),
        )

        task_ids = set(
            get_user_due_soon_tasks(
                user=self.member,
                now=now,
                days=7,
            )
            .values_list(
                "pk",
                flat=True,
            )
        )

        self.assertEqual(
            task_ids,
            {
                due_soon.pk,
            },
        )

    def test_recent_activities_are_scoped_to_accessible_workspaces(
        self,
    ):
        visible_activity = (
            TaskActivity.objects.create(
                task=self.task,
                actor=self.owner,
                action=(
                    TaskActivity
                    .Action
                    .UPDATED
                ),
                metadata={},
            )
        )

        other_workspace = (
            Workspace.objects.create(
                name="Private",
                owner=self.outsider,
            )
        )

        other_board = Board.objects.create(
            workspace=other_workspace,
            title="Private Board",
            created_by=self.outsider,
        )

        other_column = Column.objects.create(
            board=other_board,
            title="Private Column",
            position=0,
            created_by=self.outsider,
        )

        other_task = Task.objects.create(
            column=other_column,
            title="Private Task",
            description="",
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
            position=0,
            assignee=self.outsider,
            created_by=self.outsider,
        )

        hidden_activity = (
            TaskActivity.objects.create(
                task=other_task,
                actor=self.outsider,
                action=(
                    TaskActivity
                    .Action
                    .UPDATED
                ),
                metadata={},
            )
        )

        activity_ids = {
            activity.pk
            for activity in (
                get_user_recent_task_activities(
                    user=self.member,
                    limit=None,
                )
            )
        }

        self.assertIn(
            visible_activity.pk,
            activity_ids,
        )
        self.assertNotIn(
            hidden_activity.pk,
            activity_ids,
        )