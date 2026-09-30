from django.urls import path

from . import views

app_name = "importexport"

urlpatterns = [
    path("", views.home, name="home"),

    # Exports
    path("export/clients.csv", views.export_clients_view, name="export_clients"),
    path("export/techniciens.csv", views.export_technicians_view, name="export_technicians"),
    path("export/demandes.csv", views.export_tickets_view, name="export_tickets"),
    path("export/historique.csv", views.export_history_view, name="export_history"),

    # Imports
    path("import/clients/", views.import_clients_view, name="import_clients"),
    path("import/techniciens/", views.import_technicians_view, name="import_technicians"),
]
