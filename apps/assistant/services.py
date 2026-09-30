"""Services de l'assistant IA SAVIO — version 100% Python stdlib.

Aucun modèle externe, aucune librairie tierce : tout est implémenté avec des
règles, de la détection de mots-clés et des templates de réponses. C'est
volontairement « léger » (pas de réseau de neurones), mais c'est :

* totalement déterministe et reproductible (utile pour les tests),
* défendable en soutenance (chaque ligne de code est lisible),
* instantané (pas de chargement de modèle, pas de GPU).

Trois fonctions publiques :

* :func:`suggest_diagnostic` — propose un diagnostic + plan d'action à partir
  des mots-clés trouvés dans le ticket.
* :func:`chat` — répond à un utilisateur en détectant son intention parmi
  une dizaine d'intentions courantes (salutations, création de ticket, suivi,
  remerciements, etc.).
* :func:`admin_summary` — produit une synthèse textuelle de l'activité SAV
  à partir des statistiques courantes.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db.models import Count
from django.utils import timezone


# ---------------------------------------------------------------------------
# Résultat standard
# ---------------------------------------------------------------------------
@dataclass
class AssistantResult:
    """Réponse d'une fonction d'assistant.

    Le champ ``ok`` permet aux vues de distinguer une réponse normale d'une
    erreur (assistant désactivé, etc.).
    """

    ok: bool
    text: str

    def to_dict(self) -> Dict[str, object]:
        return {"ok": self.ok, "text": self.text}


def _enabled() -> bool:
    """L'assistant est désactivable via ``ASSISTANT_ENABLED=0`` dans .env."""
    return bool(getattr(settings, "ASSISTANT_ENABLED", True))


# ---------------------------------------------------------------------------
# Helpers de normalisation (insensible à la casse / aux accents)
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    """Minuscule + suppression des accents + suppression des ponctuations.

    Utilisé pour la détection de mots-clés : « problème » et « probleme »
    matchent ainsi tous les deux la même règle.
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]+", " ", ascii_only.lower())


def _has_any(text_norm: str, keywords: List[str]) -> bool:
    """Vrai si l'un des mots-clés apparaît (comme mot entier) dans ``text_norm``."""
    for kw in keywords:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text_norm):
            return True
    return False


