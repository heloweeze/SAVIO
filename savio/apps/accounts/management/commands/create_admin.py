"""Crée ou met à jour un superutilisateur administrateur SAVIO.

Usage :
    python manage.py create_admin
    python manage.py create_admin --username admin --email admin@savio.local --password admin
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User


class Command(BaseCommand):
    help = "Crée (ou met à jour) un compte administrateur superutilisateur."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@savio.local")
        parser.add_argument("--password", default="admin")
        parser.add_argument("--first-name", default="Admin")
        parser.add_argument("--last-name", default="SAVIO")

    def handle(self, *args, **options):
        username = options["username"]
        defaults = {
            "email": options["email"],
            "first_name": options["first_name"],
            "last_name": options["last_name"],
            "role": Role.ADMIN,
            "is_staff": True,
            "is_superuser": True,
        }
        user, created = User.objects.get_or_create(username=username, defaults=defaults)
        for key, value in defaults.items():
            setattr(user, key, value)
        user.set_password(options["password"])
        user.save()
        user.ensure_group()

        action = "créé" if created else "mis à jour"
        self.stdout.write(self.style.SUCCESS(
            f"Administrateur {action} : {username} / mot de passe : {options['password']}"
        ))
