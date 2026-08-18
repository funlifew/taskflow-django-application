import logging

from django.contrib.auth import (
    get_user_model,
)
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import (
    force_bytes,
)
from django.utils.http import (
    urlsafe_base64_encode,
)

from apps.core.cache_keys import (
    verification_resend_key,
)
from apps.core.emailing import (
    TemplatedEmail,
    send_templated_email,
)

from .tokens import (
    account_activation_token,
)

logger = logging.getLogger(
    __name__
)

User = get_user_model()

ACTIVATION_EMAIL_COOLDOWN = 120


class AccountLifecycleService:
    @staticmethod
    @transaction.atomic
    def create_inactive(
        *,
        user,
    ):
        user.is_active = False

        user.email_verified = (
            False
        )

        user.save()

        return user

    @staticmethod
    @transaction.atomic
    def activate(
        *,
        user,
    ):
        locked_user = (
            User.objects
            .select_for_update()
            .get(
                pk=user.pk
            )
        )

        already_active = (
            locked_user.is_active
            and locked_user.email_verified
        )

        if already_active:
            return (
                locked_user,
                False,
            )

        locked_user.is_active = (
            True
        )

        locked_user.email_verified = (
            True
        )

        locked_user.save(
            update_fields=[
                "is_active",
                "email_verified",
            ]
        )

        return (
            locked_user,
            True,
        )


def send_activation_email(
    request,
    user,
) -> None:
    uid = (
        urlsafe_base64_encode(
            force_bytes(
                user.pk
            )
        )
    )

    token = (
        account_activation_token
        .make_token(
            user
        )
    )

    activation_path = reverse(
        "accounts:activate",
        kwargs={
            "uidb64": uid,
            "token": token,
        },
    )

    activation_url = (
        request.build_absolute_uri(
            activation_path
        )
    )

    send_templated_email(
        TemplatedEmail(
            category=(
                "account_activation"
            ),
            subject_template=(
                "accounts/emails/"
                "activation_subject.txt"
            ),
            text_template=(
                "accounts/emails/"
                "activation_email.txt"
            ),
            html_template=(
                "accounts/emails/"
                "activation_email.html"
            ),
            recipients=(
                user.email,
            ),
            context={
                "user": user,
                "activation_url": (
                    activation_url
                ),
            },
        )
    )


def acquire_activation_email_lock(
    user_id: int,
) -> bool:
    cache_key = (
        verification_resend_key(
            user_id
        )
    )

    try:
        return cache.add(
            cache_key,
            True,
            timeout=(
                ACTIVATION_EMAIL_COOLDOWN
            ),
        )

    except Exception:
        logger.exception(
            (
                "Activation-email "
                "cache is unavailable "
                "for user %s"
            ),
            user_id,
        )

        # Fail open:
        # email verification should
        # remain available when the
        # cache backend is down.
        return True


def release_activation_email_lock(
    user_id: int,
) -> None:
    cache_key = (
        verification_resend_key(
            user_id
        )
    )

    try:
        cache.delete(
            cache_key
        )

    except Exception:
        logger.exception(
            (
                "Could not release "
                "activation-email lock "
                "for user %s"
            ),
            user_id,
        )


def send_activation_email_with_cooldown(
    request,
    user,
) -> bool:
    if not (
        acquire_activation_email_lock(
            user.pk
        )
    ):
        return False

    try:
        send_activation_email(
            request,
            user,
        )

    except Exception:
        # Delivery failures must not
        # consume the entire cooldown.
        release_activation_email_lock(
            user.pk
        )

        raise

    return True