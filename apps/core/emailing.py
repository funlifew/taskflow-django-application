import logging

from collections.abc import (
    Mapping,
)
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.mail import (
    EmailMultiAlternatives,
)
from django.template.loader import (
    render_to_string,
)

logger = logging.getLogger(__name__)

class EmailDeliveryError(RuntimeError):
    pass

@dataclass(
    frozen=True,
    slots=True,
)
class TemplatedEmail:
    category: str
    
    subject_template: str
    text_template: str
    
    recipients: tuple[str, ...]

    context: Mapping[
        str,
        Any,
    ]
    
    html_template: (
        str
        | None
    ) = None
    
    from_email: (
        str
        | None
    ) = None
    
    reply_to: tuple[
        str,
        ...,
    ] = ()

    headers: (
        Mapping[str, str]
        | None
    ) = None

def _normalize_recipients(
    recipients: tuple[
        str,
        ...,
    ],
) -> list[str]:
    normalized = []
    seen = set()

    for raw_email in recipients:
        email = raw_email.strip()

        if not email:
            continue
        
        lookup_value = email.casefold()

        if lookup_value in seen:
            continue
        
        seen.add(
            lookup_value
        )
        normalized.append(
            email
        )
    
    if not normalized:
        raise ValueError(
            (
                "Transactional email "
                "requires at least one "
                "recipient."
            )
        )
    
    return normalized

def _render_subject(
    *,
    template_name: str,
    context: Mapping[
        str,
        Any,
    ],
) -> str:
    rendered_subject = render_to_string(
        template_name,
        context,
    )
    
    subject = " ".join(
        line.strip()
        for line
        in rendered_subject.splitlines()
        if line.strip()
    )
    
    if not subject:
        raise ValueError(
            (
                "Email subject template "
                "rendered an empty subject."
            )
        )
    
    return subject

def build_templated_email(
    email: TemplatedEmail,
) -> EmailMultiAlternatives:
    
    recipients = _normalize_recipients(email.recipients)

    context = dict(email.context)

    subject = _render_subject(
        template_name=email.subject_template,
        context=context,
    )
    
    text_body = render_to_string(
        email.text_template,
        context,
    )
    
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=(
            email.from_email
            or settings.DEFAULT_FROM_EMAIL
        ),
        to=recipients,
        reply_to=list(email.reply_to),
        headers=dict(
            email.headers
            or {}
        ),
    )
    
    if email.html_template:
        html_body = render_to_string(
            email.html_template,
            context,
        )
        
        message.attach_alternative(
            html_body,
            'text/html',
        )
    
    return message

def send_templated_email(
    email: TemplatedEmail,
) -> None:
    try:
        message = build_templated_email(email)

        sent_count = message.send(fail_silently=False)
    
    except Exception as exc:
        logger.exception(
            (
                "Transactional email "
                "delivery failed. "
                "category=%s"
            ),
            email.category,
        )

        raise EmailDeliveryError(
            (
                "Could not deliver "
                f"{email.category} email."
            )
        ) from exc

    if sent_count != 1:
        logger.error(
            (
                "Transactional email "
                "backend returned an "
                "unexpected delivery "
                "count. category=%s "
                "sent_count=%s"
            ),
            email.category,
            sent_count,
        )

        raise EmailDeliveryError(
            (
                "Email backend did not "
                "confirm delivery."
            )
        )

    logger.info(
        (
            "Transactional email "
            "accepted by backend. "
            "category=%s "
            "recipient_count=%s"
        ),
        email.category,
        len(message.to),
    )
