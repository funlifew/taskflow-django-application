import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.cache_keys import (
    verification_resend_key,
)

from .tokens import account_activation_token


logger = logging.getLogger(__name__)

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
        user.email_verified = False
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
            .get(pk=user.pk)
        )

        already_active = (
            locked_user.is_active
            and locked_user.email_verified
        )

        if already_active:
            return locked_user, False

        locked_user.is_active = True
        locked_user.email_verified = True

        locked_user.save(
            update_fields=[
                "is_active",
                "email_verified",
            ]
        )

        return locked_user, True

def can_send_activation_email(user) -> bool:
    cache_key = verification_resend_key(user.id)
    return cache.get(cache_key) is None

def mark_activation_email_send(user) -> None:
    cache_key = verification_resend_key(user.id)
    cache.set(cache_key, True, timeout=ACTIVATION_EMAIL_COOLDOWN)

def send_activation_email(request, user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    
    activation_path = reverse(
        'accounts:activate',
        kwargs={
            'uidb64': uid,
            'token': token,
        },
    )
    
    activation_url = request.build_absolute_uri(activation_path)
    
    context = {
        'user': user,
        'activation_url': activation_url,
    }
    
    subject = 'فعالسازی حساب TaskFlow'
    
    text_body = render_to_string(
        'accounts/emails/activation_email.txt',
        context,
    )
    
    html_body = render_to_string(
        'accounts/emails/activation_email.html',
        context,
    )
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    
    email.attach_alternative(html_body, 'text/html')
    email.send()
    

def acquire_activation_email_lock(user_id: int) -> bool:
    cache_key = verification_resend_key(user_id)
    
    try:
        return cache.add(
            cache_key,
            True,
            timeout=ACTIVATION_EMAIL_COOLDOWN,
        )
    except Exception:
        logger.exception(
            'Activation-email cache is unavailable for user %s',
            user_id
        )
        
        return True

def release_activation_email_lock(user_id: int) -> None:
    cache_key = verification_resend_key(user_id)

    try:
        cache.delete(cache_key)
    except Exception:
        logger.exception(
            'Could not release activation-email lock for user %s',
            user_id,
        )

def send_activation_email_with_cooldown(request, user) -> bool:
    if not acquire_activation_email_lock(user.pk):
        return False
    
    try:
        send_activation_email(request, user)
    except Exception:
        release_activation_email_lock(user.pk)
        raise
    
    return True