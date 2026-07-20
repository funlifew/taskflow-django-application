from apps.columns.tests.base import (
    ColumnTestBase,
)

from apps.tasks.models import Task


class TaskTestBase(ColumnTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task = Task.objects.create(
            column=cls.column,
            title="پیاده‌سازی مدل Task",
            description="Task model foundation",
            priority=Task.Priority.HIGH,
            status=Task.Status.TODO,
            position=0,
            assignee=cls.member,
            created_by=cls.owner,
        )

    def create_task(
        self,
        *,
        column=None,
        title="Task جدید",
        description="",
        priority=Task.Priority.MEDIUM,
        status=Task.Status.TODO,
        position=None,
        assignee=None,
        created_by=None,
        due_at=None,
        is_archived=False,
    ):
        column = column or self.column

        if position is None:
            position = (
                Task.objects.next_position(
                    column=column,
                )
            )

        if created_by is None:
            created_by = self.owner

        return Task.objects.create(
            column=column,
            title=title,
            description=description,
            priority=priority,
            status=status,
            position=position,
            assignee=assignee,
            created_by=created_by,
            due_at=due_at,
            is_archived=is_archived,
        )