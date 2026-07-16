from django.contrib import admin


from .models import Board
# Register your models here.

@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "workspace",
        "created_by",
        "is_archived",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_archived",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "title",
        "description",
        "workspace__name",
        "created_by__username",
        "created_by__email",
    )

    autocomplete_fields = (
        "workspace",
        "created_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_select_related = (
        "workspace",
        "created_by",
    )
