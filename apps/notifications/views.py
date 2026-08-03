from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import (
    url_has_allowed_host_and_scheme,
)
from django.views import View
from django.views.generic import ListView

from .models import Notification
from .selectors import (
    get_unread_notifications_count,
    get_user_notifications,
)
from .services import NotificationService

def get_safe_redirect_url(
    *,
    request,
    fallback_url,
):
    next_url = (
        request.POST
        .get("next", "")
        .strip()
    )
    
    if not next_url:
        return fallback_url
    
    is_safe = (
        url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={
                request.get_host(),
            },
            require_https=(
                request.is_secure()
            ),
        )
    )
    
    if not is_safe:
        return fallback_url
    
    return next_url

class NotificationListView(
    LoginRequiredMixin,
    ListView,
):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return get_user_notifications(
            user=self.request.user,
        )
    
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        context['unread_count'] = (
            get_unread_notifications_count(
                user=self.request.user,
            )
        )

        return context
    
class NotificationMarkReadView(
    LoginRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    def post(
        self,
        request,
        notification_pk,
    ):
        (
            notification,
            changed,
        ) = (
            NotificationService
            .mark_as_read(
                recipient=request.user,
                notification_pk=notification_pk,
            )
        )
        
        if changed:
            messages.success(
                request,
                "اعلان خوانده شد.",
            )
        else:
            messages.info(
                request,
                (
                    "این اعلان قبلاً "
                    "خوانده شده بود."
                ),
            )
        
        fallback_url = reverse('notifications:list')

        redirect_url = (
            get_safe_redirect_url(
                request=request,
                fallback_url=fallback_url,
            )
        )
        
        return redirect(redirect_url)

class NotificationMarkAllReadView(
    LoginRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    def post(
        self,
        request,
    ):
        updated_count = (
            NotificationService
            .mark_all_as_read(
                recipient=request.user,
            )
        )
        
        if updated_count:
            messages.success(
                request,
                (
                    f"{updated_count} اعلان "
                    "خوانده شد."
                ),
            )
        else:
            messages.info(
                request,
                (
                    "اعلان خوانده‌نشده‌ای "
                    "وجود ندارد."
                ),
            )
        
        fallback_url = reverse(
            "notifications:list"
        )

        redirect_url = (
            get_safe_redirect_url(
                request=request,
                fallback_url=(
                    fallback_url
                ),
            )
        )

        return redirect(redirect_url)