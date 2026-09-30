"""Peuple la base avec des données de démonstration SAVIO.

Modèle : chaque utilisateur final EST un client (1 compte ⇔ 1 fiche Client),
ce qui colle au portail self-service où le client dépose lui-même sa demande.

Crée :
    - un administrateur (admin / admin)
    - 3 techniciens avec comptes dédiés
    - 8 utilisateurs finaux et leurs fiches Client miroir
    - ~25 demandes SAV réparties sur les 30 derniers jours
    - statuts / priorités dans la configuration
    - quelques notifications

Commande :
    python manage.py seed_savio            # création non destructive
    python manage.py seed_savio --reset    # purge + reseed
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.clients.models import Client
from apps.configuration.models import AppSetting, PriorityItem, StatusItem
from apps.history.models import HistoryEntry
from apps.notifications.models import Notification
from apps.technicians.models import Technician
from apps.tickets.models import PriorityChoices, StatusChoices, Ticket


TECHNICIANS_DATA = [
    ("Alice", "Dupont", "alice.dupont@savio.local", "alice", "Électronique"),
    ("Bruno", "Moreau", "bruno.moreau@savio.local", "bruno", "Informatique"),
    ("Claire", "Girard", "claire.girard@savio.local", "claire", "Électroménager"),
]


# Chaque entrée crée à la fois un compte User (rôle USER) et la fiche Client
# miroir correspondante : 1 utilisateur ⇔ 1 client.
# (username, email, first_name, last_name, phone, city)
USERS_DATA = [
    ("user1", "user1@savio.local", "Léa",     "Morel",    "0612345678", "Saint-Denis"),
    ("user2", "user2@savio.local", "Yann",    "Leroy",    "0623456789", "Saint-Pierre"),
    ("user3", "user3@savio.local", "Nora",    "Faure",    "0634567890", "Le Tampon"),
    ("user4", "user4@savio.local", "Marie",   "Durand",   "0645678901", "Saint-Paul"),
    ("user5", "user5@savio.local", "Paul",    "Martin",   "0656789012", "Saint-André"),
    ("user6", "user6@savio.local", "Sophie",  "Bernard",  "0667890123", "Saint-Benoît"),
    ("user7", "user7@savio.local", "Julien",  "Petit",    "0678901234", "Le Port"),
    ("user8", "user8@savio.local", "Camille", "Lefevre",  "0689012345", "Saint-Louis"),
]


TICKET_SAMPLES = [
    ("Écran allumé mais noir", "Le téléviseur s'allume mais affiche un écran noir sans signal."),
    ("Batterie déchargée rapidement", "La batterie de l'ordinateur portable tient moins d'une heure."),
    ("Bruit anormal lave-linge", "Bruit métallique important pendant l'essorage."),
    ("Application qui plante", "L'application de comptabilité se ferme toute seule au démarrage."),
    ("Imprimante hors ligne", "Impossible de se connecter à l'imprimante réseau depuis 2 jours."),
    ("Four qui ne chauffe plus", "Le four ne chauffe plus au-delà de 100°C."),
    ("Connexion Wi-Fi instable", "Le Wi-Fi coupe toutes les 10 minutes."),
    ("Smartphone très lent", "Les applications mettent plus de 10 secondes à s'ouvrir."),
    ("Écran tactile qui saute", "Le tactile ne répond plus par endroits sur la tablette."),
    ("Problème de facturation", "Une ligne ne correspond pas à la commande initiale."),
]


class Command(BaseCommand):
    help = "Peuple la base avec un jeu de données de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Purge préalable des données métier.")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        now = timezone.now()

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Purge des données métier..."))
            HistoryEntry.objects.all().delete()
            Notification.objects.all().delete()
            Ticket.objects.all().delete()
            Technician.objects.all().delete()
            Client.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        # --- Paramètres ----------------------------------------------------
        AppSetting.get_solo()
        self._seed_reference_data()

        # --- Admin ---------------------------------------------------------
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@savio.local",
                "first_name": "Admin",
                "last_name": "SAVIO",
                "role": Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("admin")
        admin.role = Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        admin.ensure_group()

        # --- Techniciens ---------------------------------------------------
        technicians = []
        for first, last, email, username, specialty in TECHNICIANS_DATA:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email, "first_name": first, "last_name": last,
                    "role": Role.TECHNICIAN, "is_staff": True,
                },
            )
            user.role = Role.TECHNICIAN
            user.is_staff = True
            user.set_password(username)
            user.save()
            user.ensure_group()

            tech, _ = Technician.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first, "last_name": last,
                    "phone": "0100000000", "specialty": specialty,
                    "is_active": True, "user": user,
                },
            )
            if tech.user_id is None:
                tech.user = user
                tech.save()
            technicians.append(tech)

        # --- Utilisateurs finaux ------------------------------------------
        # Modèle SAVIO : chaque utilisateur final EST un client. On crée donc
        # à la fois le compte User (rôle USER) et la fiche Client miroir, qui
        # partagent le même email — c'est cette fiche qui sera attachée à
        # toutes les demandes que l'utilisateur dépose.
        users = []
        user_to_client = {}
        for username, email, first, last, phone, city in USERS_DATA:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": first, "last_name": last, "role": Role.USER},
            )
            user.role = Role.USER
            user.set_password(username)
            user.save()
            user.ensure_group()
            users.append(user)

            client_for_user, _ = Client.objects.get_or_create(
                email=email,
                defaults=dict(
                    type=Client.Type.INDIVIDUAL,
                    last_name=last,
                    first_name=first,
                    phone=phone,
                    city=city,
                    country="France",
                    is_active=True,
                    notes=f"Fiche du compte « {username} ».",
                ),
            )
            user_to_client[user.pk] = client_for_user

        # --- Tickets -------------------------------------------------------
        statuses = [s for s, _ in StatusChoices.choices]
        priorities = [p for p, _ in PriorityChoices.choices]

        # Toutes les demandes sont déposées par un utilisateur simple pour
        # son propre compte (= sa fiche Client miroir).
        for i in range(25):
            subject, description = random.choice(TICKET_SAMPLES)
            author = random.choice(users)
            client = user_to_client[author.pk]
            assigned = random.choice(technicians) if random.random() > 0.3 else None
            status = random.choices(
                statuses,
                weights=[15, 15, 25, 10, 15, 10, 10],
                k=1,
            )[0]
            priority = random.choices(priorities, weights=[20, 50, 20, 10], k=1)[0]

            ticket = Ticket(
                subject=f"{subject} #{i+1}",
                description=description,
                client=client,
                author=author,
                assigned_to=assigned,
                status=status,
                priority=priority,
            )
            ticket.save()

            # Date de création répartie sur 30 jours
            created = now - timedelta(days=random.randint(0, 29), hours=random.randint(0, 23))
            Ticket.objects.filter(pk=ticket.pk).update(created_at=created, updated_at=created)

            HistoryEntry.objects.create(
                ticket=ticket, author=author, action=HistoryEntry.Action.CREATE,
                message=f"Demande {ticket.reference} créée (seed).",
            )
            if assigned:
                HistoryEntry.objects.create(
                    ticket=ticket, author=admin, action=HistoryEntry.Action.ASSIGN,
                    message=f"Affectée à {assigned}.",
                )

        # --- Notifications de démo ----------------------------------------
        for user in users[:2]:
            Notification.objects.create(
                recipient=user,
                title="Bienvenue sur SAVIO",
                message="Vos demandes apparaîtront ici.",
            )

        self.stdout.write(self.style.SUCCESS(
            "Seed terminé. Comptes créés :\n"
            "  admin / admin       (administrateur)\n"
            "  alice / alice       (technicien)\n"
            "  bruno / bruno       (technicien)\n"
            "  claire / claire     (technicien)\n"
            "  user1 / user1       (utilisateur — Léa Morel, Saint-Denis)\n"
            "  user2 / user2       (utilisateur — Yann Leroy, Saint-Pierre)\n"
            "  user3 / user3       (utilisateur — Nora Faure, Le Tampon)\n"
            "  user4 / user4       (utilisateur — Marie Durand, Saint-Paul)\n"
            "  user5 / user5       (utilisateur — Paul Martin, Saint-André)\n"
            "  user6 / user6       (utilisateur — Sophie Bernard, Saint-Benoît)\n"
            "  user7 / user7       (utilisateur — Julien Petit, Le Port)\n"
            "  user8 / user8       (utilisateur — Camille Lefevre, Saint-Louis)\n"
        ))

    # -----------------------------------------------------------------
    def _seed_reference_data(self):
        statuses = [
            ("NEW", "Nouveau", "#0d6efd", 1),
            ("OPEN", "Ouvert", "#0dcaf0", 2),
            ("PROG", "En cours", "#ffc107", 3),
            ("PEND", "En attente", "#6c757d", 4),
            ("RESO", "Résolu", "#198754", 5),
            ("CLOS", "Clôturé", "#20c997", 6),
            ("CANC", "Annulé", "#adb5bd", 7),
        ]
        for code, label, color, order in statuses:
            StatusItem.objects.update_or_create(
                code=code,
                defaults={"label": label, "color": color, "order": order, "is_active": True},
            )

        priorities = [
            ("LOW", "Faible", "#198754", 1),
            ("NORM", "Normale", "#0dcaf0", 2),
            ("HIGH", "Haute", "#fd7e14", 3),
            ("URG", "Urgente", "#dc3545", 4),
        ]
        for code, label, color, order in priorities:
            PriorityItem.objects.update_or_create(
                code=code,
                defaults={"label": label, "color": color, "order": order, "is_active": True},
            )
