"""Backend d'authentification SAVIO.

Permet de se connecter indifféremment avec son **username** ou son **email**.
Utile en particulier pour les comptes créés par import CSV/Excel : le tableau
de compte-rendu de l'import affiche l'email comme « identifiant », donc on
veut que cet email soit accepté tel quel dans le formulaire de connexion.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Authentifie un utilisateur par username **ou** par email.

    On garde l'héritage de ``ModelBackend`` pour bénéficier des contrôles
    par défaut (compte actif, permissions, etc.).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            # Recherche insensible à la casse sur username OU email.
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (cf.
            # ModelBackend).
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Cas pathologique : un username = email d'un autre user. On
            # privilégie alors le match exact sur username.
            user = UserModel.objects.filter(username__iexact=username).first()
            if user is None:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