# ---------------------------------------------------------------------------
# 1. Diagnostic technique : base de connaissances
# ---------------------------------------------------------------------------
# Chaque catégorie liste des mots-clés déclencheurs + des étapes de résolution
# + 2 à 3 questions complémentaires à poser au client. Plusieurs catégories
# peuvent matcher pour un même ticket : on les concatène.
KNOWLEDGE_BASE: List[Dict[str, object]] = [
    {
        "category": "Problème d'alimentation",
        "keywords": [
            "ne s allume", "ne s allume plus", "allumage", "demarre pas",
            "ne demarre", "alimentation", "alim", "courant", "batterie",
            "chargeur", "charge", "mort", "eteint", "rien",
        ],
        "diagnosis": "Cause probable : panne d'alimentation, batterie HS, "
                     "câble défectueux ou prise murale.",
        "steps": [
            "Vérifier que le câble d'alimentation est bien connecté des deux côtés.",
            "Tester sur une autre prise murale (de préférence sur un autre circuit).",
            "Essayer avec un autre câble / chargeur si possible.",
            "Tester sans la batterie (uniquement secteur) pour isoler la panne.",
            "Mesurer la tension de sortie du chargeur au multimètre si disponible.",
        ],
        "questions": [
            "Y a-t-il une LED qui s'allume au branchement ?",
            "Le problème est-il apparu après une coupure de courant ou un orage ?",
            "Avez-vous essayé un autre chargeur ou une autre prise ?",
        ],
    },
    {
        "category": "Problème d'affichage / écran",
        "keywords": [
            "ecran", "noir", "blanc", "bleu", "rouge", "affichage", "image",
            "pixel", "ligne", "rayure", "tache", "luminosite", "retroeclairage",
            "scintille", "clignote", "vacille", "fissure", "casse",
        ],
        "diagnosis": "Cause probable : nappe d'écran, rétroéclairage, "
                     "carte graphique ou dommage physique sur la dalle.",
        "steps": [
            "Brancher un écran externe pour isoler le défaut (interne vs carte).",
            "Tester l'écran avec une lampe rasante (rétroéclairage actif ?).",
            "Vérifier la nappe écran (ouverture si garantie expirée).",
            "Mettre à jour les pilotes graphiques (côté logiciel).",
            "Tester en mode sans échec / safe mode.",
        ],
        "questions": [
            "L'écran est-il totalement noir ou affiche-t-il quelque chose ?",
            "Le problème survient-il à l'allumage ou après un certain temps ?",
            "L'appareil a-t-il subi un choc ou une chute récemment ?",
        ],
    },
    {
        "category": "Lenteur / performances",
        "keywords": [
            "lent", "lenteur", "rame", "freeze", "fige", "bloque",
            "ralenti", "performances", "performance", "saccade", "lag",
        ],
        "diagnosis": "Cause probable : disque saturé, surchauffe, "
                     "logiciel malveillant, ou matériel obsolète pour l'usage.",
        "steps": [
            "Vérifier l'espace disque libre (laisser au moins 15 %).",
            "Examiner les processus en arrière-plan (CPU/RAM dans le gestionnaire).",
            "Nettoyer les fichiers temporaires et le cache.",
            "Lancer un antivirus / antimalware à jour.",
            "Vérifier les températures CPU/GPU (surchauffe = throttling).",
        ],
        "questions": [
            "À quel moment précis l'appareil ralentit-il ?",
            "Depuis quand le ralentissement est-il apparu ?",
            "Avez-vous installé un nouveau logiciel récemment ?",
        ],
    },
    {
        "category": "Problème de connectivité réseau",
        "keywords": [
            "wifi", "wi fi", "internet", "reseau", "connexion", "connecte",
            "deconnecte", "ethernet", "cable rj45", "bluetooth", "appairage",
            "ping", "dns", "ip",
        ],
        "diagnosis": "Cause probable : pilote réseau, configuration "
                     "défectueuse, panne FAI, ou interférences (wifi).",
        "steps": [
            "Redémarrer la box / le routeur (30 secondes hors tension).",
            "Tester en filaire si possible pour isoler le wifi.",
            "Réinitialiser la pile réseau (netsh winsock reset / ipconfig /release).",
            "Mettre à jour les pilotes de la carte réseau.",
            "Vérifier les paramètres DNS (essayer 8.8.8.8 ou 1.1.1.1).",
        ],
        "questions": [
            "D'autres appareils sont-ils affectés sur le même réseau ?",
            "Le problème est-il permanent ou intermittent ?",
            "À quelle distance êtes-vous du routeur ?",
        ],
    },
    {
        "category": "Surchauffe / bruit",
        "keywords": [
            "chaud", "chauffe", "surchauffe", "bruit", "bruyant", "ventilateur",
            "ventilo", "souffle", "siffle", "claque", "rotation",
        ],
        "diagnosis": "Cause probable : poussière dans les ventilateurs, pâte "
                     "thermique sèche, ou ventilateur défectueux.",
        "steps": [
            "Dépoussiérer les grilles d'aération (bombe à air sec).",
            "Vérifier la rotation des ventilateurs (visuellement / au son).",
            "Surveiller les températures (HWMonitor, lm-sensors).",
            "Remplacer la pâte thermique si appareil > 3-4 ans.",
            "Repositionner l'appareil sur une surface dure et ventilée.",
        ],
        "questions": [
            "À quel moment la surchauffe / le bruit survient-il ?",
            "L'appareil s'arrête-t-il tout seul à cause de la chaleur ?",
            "Quand a-t-il été dépoussiéré pour la dernière fois ?",
        ],
    },
    {
        "category": "Erreur logicielle / écran bleu",
        "keywords": [
            "ecran bleu", "bsod", "kernel panic", "plantage", "plante",
            "crash", "erreur", "bug", "fenetre erreur", "code erreur",
            "redemarre", "reboot",
        ],
        "diagnosis": "Cause probable : pilote défectueux, mise à jour ratée, "
                     "RAM défectueuse, ou conflit logiciel.",
        "steps": [
            "Noter le code d'erreur exact si affiché (utile pour le diagnostic).",
            "Démarrer en mode sans échec et tester la stabilité.",
            "Lancer un test mémoire (MemTest86, Windows Memory Diagnostic).",
            "Vérifier les dernières mises à jour Windows / pilotes installées.",
            "Restaurer un point système antérieur si possible.",
        ],
        "questions": [
            "Le code d'erreur exact est-il visible (ex. 0x0000007E) ?",
            "Le problème est-il survenu après une mise à jour ?",
            "Plante-t-il toujours dans la même application ?",
        ],
    },
    {
        "category": "Périphérique non reconnu",
        "keywords": [
            "usb", "souris", "clavier", "imprimante", "scanner", "webcam",
            "casque", "ecouteurs", "micro", "carte sd", "disque externe",
            "non reconnu", "ne fonctionne pas",
        ],
        "diagnosis": "Cause probable : port USB défectueux, pilote absent, "
                     "câble HS, ou conflit d'attribution de lettre/ID.",
        "steps": [
            "Tester le périphérique sur un autre port USB.",
            "Tester le périphérique sur un autre poste.",
            "Mettre à jour ou réinstaller les pilotes du périphérique.",
            "Vérifier dans le Gestionnaire de périphériques l'absence de point d'exclamation.",
            "Tester avec un autre câble si applicable.",
        ],
        "questions": [
            "Le périphérique est-il neuf ou utilisé depuis longtemps ?",
            "Avez-vous testé sur un autre poste ?",
            "Un message d'erreur s'affiche-t-il à la connexion ?",
        ],
    },
]


