from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SavioUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("SAVIO", {"fields": ("role", "phone", "job_title", "address", "avatar")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("SAVIO", {"fields": ("email", "role")}),
    )
    search_fields = ("username", "email", "first_name", "last_name")
