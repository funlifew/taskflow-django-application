from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "TaskFlow Profile",
            {
                "fields": (
                    "email_verified",
                    "avatar",
                    "bio",
                )
            },
        ),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "اطلاعات حساب",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                )
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "email_verified",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )