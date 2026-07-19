from django.contrib import admin

from .models import Column


@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "board",
        "position",
        "is_archived",
        "created_by",
        "updated_at",
    )

    list_filter = (
        "is_archived",
        "board__workspace",
    )

    search_fields = (
        "title",
        "board__title",
        "board__workspace__name",
        "created_by__username",
        "created_by__email",
    )

    list_select_related = (
        "board",
        "board__workspace",
        "created_by",
    )

    raw_id_fields = (
        "board",
        "created_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "board",
        "position",
        "pk",
    )