# ---------------------------------------------------------------------------
# 1. Diagnostic technicien
# ---------------------------------------------------------------------------
def suggest_diagnostic(ticket) -> AssistantResult:
    """Construit un diagnostic + plan d'action pour un ticket.

    Méthode :
      1. Concatène sujet + description + commentaires non internes.
      2. Normalise le texte (sans accent, minuscule).
      3. Cherche les catégories de la KB qui matchent (≥ 1 mot-clé).
      4. Compose la réponse à partir des sections (diagnosis / steps / questions).
      5. Si rien ne matche : message générique avec des étapes universelles.
    """
    if not _enabled():
        return AssistantResult(ok=False, text="Assistant IA désactivé.")

    # Concatène tout le texte du ticket pour la détection de mots-clés.
    pieces = [ticket.subject or "", ticket.description or ""]
    for c in ticket.comments.all()[:20]:
        if not c.is_internal:
            pieces.append(c.body or "")
    full_text = "\n".join(pieces)
    text_norm = _normalize(full_text)

    matched: List[Dict[str, object]] = []
    for entry in KNOWLEDGE_BASE:
        if _has_any(text_norm, entry["keywords"]):  # type: ignore[arg-type]
            matched.append(entry)

    lines: List[str] = []
    lines.append(f"🤖 Diagnostic SAVIO — ticket {ticket.reference}")
    lines.append(f"Sujet : {ticket.subject}")
    lines.append(f"Statut : {ticket.get_status_display()} · "
                 f"Priorité : {ticket.get_priority_display()}")
    lines.append("")

    if matched:
        lines.append(f"🔎 Catégories détectées : "
                     f"{', '.join(m['category'] for m in matched)}")
        lines.append("")
        for entry in matched:
            lines.append(f"━━ {entry['category']} ━━")
            lines.append(f"{entry['diagnosis']}")
            lines.append("")
            lines.append("Étapes de résolution suggérées :")
            for i, step in enumerate(entry["steps"], start=1):  # type: ignore[arg-type]
                lines.append(f"  {i}. {step}")
            lines.append("")
            lines.append("Questions à poser au client :")
            for q in entry["questions"]:  # type: ignore[union-attr]
                lines.append(f"  • {q}")
            lines.append("")
    else:
        lines.append("Aucun motif technique précis n'a été détecté "
                     "automatiquement dans la description.")
        lines.append("")
        lines.append("Étapes génériques recommandées :")
        lines.append("  1. Demander au client une description précise du symptôme "
                     "(quand ? à quelle fréquence ? message d'erreur exact ?).")
        lines.append("  2. Reproduire le problème en présence du client si possible.")
        lines.append("  3. Vérifier l'environnement (alimentation, câblage, mises à jour).")
        lines.append("  4. Documenter chaque test effectué dans les commentaires du ticket.")
        lines.append("")
        lines.append("Questions à poser au client :")
        lines.append("  • Pouvez-vous nous décrire précisément ce que vous observez ?")
        lines.append("  • Depuis quand le problème est-il apparu ?")
        lines.append("  • Avez-vous changé quelque chose récemment "
                     "(mise à jour, déplacement, etc.) ?")
        lines.append("")

    # Note finale en fonction de la priorité.
    if ticket.is_high_priority:
        lines.append("⚠️ Priorité haute — pensez à recontacter le client "
                     "dans la journée pour confirmer la prise en charge.")
    elif ticket.is_closed:
        lines.append("✔ Ticket clôturé — ces suggestions sont à titre indicatif "
                     "(retour d'expérience pour des cas similaires).")
    else:
        lines.append("ℹ Suggestion générée automatiquement par l'assistant — "
                     "à valider par le technicien avant action.")

    return AssistantResult(ok=True, text="\n".join(lines))


