from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("mes-demandes/", views.my_tickets, name="my_list"),
    path("nouvelle/", views.ticket_create, name="create"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("<int:pk>/modifier/", views.ticket_update, name="update"),
    path("<int:pk>/supprimer/", views.ticket_delete, name="delete"),
    path("<int:pk>/affecter/", views.ticket_assign, name="assign"),
    path("<int:pk>/statut/", views.ticket_change_status, name="status"),
    path("<int:pk>/cloturer/", views.ticket_close, name="close"),
    path("<int:pk>/commenter/", views.ticket_comment, name="comment"),
]
