from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import admin_required, staff_required
from apps.clients.models import Client
from apps.history.models import HistoryEntry
from apps.technicians.models import Technician
from apps.tickets.models import (
    CLOSED_STATUSES,
    PriorityChoices,
    StatusChoices,
    Ticket,
)


# ---------------------------------------------------------------------------
# Home — aiguille selon le rôle
# ---------------------------------------------------------------------------
@login_required
def home(request):
    if request.user.is_admin_role or request.user.is_superuser or request.user.is_technician_role:
        return admin_dashboard(request)
    return user_dashboard(request)


def _counts():
    qs = Ticket.objects.all()
    total = qs.count()
    new = qs.filter(status=StatusChoices.NEW).count()
    open_ = qs.filter(status=StatusChoices.OPEN).count()
    in_progress = qs.filter(status=StatusChoices.IN_PROGRESS).count()
    pending = qs.filter(status=StatusChoices.PENDING).count()
    closed = qs.filter(status__in=CLOSED_STATUSES).count()
    urgent = qs.filter(priority__in=(PriorityChoices.HIGH, PriorityChoices.URGENT)).exclude(
        status__in=CLOSED_STATUSES
    ).count()
    return {
        "tickets_total": total,
        "tickets_new": new,
        "tickets_open": open_,
        "tickets_in_progress": in_progress,
        "tickets_pending": pending,
        "tickets_closed": closed,
        "tickets_urgent": urgent,
    }


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------
@staff_required
def admin_dashboard(request):
    ctx = _counts()
    ctx.update({
        "clients_total": Client.objects.count(),
        "technicians_total": Technician.objects.count(),
        "recent_tickets": Ticket.objects.select_related("client", "assigned_to").order_by("-created_at")[:8],
        "recent_history": HistoryEntry.objects.select_related("ticket", "author").order_by("-created_at")[:8],
    })
    return render(request, "dashboard/admin.html", ctx)


@login_required
def user_dashboard(request):
    from django.db.models import Q
    user = request.user
    user_email = (user.email or "").strip()
    visibility = Q(author=user)
    if user_email:
        visibility |= Q(client__email__iexact=user_email)
    my_tickets = Ticket.objects.filter(visibility).distinct()
    ctx = {
        "my_total": my_tickets.count(),
        "my_open": my_tickets.exclude(status__in=CLOSED_STATUSES).count(),
        "my_closed": my_tickets.filter(status__in=CLOSED_STATUSES).count(),
        "recent_tickets": my_tickets.order_by("-created_at")[:5],
    }
    return render(request, "dashboard/user.html", ctx)


# ---------------------------------------------------------------------------
# Endpoints JSON pour les graphes
# ---------------------------------------------------------------------------
@staff_required
def chart_status(request):
    """Répartition des tickets par statut — pie chart."""
    data = (
        Ticket.objects.values("status").annotate(c=Count("id")).order_by("status")
    )
    labels_map = dict(StatusChoices.choices)
    return JsonResponse({
        "labels": [labels_map.get(d["status"], d["status"]) for d in data],
        "values": [d["c"] for d in data],
    })


@staff_required
def chart_by_technician(request):
    """Nombre de tickets par technicien — bar chart."""
    data = (
        Ticket.objects.exclude(assigned_to=None)
        .values("assigned_to__first_name", "assigned_to__last_name")
        .annotate(c=Count("id"))
        .order_by("-c")[:15]
    )
    labels, values = [], []
    for d in data:
        name = f"{d['assigned_to__first_name']} {d['assigned_to__last_name']}".strip()
        labels.append(name or "—")
        values.append(d["c"])
    return JsonResponse({"labels": labels, "values": values})


@staff_required
def chart_evolution(request):
    """Évolution du nombre de demandes sur 30 jours — line chart."""
    days = 30
    since = timezone.now() - timedelta(days=days)
    raw = (
        Ticket.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(c=Count("id"))
        .order_by("day")
    )
    by_day = {d["day"]: d["c"] for d in raw}
    labels, values = [], []
    today = timezone.now().date()
    for i in range(days, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime("%d/%m"))
        values.append(by_day.get(day, 0))
    return JsonResponse({"labels": labels, "values": values})


# ---------------------------------------------------------------------------
# Handlers d'erreur
# ---------------------------------------------------------------------------
def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)
