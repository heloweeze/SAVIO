"""Tests unitaires pour l'app accounts."""
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User


class UserModelTests(TestCase):
    def test_role_properties(self):
        u = User.objects.create_user(username="alice", email="a@a.fr", password="x", role=Role.TECHNICIAN)
        self.assertTrue(u.is_technician_role)
        self.assertFalse(u.is_admin_role)
        self.assertFalse(u.is_plain_user)

    def test_admin_role_via_superuser(self):
        u = User.objects.create_superuser(username="root", email="r@r.fr", password="x")
        self.assertTrue(u.is_admin_role)

    def test_ensure_group_syncs_django_group(self):
        u = User.objects.create_user(username="bob", email="b@b.fr", password="x", role=Role.USER)
        u.ensure_group()
        self.assertTrue(Group.objects.filter(name="Utilisateurs").exists())
        self.assertTrue(u.groups.filter(name="Utilisateurs").exists())


class AuthFlowTests(TestCase):
    def test_login_page_reachable(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertIn(response.status_code, (200, 302))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/", response.url)
