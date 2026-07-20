from apps.tasks.forms import TaskForm
from apps.tasks.models import Task

from apps.tasks.tests.base import TaskTestBase


class TaskFormTests(TaskTestBase):
    def get_valid_data(self):
        return {
            "title": "طراحی API",
            "description": "پیاده‌سازی endpoint",
            "priority": (
                Task.Priority.HIGH
            ),
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

        self.assertFalse(
            form.is_valid()
        )

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

    def test_workspace_users_are_available(
        self
    ):
        form = TaskForm(
            workspace=self.workspace,
        )

        queryset = (
            form.fields[
                "assignee"
            ].queryset
        )

        self.assertIn(
            self.owner,
            queryset,
        )
        self.assertIn(
            self.admin,
            queryset,
        )
        self.assertIn(
            self.member,
            queryset,
        )
        self.assertIn(
            self.viewer,
            queryset,
        )

    def test_outsider_is_not_available(
        self
    ):
        form = TaskForm(
            workspace=self.workspace,
        )

        queryset = (
            form.fields[
                "assignee"
            ].queryset
        )

        self.assertNotIn(
            self.outsider,
            queryset,
        )

    def test_outsider_assignee_is_rejected(
        self
    ):
        data = self.get_valid_data()

        data["assignee"] = (
            self.outsider.pk
        )

        form = TaskForm(
            data=data,
            workspace=self.workspace,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "assignee",
            form.errors,
        )

    def test_internal_fields_are_not_exposed(
        self
    ):
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