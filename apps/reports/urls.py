from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_home, name="home"),
    path("global/", views.report_global, name="global"),
    path("tickets/", views.report_tickets, name="tickets"),
    path("par-technicien/", views.report_by_technician, name="by_technician"),
    path("par-client/", views.report_by_client, name="by_client"),
]
