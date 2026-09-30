"""Tests pour l'app clients."""
from django.test import TestCase

from apps.clients.models import Client


class ClientModelTests(TestCase):
    def test_individual_display_name(self):
        c = Client.objects.create(type=Client.Type.INDIVIDUAL, first_name="Paul", last_name="Martin")
        self.assertEqual(str(c), "Paul Martin")

    def test_company_display_name(self):
        c = Client.objects.create(type=Client.Type.COMPANY, last_name="AlphaSAS", company="Alpha SAS")
        self.assertEqual(str(c), "Alpha SAS")

    def test_get_absolute_url(self):
        c = Client.objects.create(last_name="Martin")
        self.assertIn(str(c.pk), c.get_absolute_url())

    def test_default_country_is_france(self):
        c = Client.objects.create(last_name="Durand")
        self.assertEqual(c.country, "France")
