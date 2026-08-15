from django import forms
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import (
    UserCreationForm,
)

from apps.core.emailing import (
    EmailDeliveryError,
    TemplatedEmail,
    send_templated_email,
)

from .models import User


class RegisterForm(
    UserCreationForm
):
    first_name = (
        forms.CharField(
            required=True,
            label="نام",
            widget=(
                forms.widgets.TextInput(
                    attrs={
                        "class": "input",
                        "placeholder": (
                            "نام..."
                        ),
                        "autocomplete": (
                            "given-name"
                        ),
                    }
                )
            ),
        )
    )

    last_name = (
        forms.CharField(
            required=True,
            label="نام خانوادگی",
            widget=(
                forms.widgets.TextInput(
                    attrs={
                        "class": "input",
                        "placeholder": (
                            "نام خانوادگی..."
                        ),
                        "autocomplete": (
                            "family-name"
                        ),
                    }
                )
            ),
        )
    )

    username = forms.CharField(
        required=True,
        label="نام کاربری",
        widget=(
            forms.widgets.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": (
                        "نام کاربری..."
                    ),
                    "autocomplete": (
                        "username"
                    ),
                }
            )
        ),
    )

    email = forms.EmailField(
        required=True,
        label="ایمیل",
        widget=(
            forms.widgets.EmailInput(
                attrs={
                    "class": "input",
                    "placeholder": (
                        "example@email.com"
                    ),
                    "autocomplete": (
                        "email"
                    ),
                }
            )
        ),
    )

    password1 = forms.CharField(
        label="رمز عبور",
        widget=(
            forms.widgets.PasswordInput(
                attrs={
                    "class": "input",
                    "placeholder": (
                        "........"
                    ),
                    "autocomplete": (
                        "new-password"
                    ),
                }
            )
        ),
    )

    password2 = forms.CharField(
        label="تکرار رمز عبور",
        widget=(
            forms.widgets.PasswordInput(
                attrs={
                    "class": "input",
                    "placeholder": (
                        "........"
                    ),
                    "autocomplete": (
                        "new-password"
                    ),
                }
            )
        ),
    )

    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = (
            self.cleaned_data[
                "email"
            ]
            .lower()
            .strip()
        )

        if (
            User.objects.filter(
                email__iexact=email
            ).exists()
        ):
            raise (
                forms.ValidationError(
                    (
                        "این ایمیل قبلاً "
                        "ثبت شده است."
                    )
                )
            )

        return email


class ResendActivationEmailForm(
    forms.Form
):
    email = forms.EmailField(
        required=True,
        widget=(
            forms.widgets.EmailInput(
                attrs={
                    "class": "input",
                    "placeholder": (
                        "ایمیل..."
                    ),
                    "autocomplete": (
                        "email"
                    ),
                }
            )
        ),
    )

    def clean_email(self):
        return (
            self.cleaned_data[
                "email"
            ]
            .lower()
            .strip()
        )


class TaskFlowPasswordResetForm(
    DjangoPasswordResetForm
):
    """
    Keep Django's secure password-reset
    lookup/token behavior while routing
    delivery through TaskFlow's common
    transactional email gateway.

    Delivery errors are intentionally
    swallowed here after the gateway
    logs them, preserving Django's
    generic password-reset response.
    """

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        email = TemplatedEmail(
            category=(
                "password_reset"
            ),
            subject_template=(
                subject_template_name
            ),
            text_template=(
                email_template_name
            ),
            html_template=(
                html_email_template_name
            ),
            recipients=(
                to_email,
            ),
            from_email=(
                from_email
            ),
            context=context,
        )

        try:
            send_templated_email(
                email
            )

        except EmailDeliveryError:
            # The common email layer
            # already logged the failure.
            #
            # Do not expose account
            # existence through divergent
            # password-reset behavior.
            return