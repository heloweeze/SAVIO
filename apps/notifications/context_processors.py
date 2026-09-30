from .models import Notification


def unread_notifications(request):
    """Injecte le nombre de notifications non lues + les 5 dernières dans le header."""
    if not request.user.is_authenticated:
        return {"unread_count": 0, "latest_notifications": []}
    qs = Notification.objects.filter(recipient=request.user)
    return {
        "unread_count": qs.filter(is_read=False).count(),
        "latest_notifications": list(qs[:5]),
    }
