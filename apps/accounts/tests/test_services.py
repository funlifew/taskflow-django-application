from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import (
    RequestFactory,
    override_settings,
)

from apps.accounts.services import (
    acquire_activation_email_lock,
    can_send_activation_email,
    mark_activation_email_send,
    release_activation_email_lock,
    send_activation_email,
    send_activation_email_with_cooldown,
)
from apps.core.cache_keys import (
    verification_resend_key,
)

from apps.accounts.tests.base import AccountsTestBase, TEST_CACHES


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    CACHES=TEST_CACHES,
    ALLOWED_HOSTS=["testserver"],
)
class ActivationEmailServiceTests(
    AccountsTestBase
):
    def setUp(self):
        super().setUp()
        cache.clear()

        self.request = RequestFactory().get(
            "/",
            HTTP_HOST="testserver",
        )

    def test_activation_cache_key(self):
        self.assertEqual(
            verification_resend_key(
                self.inactive_user.pk
            ),
            (
                f"user:{self.inactive_user.pk}:"
                "verification:resend-lock"
            ),
        )

    def test_can_send_returns_true_without_lock(self):
        self.assertTrue(
            can_send_activation_email(
                self.inactive_user
            )
        )

    def test_mark_activation_email_send_creates_lock(
        self,
    ):
        mark_activation_email_send(
            self.inactive_user
        )

        self.assertFalse(
            can_send_activation_email(
                self.inactive_user
            )
        )

    def test_acquire_lock_only_succeeds_once(self):
        first_result = (
            acquire_activation_email_lock(
                self.inactive_user.pk
            )
        )
        second_result = (
            acquire_activation_email_lock(
                self.inactive_user.pk
            )
        )

        self.assertTrue(first_result)
        self.assertFalse(second_result)

    def test_release_lock_allows_new_acquisition(self):
        acquire_activation_email_lock(
            self.inactive_user.pk
        )

        release_activation_email_lock(
            self.inactive_user.pk
        )

        self.assertTrue(
            acquire_activation_email_lock(
                self.inactive_user.pk
            )
        )

    def test_send_activation_email(self):
        send_activation_email(
            self.request,
            self.inactive_user,
        )

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            [self.inactive_user.email],
        )
        self.assertIn(
            "فعالسازی حساب TaskFlow",
            email.subject,
        )
        self.assertIn(
            "/activate/",
            email.body,
        )
        self.assertIn(
            str(self.inactive_user.pk),
            email.body,
        )
        self.assertEqual(
            len(email.alternatives),
            1,
        )

    def test_send_with_cooldown_sends_first_email(
        self,
    ):
        sent = send_activation_email_with_cooldown(
            self.request,
            self.inactive_user,
        )

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_with_cooldown_blocks_second_email(
        self,
    ):
        first = send_activation_email_with_cooldown(
            self.request,
            self.inactive_user,
        )
        second = send_activation_email_with_cooldown(
            self.request,
            self.inactive_user,
        )

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(mail.outbox), 1)

    @patch(
        "apps.accounts.services.send_activation_email",
        side_effect=RuntimeError("Email failed"),
    )
    def test_failed_email_releases_lock(
        self,
        mocked_send,
    ):
        with self.assertRaises(RuntimeError):
            send_activation_email_with_cooldown(
                self.request,
                self.inactive_user,
            )

        self.assertTrue(
            acquire_activation_email_lock(
                self.inactive_user.pk
            )
        )

    @patch(
        "apps.accounts.services.cache.add",
        side_effect=RuntimeError(
            "Cache unavailable"
        ),
    )
    def test_cache_failure_uses_fail_open_policy(
        self,
        mocked_cache_add,
    ):
        result = acquire_activation_email_lock(
            self.inactive_user.pk
        )

        self.assertTrue(result)

    @patch(
        "apps.accounts.services.cache.delete",
        side_effect=RuntimeError(
            "Cache unavailable"
        ),
    )
    def test_release_lock_does_not_raise_on_cache_error(
        self,
        mocked_cache_delete,
    ):
        release_activation_email_lock(
            self.inactive_user.pk
        )