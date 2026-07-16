from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


TEST_CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": "taskflow-account-tests",
    },
}


class AccountsTestBase(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.active_user = User.objects.create_user(
            username="shelly",
            email="shelly@example.com",
            password=cls.password,
            first_name="Shelly",
            last_name="Tester",
            email_verified=True,
            is_active=True,
        )

        cls.inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password=cls.password,
            first_name="Inactive",
            last_name="Tester",
            email_verified=False,
            is_active=False,
        )

    def setUp(self):
        self.active_user.refresh_from_db()
        self.inactive_user.refresh_from_db()

    def registration_data(self, **overrides):
        data = {
            "first_name": "New",
            "last_name": "User",
            "username": "new-user",
            "email": "new-user@example.com",
            "password1": self.password,
            "password2": self.password,
        }

        data.update(overrides)
        return data