from django.urls import path

from . import views

app_name = "configuration"

urlpatterns = [
    path("", views.configuration_home, name="home"),
    path("statuts/ajouter/", views.status_create, name="status_create"),
    path("statuts/<int:pk>/modifier/", views.status_update, name="status_update"),
    path("statuts/<int:pk>/supprimer/", views.status_delete, name="status_delete"),
    path("priorites/ajouter/", views.priority_create, name="priority_create"),
    path("priorites/<int:pk>/modifier/", views.priority_update, name="priority_update"),
    path("priorites/<int:pk>/supprimer/", views.priority_delete, name="priority_delete"),
]
