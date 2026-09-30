"""Vues de l'assistant IA SAVIO.

Trois endpoints AJAX (POST, JSON) :

* ``suggest`` : diagnostic IA pour un ticket (admin / technicien)
* ``chat``    : dialogue libre avec un utilisateur connecté
* ``summary`` : synthèse de l'activité (admin)

Plus deux pages servies en HTML :

* ``chat_page``    : page dédiée au chat (utilisateur)
* ``admin_panel``  : page admin de status + résumé à la demande
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.decorators import admin_required, staff_required
from apps.tickets.models import Ticket

from . import services


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _json_body(request) -> dict:
    """Parse le body JSON d'une requête. Renvoie {} si non-JSON."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}


# ---------------------------------------------------------------------------
# 1. Diagnostic IA pour un ticket (technicien / admin)
# ---------------------------------------------------------------------------
@staff_required
@require_POST
def suggest_diagnostic(request, pk):
    """Retourne un diagnostic IA pour le ticket ``pk``."""
    ticket = get_object_or_404(Ticket, pk=pk)
    result = services.suggest_diagnostic(ticket)
    return JsonResponse(result.to_dict())


# ---------------------------------------------------------------------------
# 2. Chat utilisateur
# ---------------------------------------------------------------------------
CHAT_HISTORY_KEY = "assistant_chat_history"
MAX_HISTORY = 20  # 10 échanges user/assistant


@login_required
@require_GET
def chat_page(request):
    """Page dédiée au chat (rendu HTML)."""
    history = request.session.get(CHAT_HISTORY_KEY, [])
    return render(request, "assistant/chat.html", {"history": history})


@login_required
@require_POST
def chat_send(request):
    """Endpoint AJAX : envoie un message, reçoit la réponse de l'assistant.

    Stocke l'historique en session côté serveur pour garder le fil de la
    conversation entre deux requêtes.
    """
    payload = _json_body(request)
    message = (payload.get("message") or "").strip()
    if not message:
        return HttpResponseBadRequest("message vide")

    history = request.session.get(CHAT_HISTORY_KEY, [])
    result = services.chat(message, history=history, user=request.user)

    if result.ok:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result.text})
        # On garde seulement les N derniers messages.
        request.session[CHAT_HISTORY_KEY] = history[-MAX_HISTORY:]
        request.session.modified = True

    return JsonResponse(result.to_dict())


@login_required
@require_POST
def chat_reset(request):
    """Vide l'historique du chat en session."""
    request.session[CHAT_HISTORY_KEY] = []
    request.session.modified = True
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# 3. Résumé admin
# ---------------------------------------------------------------------------
@admin_required
@require_GET
def admin_panel(request):
    """Page admin avec status du LLM + bouton 'Générer un résumé'."""
    return render(request, "assistant/admin_panel.html", {
        "status": services.get_status(),
    })


@admin_required
@require_POST
def admin_summary(request):
    """Endpoint AJAX : génère un résumé d'activité."""
    result = services.admin_summary()
    return JsonResponse(result.to_dict())
