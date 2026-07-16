from apps.accounts.forms import (
    RegisterForm,
    ResendActivationEmailForm,
)

from apps.accounts.tests.base import AccountsTestBase


class RegisterFormTests(AccountsTestBase):
    def test_valid_registration_form(self):
        form = RegisterForm(
            data=self.registration_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_email_is_normalized(self):
        form = RegisterForm(
            data=self.registration_data(
                email="  NEW-USER@EXAMPLE.COM  ",
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["email"],
            "new-user@example.com",
        )

    def test_duplicate_email_is_rejected_case_insensitively(
        self,
    ):
        form = RegisterForm(
            data=self.registration_data(
                email="SHELLY@EXAMPLE.COM",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_username_is_rejected(self):
        form = RegisterForm(
            data=self.registration_data(
                username=self.active_user.username,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_password_mismatch_is_rejected(self):
        form = RegisterForm(
            data=self.registration_data(
                password2="DifferentPassword123!",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_weak_password_is_rejected(self):
        form = RegisterForm(
            data=self.registration_data(
                password1="123",
                password2="123",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_first_name_is_required(self):
        form = RegisterForm(
            data=self.registration_data(
                first_name="",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_last_name_is_required(self):
        form = RegisterForm(
            data=self.registration_data(
                last_name="",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)

    def test_email_is_required(self):
        form = RegisterForm(
            data=self.registration_data(
                email="",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_register_form_saves_hashed_password(self):
        form = RegisterForm(
            data=self.registration_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        user = form.save()

        self.assertTrue(
            user.check_password(self.password)
        )


class ResendActivationEmailFormTests(
    AccountsTestBase
):
    def test_valid_email_is_normalized(self):
        form = ResendActivationEmailForm(
            data={
                "email": (
                    "  INACTIVE@EXAMPLE.COM  "
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["email"],
            "inactive@example.com",
        )

    def test_invalid_email_is_rejected(self):
        form = ResendActivationEmailForm(
            data={
                "email": "not-an-email",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_is_required(self):
        form = ResendActivationEmailForm(
            data={
                "email": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)