# ---------------------------------------------------------------------------
# 2. Chat utilisateur — détection d'intentions
# ---------------------------------------------------------------------------
# Liste d'intentions ordonnées par priorité de matching (la 1ʳᵉ qui matche gagne).
INTENTS: List[Dict[str, object]] = [
    {
        "name": "salutation",
        "keywords": ["bonjour", "salut", "hello", "coucou", "bonsoir", "hey"],
        "responses": [
            "Bonjour {name} 👋 ! Je suis l'assistant SAVIO. Comment puis-je vous "
            "aider aujourd'hui ?",
        ],
    },
    {
        "name": "remerciement",
        "keywords": ["merci", "thanks", "thx", "remerci"],
        "responses": [
            "De rien {name} ! Si vous avez d'autres questions, je reste à votre "
            "écoute.",
        ],
    },
    {
        "name": "au_revoir",
        "keywords": ["au revoir", "bye", "ciao", "a bientot", "a plus", "adieu"],
        "responses": [
            "À bientôt {name}. Un technicien restera en charge de vos demandes "
            "ouvertes — n'hésitez pas à revenir en cas de besoin.",
        ],
    },
    {
        "name": "creer_ticket",
        "keywords": [
            "nouvelle demande", "creer ticket", "creer une demande", "ouvrir ticket",
            "soumettre", "ouvrir une demande", "deposer", "signaler",
        ],
        "responses": [
            "Pour créer une nouvelle demande, cliquez sur « Nouvelle demande » "
            "dans le menu de gauche, puis remplissez le formulaire. Décrivez "
            "précisément :\n"
            "• le problème observé,\n"
            "• depuis quand il survient,\n"
            "• ce que vous avez déjà tenté.\n\n"
            "Plus la description est précise, plus le technicien sera efficace.",
        ],
    },
    {
        "name": "statut_ticket",
        "keywords": [
            "statut", "avancement", "etat", "suivi", "ou en est",
            "ou en sont", "progression",
        ],
        "responses": [
            "Vous pouvez suivre vos demandes en cliquant sur « Mes demandes » "
            "dans le menu de gauche. Chaque ticket affiche son statut "
            "(Nouveau, En cours, En attente, Résolu...) et la liste des "
            "actions menées par le technicien.\n\n"
            "Si vous voulez le statut d'une référence précise (ex. SAV-20260120-0042), "
            "indiquez-la-moi.",
        ],
    },
    {
        "name": "delai",
        "keywords": [
            "delai", "combien temps", "combien de temps", "quand", "rapidement",
            "urgent", "vite",
        ],
        "responses": [
            "Les délais dépendent de la priorité de la demande :\n"
            "• Urgente : prise en charge sous 4 heures ouvrées.\n"
            "• Haute : sous 24 heures ouvrées.\n"
            "• Normale : sous 3 jours ouvrés.\n"
            "• Faible : sous 1 semaine.\n\n"
            "Vous pouvez préciser le caractère urgent au moment de la création "
            "du ticket.",
        ],
    },
    {
        "name": "mot_de_passe",
        "keywords": [
            "mot de passe", "password", "perdu", "oublie", "changer mdp",
            "reset", "reinitialiser",
        ],
        "responses": [
            "Pour changer votre mot de passe :\n"
            "1. Cliquez sur « Mot de passe » dans le menu (rubrique Compte).\n"
            "2. Saisissez votre mot de passe actuel.\n"
            "3. Saisissez deux fois le nouveau (8 caractères minimum).\n\n"
            "Si vous l'avez totalement perdu, contactez votre administrateur "
            "SAVIO qui pourra le réinitialiser.",
        ],
    },
    {
        "name": "contact",
        "keywords": [
            "contact", "joindre", "telephone", "appeler", "email", "mail",
            "agent", "humain", "technicien",
        ],
        "responses": [
            "Pour contacter un technicien humain, le mieux est de créer un "
            "ticket via « Nouvelle demande ». Vous pouvez aussi joindre le "
            "support à l'adresse indiquée dans la configuration de votre "
            "application. Je suis un assistant automatique : pour les cas "
            "complexes, le ticket reste la meilleure option.",
        ],
    },
    {
        "name": "aide",
        "keywords": ["aide", "help", "comment", "que faire", "perdu"],
        "responses": [
            "Je peux vous aider à :\n"
            "• créer une nouvelle demande SAV,\n"
            "• suivre vos demandes existantes,\n"
            "• comprendre les délais de prise en charge,\n"
            "• vous expliquer comment changer votre mot de passe.\n\n"
            "Posez-moi votre question en quelques mots !",
        ],
    },
    {
        "name": "qui",
        "keywords": ["qui es tu", "qui es-tu", "que es tu", "qui est tu",
                     "tu es qui", "comment t appelle", "ton nom"],
        "responses": [
            "Je suis l'assistant virtuel de SAVIO. Je tourne entièrement en "
            "local sur ce serveur (aucune donnée n'est envoyée à l'extérieur) "
            "et je fonctionne par détection de mots-clés. Je ne suis pas une "
            "vraie IA générative : pour les questions complexes, créez un "
            "ticket et un technicien humain prendra le relais.",
        ],
    },
]

