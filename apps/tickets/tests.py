"""Tests pour l'app tickets (demandes SAV)."""
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.clients.models import Client
from apps.technicians.models import Technician
from apps.tickets.models import CLOSED_STATUSES, PriorityChoices, StatusChoices, Ticket


class TicketModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_obj = Client.objects.create(last_name="Martin", first_name="Paul", email="p@p.fr")
        cls.user = User.objects.create_user(username="u", email="u@u.fr", password="x", role=Role.USER)
        cls.tech_user = User.objects.create_user(username="t", email="t@t.fr", password="x", role=Role.TECHNICIAN)
        cls.tech = Technician.objects.create(first_name="Alice", last_name="Dupont", email="a.dupont@savio.local")

    def test_reference_is_generated(self):
        t = Ticket.objects.create(
            subject="Ecran noir", description="...", client=self.client_obj, author=self.user,
        )
        self.assertTrue(t.reference.startswith("SAV-"))
        self.assertGreaterEqual(len(t.reference), len("SAV-20240101-0001"))

    def test_references_are_unique_and_sequential(self):
        t1 = Ticket.objects.create(subject="A", description="a", client=self.client_obj, author=self.user)
        t2 = Ticket.objects.create(subject="B", description="b", client=self.client_obj, author=self.user)
        self.assertNotEqual(t1.reference, t2.reference)
        seq1 = int(t1.reference.rsplit("-", 1)[-1])
        seq2 = int(t2.reference.rsplit("-", 1)[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_closed_at_set_when_status_closed(self):
        t = Ticket.objects.create(subject="X", description=".", client=self.client_obj, author=self.user)
        self.assertIsNone(t.closed_at)
        t.status = StatusChoices.CLOSED
        t.save()
        self.assertIsNotNone(t.closed_at)
        self.assertIn(t.status, CLOSED_STATUSES)

    def test_closed_at_reset_when_reopened(self):
        t = Ticket.objects.create(
            subject="X", description=".", client=self.client_obj, author=self.user,
            status=StatusChoices.CLOSED,
        )
        self.assertIsNotNone(t.closed_at)
        t.status = StatusChoices.OPEN
        t.save()
        self.assertIsNone(t.closed_at)

    def test_priority_helpers(self):
        t = Ticket.objects.create(
            subject="X", description=".", client=self.client_obj, author=self.user,
            priority=PriorityChoices.URGENT,
        )
        self.assertTrue(t.is_high_priority)
        self.assertIn("priority-urgent", t.priority_css)
