from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
)
class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "A-Strong-Test-Password-123"

    def test_login_respects_next_parameter(self):
        user = User.objects.create_user(
            username="shelly",
            email="shelly@example.com",
            password=self.password,
            first_name="Shelly",
            last_name="Test",
            email_verified=True,
            is_active=True,
        )

        target_url = reverse("dashboard:dashboard")
        login_url = reverse("accounts:login")

        response = self.client.post(
            f"{login_url}?next={target_url}",
            {
                "username": user.username,
                "password": self.password,
                "next": target_url,
            },
        )

        self.assertRedirects(response, target_url)

    def test_register_creates_inactive_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Shelly",
                "last_name": "Test",
                "username": "shelly",
                "email": "SHELLY@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:verification_sent"),
        )

        user = User.objects.get(username="shelly")

        self.assertEqual(user.email, "shelly@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_duplicate_email_is_case_insensitive(self):
        User.objects.create_user(
            username="first-user",
            email="shelly@example.com",
            password=self.password,
        )

        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Shelly",
                "last_name": "Test",
                "username": "second-user",
                "email": "SHELLY@EXAMPLE.COM",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "این ایمیل قبلاً ثبت شده است.",
        )

    def test_logout_requires_post(self):
        user = User.objects.create_user(
            username="shelly",
            email="shelly@example.com",
            password=self.password,
            is_active=True,
        )
        self.client.force_login(user)

        get_response = self.client.get(
            reverse("accounts:logout")
        )
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(
            reverse("accounts:logout")
        )
        self.assertRedirects(
            post_response,
            reverse("accounts:login"),
        )