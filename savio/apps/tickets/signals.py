from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.history.services import record_action

from .models import Ticket


@receiver(post_delete, sender=Ticket)
def log_ticket_delete(sender, instance: Ticket, **kwargs):
    """Conserve une trace minimale lors de la suppression d'un ticket."""
    # instance.pk est encore disponible, mais plus la FK → on log sans ticket lié
    try:
        record_action(
            None, None, "DELETE",
            f"Suppression du ticket {instance.reference} — {instance.subject}",
        )
    except Exception:  # pragma: no cover
        pass