# Regex de référence ticket : SAV-YYYYMMDD-XXXX
TICKET_REF_RE = re.compile(r"\bSAV-(\d{8})-(\d{4})\b", re.IGNORECASE)


def _try_ticket_lookup(message: str, user) -> Optional[str]:
    """Si l'utilisateur cite une référence SAV-... dans son message, on lui
    répond directement avec le statut du ticket (si on a le droit de le voir).
    """
    m = TICKET_REF_RE.search(message)
    if not m:
        return None

    from apps.tickets.models import Ticket  # import paresseux

    ref = m.group(0).upper()
    try:
        t = Ticket.objects.get(reference=ref)
    except Ticket.DoesNotExist:
        return f"Désolé, je ne trouve aucun ticket avec la référence {ref}."

    # On respecte la visibilité : un USER simple ne voit que ses tickets.
    if user is not None and getattr(user, "is_plain_user", False):
        if t.author_id != user.id:
            return (f"Désolé, vous n'avez pas accès au ticket {ref} "
                    f"(il appartient à un autre utilisateur).")

    return (
        f"Voici l'état du ticket {ref} :\n"
        f"• Sujet : {t.subject}\n"
        f"• Statut : {t.get_status_display()}\n"
        f"• Priorité : {t.get_priority_display()}\n"
        f"• Technicien assigné : {t.assigned_to or 'non assigné'}\n"
        f"• Créé le : {timezone.localtime(t.created_at).strftime('%d/%m/%Y à %H:%M')}"
        + (f"\n• Clôturé le : "
           f"{timezone.localtime(t.closed_at).strftime('%d/%m/%Y à %H:%M')}"
           if t.closed_at else "")
    )


