from django.contrib import admin

from .models import (
    Task,
    TaskActivity,
    TaskComment,
)


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

@admin.register(TaskComment)
class TaskCommentAdmin(
    admin.ModelAdmin
):
    list_display = (
        "id",
        "task",
        "author",
        "is_deleted",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_deleted",
        "created_at",
    )

    search_fields = (
        "body",
        "task__title",
        "author__username",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(TaskActivity)
class TaskActivityAdmin(
    admin.ModelAdmin
):
    list_display = (
        "id",
        "task",
        "actor",
        "action",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "task__title",
        "actor__username",
    )

    readonly_fields = (
        "task",
        "actor",
        "action",
        "metadata",
        "created_at",
    )

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False