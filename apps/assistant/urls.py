from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    # 1. Diagnostic ticket (admin / tech)
    path("ticket/<int:pk>/suggest/", views.suggest_diagnostic, name="suggest"),

    # 2. Chat utilisateur
    path("chat/", views.chat_page, name="chat_page"),
    path("chat/send/", views.chat_send, name="chat_send"),
    path("chat/reset/", views.chat_reset, name="chat_reset"),

    # 3. Résumé admin
    path("admin/", views.admin_panel, name="admin_panel"),
    path("admin/summary/", views.admin_summary, name="admin_summary"),
]
