from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.client_list, name="list"),
    path("ajouter/", views.client_create, name="create"),
    path("supprimer-selection/", views.client_bulk_delete, name="bulk_delete"),
    path("<int:pk>/", views.client_detail, name="detail"),
    path("<int:pk>/modifier/", views.client_update, name="update"),
    path("<int:pk>/supprimer/", views.client_delete, name="delete"),
]
