from apps.boards.forms import BoardForm

from apps.boards.tests.base import BoardTestBase


class BoardFormTests(BoardTestBase):
    def test_form_is_valid_with_valid_data(self):
        form = BoardForm(
            data={
                "title": "Backend Development",
                "description": (
                    "Tasks related to backend development."
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_title_is_required(self):
        form = BoardForm(
            data={
                "title": "",
                "description": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_title_must_have_at_least_three_characters(
        self
    ):
        form = BoardForm(
            data={
                "title": "ab",
                "description": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_title_whitespace_is_removed(self):
        form = BoardForm(
            data={
                "title": "   TaskFlow Board   ",
                "description": "",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data["title"],
            "TaskFlow Board",
        )

    def test_whitespace_only_title_is_invalid(self):
        form = BoardForm(
            data={
                "title": "     ",
                "description": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_description_is_optional(self):
        form = BoardForm(
            data={
                "title": "TaskFlow Board",
                "description": "",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_description_whitespace_is_removed(self):
        form = BoardForm(
            data={
                "title": "TaskFlow Board",
                "description": (
                    "   Main project board   "
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data["description"],
            "Main project board",
        )

    def test_form_exposes_only_public_fields(self):
        form = BoardForm()

        self.assertEqual(
            list(form.fields),
            [
                "title",
                "description",
            ],
        )

    def test_workspace_cannot_be_submitted_by_form(self):
        form = BoardForm(
            data={
                "title": "TaskFlow Board",
                "description": "",
                "workspace": self.workspace.pk,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        board = form.save(commit=False)

        self.assertIsNone(board.workspace_id)

    def test_created_by_cannot_be_submitted_by_form(self):
        form = BoardForm(
            data={
                "title": "TaskFlow Board",
                "description": "",
                "created_by": self.member.pk,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        board = form.save(commit=False)

        self.assertIsNone(board.created_by_id)

    def test_archived_status_cannot_be_submitted_by_form(
        self
    ):
        form = BoardForm(
            data={
                "title": "TaskFlow Board",
                "description": "",
                "is_archived": True,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        board = form.save(commit=False)

        self.assertFalse(board.is_archived)