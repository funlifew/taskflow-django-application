from django.test import SimpleTestCase

from apps.columns.forms import ColumnForm


class ColumnFormTests(SimpleTestCase):
    def test_valid_title_is_accepted(self):
        form = ColumnForm(
            data={
                "title": "در حال انجام",
            }
        )

        self.assertTrue(
            form.is_valid()
        )

    def test_title_is_trimmed(self):
        form = ColumnForm(
            data={
                "title": "  انجام‌شده  ",
            }
        )

        self.assertTrue(
            form.is_valid()
        )
        self.assertEqual(
            form.cleaned_data["title"],
            "انجام‌شده",
        )

    def test_short_title_is_invalid(self):
        form = ColumnForm(
            data={
                "title": "ا",
            }
        )

        self.assertFalse(
            form.is_valid()
        )
        self.assertIn(
            "title",
            form.errors,
        )

    def test_internal_fields_are_not_exposed(self):
        form = ColumnForm()

        self.assertEqual(
            set(form.fields),
            {
                "title",
            },
        )