from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, staff_required
from apps.history.services import record_action
from apps.notifications.services import notify_admins, notify_user

from .forms import (
    AssignTechnicianForm,
    ChangeStatusForm,
    CommentForm,
    TechnicianTicketUpdateForm,
    TicketFilterForm,
    TicketForm,
    UserTicketForm,
)
from .models import CLOSED_STATUSES, StatusChoices, Ticket
from .services import get_or_create_client_for_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_locked_for_technician(user, ticket: Ticket) -> bool:
    """Vrai si le ticket est clôturé et que l'utilisateur n'a pas les
    droits admin pour le rouvrir / le re-modifier.

    Un technicien ne peut plus toucher (ni au formulaire complet, ni aux
    actions latérales statut/affectation) à un ticket dans
    ``CLOSED_STATUSES``. Seul un admin peut le rouvrir.
    """
    is_admin_level = user.is_admin_role or user.is_superuser
    return ticket.status in CLOSED_STATUSES and not is_admin_level


def _can_view_ticket(user, ticket: Ticket) -> bool:
    if user.is_superuser or user.is_admin_role or user.is_technician_role:
        return True
    # Un utilisateur simple voit un ticket si :
    #   - il en est l'auteur, OU
    #   - le client du ticket correspond à son adresse e-mail
    if ticket.author_id == user.id:
        return True
    user_email = (user.email or "").strip().lower()
    client_email = (ticket.client.email or "").strip().lower() if ticket.client_id else ""
    return bool(user_email) and user_email == client_email


def _apply_filters(qs, form: TicketFilterForm):
    if not form.is_valid():
        return qs
    data = form.cleaned_data
    if data.get("q"):
        q = data["q"]
        qs = qs.filter(Q(reference__icontains=q) | Q(subject__icontains=q) | Q(description__icontains=q))
    for field in ("status", "priority"):
        if data.get(field):
            qs = qs.filter(**{field: data[field]})
    if data.get("assigned_to"):
        qs = qs.filter(assigned_to=data["assigned_to"])
    if data.get("client"):
        qs = qs.filter(client=data["client"])
    return qs


# ---------------------------------------------------------------------------
# Liste - admin / tech
# ---------------------------------------------------------------------------
@staff_required
def ticket_list(request):
    form = TicketFilterForm(request.GET or None)
    qs = Ticket.objects.select_related("client", "assigned_to", "author").all()
    qs = _apply_filters(qs, form)
    paginator = Paginator(qs, settings.DEFAULT_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "tickets/list.html", {
        "page_obj": page, "tickets": page.object_list, "form": form,
    })


# ---------------------------------------------------------------------------
# Liste - utilisateur : mes demandes
# ---------------------------------------------------------------------------
@login_required
def my_tickets(request):
    user = request.user
    user_email = (user.email or "").strip()
    visibility = Q(author=user)
    if user_email:
        visibility |= Q(client__email__iexact=user_email)
    qs = (
        Ticket.objects.select_related("client", "assigned_to")
        .filter(visibility)
        .distinct()
    )
    form = TicketFilterForm(request.GET or None)
    # Pour les utilisateurs, on masque les filtres avancés mais on garde q/status
    qs = _apply_filters(qs, form)
    paginator = Paginator(qs, settings.DEFAULT_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "tickets/my_list.html", {
        "page_obj": page, "tickets": page.object_list, "form": form,
    })


# ---------------------------------------------------------------------------
# Détail
# ---------------------------------------------------------------------------
@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("client", "assigned_to", "author"), pk=pk
    )
    if not _can_view_ticket(request.user, ticket):
        raise PermissionDenied("Vous n'avez pas accès à cette demande.")

    # Commentaires - masquer les notes internes aux utilisateurs simples
    comments = ticket.comments.select_related("author").all()
    if request.user.is_plain_user:
        comments = comments.filter(is_internal=False)

    history = ticket.history_entries.select_related("author").all()[:50]

    comment_form = CommentForm()
    assign_form = AssignTechnicianForm()
    status_form = ChangeStatusForm(initial={"status": ticket.status})

    return render(request, "tickets/detail.html", {
        "ticket": ticket,
        "comments": comments,
        "history": history,
        "comment_form": comment_form,
        "assign_form": assign_form,
        "status_form": status_form,
        # Verrou « ticket clôturé » pour les techniciens : on cache les actions
        # (Modifier / Statut / Affecter). L'admin garde le contrôle.
        "ticket_locked_for_tech": _is_locked_for_technician(request.user, ticket),
    })


# ---------------------------------------------------------------------------
# Création (admin/technicien OU utilisateur simple)
# ---------------------------------------------------------------------------
@login_required
def ticket_create(request):
    is_staff_level = request.user.is_admin_role or request.user.is_technician_role or request.user.is_superuser
    FormClass = TicketForm if is_staff_level else UserTicketForm

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.author = request.user
            # Utilisateur simple : le client est dérivé du compte connecté.
            if not is_staff_level:
                ticket.client = get_or_create_client_for_user(request.user)
            ticket.save()
            record_action(ticket, request.user, "CREATE", "Création de la demande")
            notify_admins(
                f"Nouvelle demande {ticket.reference}",
                f"« {ticket.subject} » créée par {request.user.get_full_name() or request.user.username}",
                related_ticket=ticket,
            )
            messages.success(request, f"Demande {ticket.reference} créée.")
            return redirect(ticket.get_absolute_url())
    else:
        form = FormClass()
    return render(request, "tickets/form.html", {
        "form": form, "is_create": True, "is_staff_level": is_staff_level,
    })


