"""Nettoie les fiches Client créées par erreur pour un compte admin/technicien.

Cas typique : avant que ``sync_client_from_user`` ne soit limité aux
utilisateurs simples, sauvegarder le profil d'un technicien créait à tort
une fiche Client miroir. Cette commande supprime ces fiches en se basant
sur la correspondance d'email (insensible à la casse) avec un compte de
rôle ADMIN ou TECHNICIAN.

Commandes :
    python manage.py cleanup_mirror_clients          # affiche ce qui serait supprimé (dry-run)
    python manage.py cleanup_mirror_clients --apply  # supprime réellement
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import Role, User
from apps.clients.models import Client


class Command(BaseCommand):
    help = (
        "Supprime les fiches Client dont l'email correspond à un compte "
        "admin ou technicien (fiches miroir orphelines)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Effectue réellement la suppression. Sans ce flag, simple dry-run.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]

        staff_emails = list(
            User.objects
            .filter(role__in=[Role.ADMIN, Role.TECHNICIAN])
            .exclude(email="")
            .values_list("email", flat=True)
        )

        if not staff_emails:
            self.stdout.write(self.style.WARNING(
                "Aucun compte admin/technicien avec email — rien à nettoyer."
            ))
            return

        # Match insensible à la casse via un OR de Q(email__iexact=...).
        q = Q()
        for email in staff_emails:
            q |= Q(email__iexact=email)
        candidates = Client.objects.filter(q).distinct()

        count = candidates.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                "Aucune fiche Client miroir à supprimer."
            ))
            return

        self.stdout.write(
            f"{count} fiche(s) Client correspondent à un compte admin/technicien :"
        )
        for client in candidates.order_by("last_name", "first_name"):
            self.stdout.write(f"  - {client} <{client.email}> (id={client.pk})")

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "\nDry-run : aucune suppression effectuée. "
                "Relance avec --apply pour supprimer."
            ))
            return

        deleted, _ = candidates.delete()
        self.stdout.write(self.style.SUCCESS(
            f"\n{deleted} fiche(s) Client supprimée(s)."
        ))
