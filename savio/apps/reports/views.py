"""Vues de reporting.

Toutes les vues sont réservées aux administrateurs et calculent des agrégats
à la volée à partir des modèles métier. Aucun modèle propre n'est nécessaire.
"""
from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import admin_required
from apps.clients.models import Client
from apps.technicians.models import Technician
from apps.tickets.models import CLOSED_STATUSES, PriorityChoices, StatusChoices, Ticket

from . import pdf as pdf_builder


def _wants_pdf(request) -> bool:
    """Détecte ?format=pdf dans la querystring."""
    return (request.GET.get("format") or "").lower() == "pdf"


def _period(request):
    """Lit les paramètres start/end de la querystring (par défaut 30 derniers jours)."""
    today = timezone.localdate()
    default_start = today - timedelta(days=30)
    start = request.GET.get("start") or default_start.isoformat()
    end = request.GET.get("end") or today.isoformat()
    return start, end


@admin_required
def reports_home(request):
    """Page d'accueil des rapports."""
    return render(request, "reports/home.html", {
        "total_tickets": Ticket.objects.count(),
        "total_clients": Client.objects.count(),
        "total_technicians": Technician.objects.filter(is_active=True).count(),
    })


@admin_required
def report_global(request):
    start, end = _period(request)
    qs = Ticket.objects.filter(created_at__date__gte=start, created_at__date__lte=end)

    by_status = list(
        qs.values("status").annotate(total=Count("id")).order_by("-total")
    )
    status_map = dict(StatusChoices.choices)
    for row in by_status:
        row["label"] = status_map.get(row["status"], row["status"])

    by_priority = list(
        qs.values("priority").annotate(total=Count("id")).order_by("-total")
    )
    priority_map = dict(PriorityChoices.choices)
    for row in by_priority:
        row["label"] = priority_map.get(row["priority"], row["priority"])

    evolution = list(
        qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    total = qs.count()
    open_count = qs.exclude(status__in=CLOSED_STATUSES).count()
    closed_count = qs.filter(status__in=CLOSED_STATUSES).count()

    if _wants_pdf(request):
        return pdf_builder.build_global_pdf(
            start=start,
            end=end,
            total=total,
            open_count=open_count,
            closed_count=closed_count,
            by_status=by_status,
            by_priority=by_priority,
            evolution=evolution,
        )

    return render(request, "reports/global.html", {
        "start": start,
        "end": end,
        "total": total,
        "open_count": open_count,
        "closed_count": closed_count,
        "by_status": by_status,
        "by_priority": by_priority,
        "evolution": evolution,
    })


@admin_required
def report_tickets(request):
    start, end = _period(request)
    qs = (
        Ticket.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        .select_related("client", "assigned_to")
        .order_by("-created_at")
    )
    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)
    priority_filter = request.GET.get("priority")
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    total = qs.count()
    tickets = list(qs[:500])

    if _wants_pdf(request):
        return pdf_builder.build_tickets_pdf(
            start=start,
            end=end,
            total=total,
            tickets=tickets,
            status_filter=status_filter,
            priority_filter=priority_filter,
        )

    return render(request, "reports/tickets.html", {
        "start": start,
        "end": end,
        "tickets": tickets,
        "total": total,
        "status_filter": status_filter,
        "priority_filter": priority_filter,
        "statuses": StatusChoices.choices,
        "priorities": PriorityChoices.choices,
    })


@admin_required
def report_by_technician(request):
    start, end = _period(request)
    qs = Ticket.objects.filter(created_at__date__gte=start, created_at__date__lte=end)

    rows = (
        Technician.objects.annotate(
            total=Count("tickets_assigned", filter=Q(tickets_assigned__in=qs)),
            open_tickets=Count(
                "tickets_assigned",
                filter=Q(tickets_assigned__in=qs)
                & ~Q(tickets_assigned__status__in=CLOSED_STATUSES),
            ),
            closed_tickets=Count(
                "tickets_assigned",
                filter=Q(
                    tickets_assigned__in=qs,
                    tickets_assigned__status__in=CLOSED_STATUSES,
                ),
            ),
        )
        .order_by("-total", "last_name")
    )

    unassigned = qs.filter(assigned_to__isnull=True).count()
    rows_list = list(rows)

    if _wants_pdf(request):
        return pdf_builder.build_by_technician_pdf(
            start=start,
            end=end,
            rows=rows_list,
            unassigned=unassigned,
        )

    return render(request, "reports/by_technician.html", {
        "start": start,
        "end": end,
        "rows": rows_list,
        "unassigned": unassigned,
    })


@admin_required
def report_by_client(request):
    start, end = _period(request)
    qs = Ticket.objects.filter(created_at__date__gte=start, created_at__date__lte=end)

    rows = (
        Client.objects.annotate(
            total=Count("tickets", filter=Q(tickets__in=qs)),
            open_tickets=Count(
                "tickets",
                filter=Q(tickets__in=qs) & ~Q(tickets__status__in=CLOSED_STATUSES),
            ),
            closed_tickets=Count(
                "tickets",
                filter=Q(tickets__in=qs, tickets__status__in=CLOSED_STATUSES),
            ),
        )
        .filter(total__gt=0)
        .order_by("-total", "last_name")
    )

    rows_list = list(rows)

    if _wants_pdf(request):
        return pdf_builder.build_by_client_pdf(
            start=start,
            end=end,
            rows=rows_list,
        )

    return render(request, "reports/by_client.html", {
        "start": start,
        "end": end,
        "rows": rows_list,
    })
