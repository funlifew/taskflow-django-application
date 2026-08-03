from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(
    admin.ModelAdmin
):
    list_display = (
        "id",
        "recipient",
        "actor",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "recipient__username",
        "recipient__email",
        "actor__username",
        "title",
        "message",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "read_at",
    )

    list_select_related = (
        "recipient",
        "actor",
    )

    ordering = (
        "-created_at",
        "-pk",
    )