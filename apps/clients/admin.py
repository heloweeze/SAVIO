from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type", "email", "phone", "city", "is_active")
    list_filter = ("type", "is_active", "country")
    search_fields = ("last_name", "first_name", "company", "email", "phone")
