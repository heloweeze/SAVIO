from django.db import models
from django.urls import reverse


class Client(models.Model):
    """Client SAV : personne physique ou morale."""

    class Type(models.TextChoices):
        INDIVIDUAL = "IND", "Particulier"
        COMPANY = "COM", "Entreprise"

    type = models.CharField("type", max_length=3, choices=Type.choices, default=Type.INDIVIDUAL)
    last_name = models.CharField("nom / raison sociale", max_length=120)
    first_name = models.CharField("prénom", max_length=80, blank=True)
    company = models.CharField("société", max_length=150, blank=True)
    email = models.EmailField("email", blank=True)
    phone = models.CharField("téléphone", max_length=30, blank=True)
    address = models.CharField("adresse", max_length=255, blank=True)
    city = models.CharField("ville", max_length=120, blank=True)
    postal_code = models.CharField("code postal", max_length=20, blank=True)
    country = models.CharField("pays", max_length=120, blank=True, default="France")
    notes = models.TextField("notes", blank=True)

    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "client"
        verbose_name_plural = "clients"
        ordering = ("last_name", "first_name")
        indexes = [models.Index(fields=["last_name", "first_name"])]

    def __str__(self):
        if self.type == self.Type.COMPANY and self.company:
            return self.company
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.last_name

    @property
    def display_name(self):
        return str(self)

    def get_absolute_url(self):
        return reverse("clients:detail", args=[self.pk])
