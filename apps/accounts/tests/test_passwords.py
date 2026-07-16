from django.contrib.auth.tokens import (
    default_token_generator,
)
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import (
    urlsafe_base64_encode,
)

from apps.accounts.tests.base import AccountsTestBase


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    ALLOWED_HOSTS=["testserver"],
)
class PasswordResetViewTests(
    AccountsTestBase
):
    def test_password_reset_page_is_available(
        self,
    ):
        response = self.client.get(
            reverse("accounts:password_reset")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/password_reset.html",
        )

    def test_password_reset_done_page_is_available(
        self,
    ):
        response = self.client.get(
            reverse(
                "accounts:password_reset_done"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/password_reset_done.html",
        )

    def test_active_user_receives_reset_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": self.active_user.email,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:password_reset_done"
            ),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            [self.active_user.email],
        )
        self.assertEqual(
            len(mail.outbox[0].alternatives),
            1,
        )

    def test_unknown_email_does_not_send_email(
        self,
    ):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": "unknown@example.com",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:password_reset_done"
            ),
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_user_does_not_receive_reset_email(
        self,
    ):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {
                "email": self.inactive_user.email,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:password_reset_done"
            ),
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_reset_token_is_rejected(self):
        uid = urlsafe_base64_encode(
            force_bytes(self.active_user.pk)
        )

        response = self.client.get(
            reverse(
                "accounts:password_reset_confirm",
                kwargs={
                    "uidb64": uid,
                    "token": "invalid-token",
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            response.context["validlink"]
        )

    def test_full_password_reset_flow(self):
        uid = urlsafe_base64_encode(
            force_bytes(self.active_user.pk)
        )
        token = (
            default_token_generator.make_token(
                self.active_user
            )
        )

        initial_url = reverse(
            "accounts:password_reset_confirm",
            kwargs={
                "uidb64": uid,
                "token": token,
            },
        )

        initial_response = self.client.get(
            initial_url
        )

        self.assertEqual(
            initial_response.status_code,
            302,
        )

        set_password_url = (
            initial_response.url
        )
        new_password = (
            "New-Strong-Password-456!"
        )

        response = self.client.post(
            set_password_url,
            {
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:password_reset_complete"
            ),
        )

        self.active_user.refresh_from_db()

        self.assertTrue(
            self.active_user.check_password(
                new_password
            )
        )
        self.assertFalse(
            self.active_user.check_password(
                self.password
            )
        )

    def test_reset_complete_page_is_available(
        self,
    ):
        response = self.client.get(
            reverse(
                "accounts:password_reset_complete"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            (
                "accounts/"
                "password_reset_complete.html"
            ),
        )


class PasswordChangeViewTests(
    AccountsTestBase
):
    def test_guest_is_redirected_to_login(self):
        url = reverse(
            "accounts:change_password"
        )

        response = self.client.get(url)

        self.assertRedirects(
            response,
            (
                f"{reverse('accounts:login')}"
                f"?next={url}"
            ),
        )

    def test_password_change_page_is_available(
        self,
    ):
        self.client.force_login(self.active_user)

        response = self.client.get(
            reverse(
                "accounts:change_password"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/password_change.html",
        )

    def test_user_can_change_password(self):
        self.client.force_login(self.active_user)

        new_password = (
            "Changed-Strong-Password-789!"
        )

        response = self.client.post(
            reverse(
                "accounts:change_password"
            ),
            {
                "old_password": self.password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:profile"),
        )

        self.active_user.refresh_from_db()

        self.assertTrue(
            self.active_user.check_password(
                new_password
            )
        )

    def test_session_remains_active_after_password_change(
        self,
    ):
        self.client.force_login(self.active_user)

        new_password = (
            "Changed-Strong-Password-789!"
        )

        self.client.post(
            reverse(
                "accounts:change_password"
            ),
            {
                "old_password": self.password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        response = self.client.get(
            reverse("dashboard:profile")
        )

        self.assertEqual(response.status_code, 200)

    def test_wrong_old_password_is_rejected(self):
        self.client.force_login(self.active_user)

        response = self.client.post(
            reverse(
                "accounts:change_password"
            ),
            {
                "old_password": "WrongPassword!",
                "new_password1": (
                    "New-Strong-Password-456!"
                ),
                "new_password2": (
                    "New-Strong-Password-456!"
                ),
            },
        )

        self.active_user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "old_password",
            response.context["form"].errors,
        )
        self.assertTrue(
            self.active_user.check_password(
                self.password
            )
        )

    def test_mismatched_new_password_is_rejected(
        self,
    ):
        self.client.force_login(self.active_user)

        response = self.client.post(
            reverse(
                "accounts:change_password"
            ),
            {
                "old_password": self.password,
                "new_password1": (
                    "New-Strong-Password-456!"
                ),
                "new_password2": (
                    "Different-Password-789!"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "new_password2",
            response.context["form"].errors,
        )