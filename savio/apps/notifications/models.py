from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notification interne à destination d'un utilisateur."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications", verbose_name="destinataire",
    )
    title = models.CharField("titre", max_length=200)
    message = models.TextField("message", blank=True)
    url = models.CharField("lien", max_length=500, blank=True)
    ticket = models.ForeignKey(
        "tickets.Ticket", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="notifications",
    )
    is_read = models.BooleanField("lue", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"[{self.recipient}] {self.title}"
