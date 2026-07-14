from django.contrib import admin

from .models import Workspace, WorkspaceMembership, WorkspaceInvitation

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


@admin.register(WorkspaceInvitation)
class WorkspaceInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "workspace",
        "role",
        "status",
        "invited_by",
        "expires_at",
        "created_at",
    )

    list_filter = (
        "status",
        "role",
        "created_at",
    )

    search_fields = (
        "email",
        "workspace__name",
        "invited_by__username",
    )

    readonly_fields = (
        "token",
        "created_at",
        "updated_at",
    )


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "workspace",
        "role",
        "created_at",
    )

    list_filter = ("role",)

    search_fields = (
        "user__username",
        "user__email",
        "workspace__name",
    )
    
    autocomplete_fields = (
        "workspace",
        "user",
    )