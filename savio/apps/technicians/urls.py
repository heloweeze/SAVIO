from django.urls import path

from . import views

app_name = "technicians"

urlpatterns = [
    path("", views.technician_list, name="list"),
    path("ajouter/", views.technician_create, name="create"),
    path("supprimer-selection/", views.technician_bulk_delete, name="bulk_delete"),
    path("<int:pk>/", views.technician_detail, name="detail"),
    path("<int:pk>/modifier/", views.technician_update, name="update"),
    path("<int:pk>/supprimer/", views.technician_delete, name="delete"),
]
