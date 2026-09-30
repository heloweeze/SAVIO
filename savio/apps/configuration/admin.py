from django.contrib import admin
from .models import AppSetting, PriorityItem, StatusItem


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ("site_name", "support_email", "enable_notifications", "updated_at")


@admin.register(StatusItem)
class StatusItemAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(PriorityItem)
class PriorityItemAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "order", "is_active")
    list_editable = ("order", "is_active")
