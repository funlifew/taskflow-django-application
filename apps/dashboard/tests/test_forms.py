from types import SimpleNamespace

from django.core.exceptions import ValidationError

from apps.dashboard.forms import (
    ProfileUpdateForm,
)

from apps.dashboard.tests.base import DashboardTestBase


class ProfileUpdateFormTests(
    DashboardTestBase
):
    def test_valid_profile_form(self):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(),
            instance=self.user,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_current_username_is_allowed(self):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                username=self.user.username,
            ),
            instance=self.user,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_current_username_with_different_case_is_allowed(
        self,
    ):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                username=self.user.username.upper(),
            ),
            instance=self.user,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_duplicate_username_is_rejected_case_insensitively(
        self,
    ):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                username=(
                    self.other_user
                    .username
                    .upper()
                ),
            ),
            instance=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "username",
            form.errors,
        )

    def test_first_name_is_required(self):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                first_name="",
            ),
            instance=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "first_name",
            form.errors,
        )

    def test_last_name_is_required(self):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                last_name="",
            ),
            instance=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "last_name",
            form.errors,
        )

    def test_bio_can_be_empty(self):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                bio="",
            ),
            instance=self.user,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_bio_cannot_exceed_500_characters(
        self,
    ):
        form = ProfileUpdateForm(
            data=self.valid_profile_data(
                bio="x" * 501,
            ),
            instance=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("bio", form.errors)

    def test_avatar_without_content_type_is_returned(
        self,
    ):
        avatar = object()

        form = ProfileUpdateForm(
            instance=self.user
        )
        form.cleaned_data = {
            "avatar": avatar,
        }

        self.assertIs(
            form.clean_avatar(),
            avatar,
        )

    def test_disallowed_avatar_content_type_is_rejected(
        self,
    ):
        avatar = SimpleNamespace(
            content_type="application/pdf",
            size=100,
        )

        form = ProfileUpdateForm(
            instance=self.user
        )
        form.cleaned_data = {
            "avatar": avatar,
        }

        with self.assertRaisesMessage(
            ValidationError,
            (
                "فقط تصاویر "
                "JPG/JPEG/PNG/WEBP/GIF "
                "مجاز هستند."
            ),
        ):
            form.clean_avatar()

    def test_avatar_larger_than_five_mb_is_rejected(
        self,
    ):
        avatar = SimpleNamespace(
            content_type="image/png",
            size=(5 * 1024 * 1024) + 1,
        )

        form = ProfileUpdateForm(
            instance=self.user
        )
        form.cleaned_data = {
            "avatar": avatar,
        }

        with self.assertRaisesMessage(
            ValidationError,
            (
                "حجم تصویر نباید بیشتر "
                "از 5 مگابایت باشد."
            ),
        ):
            form.clean_avatar()

    def test_allowed_avatar_is_returned(self):
        avatar = SimpleNamespace(
            content_type="image/webp",
            size=1024,
        )

        form = ProfileUpdateForm(
            instance=self.user
        )
        form.cleaned_data = {
            "avatar": avatar,
        }

        self.assertIs(
            form.clean_avatar(),
            avatar,
        )