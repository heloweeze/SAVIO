from django.contrib import admin

from .models import Comment, Ticket


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("reference", "subject", "client", "status", "priority", "assigned_to", "created_at")
    list_filter = ("status", "priority", "assigned_to")
    search_fields = ("reference", "subject", "description")
    autocomplete_fields = ("client", "assigned_to", "author")
    inlines = [CommentInline]
    readonly_fields = ("reference", "created_at", "updated_at", "closed_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
