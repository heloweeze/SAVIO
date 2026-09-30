from django.conf import settings
from django.db import models
from django.urls import reverse


class Technician(models.Model):
    """Technicien SAV. Optionnellement relié à un User pour authentification."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="technician_profile",
        help_text="Compte utilisateur associé (pour login)",
    )
    first_name = models.CharField("prénom", max_length=80)
    last_name = models.CharField("nom", max_length=120)
    email = models.EmailField("email", unique=True)
    phone = models.CharField("téléphone", max_length=30, blank=True)
    specialty = models.CharField("spécialité", max_length=120, blank=True)
    is_active = models.BooleanField("actif", default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "technicien"
        verbose_name_plural = "techniciens"
        ordering = ("last_name", "first_name")

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def full_name(self) -> str:
        return str(self)

    def get_absolute_url(self):
        return reverse("technicians:detail", args=[self.pk])
