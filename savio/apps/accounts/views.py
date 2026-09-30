from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import LoginForm, ProfileForm, SavioPasswordChangeForm


class SavioLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class SavioLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            # On répercute les changements sur la fiche Client miroir
            # (utilisateur simple) ou Technician (technicien) afin que les
            # demandes SAV et les listes affichent le nom à jour. Imports
            # locaux pour éviter une dépendance circulaire au chargement.
            from apps.tickets.services import sync_client_from_user
            from apps.technicians.services import sync_technician_from_user
            sync_client_from_user(user)
            sync_technician_from_user(user)
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def password_change(request):
    if request.method == "POST":
        form = SavioPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Votre mot de passe a été modifié.")
            return redirect("accounts:profile")
    else:
        form = SavioPasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})
