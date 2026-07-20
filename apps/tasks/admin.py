from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "column",
        "priority",
        "status",
        "position",
        "assignee",
        "due_at",
        "is_archived",
        "updated_at",
    )

    list_filter = (
        "priority",
        "status",
        "is_archived",
        "column__board__workspace",
    )

    search_fields = (
        "title",
        "description",
        "column__title",
        "column__board__title",
        "assignee__username",
        "assignee__email",
        "created_by__username",
    )

    list_select_related = (
        "column",
        "column__board",
        "column__board__workspace",
        "assignee",
        "created_by",
    )

    raw_id_fields = (
        "column",
        "assignee",
        "created_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "column",
        "position",
        "pk",
    )