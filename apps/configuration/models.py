"""Paramétrage applicatif de SAVIO.

Le noyau fonctionnel (statuts / priorités) utilise des TextChoices pour la
robustesse du code métier. Ces modèles reflètent ces valeurs en base pour
offrir à l'administrateur une vue gérable depuis l'interface.
"""
from django.db import models


class AppSetting(models.Model):
    """Singleton contenant les paramètres globaux de SAVIO."""

    site_name = models.CharField("nom de l'application", max_length=100, default="SAVIO")
    site_tagline = models.CharField("slogan", max_length=200, blank=True,
                                    default="Gestion du Service Après-Vente")
    support_email = models.EmailField("email de support", blank=True, default="support@savio.local")

    enable_notifications = models.BooleanField("notifications internes activées", default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "paramètre général"
        verbose_name_plural = "paramètres généraux"

    def __str__(self):
        return self.site_name

    @classmethod
    def get_solo(cls):
        """Retourne l'unique instance (la crée si nécessaire)."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class StatusItem(models.Model):
    """Miroir des statuts de ticket, visible/paramétrable depuis l'UI."""

    code = models.CharField("code", max_length=10, unique=True)
    label = models.CharField("libellé", max_length=80)
    color = models.CharField("couleur", max_length=16, default="#6c757d")
    order = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ("order", "label")
        verbose_name = "statut"
        verbose_name_plural = "statuts"

    def __str__(self):
        return f"{self.label} ({self.code})"


class PriorityItem(models.Model):
    """Miroir des priorités de ticket."""

    code = models.CharField("code", max_length=10, unique=True)
    label = models.CharField("libellé", max_length=80)
    color = models.CharField("couleur", max_length=16, default="#0dcaf0")
    order = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ("order", "label")
        verbose_name = "priorité"
        verbose_name_plural = "priorités"

    def __str__(self):
        return f"{self.label} ({self.code})"
