from apps.accounts.tokens import (
    account_activation_token,
)

from apps.accounts.tests.base import AccountsTestBase


class AccountActivationTokenTests(
    AccountsTestBase
):
    def test_token_is_valid_for_inactive_user(self):
        token = (
            account_activation_token.make_token(
                self.inactive_user
            )
        )

        self.assertTrue(
            account_activation_token.check_token(
                self.inactive_user,
                token,
            )
        )

    def test_token_is_invalid_after_activation(self):
        token = (
            account_activation_token.make_token(
                self.inactive_user
            )
        )

        self.inactive_user.is_active = True
        self.inactive_user.email_verified = True
        self.inactive_user.save(
            update_fields=[
                "is_active",
                "email_verified",
            ]
        )

        self.assertFalse(
            account_activation_token.check_token(
                self.inactive_user,
                token,
            )
        )

    def test_token_is_invalid_after_email_change(self):
        token = (
            account_activation_token.make_token(
                self.inactive_user
            )
        )

        self.inactive_user.email = (
            "changed@example.com"
        )
        self.inactive_user.save(
            update_fields=["email"],
        )

        self.assertFalse(
            account_activation_token.check_token(
                self.inactive_user,
                token,
            )
        )

    def test_invalid_token_is_rejected(self):
        self.assertFalse(
            account_activation_token.check_token(
                self.inactive_user,
                "invalid-token",
            )
        )