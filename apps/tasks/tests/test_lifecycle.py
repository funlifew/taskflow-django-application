from django.urls import reverse

from apps.tasks.models import Task

from apps.tasks.tests.base import TaskTestBase


class TaskLifecycleTestBase(
    TaskTestBase
):
    def detail_url(
        self,
        task=None,
        column=None,
    ):
        task = task or self.task
        column = column or task.column

        return reverse(
            "tasks:detail",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
                "task_pk": task.pk,
            },
        )

    def update_url(self, task=None):
        task = task or self.task

        return reverse(
            "tasks:update",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": task.column_id,
                "task_pk": task.pk,
            },
        )

    def archive_url(self, task=None):
        task = task or self.task

        return reverse(
            "tasks:archive",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": task.column_id,
                "task_pk": task.pk,
            },
        )

    def archived_list_url(
        self,
        column=None,
    ):
        column = column or self.column

        return reverse(
            "tasks:archived_list",
            kwargs={
                "workspace_pk": (
                    self.workspace.pk
                ),
                "board_pk": self.board.pk,
                "column_pk": column.pk,
            },
        )