# ---------------------------------------------------------------------------
# Modification (staff uniquement)
# ---------------------------------------------------------------------------
@staff_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # Un technicien ne peut plus modifier un ticket clôturé : il doit passer
    # par l'admin pour qu'il soit rouvert au préalable.
    if _is_locked_for_technician(request.user, ticket):
        messages.warning(
            request,
            "Cette demande est clôturée. Demandez à l'administrateur de la rouvrir avant de la modifier.",
        )
        return redirect(ticket.get_absolute_url())
    # L'admin garde le formulaire complet (peut tout modifier, y compris
    # l'objet, la description et le client). Le technicien n'a accès qu'aux
    # champs opérationnels.
    is_admin_level = request.user.is_admin_role or request.user.is_superuser
    FormClass = TicketForm if is_admin_level else TechnicianTicketUpdateForm

    previous = {
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": ticket.priority,
        "assigned_to_id": ticket.assigned_to_id,
    }
    if request.method == "POST":
        form = FormClass(request.POST, instance=ticket)
        if form.is_valid():
            updated = form.save()
            changes = []
            if previous["status"] != updated.status:
                changes.append(f"statut → {updated.get_status_display()}")
            if previous["priority"] != updated.priority:
                changes.append(f"priorité → {updated.get_priority_display()}")
            if previous["assigned_to_id"] != updated.assigned_to_id:
                changes.append(f"technicien → {updated.assigned_to or 'aucun'}")
            if previous["subject"] != updated.subject:
                changes.append("objet modifié")
            record_action(
                updated, request.user, "UPDATE",
                "Modification : " + (", ".join(changes) if changes else "détails mis à jour"),
            )
            messages.success(request, "Demande mise à jour.")
            return redirect(updated.get_absolute_url())
    else:
        form = FormClass(instance=ticket)
    return render(request, "tickets/form.html", {
        "form": form, "ticket": ticket, "is_staff_level": True,
        "is_admin_level": is_admin_level,
    })


# ---------------------------------------------------------------------------
# Suppression (admin uniquement)
# ---------------------------------------------------------------------------
@admin_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == "POST":
        ref = ticket.reference
        ticket.delete()
        messages.success(request, f"Demande {ref} supprimée.")
        return redirect("tickets:list")
    return render(request, "tickets/delete_confirm.html", {"ticket": ticket})


# ---------------------------------------------------------------------------
# Actions ponctuelles
# ---------------------------------------------------------------------------
@require_POST
@staff_required
def ticket_assign(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if _is_locked_for_technician(request.user, ticket):
        messages.warning(request, "Demande clôturée — affectation impossible sans réouverture par l'admin.")
        return redirect(ticket.get_absolute_url())
    form = AssignTechnicianForm(request.POST)
    if form.is_valid():
        tech = form.cleaned_data["technician"]
        ticket.assigned_to = tech
        if ticket.status == StatusChoices.NEW:
            ticket.status = StatusChoices.OPEN
        ticket.save()
        record_action(ticket, request.user, "ASSIGN", f"Affectation à {tech}")
        if tech.user_id:
            notify_user(tech.user, f"Demande {ticket.reference} affectée",
                        f"Vous avez été affecté·e à « {ticket.subject} »", related_ticket=ticket)
        messages.success(request, "Technicien affecté.")
    else:
        messages.error(request, "Sélection invalide.")
    return redirect(ticket.get_absolute_url())


@require_POST
@staff_required
def ticket_change_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if _is_locked_for_technician(request.user, ticket):
        messages.warning(request, "Demande clôturée — changement de statut réservé à l'admin.")
        return redirect(ticket.get_absolute_url())
    form = ChangeStatusForm(request.POST)
    if form.is_valid():
        new_status = form.cleaned_data["status"]
        if new_status != ticket.status:
            old_display = ticket.get_status_display()
            ticket.status = new_status
            ticket.save()
            record_action(
                ticket, request.user, "STATUS",
                f"Statut : {old_display} → {ticket.get_status_display()}",
            )
            if ticket.author_id:
                notify_user(
                    ticket.author, f"Mise à jour de {ticket.reference}",
                    f"Nouveau statut : {ticket.get_status_display()}",
                    related_ticket=ticket,
                )
            messages.success(request, "Statut mis à jour.")
    return redirect(ticket.get_absolute_url())


@require_POST
@staff_required
def ticket_close(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if ticket.status != StatusChoices.CLOSED:
        ticket.status = StatusChoices.CLOSED
        ticket.closed_at = timezone.now()
        ticket.save()
        record_action(ticket, request.user, "CLOSE", "Clôture de la demande")
        if ticket.author_id:
            notify_user(ticket.author, f"Demande {ticket.reference} clôturée",
                        "Votre demande a été clôturée.", related_ticket=ticket)
        messages.success(request, "Demande clôturée.")
    return redirect(ticket.get_absolute_url())


@require_POST
@login_required
def ticket_comment(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not _can_view_ticket(request.user, ticket):
        raise PermissionDenied
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        # Les utilisateurs simples ne peuvent jamais créer une note interne
        if request.user.is_plain_user:
            comment.is_internal = False
        comment.save()
        record_action(ticket, request.user, "COMMENT", "Nouveau commentaire ajouté")
        # Notifier les bonnes personnes
        if request.user.id != ticket.author_id and ticket.author_id and not comment.is_internal:
            notify_user(ticket.author, f"Nouveau commentaire sur {ticket.reference}",
                        comment.body[:140], related_ticket=ticket)
        if ticket.assigned_to and ticket.assigned_to.user_id and ticket.assigned_to.user_id != request.user.id:
            notify_user(ticket.assigned_to.user, f"Nouveau commentaire sur {ticket.reference}",
                        comment.body[:140], related_ticket=ticket)
        messages.success(request, "Commentaire publié.")
    else:
        messages.error(request, "Commentaire invalide.")
    return redirect(ticket.get_absolute_url())
