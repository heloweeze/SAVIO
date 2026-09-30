from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/charts/status/", views.chart_status, name="chart_status"),
    path("api/charts/technician/", views.chart_by_technician, name="chart_by_technician"),
    path("api/charts/evolution/", views.chart_evolution, name="chart_evolution"),
]
