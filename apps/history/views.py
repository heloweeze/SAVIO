from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from apps.accounts.decorators import admin_required
from apps.clients.models import Client
from apps.tickets.models import Ticket

from .models import HistoryEntry


@admin_required
def history_list(request):
    q = request.GET.get("q", "").strip()
    action = request.GET.get("action", "").strip()

    qs = HistoryEntry.objects.select_related("ticket", "author").all()
    if q:
        qs = qs.filter(
            Q(message__icontains=q)
            | Q(ticket__reference__icontains=q)
            | Q(ticket__subject__icontains=q)
        )
    if action:
        qs = qs.filter(action=action)

    paginator = Paginator(qs, settings.DEFAULT_PAGE_SIZE * 2)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "history/list.html", {
        "page_obj": page,
        "entries": page.object_list,
        "q": q,
        "action": action,
        "actions": HistoryEntry.Action.choices,
    })


@admin_required
def history_for_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    entries = ticket.history_entries.select_related("author").all()
    return render(request, "history/by_ticket.html", {
        "ticket": ticket, "entries": entries,
    })


@admin_required
def history_for_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    entries = HistoryEntry.objects.select_related("ticket", "author").filter(
        ticket__client=client
    )
    return render(request, "history/by_client.html", {
        "client": client, "entries": entries,
    })
