from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

handler403 = "apps.dashboard.views.handler403"
handler404 = "apps.dashboard.views.handler404"
handler500 = "apps.dashboard.views.handler500"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard:home", permanent=False)),
    path("admin/", admin.site.urls),
    path("auth/", include("apps.accounts.urls", namespace="accounts")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("clients/", include("apps.clients.urls", namespace="clients")),
    path("techniciens/", include("apps.technicians.urls", namespace="technicians")),
    path("demandes/", include("apps.tickets.urls", namespace="tickets")),
    path("historique/", include("apps.history.urls", namespace="history")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("rapports/", include("apps.reports.urls", namespace="reports")),
    path("import-export/", include("apps.importexport.urls", namespace="importexport")),
    path("configuration/", include("apps.configuration.urls", namespace="configuration")),
    path("assistant/", include("apps.assistant.urls", namespace="assistant")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
