"""Vues d'import / export CSV (réservées aux administrateurs)."""
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import admin_required

from . import services
from .forms import CsvUploadForm


def _csv_response(content: str, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@admin_required
def home(request):
    return render(request, "importexport/home.html")


# --- Exports ---------------------------------------------------------------
@admin_required
def export_clients_view(request):
    return _csv_response(services.export_clients(), "clients.csv")


@admin_required
def export_technicians_view(request):
    return _csv_response(services.export_technicians(), "techniciens.csv")


@admin_required
def export_tickets_view(request):
    return _csv_response(services.export_tickets(), "demandes.csv")


@admin_required
def export_history_view(request):
    return _csv_response(services.export_history(), "historique.csv")


# --- Imports ---------------------------------------------------------------
def _handle_import(request, import_func, title: str, example_headers: list[str]):
    report = None
    if request.method == "POST":
        form = CsvUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = import_func(form.cleaned_data["file"])
            messages.success(
                request,
                f"Import terminé : {report['created']} créés, {report['updated']} mis à jour, "
                f"{len(report['errors'])} erreurs.",
            )
    else:
        form = CsvUploadForm()
    return render(request, "importexport/import_form.html", {
        "form": form,
        "title": title,
        "example_headers": example_headers,
        "report": report,
        "is_client_import": import_func is services.import_clients,
        "is_technician_import": import_func is services.import_technicians,
    })


@admin_required
def import_clients_view(request):
    return _handle_import(request, services.import_clients, "Importer des clients",
                          services.CLIENT_IMPORT_HEADERS)


@admin_required
def import_technicians_view(request):
    return _handle_import(request, services.import_technicians, "Importer des techniciens",
                          services.TECH_IMPORT_HEADERS)
