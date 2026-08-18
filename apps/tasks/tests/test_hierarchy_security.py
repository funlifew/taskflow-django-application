import json

from django.urls import reverse

from apps.tasks.models import (
    Task,
    TaskComment,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)
from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
)


class ResourceHierarchySecurityTests(
    TaskTestBase
):
    """
    Regression tests for nested-resource
    identifier tampering.

    The authenticated user intentionally
    owns both workspaces used by these tests.

    Therefore a 404 response demonstrates
    hierarchy scoping rather than a simple
    lack of permission to the foreign
    resource.
    """

    def setUp(self):
        super().setUp()

        self.foreign_workspace = (
            Workspace.objects.create(
                name="Foreign Workspace",
                owner=self.owner,
            )
        )

        WorkspaceMembership.objects.create(
            workspace=(
                self.foreign_workspace
            ),
            user=self.owner,
            role=(
                WorkspaceMembership
                .Role
                .OWNER
            ),
        )

        self.foreign_board = (
            self.create_board(
                workspace=(
                    self.foreign_workspace
                ),
                title="Foreign Board",
                created_by=self.owner,
            )
        )

        self.foreign_column = (
            self.create_column(
                board=self.foreign_board,
                title="Foreign Column",
                position=0,
                created_by=self.owner,
            )
        )

        self.foreign_task = (
            self.create_task(
                column=self.foreign_column,
                title="Foreign Task",
                position=0,
                assignee=self.owner,
                created_by=self.owner,
            )
        )

    def local_task_url(
        self,
        name,
        *,
        task=None,
    ):
        """
        Build a deliberately mismatched
        nested URL.

        Workspace, board and column belong
        to the local hierarchy while the
        task belongs to the foreign one.
        """

        task = (
            task
            or self.foreign_task
        )

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
                    self.column.pk
                ),
                "task_pk": task.pk,
            },
        )

    def test_foreign_board_cannot_be_archived_through_local_workspace_url(
        self,
    ):
        url = reverse(
            "boards:archive",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.foreign_board.pk
                ),
            },
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.foreign_board.refresh_from_db()

        self.assertFalse(
            self.foreign_board.is_archived
        )

    def test_foreign_column_cannot_be_archived_through_local_board_url(
        self,
    ):
        url = reverse(
            "columns:archive",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": (
                    self.board.pk
                ),
                "column_pk": (
                    self.foreign_column.pk
                ),
            },
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.foreign_column.refresh_from_db()

        self.assertFalse(
            self.foreign_column.is_archived
        )

    def test_foreign_task_status_cannot_be_changed_through_local_column_url(
        self,
    ):
        original_status = (
            self.foreign_task.status
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.local_task_url(
                "status"
            ),
            data={
                "status": (
                    Task.Status.DONE
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.foreign_task.refresh_from_db()

        self.assertEqual(
            self.foreign_task.status,
            original_status,
        )

    def test_foreign_task_cannot_be_archived_through_local_column_url(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.local_task_url(
                "archive"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.foreign_task.refresh_from_db()

        self.assertFalse(
            self.foreign_task.is_archived
        )

    def test_foreign_archived_task_cannot_be_deleted_through_local_column_url(
        self,
    ):
        archived_task = (
            self.create_task(
                column=(
                    self.foreign_column
                ),
                title=(
                    "Foreign Archived Task"
                ),
                position=1,
                created_by=self.owner,
                is_archived=True,
            )
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.local_task_url(
                "delete",
                task=archived_task,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            Task.objects.filter(
                pk=archived_task.pk,
            ).exists()
        )

    def test_foreign_task_cannot_be_dragged_through_local_source_column_url(
        self,
    ):
        original_column_id = (
            self.foreign_task.column_id
        )

        original_position = (
            self.foreign_task.position
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.local_task_url(
                "drag_reorder"
            ),
            data=json.dumps(
                {
                    "target_column": (
                        self.column.pk
                    ),
                    "target_position": 0,
                }
            ),
            content_type=(
                "application/json"
            ),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.foreign_task.refresh_from_db()

        self.assertEqual(
            self.foreign_task.column_id,
            original_column_id,
        )

        self.assertEqual(
            self.foreign_task.position,
            original_position,
        )

    def test_comment_cannot_be_created_for_foreign_task_through_local_hierarchy(
        self,
    ):
        initial_count = (
            TaskComment.objects.count()
        )

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            self.local_task_url(
                "comment_create"
            ),
            data={
                "body": (
                    "Unauthorized comment"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            TaskComment.objects.count(),
            initial_count,
        )