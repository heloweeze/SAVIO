from django.urls import path

from . import views

app_name = "history"

urlpatterns = [
    path("", views.history_list, name="list"),
    path("demande/<int:ticket_id>/", views.history_for_ticket, name="by_ticket"),
    path("client/<int:client_id>/", views.history_for_client, name="by_client"),
]
