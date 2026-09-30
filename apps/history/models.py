from django.conf import settings
from django.db import models


class HistoryEntry(models.Model):
    """Trace d'action. Attachée optionnellement à un ticket."""

    class Action(models.TextChoices):
        CREATE = "CREATE", "Création"
        UPDATE = "UPDATE", "Modification"
        STATUS = "STATUS", "Changement de statut"
        ASSIGN = "ASSIGN", "Affectation"
        COMMENT = "COMMENT", "Commentaire"
        CLOSE = "CLOSE", "Clôture"
        REOPEN = "REOPEN", "Réouverture"
        DELETE = "DELETE", "Suppression"
        OTHER = "OTHER", "Autre"

    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="history_entries",
        verbose_name="demande",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="history_entries",
        verbose_name="auteur",
    )
    action = models.CharField("action", max_length=10, choices=Action.choices, default=Action.OTHER)
    message = models.TextField("message", blank=True)
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "entrée d'historique"
        verbose_name_plural = "historique"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        return f"[{self.get_action_display()}] {self.message[:60]}"

    @property
    def icon(self) -> str:
        mapping = {
            self.Action.CREATE: "bi-plus-circle text-success",
            self.Action.UPDATE: "bi-pencil text-primary",
            self.Action.STATUS: "bi-arrow-repeat text-warning",
            self.Action.ASSIGN: "bi-person-check text-info",
            self.Action.COMMENT: "bi-chat-left-text text-secondary",
            self.Action.CLOSE: "bi-lock text-success",
            self.Action.REOPEN: "bi-unlock text-warning",
            self.Action.DELETE: "bi-trash text-danger",
            self.Action.OTHER: "bi-circle text-secondary",
        }
        return mapping.get(self.action, "bi-circle")
