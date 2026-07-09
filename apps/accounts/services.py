from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


from apps.core.cache_keys import verification_resend_key

from .tokens import account_activation_token

from random import randint
import os

User = get_user_model()
ACTIVATION_EMAIL_COOLDOWN = 60 * 2 # 2 minutes

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