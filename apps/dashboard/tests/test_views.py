from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.dashboard.tests.base import DashboardTestBase


class DashboardAuthenticationTests(
    DashboardTestBase
):
    def test_guest_is_redirected_from_dashboard(
        self,
    ):
        url = reverse("dashboard:dashboard")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            (
                f"{reverse('accounts:login')}"
                f"?next={url}"
            ),
        )

    def test_guest_is_redirected_from_profile(
        self,
    ):
        url = reverse("dashboard:profile")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            (
                f"{reverse('accounts:login')}"
                f"?next={url}"
            ),
        )

    def test_guest_is_redirected_from_profile_update(
        self,
    ):
        url = reverse(
            "dashboard:profile_update"
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            (
                f"{reverse('accounts:login')}"
                f"?next={url}"
            ),
        )


class DashboardViewTests(DashboardTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_dashboard_page_is_available(self):
        response = self.client.get(
            reverse("dashboard:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/dashboard.html",
        )

    def test_profile_page_is_available(self):
        response = self.client.get(
            reverse("dashboard:profile")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/profile.html",
        )
        self.assertEqual(
            response.wsgi_request.user,
            self.user,
        )

    def test_profile_update_page_is_available(
        self,
    ):
        response = self.client.get(
            reverse(
                "dashboard:profile_update"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/profile_update.html",
        )
        self.assertEqual(
            response.context["form"].instance,
            self.user,
        )

    def test_user_can_update_profile(self):
        response = self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            self.valid_profile_data(
                first_name="Mehdi",
                last_name="Radfar",
                username="funlifew",
                bio="Backend Developer",
            ),
        )

        self.assertRedirects(
            response,
            reverse("dashboard:profile"),
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.first_name,
            "Mehdi",
        )
        self.assertEqual(
            self.user.last_name,
            "Radfar",
        )
        self.assertEqual(
            self.user.username,
            "funlifew",
        )
        self.assertEqual(
            self.user.bio,
            "Backend Developer",
        )

    def test_profile_update_does_not_change_email(
        self,
    ):
        old_email = self.user.email

        self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            self.valid_profile_data(),
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            old_email,
        )

    def test_profile_update_only_updates_current_user(
        self,
    ):
        original_other_username = (
            self.other_user.username
        )

        self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            self.valid_profile_data(
                username="changed-user",
            ),
        )

        self.other_user.refresh_from_db()

        self.assertEqual(
            self.other_user.username,
            original_other_username,
        )

    def test_duplicate_username_returns_form_error(
        self,
    ):
        response = self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            self.valid_profile_data(
                username=(
                    self.other_user.username.upper()
                ),
            ),
        )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "username",
            response.context["form"].errors,
        )
        self.assertEqual(
            self.user.username,
            "rodya",
        )

    def test_success_message_is_added(self):
        response = self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            self.valid_profile_data(),
        )

        messages = [
            str(message)
            for message in get_messages(
                response.wsgi_request
            )
        ]

        self.assertIn(
            (
                "پروفایل شما با موفقیت "
                "به روزرسانی شد."
            ),
            messages,
        )


class ProfileAvatarUploadTests(
    DashboardTestBase
):
    def setUp(self):
        super().setUp()

        self.temporary_media = (
            TemporaryDirectory()
        )
        self.override_media = (
            override_settings(
                MEDIA_ROOT=(
                    self.temporary_media.name
                )
            )
        )
        self.override_media.enable()

        self.addCleanup(
            self.override_media.disable
        )
        self.addCleanup(
            self.temporary_media.cleanup
        )

        self.client.force_login(self.user)

    def create_png_file(self):
        buffer = BytesIO()

        image = Image.new(
            "RGB",
            (20, 20),
            "white",
        )
        image.save(
            buffer,
            format="PNG",
        )

        return SimpleUploadedFile(
            "avatar.png",
            buffer.getvalue(),
            content_type="image/png",
        )

    def test_user_can_upload_valid_avatar(self):
        response = self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            {
                **self.valid_profile_data(),
                "avatar": self.create_png_file(),
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:profile"),
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.avatar.name.startswith(
                f"avatars/{self.user.pk}/"
            )
        )
        self.assertTrue(
            self.user.avatar.name.endswith(
                ".png"
            )
        )

    def test_invalid_file_is_rejected(self):
        invalid_file = SimpleUploadedFile(
            "document.txt",
            b"not an image",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse(
                "dashboard:profile_update"
            ),
            {
                **self.valid_profile_data(),
                "avatar": invalid_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "avatar",
            response.context["form"].errors,
        )