from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk)
            + str(timestamp)
            + str(user.email_verified)
            + str(user.is_active)
            + str(user.email)
        )

account_activation_token = AccountActivationTokenGenerator()