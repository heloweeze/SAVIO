from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Notification


def notify_user(user, title, message="", url="", related_ticket=None):
    """Envoie une notification à un utilisateur précis."""
    if not user or not getattr(user, "pk", None):
        return None
    if not url and related_ticket is not None:
        try:
            url = reverse("tickets:detail", args=[related_ticket.pk])
        except Exception:
            url = ""
    return Notification.objects.create(
        recipient=user,
        title=title,
        message=message or "",
        url=url or "",
        ticket=related_ticket,
    )


def notify_admins(title, message="", url="", related_ticket=None):
    """Envoie une notification à tous les administrateurs."""
    User = get_user_model()
    admins = User.objects.filter(
        is_active=True,
    ).filter(role="ADMIN") | User.objects.filter(is_superuser=True, is_active=True)
    admins = admins.distinct()
    created = []
    for admin in admins:
        note = notify_user(admin, title, message, url=url, related_ticket=related_ticket)
        if note:
            created.append(note)
    return created
