"""Modèle utilisateur personnalisé pour SAVIO.

On utilise un User custom dès le départ (bonne pratique Django) afin de
pouvoir étendre les informations de profil et la notion de rôle sans
migration douloureuse ultérieure.
"""
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    ADMIN = "ADMIN", _("Administrateur")
    TECHNICIAN = "TECH", _("Technicien")
    USER = "USER", _("Utilisateur")


class User(AbstractUser):
    """Utilisateur de SAVIO avec un champ de rôle explicite."""

    email = models.EmailField(_("email"), unique=True)
    role = models.CharField(
        _("rôle"), max_length=10, choices=Role.choices, default=Role.USER
    )
    phone = models.CharField(_("téléphone"), max_length=30, blank=True)
    avatar = models.ImageField(
        _("avatar"), upload_to="avatars/", blank=True, null=True
    )
    job_title = models.CharField(_("fonction"), max_length=120, blank=True)
    address = models.CharField(_("adresse"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("utilisateur")
        verbose_name_plural = _("utilisateurs")
        ordering = ("last_name", "first_name")

    def __str__(self):  # pragma: no cover
        return self.get_full_name() or self.username

    # -- Helpers rôle -------------------------------------------------------
    @property
    def is_admin_role(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_technician_role(self) -> bool:
        return self.role == Role.TECHNICIAN

    @property
    def is_plain_user(self) -> bool:
        return self.role == Role.USER and not self.is_superuser

    def ensure_group(self) -> None:
        """Synchronise les groupes Django avec le rôle."""
        mapping = {
            Role.ADMIN: "Administrateurs",
            Role.TECHNICIAN: "Techniciens",
            Role.USER: "Utilisateurs",
        }
        target = mapping.get(self.role)
        if not target:
            return
        group, _created = Group.objects.get_or_create(name=target)
        # On garde les autres groupes éventuels mais on assure l'appartenance
        self.groups.add(group)
