from .models import HistoryEntry


def record_action(ticket, author, action, message=""):
    """Enregistre une action d'historique de manière robuste."""
    try:
        return HistoryEntry.objects.create(
            ticket=ticket,
            author=author,
            action=action,
            message=message or "",
        )
    except Exception:  # pragma: no cover
        # Ne jamais casser l'appelant à cause de l'historique
        return None
