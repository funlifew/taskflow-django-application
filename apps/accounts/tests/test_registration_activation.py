from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import (
    urlsafe_base64_encode,
)

from apps.accounts.tokens import (
    account_activation_token,
)

from apps.accounts.tests.base import AccountsTestBase, TEST_CACHES


User = get_user_model()


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    CACHES=TEST_CACHES,
    ALLOWED_HOSTS=["testserver"],
)
class RegistrationViewTests(
    AccountsTestBase
):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_register_page_is_available(self):
        response = self.client.get(
            reverse("accounts:register")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/register.html",
        )

    def test_register_creates_inactive_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(
                email="NEW-USER@EXAMPLE.COM",
            ),
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:verification_sent"
            ),
        )

        user = User.objects.get(
            username="new-user",
        )

        self.assertEqual(
            user.email,
            "new-user@example.com",
        )
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertTrue(
            user.check_password(self.password)
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_duplicate_email_does_not_create_user(
        self,
    ):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(
                email="SHELLY@EXAMPLE.COM",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "email",
            response.context["form"].errors,
        )
        self.assertFalse(
            User.objects.filter(
                username="new-user",
            ).exists()
        )

    def test_duplicate_username_does_not_create_user(
        self,
    ):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(
                username=self.active_user.username,
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "username",
            response.context["form"].errors,
        )

    def test_password_mismatch_does_not_create_user(
        self,
    ):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(
                password2="DifferentPassword123!",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(
                username="new-user",
            ).exists()
        )

    @patch(
        (
            "apps.accounts.views."
            "send_activation_email_with_cooldown"
        ),
        side_effect=RuntimeError(
            "Email provider failed"
        ),
    )
    def test_user_is_kept_when_activation_email_fails(
        self,
        mocked_send,
    ):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(),
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:verification_sent"
            ),
        )
        self.assertTrue(
            User.objects.filter(
                username="new-user",
                is_active=False,
                email_verified=False,
            ).exists()
        )

    @patch(
        "apps.accounts.views.RegisterForm.save",
        side_effect=IntegrityError,
    )
    def test_integrity_error_returns_form_error(
        self,
        mocked_save,
    ):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.context[
                "form"
            ].non_field_errors()
        )
        self.assertFalse(
            User.objects.filter(
                username="new-user",
            ).exists()
        )

    def test_authenticated_user_is_redirected_from_register(
        self,
    ):
        self.client.force_login(self.active_user)

        response = self.client.get(
            reverse("accounts:register")
        )

        self.assertRedirects(
            response,
            reverse("dashboard:dashboard"),
        )

    def test_verification_sent_page_is_available(
        self,
    ):
        response = self.client.get(
            reverse(
                "accounts:verification_sent"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/verification_sent.html",
        )


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    CACHES=TEST_CACHES,
    ALLOWED_HOSTS=["testserver"],
)
class ActivationViewTests(AccountsTestBase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def activation_url(
        self,
        *,
        user=None,
        token=None,
        uid=None,
    ):
        user = user or self.inactive_user

        if uid is None:
            uid = urlsafe_base64_encode(
                force_bytes(user.pk)
            )

        if token is None:
            token = (
                account_activation_token
                .make_token(user)
            )

        return reverse(
            "accounts:activate",
            kwargs={
                "uidb64": uid,
                "token": token,
            },
        )

    def test_valid_activation_activates_user(self):
        response = self.client.get(
            self.activation_url()
        )

        self.inactive_user.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )
        self.assertTrue(
            self.inactive_user.is_active
        )
        self.assertTrue(
            self.inactive_user.email_verified
        )

    def test_invalid_token_renders_invalid_page(self):
        response = self.client.get(
            self.activation_url(
                token="invalid-token",
            )
        )

        self.inactive_user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/activation_invalid.html",
        )
        self.assertFalse(
            self.inactive_user.is_active
        )
        self.assertFalse(
            self.inactive_user.email_verified
        )

    def test_invalid_uid_renders_invalid_page(self):
        response = self.client.get(
            self.activation_url(
                uid="invalid-uid",
                token="invalid-token",
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/activation_invalid.html",
        )

    def test_already_active_user_redirects_to_login(
        self,
    ):
        token = (
            account_activation_token.make_token(
                self.active_user
            )
        )

        response = self.client.get(
            self.activation_url(
                user=self.active_user,
                token=token,
            )
        )

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )

    def test_token_cannot_be_reused_after_activation(
        self,
    ):
        url = self.activation_url()

        first_response = self.client.get(url)
        second_response = self.client.get(url)

        self.assertEqual(
            first_response.status_code,
            302,
        )
        self.assertEqual(
            second_response.status_code,
            200,
        )
        self.assertTemplateUsed(
            second_response,
            "accounts/activation_invalid.html",
        )

    def test_authenticated_user_is_redirected_from_activation(
        self,
    ):
        url = self.activation_url()

        self.client.force_login(self.active_user)

        response = self.client.get(url)

        self.assertRedirects(
            response,
            reverse("dashboard:dashboard"),
        )


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    CACHES=TEST_CACHES,
    ALLOWED_HOSTS=["testserver"],
)
class ResendActivationViewTests(
    AccountsTestBase
):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_resend_page_is_available(self):
        response = self.client.get(
            reverse(
                "accounts:resend_verification"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            (
                "accounts/"
                "resend_activation_email.html"
            ),
        )

    def test_resend_sends_email_to_inactive_user(
        self,
    ):
        response = self.client.post(
            reverse(
                "accounts:resend_verification"
            ),
            {
                "email": (
                    self.inactive_user.email
                ),
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:verification_sent"
            ),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            [self.inactive_user.email],
        )

    def test_cooldown_blocks_repeated_resend(self):
        url = reverse(
            "accounts:resend_verification"
        )

        self.client.post(
            url,
            {
                "email": (
                    self.inactive_user.email
                ),
            },
        )
        self.client.post(
            url,
            {
                "email": (
                    self.inactive_user.email
                ),
            },
        )

        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_email_does_not_send_email(
        self,
    ):
        response = self.client.post(
            reverse(
                "accounts:resend_verification"
            ),
            {
                "email": "unknown@example.com",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:verification_sent"
            ),
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_active_user_does_not_receive_activation_email(
        self,
    ):
        response = self.client.post(
            reverse(
                "accounts:resend_verification"
            ),
            {
                "email": self.active_user.email,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:verification_sent"
            ),
        )
        self.assertEqual(len(mail.outbox), 0)

    @patch(
        (
            "apps.accounts.views."
            "send_activation_email_with_cooldown"
        ),
        side_effect=RuntimeError(
            "Email failed"
        ),
    )
    def test_resend_email_failure_is_hidden(
        self,
        mocked_send,
    ):
        response = self.client.post(
            reverse(
                "accounts:resend_verification"
            ),
            {
                "email": (
                    self.inactive_user.email
                ),
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:verification_sent"
            ),
        )

    def test_authenticated_user_is_redirected_from_resend(
        self,
    ):
        self.client.force_login(self.active_user)

        response = self.client.get(
            reverse(
                "accounts:resend_verification"
            )
        )

        self.assertRedirects(
            response,
            reverse("dashboard:dashboard"),
        )