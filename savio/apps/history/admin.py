from django.contrib import admin
from .models import HistoryEntry


@admin.register(HistoryEntry)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "ticket", "author", "message")
    list_filter = ("action",)
    search_fields = ("message", "ticket__reference")
    readonly_fields = ("ticket", "author", "action", "message", "created_at")
