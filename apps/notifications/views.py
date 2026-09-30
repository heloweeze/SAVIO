from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(recipient=request.user)
    paginator = Paginator(qs, settings.DEFAULT_PAGE_SIZE * 2)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {
        "page_obj": page, "notifications": page.object_list,
    })


@login_required
def notification_open(request, pk):
    """Ouvre une notification : la marque comme lue puis redirige."""
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not note.is_read:
        note.is_read = True
        note.read_at = timezone.now()
        note.save(update_fields=["is_read", "read_at"])
    return redirect(note.url or "notifications:list")


@require_POST
@login_required
def mark_read(request, pk):
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    note.is_read = True
    note.read_at = timezone.now()
    note.save(update_fields=["is_read", "read_at"])
    return redirect("notifications:list")


@require_POST
@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now(),
    )
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect("notifications:list")
