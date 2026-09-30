from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def sync_role_group(sender, instance: User, created, **kwargs):
    """Assure que l'utilisateur appartient au groupe Django correspondant à son rôle."""
    try:
        instance.ensure_group()
    except Exception:  # pragma: no cover - best effort
        pass
