"""Décorateurs et mixins pour le contrôle d'accès basé sur les rôles."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """Autorise uniquement les utilisateurs avec rôle ADMIN (ou superuser)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or getattr(user, "is_admin_role", False)):
            raise PermissionDenied("Réservé aux administrateurs.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def staff_required(view_func):
    """Admin OU Technicien (pour certaines opérations sur les tickets)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not (
            user.is_superuser
            or getattr(user, "is_admin_role", False)
            or getattr(user, "is_technician_role", False)
        ):
            raise PermissionDenied("Réservé au personnel.")
        return view_func(request, *args, **kwargs)

    return _wrapped


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        u = self.request.user
        return bool(u and (u.is_superuser or getattr(u, "is_admin_role", False)))


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        u = self.request.user
        return bool(
            u
            and (
                u.is_superuser
                or getattr(u, "is_admin_role", False)
                or getattr(u, "is_technician_role", False)
            )
        )
