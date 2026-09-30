from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class StatusChoices(models.TextChoices):
    NEW = "NEW", "Nouveau"
    OPEN = "OPEN", "Ouvert"
    IN_PROGRESS = "PROG", "En cours"
    PENDING = "PEND", "En attente"
    RESOLVED = "RESO", "Résolu"
    CLOSED = "CLOS", "Clôturé"
    CANCELED = "CANC", "Annulé"


class PriorityChoices(models.TextChoices):
    LOW = "LOW", "Faible"
    NORMAL = "NORM", "Normale"
    HIGH = "HIGH", "Haute"
    URGENT = "URG", "Urgente"


CLOSED_STATUSES = {StatusChoices.RESOLVED, StatusChoices.CLOSED, StatusChoices.CANCELED}


def _gen_reference():
    """Génère une référence lisible SAV-YYYYMMDD-XXXX."""
    today = timezone.now().strftime("%Y%m%d")
    last = Ticket.objects.filter(reference__startswith=f"SAV-{today}").order_by("-id").first()
    seq = 1
    if last:
        try:
            seq = int(last.reference.rsplit("-", 1)[-1]) + 1
        except (ValueError, AttributeError):
            seq = 1
    return f"SAV-{today}-{seq:04d}"


class Ticket(models.Model):
    """Demande SAV / Ticket."""

    reference = models.CharField("référence", max_length=30, unique=True, editable=False)
    subject = models.CharField("objet", max_length=200)
    description = models.TextField("description")

    client = models.ForeignKey(
        "clients.Client", on_delete=models.PROTECT, related_name="tickets", verbose_name="client"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tickets_created",
        verbose_name="auteur",
    )
    assigned_to = models.ForeignKey(
        "technicians.Technician",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tickets_assigned",
        verbose_name="technicien assigné",
    )

    status = models.CharField(
        "statut", max_length=4, choices=StatusChoices.choices, default=StatusChoices.NEW
    )
    priority = models.CharField(
        "priorité", max_length=4, choices=PriorityChoices.choices, default=PriorityChoices.NORMAL
    )

    due_date = models.DateField("échéance", null=True, blank=True)
    closed_at = models.DateTimeField("clôturé le", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "demande SAV"
        verbose_name_plural = "demandes SAV"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.subject}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _gen_reference()
        # Mise à jour automatique de closed_at
        if self.status in CLOSED_STATUSES and self.closed_at is None:
            self.closed_at = timezone.now()
        elif self.status not in CLOSED_STATUSES and self.closed_at is not None:
            self.closed_at = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tickets:detail", args=[self.pk])

    # -------- Helpers UI ---------------------------------------------------
    @property
    def is_closed(self) -> bool:
        return self.status in CLOSED_STATUSES

    @property
    def is_high_priority(self) -> bool:
        return self.priority in (PriorityChoices.HIGH, PriorityChoices.URGENT)

    @property
    def status_css(self) -> str:
        mapping = {
            StatusChoices.NEW: "badge-status-new",
            StatusChoices.OPEN: "badge-status-open",
            StatusChoices.IN_PROGRESS: "badge-status-progress",
            StatusChoices.PENDING: "badge-status-pending",
            StatusChoices.RESOLVED: "badge-status-resolved",
            StatusChoices.CLOSED: "badge-status-closed",
            StatusChoices.CANCELED: "badge-status-cancel",
        }
        return mapping.get(self.status, "bg-secondary")

    @property
    def priority_css(self) -> str:
        mapping = {
            PriorityChoices.LOW: "badge-priority-low",
            PriorityChoices.NORMAL: "badge-priority-normal",
            PriorityChoices.HIGH: "badge-priority-high",
            PriorityChoices.URGENT: "badge-priority-urgent",
        }
        return mapping.get(self.priority, "bg-secondary")


class Comment(models.Model):
    """Commentaire attaché à un ticket."""

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="ticket_comments", verbose_name="auteur",
    )
    body = models.TextField("message")
    is_internal = models.BooleanField(
        "note interne", default=False,
        help_text="Non visible par les utilisateurs simples",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"

    def __str__(self):
        return f"Commentaire #{self.pk} sur {self.ticket.reference}"
