from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.tasks.models import Task
from apps.tasks.tests.base import TaskTestBase


class TaskHardeningViewTests(TaskTestBase):
    def task_url(
        self,
        name,
        *,
        task=None,
    ):
        task = task or self.task

        return reverse(
            f"tasks:{name}",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": (
                    task.column_id
                ),
                "task_pk": task.pk,
            },
        )

    def archived_list_url(self):
        return reverse(
            "tasks:archived_list",
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

    def test_create_form_does_not_offer_viewer(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            reverse(
                "tasks:create",
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
                },
            )
        )

        queryset = (
            response.context[
                "form"
            ].fields[
                "assignee"
            ].queryset
        )

        self.assertNotIn(
            self.viewer,
            queryset,
        )

    def test_update_form_does_not_offer_viewer(
        self,
    ):
        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            self.task_url("update")
        )

        queryset = (
            response.context[
                "form"
            ].fields[
                "assignee"
            ].queryset
        )

        self.assertNotIn(
            self.viewer,
            queryset,
        )

    def test_archive_view_sets_archived_at(self):
        self.client.force_login(
            self.member
        )

        self.client.post(
            self.task_url("archive")
        )

        self.task.refresh_from_db()

        self.assertTrue(
            self.task.is_archived
        )
        self.assertIsNotNone(
            self.task.archived_at
        )

    def test_restore_view_clears_archived_at(
        self,
    ):
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.member
        )

        self.client.post(
            self.task_url(
                "restore",
                task=archived,
            )
        )

        archived.refresh_from_db()

        self.assertFalse(
            archived.is_archived
        )
        self.assertIsNone(
            archived.archived_at
        )

    def test_archived_list_orders_by_archived_at(
        self,
    ):
        older = self.create_task(
            title="Older archive",
            position=20,
            is_archived=True,
            archived_at=(
                timezone.now()
                - timedelta(days=2)
            ),
        )
        newer = self.create_task(
            title="Newer archive",
            position=21,
            is_archived=True,
            archived_at=timezone.now(),
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.archived_list_url()
        )

        tasks = list(
            response.context["tasks"]
        )

        self.assertLess(
            tasks.index(newer),
            tasks.index(older),
        )

    def test_archived_list_contains_only_consistent_archive_rows(
        self,
    ):
        archived = self.create_task(
            title="Archived",
            position=20,
            is_archived=True,
        )

        self.client.force_login(
            self.viewer
        )

        response = self.client.get(
            self.archived_list_url()
        )

        self.assertContains(
            response,
            archived.title,
        )
        self.assertNotContains(
            response,
            self.task.title,
        )