def _detect_intent(message_norm: str) -> Optional[Dict[str, object]]:
    """Renvoie la 1ʳᵉ intention dont au moins un mot-clé matche."""
    for intent in INTENTS:
        if _has_any(message_norm, intent["keywords"]):  # type: ignore[arg-type]
            return intent
    return None


def chat(message: str,
         history: Optional[List[Dict[str, str]]] = None,
         user=None) -> AssistantResult:
    """Réponse à un message du chat utilisateur.

    Pipeline :
      1. Si une référence SAV-... est citée, on cherche le ticket en base.
      2. Sinon, on détecte l'intention dans une liste fermée.
      3. Si aucune intention ne matche, on tombe sur une réponse de repli
         qui invite à reformuler ou à créer un ticket.

    L'historique n'est pas utilisé pour générer la réponse (modèle sans
    mémoire), mais la vue le maintient en session pour afficher le fil.
    """
    if not _enabled():
        return AssistantResult(ok=False, text="Assistant IA désactivé.")

    message = (message or "").strip()
    if not message:
        return AssistantResult(ok=False, text="Message vide.")

    # 1. Référence de ticket explicite ?
    ticket_answer = _try_ticket_lookup(message, user)
    if ticket_answer:
        return AssistantResult(ok=True, text=ticket_answer)

    # 2. Intention détectée ?
    message_norm = _normalize(message)
    intent = _detect_intent(message_norm)
    name = ""
    if user is not None and getattr(user, "is_authenticated", False):
        name = user.first_name or user.get_full_name() or user.username

    if intent:
        # On prend la 1ʳᵉ réponse (variantes possibles dans le futur).
        response = intent["responses"][0].format(name=name).strip()  # type: ignore[index]
        return AssistantResult(ok=True, text=response)

    # 3. Repli — réponse générique.
    return AssistantResult(
        ok=True,
        text=(
            "Je ne suis pas sûr d'avoir compris votre demande. Voici ce que je "
            "sais faire :\n"
            "• Créer une nouvelle demande SAV (« comment créer un ticket »)\n"
            "• Suivre une demande (« où en est ma demande SAV-... »)\n"
            "• Expliquer les délais (« combien de temps »)\n"
            "• Vous aider à changer votre mot de passe\n\n"
            "Reformulez votre question avec ces mots-clés, ou créez un ticket "
            "pour qu'un technicien humain vous réponde."
        ),
    )


# ---------------------------------------------------------------------------
# 3. Résumé d'activité pour l'admin
# ---------------------------------------------------------------------------
def _collect_admin_stats() -> Dict[str, object]:
    """Récupère les KPI à analyser pour le résumé."""
    from apps.tickets.models import CLOSED_STATUSES, PriorityChoices, Ticket
    from apps.technicians.models import Technician

    now = timezone.now()
    qs = Ticket.objects.all()
    closed_values = [s.value for s in CLOSED_STATUSES]

    total = qs.count()
    closed = qs.filter(status__in=closed_values).count()
    open_ = total - closed
    last_30 = qs.filter(created_at__gte=now - timezone.timedelta(days=30)).count()
    last_7 = qs.filter(created_at__gte=now - timezone.timedelta(days=7)).count()
    urgent = qs.filter(
        priority__in=[PriorityChoices.HIGH, PriorityChoices.URGENT],
    ).exclude(status__in=closed_values).count()
    unassigned = qs.exclude(status__in=closed_values).filter(assigned_to__isnull=True).count()

    top_techs = list(
        Technician.objects.annotate(n=Count("tickets_assigned"))
        .filter(n__gt=0).order_by("-n")[:5]
        .values("first_name", "last_name", "n")
    )
    return {
        "total": total,
        "open": open_,
        "closed": closed,
        "last_30": last_30,
        "last_7": last_7,
        "urgent": urgent,
        "unassigned": unassigned,
        "top_techs": top_techs,
    }


