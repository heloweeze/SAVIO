from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, staff_required
from apps.accounts.models import Role, User

from .forms import ClientForm, ClientSearchForm
from .models import Client


def _delete_linked_user_by_email(email: str | None) -> bool:
    """Supprime le compte ``User`` lié à un client (match sur l'email).

    Le lien Client ↔ User se fait par l'email (cf. ``sync_client_from_user``).
    Pour éviter tout effet de bord, on ne supprime QUE les comptes de rôle
    ``USER`` (jamais un admin ou un technicien) et qui ne sont pas
    super-utilisateurs. Retourne ``True`` si un compte a été supprimé.
    """
    email = (email or "").strip()
    if not email:
        return False
    user = User.objects.filter(
        email__iexact=email,
        role=Role.USER,
        is_superuser=False,
    ).first()
    if user is None:
        return False
    user.delete()
    return True


@staff_required
def client_list(request):
    form = ClientSearchForm(request.GET or None)
    qs = Client.objects.all()
    if form.is_valid():
        q = form.cleaned_data.get("q")
        type_ = form.cleaned_data.get("type")
        if q:
            qs = qs.filter(
                Q(last_name__icontains=q)
                | Q(first_name__icontains=q)
                | Q(company__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
            )
        if type_:
            qs = qs.filter(type=type_)

    paginator = Paginator(qs, settings.DEFAULT_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "clients/list.html", {
        "page_obj": page,
        "clients": page.object_list,
        "form": form,
    })


@staff_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    tickets = client.tickets.select_related("assigned_to").all()[:20]
    return render(request, "clients/detail.html", {"client": client, "tickets": tickets})


@admin_required
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client « {client} » créé.")
            return redirect(client.get_absolute_url())
    else:
        form = ClientForm()
    return render(request, "clients/form.html", {"form": form, "is_create": True})


@admin_required
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client mis à jour.")
            return redirect(client.get_absolute_url())
    else:
        form = ClientForm(instance=client)
    return render(request, "clients/form.html", {"form": form, "client": client})


@admin_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        # Le compte User lié (rôle USER uniquement) est supprimé en même temps
        # pour éviter les comptes orphelins qui bloqueraient un futur import.
        email = client.email
        client.delete()
        had_user = _delete_linked_user_by_email(email)
        if had_user:
            messages.success(request, "Client et compte associé supprimés.")
        else:
            messages.success(request, "Client supprimé.")
        return redirect("clients:list")
    return render(request, "clients/delete_confirm.html", {"client": client})


@admin_required
@require_POST
def client_bulk_delete(request):
    """Suppression d'un groupe de clients sélectionnés depuis la liste.

    Comportement par client :
      - Si le client n'a aucun ticket → suppression immédiate.
      - Sinon (FK Ticket.client = PROTECT) → conservé et signalé.

    Le compte-rendu est restitué via le système de messages Django.
    """
    raw_ids = request.POST.getlist("ids")
    pks: list[int] = []
    for raw in raw_ids:
        try:
            pks.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not pks:
        messages.warning(request, "Aucun client sélectionné.")
        return redirect("clients:list")

    qs = Client.objects.filter(pk__in=pks)
    deleted = 0
    users_deleted = 0
    protected: list[str] = []

    for client in qs:
        label = str(client)
        email = client.email
        try:
            # On tente d'abord la suppression du Client. Si elle réussit
            # (pas de ticket associé), on supprime aussi le compte User
            # rattaché — sinon on conserve l'utilisateur tel quel.
            client.delete()
            deleted += 1
            if _delete_linked_user_by_email(email):
                users_deleted += 1
        except ProtectedError:
            # Au moins un ticket existe → on conserve le client.
            protected.append(label)

    if deleted:
        suffix = (
            f" (dont {users_deleted} compte(s) utilisateur)"
            if users_deleted else ""
        )
        messages.success(
            request,
            f"{deleted} client(s) supprimé(s){suffix}.",
        )
    if protected:
        sample = ", ".join(protected[:5])
        more = f" (+ {len(protected) - 5} autres)" if len(protected) > 5 else ""
        messages.warning(
            request,
            f"{len(protected)} client(s) non supprimé(s) car ils ont des "
            f"demandes SAV associées : {sample}{more}.",
        )
    if not deleted and not protected:
        messages.info(request, "Aucun client correspondant trouvé.")

    return redirect("clients:list")
