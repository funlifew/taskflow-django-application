from datetime import timedelta

from django.contrib.auth import (
    get_user_model,
)
from django.core.exceptions import (
    ValidationError,
)
from django.db import (
    IntegrityError,
    transaction,
)
from django.utils import timezone

from apps.tasks.models import Task

from apps.tasks.tests.base import TaskTestBase


User = get_user_model()


class TaskModelTests(TaskTestBase):
    def test_task_belongs_to_column(self):
        self.assertEqual(
            self.task.column,
            self.column,
        )

        self.assertIn(
            self.task,
            self.column.tasks.all(),
        )

    def test_task_defaults(self):
        task = self.create_task(
            title="Default Task",
        )

        self.assertEqual(
            task.priority,
            Task.Priority.MEDIUM,
        )
        self.assertEqual(
            task.status,
            Task.Status.TODO,
        )
        self.assertFalse(
            task.is_archived
        )

    def test_task_string_representation(self):
        self.assertEqual(
            str(self.task),
            self.task.title,
        )

    def test_tasks_are_ordered_by_position(self):
        second_task = self.create_task(
            title="Second",
            position=1,
        )

        third_task = self.create_task(
            title="Third",
            position=2,
        )

        tasks = list(
            Task.objects.for_column(
                self.column
            )
        )

        self.assertEqual(
            tasks,
            [
                self.task,
                second_task,
                third_task,
            ],
        )

    def test_active_queryset(self):
        archived_task = self.create_task(
            title="Archived",
            position=10,
            is_archived=True,
        )

        self.assertIn(
            self.task,
            Task.objects.active(),
        )
        self.assertNotIn(
            archived_task,
            Task.objects.active(),
        )

    def test_archived_queryset(self):
        archived_task = self.create_task(
            title="Archived",
            position=10,
            is_archived=True,
        )

        self.assertIn(
            archived_task,
            Task.objects.archived(),
        )
        self.assertNotIn(
            self.task,
            Task.objects.archived(),
        )

    def test_assigned_to_queryset(self):
        tasks = Task.objects.assigned_to(
            self.member
        )

        self.assertIn(
            self.task,
            tasks,
        )

    def test_next_position_for_empty_column(self):
        other_column = self.create_column(
            title="Other Column",
            position=1,
        )

        position = (
            Task.objects.next_position(
                column=other_column,
            )
        )

        self.assertEqual(
            position,
            0,
        )

    def test_next_position_appends_to_end(self):
        self.create_task(
            title="Second",
            position=1,
        )

        position = (
            Task.objects.next_position(
                column=self.column,
            )
        )

        self.assertEqual(
            position,
            2,
        )

    def test_next_position_ignores_archived_tasks(
        self
    ):
        self.create_task(
            title="Archived",
            position=100,
            is_archived=True,
        )

        position = (
            Task.objects.next_position(
                column=self.column,
            )
        )

        self.assertEqual(
            position,
            1,
        )

    def test_active_positions_are_unique_per_column(
        self
    ):
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                self.create_task(
                    title="Duplicate",
                    position=0,
                )

    def test_archived_tasks_may_share_positions(
        self
    ):
        first = self.create_task(
            title="Archived One",
            position=7,
            is_archived=True,
        )

        second = self.create_task(
            title="Archived Two",
            position=7,
            is_archived=True,
        )

        self.assertEqual(
            first.position,
            second.position,
        )

    def test_same_position_in_different_columns(
        self
    ):
        other_column = self.create_column(
            title="Other Column",
            position=1,
        )

        other_task = self.create_task(
            column=other_column,
            title="Other Task",
            position=0,
        )

        self.assertEqual(
            other_task.position,
            self.task.position,
        )

    def test_workspace_member_is_valid_assignee(
        self
    ):
        self.task.full_clean()

    def test_workspace_owner_is_valid_assignee(
        self
    ):
        task = self.create_task(
            title="Owner Task",
            assignee=self.owner,
        )

        task.full_clean()

    def test_outsider_is_invalid_assignee(self):
        task = self.create_task(
            title="Invalid Assignment",
            assignee=self.outsider,
        )

        with self.assertRaises(
            ValidationError
        ):
            task.full_clean()

    def test_due_at_is_optional(self):
        task = self.create_task(
            title="No Due Date",
        )

        self.assertIsNone(
            task.due_at
        )

    def test_due_at_can_be_stored(self):
        due_at = (
            timezone.now()
            + timedelta(days=3)
        )

        task = self.create_task(
            title="Scheduled Task",
            due_at=due_at,
        )

        self.assertEqual(
            task.due_at,
            due_at,
        )

    def test_deleting_column_deletes_tasks(self):
        other_column = self.create_column(
            title="Temporary Column",
            position=1,
        )

        task = self.create_task(
            column=other_column,
            title="Temporary Task",
        )

        task_pk = task.pk

        other_column.delete()

        self.assertFalse(
            Task.objects.filter(
                pk=task_pk,
            ).exists()
        )

    def test_deleting_assignee_keeps_task(self):
        assignee = User.objects.create_user(
            username="temporary-assignee",
            first_name="Temporary",
            last_name="Assignee",
            email="temporary-assignee@example.com",
            password="StrongPassword123!",
        )

        task = self.create_task(
            title="Assigned Task",
            assignee=assignee,
        )

        assignee.delete()
        task.refresh_from_db()

        self.assertIsNone(
            task.assignee
        )

    def test_deleting_creator_keeps_task(self):
        creator = User.objects.create_user(
            username="temporary-creator",
            first_name="Temporary",
            last_name="Creator",
            email="temporary-creator@example.com",
            password="StrongPassword123!",
        )

        task = self.create_task(
            title="Created Task",
            created_by=creator,
        )

        creator.delete()
        task.refresh_from_db()

        self.assertIsNone(
            task.created_by
        )

    def test_task_has_timestamps(self):
        self.assertIsNotNone(
            self.task.created_at
        )
        self.assertIsNotNone(
            self.task.updated_at
        )