def admin_summary() -> AssistantResult:
    """Produit un résumé textuel de l'activité SAV.

    Le résumé est généré par templates : on ne fait pas de génération
    libre, on choisit les phrases en fonction des seuils sur les KPI.
    Cela garantit que les chiffres sont toujours corrects (jamais inventés).
    """
    if not _enabled():
        return AssistantResult(ok=False, text="Assistant IA désactivé.")

    s = _collect_admin_stats()

    # Calculs dérivés
    total = s["total"] or 0
    closed = s["closed"] or 0
    closure_rate = (closed / total * 100) if total else 0.0

    lines: List[str] = []
    lines.append("🤖 Synthèse SAVIO — " +
                 timezone.localtime().strftime("%d/%m/%Y %H:%M"))
    lines.append("")

    # --- Activité ---
    lines.append("📊 Activité")
    lines.append(f"• {total} demande{'s' if total > 1 else ''} au total — "
                 f"{closed} clôturée{'s' if closed > 1 else ''} ({closure_rate:.0f} %).")
    lines.append(f"• {s['last_30']} demandes créées sur 30 jours, "
                 f"dont {s['last_7']} sur les 7 derniers jours.")
    if s["last_7"] and s["last_30"]:
        rate_week = s["last_7"] / 7
        rate_month = s["last_30"] / 30
        if rate_week > rate_month * 1.3:
            lines.append("  ↗ La cadence d'arrivée des tickets s'accélère "
                         "(semaine > moyenne mensuelle).")
        elif rate_week < rate_month * 0.7:
            lines.append("  ↘ La cadence ralentit nettement sur la dernière semaine.")
        else:
            lines.append("  → Cadence stable par rapport au mois écoulé.")
    lines.append("")

    # --- Points de vigilance ---
    lines.append("⚠ Points de vigilance")
    vigilance: List[str] = []
    if s["urgent"]:
        vigilance.append(
            f"{s['urgent']} ticket{'s' if s['urgent'] > 1 else ''} "
            f"haute / urgente priorité encore ouvert"
            f"{'s' if s['urgent'] > 1 else ''} — à traiter en priorité."
        )
    if s["unassigned"]:
        vigilance.append(
            f"{s['unassigned']} ticket{'s' if s['unassigned'] > 1 else ''} "
            f"ouvert{'s' if s['unassigned'] > 1 else ''} "
            f"sans technicien assigné — à dispatcher."
        )
    if closure_rate < 50 and total > 10:
        vigilance.append(
            f"Le taux de clôture est faible ({closure_rate:.0f} %) — "
            f"vérifier si certains tickets sont coincés en attente."
        )
    if not vigilance:
        vigilance.append("Aucun point critique détecté à ce stade.")
    for v in vigilance:
        lines.append(f"• {v}")
    lines.append("")

    # --- Recommandations ---
    lines.append("💡 Recommandations")
    recos: List[str] = []
    if s["urgent"]:
        recos.append("Affecter ou réaffecter en priorité les tickets urgents "
                     "et planifier un rappel client dans la journée.")
    if s["unassigned"]:
        recos.append("Répartir les tickets non assignés sur les techniciens "
                     "disponibles (voir le top des affectations ci-dessous).")
    if closure_rate < 70 and total >= 20:
        recos.append("Faire un point hebdomadaire pour traiter les tickets "
                     "en attente depuis longtemps.")
    if not recos:
        recos.append("Maintenir le rythme actuel — l'activité est bien tenue.")
    for r in recos:
        lines.append(f"• {r}")
    lines.append("")

    # --- Top techniciens ---
    if s["top_techs"]:
        lines.append("👷 Top techniciens (tickets affectés)")
        for t in s["top_techs"]:
            lines.append(f"• {t['first_name']} {t['last_name']} : {t['n']} ticket(s)")
        lines.append("")

    lines.append("ℹ Synthèse générée automatiquement à partir des données "
                 "SAVIO en base — aucune donnée n'a été envoyée à l'extérieur.")
    return AssistantResult(ok=True, text="\n".join(lines))


# ---------------------------------------------------------------------------
# Statut public (pour la page admin)
# ---------------------------------------------------------------------------
def get_status() -> Dict[str, object]:
    """État lisible de l'assistant — pour la page admin_panel."""
    return {
        "enabled": _enabled(),
        "engine": "Python stdlib (règles + détection de mots-clés)",
        "knowledge_base_size": len(KNOWLEDGE_BASE),
        "intents": len(INTENTS),
    }
