from django.contrib import admin

from .models import Workspace, WorkspaceMembership

# Register your models here.

class WorkspaceMembershipInline(admin.TabularInline):
    model = WorkspaceMembership
    extra = 0
    autocomplete_fields = ('user', )
    
@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "is_archived",
        "created_at",
    )
    list_filter = (
        "is_archived",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "owner__username",
        "owner__email",
    )
    autocomplete_fields = ("owner",)
    inlines = (WorkspaceMembershipInline,)

@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "workspace",
        "user",
        "role",
        "created_at",
    )
    list_filter = ("role",)
    search_fields = (
        "workspace__name",
        "user__username",
        "user__email",
    )
    autocomplete_fields = (
        "workspace",
        "user",
    )