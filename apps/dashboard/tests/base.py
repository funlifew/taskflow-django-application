from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


class DashboardTestBase(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="rodya",
            email="rodya@example.com",
            password=cls.password,
            first_name="Rodya",
            last_name="Tester",
            email_verified=True,
            is_active=True,
            bio="Backend developer",
        )

        cls.other_user = User.objects.create_user(
            username="other-user",
            email="other@example.com",
            password=cls.password,
            first_name="Other",
            last_name="User",
            email_verified=True,
            is_active=True,
        )

    def setUp(self):
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()

    def valid_profile_data(self, **overrides):
        data = {
            "first_name": "Rodya",
            "last_name": "Updated",
            "username": "rodya",
            "bio": "Django and FastAPI developer",
        }

        data.update(overrides)
        return data