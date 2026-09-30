from django.contrib import admin
from .models import Technician


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ("__str__", "email", "phone", "specialty", "is_active")
    list_filter = ("is_active",)
    search_fields = ("first_name", "last_name", "email", "specialty")
