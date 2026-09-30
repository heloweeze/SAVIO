from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, staff_required
from apps.accounts.models import Role

from .forms import TechnicianForm, TechnicianSearchForm
from .models import Technician


def _delete_linked_user(user) -> bool:
    """Supprime le compte ``User`` lié à un technicien.

    Pour éviter tout effet de bord, on ne supprime QUE les comptes de rôle
    ``TECHNICIAN`` (jamais un admin ou un utilisateur simple) et qui ne sont
    pas super-utilisateurs. Retourne ``True`` si un compte a été supprimé.
    """
    if user is None:
        return False
    if user.is_superuser or user.role != Role.TECHNICIAN:
        return False
    user.delete()
    return True


@staff_required
def technician_list(request):
    form = TechnicianSearchForm(request.GET or None)
    qs = Technician.objects.annotate(ticket_count=Count("tickets_assigned"))
    if form.is_valid() and form.cleaned_data.get("q"):
        q = form.cleaned_data["q"]
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(email__icontains=q) | Q(specialty__icontains=q)
        )
    paginator = Paginator(qs, settings.DEFAULT_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "technicians/list.html", {
        "page_obj": page, "technicians": page.object_list, "form": form,
    })


@staff_required
def technician_detail(request, pk):
    tech = get_object_or_404(Technician, pk=pk)
    tickets = tech.tickets_assigned.select_related("client").all()[:20]
    return render(request, "technicians/detail.html", {"technician": tech, "tickets": tickets})


@admin_required
def technician_create(request):
    if request.method == "POST":
        form = TechnicianForm(request.POST)
        if form.is_valid():
            tech = form.save()
            messages.success(request, f"Technicien « {tech} » créé.")
            return redirect(tech.get_absolute_url())
    else:
        form = TechnicianForm()
    return render(request, "technicians/form.html", {"form": form, "is_create": True})


@admin_required
def technician_update(request, pk):
    tech = get_object_or_404(Technician, pk=pk)
    if request.method == "POST":
        form = TechnicianForm(request.POST, instance=tech)
        if form.is_valid():
            form.save()
            messages.success(request, "Technicien mis à jour.")
            return redirect(tech.get_absolute_url())
    else:
        form = TechnicianForm(instance=tech)
    return render(request, "technicians/form.html", {"form": form, "technician": tech})


@admin_required
def technician_delete(request, pk):
    tech = get_object_or_404(Technician, pk=pk)
    if request.method == "POST":
        # Le compte User lié (rôle TECHNICIAN uniquement) est supprimé en
        # même temps pour éviter les comptes orphelins qui bloqueraient un
        # futur import.
        linked_user = tech.user
        tech.delete()
        had_user = _delete_linked_user(linked_user)
        if had_user:
            messages.success(request, "Technicien et compte associé supprimés.")
        else:
            messages.success(request, "Technicien supprimé.")
        return redirect("technicians:list")
    return render(request, "technicians/delete_confirm.html", {"technician": tech})


@admin_required
@require_POST
def technician_bulk_delete(request):
    """Suppression d'un groupe de techniciens sélectionnés depuis la liste.

    Le FK Ticket.assigned_to étant en SET_NULL, les demandes affectées au
    technicien supprimé deviennent simplement « non affectées ».
    """
    raw_ids = request.POST.getlist("ids")
    pks: list[int] = []
    for raw in raw_ids:
        try:
            pks.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not pks:
        messages.warning(request, "Aucun technicien sélectionné.")
        return redirect("technicians:list")

    qs = Technician.objects.filter(pk__in=pks).select_related("user")
    really_deleted = 0
    users_deleted = 0

    for tech in qs:
        linked_user = tech.user
        tech.delete()
        really_deleted += 1
        if _delete_linked_user(linked_user):
            users_deleted += 1

    if really_deleted:
        suffix = (
            f" (dont {users_deleted} compte(s) utilisateur)"
            if users_deleted else ""
        )
        messages.success(
            request,
            f"{really_deleted} technicien(s) supprimé(s){suffix}. "
            "Les demandes qui leur étaient affectées sont désormais non affectées.",
        )
    else:
        messages.info(request, "Aucun technicien correspondant trouvé.")

    return redirect("technicians:list")
