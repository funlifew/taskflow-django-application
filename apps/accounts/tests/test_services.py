from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)
from django.core import mail
from django.core.cache import cache
from django.test import (
    RequestFactory,
    override_settings,
)

from apps.accounts.services import (
    AccountLifecycleService,
    acquire_activation_email_lock,
    release_activation_email_lock,
    send_activation_email,
    send_activation_email_with_cooldown,
)
from apps.accounts.tests.base import TEST_CACHES, AccountsTestBase
from apps.core.cache_keys import (
    verification_resend_key,
)

User = get_user_model()

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

    def test_send_activation_email(
        self,
    ):
        send_activation_email(
            self.request,
            self.inactive_user,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            [
                self.inactive_user.email,
            ],
        )

        self.assertEqual(
            email.subject,
            "فعال‌سازی حساب TaskFlow",
        )

        self.assertIn(
            (
                f"سلام "
                f"{self.inactive_user.get_full_name()}"
            ),
            email.body,
        )

        self.assertIn(
            "/activate/",
            email.body,
        )

        self.assertEqual(
            len(email.alternatives),
            1,
        )

        self.assertEqual(
            email.alternatives[0].mimetype,
            "text/html",
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

class AccountLifecycleServiceTests(
    AccountsTestBase
):
    def test_create_inactive_account(self):
        user = User(
            username="inactive-created-user",
            email="CREATED-INACTIVE@EXAMPLE.COM",
            first_name="Inactive",
            last_name="User",
            is_active=True,
            email_verified=True,
        )

        user.set_password(
            "StrongPassword123!"
        )

        created_user = (
            AccountLifecycleService
            .create_inactive(
                user=user,
            )
        )

        created_user.refresh_from_db()

        self.assertFalse(
            created_user.is_active
        )
        self.assertFalse(
            created_user.email_verified
        )
        self.assertEqual(
            created_user.email,
            "created-inactive@example.com",
        )
        self.assertTrue(
            created_user.check_password(
                "StrongPassword123!"
            )
        )

    def test_activate_account(self):
        (
            activated_user,
            changed,
        ) = AccountLifecycleService.activate(
            user=self.inactive_user,
        )

        activated_user.refresh_from_db()

        self.assertTrue(changed)
        self.assertTrue(
            activated_user.is_active
        )
        self.assertTrue(
            activated_user.email_verified
        )

    def test_activate_is_idempotent(self):
        AccountLifecycleService.activate(
            user=self.inactive_user,
        )

        (
            activated_user,
            changed,
        ) = AccountLifecycleService.activate(
            user=self.inactive_user,
        )

        self.assertFalse(changed)
        self.assertTrue(
            activated_user.is_active
        )
        self.assertTrue(
            activated_user.email_verified
        )