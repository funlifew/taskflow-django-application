from django.utils import timezone

from apps.tasks.constants import (
    TASK_ASSIGNABLE_ROLES,
)
from apps.tasks.forms import (
    TaskForm,
    TaskMoveForm,
    TaskStatusForm,
)
from apps.tasks.models import Task
from apps.tasks.tests.base import TaskTestBase
from apps.workspaces.models import (
    WorkspaceMembership,
)


class TaskFormTests(TaskTestBase):
    def get_valid_data(self):
        return {
            "title": "طراحی API",
            "description": "پیاده‌سازی endpoint",
            "priority": Task.Priority.HIGH,
            "assignee": self.member.pk,
            "due_at": "",
        }

    def test_valid_form_is_accepted(self):
        form = TaskForm(
            data=self.get_valid_data(),
            workspace=self.workspace,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_title_is_trimmed(self):
        data = self.get_valid_data()
        data["title"] = "  طراحی API  "

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["title"],
            "طراحی API",
        )

    def test_short_title_is_invalid(self):
        data = self.get_valid_data()
        data["title"] = "ت"

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "title",
            form.errors,
        )

    def test_assignee_is_optional(self):
        data = self.get_valid_data()
        data["assignee"] = ""

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertIsNone(
            form.cleaned_data["assignee"]
        )

    def test_due_at_accepts_datetime_local_format(
        self,
    ):
        data = self.get_valid_data()
        data["due_at"] = "2030-01-02T14:30"

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        due_at = form.cleaned_data["due_at"]

        self.assertEqual(due_at.year, 2030)
        self.assertEqual(due_at.month, 1)
        self.assertEqual(due_at.day, 2)
        self.assertEqual(due_at.hour, 14)
        self.assertEqual(due_at.minute, 30)

        if timezone.is_aware(timezone.now()):
            self.assertTrue(
                timezone.is_aware(due_at)
            )

    def test_only_assignable_workspace_users_are_available(
        self,
    ):
        form = TaskForm(
            workspace=self.workspace,
        )

        queryset = (
            form.fields["assignee"].queryset
        )

        self.assertIn(self.owner, queryset)
        self.assertIn(self.admin, queryset)
        self.assertIn(self.member, queryset)
        self.assertNotIn(
            self.viewer,
            queryset,
        )
        self.assertNotIn(
            self.outsider,
            queryset,
        )

    def test_viewer_assignee_is_rejected(self):
        data = self.get_valid_data()
        data["assignee"] = self.viewer.pk

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "assignee",
            form.errors,
        )

    def test_outsider_assignee_is_rejected(self):
        data = self.get_valid_data()
        data["assignee"] = self.outsider.pk

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "assignee",
            form.errors,
        )

    def test_form_without_workspace_has_empty_assignee_queryset(
        self,
    ):
        form = TaskForm()

        self.assertFalse(
            form.fields[
                "assignee"
            ].queryset.exists()
        )

    def test_internal_fields_are_not_exposed(self):
        form = TaskForm(
            workspace=self.workspace,
        )

        self.assertEqual(
            set(form.fields),
            {
                "title",
                "description",
                "priority",
                "assignee",
                "due_at",
            },
        )


class TaskAssignableRolesTests(TaskTestBase):
    def test_owner_admin_and_member_are_assignable(
        self,
    ):
        self.assertIn(
            WorkspaceMembership.Role.OWNER,
            TASK_ASSIGNABLE_ROLES,
        )
        self.assertIn(
            WorkspaceMembership.Role.ADMIN,
            TASK_ASSIGNABLE_ROLES,
        )
        self.assertIn(
            WorkspaceMembership.Role.MEMBER,
            TASK_ASSIGNABLE_ROLES,
        )

    def test_viewer_is_not_assignable(self):
        self.assertNotIn(
            WorkspaceMembership.Role.VIEWER,
            TASK_ASSIGNABLE_ROLES,
        )


class TaskStatusFormTests(TaskTestBase):
    def test_only_status_is_exposed(self):
        form = TaskStatusForm()

        self.assertEqual(
            set(form.fields),
            {"status"},
        )

    def test_every_defined_status_is_valid(self):
        for status, _label in Task.Status.choices:
            with self.subTest(status=status):
                form = TaskStatusForm(
                    data={
                        "status": status,
                    },
                    instance=self.task,
                )

                self.assertTrue(
                    form.is_valid(),
                    form.errors,
                )

    def test_invalid_status_is_rejected(self):
        form = TaskStatusForm(
            data={
                "status": "not-a-status",
            },
            instance=self.task,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "status",
            form.errors,
        )


class TaskMoveFormTests(TaskTestBase):
    def setUp(self):
        super().setUp()

        self.target_column = self.create_column(
            title="در حال انجام",
            position=1,
        )
        self.archived_column = (
            self.create_column(
                title="ستون آرشیوشده",
                position=50,
                is_archived=True,
            )
        )

        self.other_board = self.create_board(
            title="Board دیگر",
        )
        self.other_board_column = (
            self.create_column(
                board=self.other_board,
                title="ستون Board دیگر",
                position=0,
            )
        )

    def test_only_active_same_board_columns_are_available(
        self,
    ):
        form = TaskMoveForm(
            board=self.board,
            current_column=self.column,
        )

        queryset = (
            form.fields[
                "target_column"
            ].queryset
        )

        self.assertIn(
            self.target_column,
            queryset,
        )
        self.assertNotIn(
            self.column,
            queryset,
        )
        self.assertNotIn(
            self.archived_column,
            queryset,
        )
        self.assertNotIn(
            self.other_board_column,
            queryset,
        )

    def test_valid_target_column_is_accepted(self):
        form = TaskMoveForm(
            data={
                "target_column": (
                    self.target_column.pk
                ),
            },
            board=self.board,
            current_column=self.column,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data[
                "target_column"
            ],
            self.target_column,
        )

    def test_current_column_is_rejected(self):
        form = TaskMoveForm(
            data={
                "target_column": (
                    self.column.pk
                ),
            },
            board=self.board,
            current_column=self.column,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "target_column",
            form.errors,
        )

    def test_archived_column_is_rejected(self):
        form = TaskMoveForm(
            data={
                "target_column": (
                    self.archived_column.pk
                ),
            },
            board=self.board,
            current_column=self.column,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "target_column",
            form.errors,
        )

    def test_other_board_column_is_rejected(self):
        form = TaskMoveForm(
            data={
                "target_column": (
                    self.other_board_column.pk
                ),
            },
            board=self.board,
            current_column=self.column,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "target_column",
            form.errors,
        )

    def test_form_without_board_has_empty_queryset(
        self,
    ):
        form = TaskMoveForm()

        self.assertFalse(
            form.fields[
                "target_column"
            ].queryset.exists()
        )
