from django.urls import reverse

from apps.accounts.tests.base import AccountsTestBase


class LoginViewTests(AccountsTestBase):
    def test_login_page_is_available(self):
        response = self.client.get(
            reverse("accounts:login")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/login.html",
        )

    def test_login_form_has_expected_attributes(
        self,
    ):
        response = self.client.get(
            reverse("accounts:login")
        )

        form = response.context["form"]

        self.assertEqual(
            form.fields[
                "username"
            ].widget.attrs["class"],
            "input",
        )
        self.assertEqual(
            form.fields[
                "username"
            ].widget.attrs["autocomplete"],
            "username",
        )
        self.assertEqual(
            form.fields[
                "password"
            ].widget.attrs["class"],
            "input",
        )
        self.assertEqual(
            form.fields[
                "password"
            ].widget.attrs["autocomplete"],
            "password",
        )

    def test_active_user_can_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": (
                    self.active_user.username
                ),
                "password": self.password,
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:dashboard"),
        )
        self.assertEqual(
            int(
                self.client.session[
                    "_auth_user_id"
                ]
            ),
            self.active_user.pk,
        )

    def test_login_respects_next_parameter(self):
        target_url = reverse(
            "dashboard:profile"
        )
        login_url = reverse(
            "accounts:login"
        )

        response = self.client.post(
            f"{login_url}?next={target_url}",
            {
                "username": (
                    self.active_user.username
                ),
                "password": self.password,
                "next": target_url,
            },
        )

        self.assertRedirects(
            response,
            target_url,
        )

    def test_invalid_password_does_not_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": (
                    self.active_user.username
                ),
                "password": "WrongPassword!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_inactive_user_cannot_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": (
                    self.inactive_user.username
                ),
                "password": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_authenticated_user_is_redirected_from_login(
        self,
    ):
        self.client.force_login(self.active_user)

        response = self.client.get(
            reverse("accounts:login")
        )

        self.assertRedirects(
            response,
            reverse("dashboard:dashboard"),
        )


class LogoutViewTests(AccountsTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.active_user)

    def test_logout_rejects_get_request(self):
        response = self.client.get(
            reverse("accounts:logout")
        )

        self.assertEqual(response.status_code, 405)
        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_accepts_post_request(self):
        response = self.client.post(
            reverse("accounts:logout")
        )

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )