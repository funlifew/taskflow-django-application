from unittest.mock import (
    patch,
)

from django.core import mail
from django.test import (
    SimpleTestCase,
    override_settings,
)

from apps.core.emailing import (
    EmailDeliveryError,
    TemplatedEmail,
    build_templated_email,
    send_templated_email,
)


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends."
        "locmem.EmailBackend"
    ),
    DEFAULT_FROM_EMAIL=(
        "TaskFlow "
        "<noreply@example.com>"
    ),
)
class TemplatedEmailTests(
    SimpleTestCase
):
    def setUp(self):
        mail.outbox = []

    @staticmethod
    def render_template(
        template_name,
        context,
    ):
        values = {
            "subject.txt": (
                "\n"
                "ایمیل آزمایشی TaskFlow"
                "\n"
            ),
            "body.txt": (
                "سلام مهدی"
            ),
            "body.html": (
                "<p>سلام مهدی</p>"
            ),
        }

        return values[
            template_name
        ]

    def make_email(
        self,
        **overrides,
    ):
        values = {
            "category": "test",
            "subject_template": (
                "subject.txt"
            ),
            "text_template": (
                "body.txt"
            ),
            "html_template": (
                "body.html"
            ),
            "recipients": (
                "user@example.com",
            ),
            "context": {
                "name": "مهدی",
            },
        }

        values.update(
            overrides
        )

        return TemplatedEmail(
            **values
        )

    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_builds_multipart_email(
        self,
        mocked_render,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        message = (
            build_templated_email(
                self.make_email()
            )
        )

        self.assertEqual(
            message.subject,
            (
                "ایمیل آزمایشی "
                "TaskFlow"
            ),
        )

        self.assertEqual(
            message.to,
            [
                "user@example.com",
            ],
        )

        self.assertEqual(
            message.body,
            "سلام مهدی",
        )

        self.assertEqual(
            len(
                message.alternatives
            ),
            1,
        )

        alternative = (
            message.alternatives[0]
        )

        self.assertEqual(
            alternative.mimetype,
            "text/html",
        )

        self.assertEqual(
            alternative.content,
            "<p>سلام مهدی</p>",
        )

    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_uses_default_sender(
        self,
        mocked_render,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        message = (
            build_templated_email(
                self.make_email()
            )
        )

        self.assertEqual(
            message.from_email,
            (
                "TaskFlow "
                "<noreply@example.com>"
            ),
        )

    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_recipient_duplicates_are_removed(
        self,
        mocked_render,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        message = (
            build_templated_email(
                self.make_email(
                    recipients=(
                        " USER@example.com ",
                        "user@example.com",
                        "other@example.com",
                    )
                )
            )
        )

        self.assertEqual(
            message.to,
            [
                "USER@example.com",
                "other@example.com",
            ],
        )

    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_empty_recipient_list_is_rejected(
        self,
        mocked_render,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        with self.assertRaises(
            ValueError
        ):
            build_templated_email(
                self.make_email(
                    recipients=()
                )
            )

    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_send_delivers_message(
        self,
        mocked_render,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        send_templated_email(
            self.make_email()
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

    @patch(
        (
            "apps.core.emailing."
            "EmailMultiAlternatives."
            "send"
        ),
        return_value=0,
    )
    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_zero_delivery_count_is_failure(
        self,
        mocked_render,
        mocked_send,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        with self.assertRaises(
            EmailDeliveryError
        ):
            send_templated_email(
                self.make_email()
            )

    @patch(
        (
            "apps.core.emailing."
            "EmailMultiAlternatives."
            "send"
        ),
        side_effect=RuntimeError(
            "SMTP unavailable"
        ),
    )
    @patch(
        
            "apps.core.emailing."
            "render_to_string"
        
    )
    def test_backend_exception_is_wrapped(
        self,
        mocked_render,
        mocked_send,
    ):
        mocked_render.side_effect = (
            self.render_template
        )

        with self.assertRaises(
            EmailDeliveryError
        ) as error:
            send_templated_email(
                self.make_email()
            )

        self.assertIsInstance(
            error.exception.__cause__,
            RuntimeError,
        )