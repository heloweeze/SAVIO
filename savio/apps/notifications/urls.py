from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("<int:pk>/ouvrir/", views.notification_open, name="open"),
    path("<int:pk>/lue/", views.mark_read, name="mark_read"),
    path("toutes-lues/", views.mark_all_read, name="mark_all_read"),
]
