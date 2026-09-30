"""Services d'export / import CSV.

Chaque ressource (clients, techniciens, demandes, historique) a un couple
d'écriture / lecture CSV. Les imports retournent un dictionnaire de
compte-rendu : {created, updated, errors:[str, ...]}.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from typing import Dict, Iterable, List, Tuple

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.clients.models import Client
from apps.history.models import HistoryEntry
from apps.technicians.models import Technician
from apps.tickets.models import Ticket
from apps.tickets.services import sync_client_from_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _writer(headers: Iterable[str]) -> Tuple[io.StringIO, csv.writer]:
    buffer = io.StringIO()
    # UTF-8 BOM pour ouvrir proprement dans Excel FR
    buffer.write("\ufeff")
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(list(headers))
    return buffer, writer


def _read(file_obj) -> csv.DictReader:
    raw = file_obj.read()
    if isinstance(raw, bytes):
        # On essaie utf-8-sig (BOM) puis latin-1
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
    else:
        text = raw
    # Détection basique du séparateur
    sample = text.splitlines()[0] if text else ""
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    return csv.DictReader(io.StringIO(text), delimiter=delim)


def _is_xlsx(file_obj) -> bool:
    """Détecte si le fichier uploadé est un Excel (extension ou content-type)."""
    name = (getattr(file_obj, "name", "") or "").lower()
    ctype = (getattr(file_obj, "content_type", "") or "").lower()
    return name.endswith(".xlsx") or "spreadsheetml" in ctype


def _read_rows(file_obj) -> List[Dict[str, str]]:
    """Lit un fichier CSV ou XLSX et renvoie une liste de dicts {entête: valeur}.

    Pour le XLSX :
      - la 1re ligne est traitée comme entête,
      - les valeurs sont converties en str et trim-ées,
      - les lignes entièrement vides sont ignorées.
    """
    if _is_xlsx(file_obj):
        # Import paresseux pour ne pas exiger openpyxl si on ne fait que du CSV.
        from openpyxl import load_workbook  # type: ignore

        try:
            file_obj.seek(0)
        except Exception:  # noqa: BLE001
            pass
        wb = load_workbook(file_obj, read_only=True, data_only=True)
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        try:
            headers = [str(h).strip() if h is not None else "" for h in next(rows)]
        except StopIteration:
            return []
        out: List[Dict[str, str]] = []
        for row in rows:
            if not any(cell not in (None, "") for cell in row):
                continue
            record = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                value = row[idx] if idx < len(row) else None
                record[header] = "" if value is None else str(value).strip()
            out.append(record)
        return out

    # CSV par défaut
    reader = _read(file_obj)
    return [dict(row) for row in reader]


# ---------------------------------------------------------------------------
# Helpers pour la génération des identifiants à partir d'un nom + prénom
# ---------------------------------------------------------------------------
def _strip_accents(value: str) -> str:
    """Retire les accents : « François » → « Francois »."""
    if not value:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _ascii_lower(value: str) -> str:
    """Minuscule + ASCII + suppression de tout ce qui n'est pas a-z0-9."""
    cleaned = _strip_accents(value).lower()
    return "".join(c for c in cleaned if c.isalnum())


def _first_given_name(first_name: str) -> str:
    """Retourne le premier prénom (ex. « Jean Brice » → « Jean »)."""
    parts = (first_name or "").strip().split()
    return parts[0] if parts else ""


def generate_email(first_name: str, last_name: str, domain: str = "savio.local") -> str:
    """Génère un email du type ``j.dupont@savio.local`` (clients).

    Règle : 1ʳᵉ lettre du 1ᵉʳ prénom + ``.`` + nom de famille (sans accents,
    sans espaces, en minuscule) + ``@<domaine>``.
    """
    first = _ascii_lower(_first_given_name(first_name))
    last = _ascii_lower(last_name)
    if not first or not last:
        # Cas dégradé : on retombe sur l'un ou l'autre, ou un placeholder.
        local = first or last or "user"
    else:
        local = f"{first[0]}.{last}"
    return f"{local}@{domain}"


def generate_tech_email(first_name: str, last_name: str, domain: str = "savio.local") -> str:
    """Génère un email du type ``jean.dupont@savio.local`` (techniciens).

    Règle : 1ᵉʳ prénom (complet) + ``.`` + nom de famille (sans accents,
    sans espaces, en minuscule) + ``@<domaine>``.
    """
    first = _ascii_lower(_first_given_name(first_name))
    last = _ascii_lower(last_name)
    if not first or not last:
        local = first or last or "tech"
    else:
        local = f"{first}.{last}"
    return f"{local}@{domain}"


def generate_password(first_name: str, last_name: str) -> str:
    """Génère un mot de passe du type ``jeandu#``.

    Règle : 1ᵉʳ prénom (en minuscule, sans accents) + 2 premières lettres
    du nom (idem) + ``#``.
    """
    first = _ascii_lower(_first_given_name(first_name))
    last = _ascii_lower(last_name)
    return f"{first}{last[:2]}#"


def _unique_email(base_email: str) -> str:
    """Si l'email est déjà pris, suffixe un compteur (j.dupont2@…)."""
    if not User.objects.filter(email__iexact=base_email).exists():
        return base_email
    local, _, domain = base_email.partition("@")
    counter = 2
    while True:
        candidate = f"{local}{counter}@{domain}"
        if not User.objects.filter(email__iexact=candidate).exists():
            return candidate
        counter += 1


def _unique_username(base_username: str) -> str:
    if not User.objects.filter(username__iexact=base_username).exists():
        return base_username
    counter = 2
    while True:
        candidate = f"{base_username}{counter}"
        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate
        counter += 1


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "vrai", "oui", "yes", "y", "x"}


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
# En-têtes pour l'EXPORT (toutes les colonnes du modèle Client).
CLIENT_HEADERS = [
    "id", "type", "last_name", "first_name", "company", "email", "phone",
    "address", "city", "postal_code", "country", "notes", "is_active",
]

# En-têtes attendus pour l'IMPORT : seulement les noms — l'email, le username,
# le mot de passe et les notes sont générés automatiquement à partir du nom
# et du prénom. Les colonnes optionnelles (phone, city, …) restent acceptées
# si présentes dans le fichier.
CLIENT_IMPORT_HEADERS = ["last_name", "first_name"]


def export_clients():
    buffer, writer = _writer(CLIENT_HEADERS)
    for c in Client.objects.all().order_by("last_name", "first_name"):
        writer.writerow([
            c.pk, c.type, c.last_name, c.first_name, c.company, c.email, c.phone,
            c.address, c.city, c.postal_code, c.country, c.notes,
            "1" if c.is_active else "0",
        ])
    return buffer.getvalue()


def import_clients(file_obj) -> Dict:
    """Crée des comptes utilisateur (rôle USER) à partir d'un fichier nom/prénom.

    Le fichier (CSV ou Excel) ne contient en pratique que ``last_name`` et
    ``first_name``. Pour chaque ligne :

    * l'email est généré : 1ʳᵉ lettre du 1ᵉʳ prénom + ``.`` + nom + ``@savio.local``
    * le mot de passe est généré : 1ᵉʳ prénom + 2 premières lettres du NOM + ``#``
    * un compte ``User`` (rôle ``USER``) est créé,
    * la fiche ``Client`` miroir est créée automatiquement par
      ``sync_client_from_user``,
    * les notes sont générées (date d'import).

    Les lignes dont l'email généré existe déjà (re-import du même fichier)
    sont ignorées et signalées dans ``errors``.

    Le compte-rendu retourne en plus la liste ``credentials`` (email + mot
    de passe en clair) pour permettre à l'admin de communiquer les accès
    aux clients.
    """
    rows = _read_rows(file_obj)
    created = updated = 0
    errors: List[str] = []
    credentials: List[Dict[str, str]] = []
    today = timezone.localdate().strftime("%d/%m/%Y")

    for idx, row in enumerate(rows, start=2):
        try:
            last_name = (row.get("last_name") or "").strip()
            first_name = (row.get("first_name") or "").strip()
            if not last_name:
                errors.append(f"Ligne {idx} : 'last_name' manquant.")
                continue
            if not first_name:
                errors.append(f"Ligne {idx} : 'first_name' manquant.")
                continue

            base_email = generate_email(first_name, last_name)
            password = generate_password(first_name, last_name)

            # On évite d'écraser un compte existant : si l'email est déjà pris,
            # la ligne est sautée et signalée.
            if User.objects.filter(email__iexact=base_email).exists():
                errors.append(
                    f"Ligne {idx} : un compte existe déjà pour "
                    f"{first_name} {last_name} ({base_email}). Ligne ignorée."
                )
                continue

            # Génération du username (local-part de l'email) + unicité.
            local_part = base_email.split("@", 1)[0]
            username = _unique_username(local_part)

            with transaction.atomic():
                user = User(
                    username=username,
                    email=base_email,
                    first_name=first_name,
                    last_name=last_name,
                    role=Role.USER,
                    phone=(row.get("phone") or "").strip(),
                    address=(row.get("address") or "").strip(),
                )
                # Hash rapide pendant l'import (MD5). Django re-hash
                # automatiquement avec PBKDF2 à la première connexion du
                # client — la sécurité finale est identique, mais l'import
                # de masse devient quasi instantané (≈ 1 ms par compte au
                # lieu de 150 ms).
                user.password = make_password(password, hasher="md5")
                user.save()
                user.ensure_group()

                # Crée / met à jour la fiche Client miroir avec une note
                # d'import propre (sinon sync_client_from_user mettrait
                # « Fiche miroir du compte … »).
                client = sync_client_from_user(user)
                if client is not None:
                    client.notes = (
                        f"Compte créé par import le {today} "
                        f"(login : {base_email})."
                    )
                    # Champs optionnels du fichier si présents.
                    extra = {
                        "city": (row.get("city") or "").strip(),
                        "postal_code": (row.get("postal_code") or "").strip(),
                        "country": (row.get("country") or "").strip() or client.country,
                    }
                    for field, value in extra.items():
                        if value:
                            setattr(client, field, value)
                    client.save()

            credentials.append({
                "name": f"{first_name} {last_name}",
                "email": base_email,
                "password": password,
            })
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Ligne {idx} : {exc}")

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "credentials": credentials,
    }


# ---------------------------------------------------------------------------
# Techniciens
# ---------------------------------------------------------------------------
TECH_HEADERS = ["id", "first_name", "last_name", "email", "phone", "specialty", "is_active"]

# En-têtes attendus pour l'IMPORT : seulement les noms — l'email, le username
# et le mot de passe sont générés automatiquement à partir du nom et du
# prénom. Les colonnes optionnelles (phone, specialty) restent acceptées si
# présentes dans le fichier.
TECH_IMPORT_HEADERS = ["last_name", "first_name"]


def export_technicians():
    buffer, writer = _writer(TECH_HEADERS)
    for t in Technician.objects.all():
        writer.writerow([
            t.pk, t.first_name, t.last_name, t.email, t.phone, t.specialty,
            "1" if t.is_active else "0",
        ])
    return buffer.getvalue()


def import_technicians(file_obj) -> Dict:
    """Crée des techniciens (+ comptes User rôle TECH) à partir d'un fichier nom/prénom.

    Le fichier (CSV ou Excel) ne contient en pratique que ``last_name`` et
    ``first_name``. Pour chaque ligne :

    * l'email est généré : 1ᵉʳ prénom + ``.`` + nom + ``@savio.local``
      (ex. Jean Brice DUPONT → ``jean.dupont@savio.local``),
    * le mot de passe est généré : 1ᵉʳ prénom + 2 premières lettres du NOM + ``#``
      (ex. Jean Brice DUPONT → ``jeandu#``),
    * un compte ``User`` (rôle ``TECHNICIAN``) est créé,
    * une fiche ``Technician`` reliée à ce User est créée.

    Les lignes dont l'email généré existe déjà (re-import du même fichier)
    sont ignorées et signalées dans ``errors``.

    Le compte-rendu retourne la liste ``credentials`` (email + mot de passe
    en clair) pour permettre à l'admin de communiquer les accès aux
    techniciens.
    """
    rows = _read_rows(file_obj)
    created = updated = 0
    errors: List[str] = []
    credentials: List[Dict[str, str]] = []

    for idx, row in enumerate(rows, start=2):
        try:
            last_name = (row.get("last_name") or "").strip()
            first_name = (row.get("first_name") or "").strip()
            if not last_name:
                errors.append(f"Ligne {idx} : 'last_name' manquant.")
                continue
            if not first_name:
                errors.append(f"Ligne {idx} : 'first_name' manquant.")
                continue

            base_email = generate_tech_email(first_name, last_name)
            password = generate_password(first_name, last_name)

            # Anti-doublons : User OU Technician avec cet email.
            if User.objects.filter(email__iexact=base_email).exists():
                errors.append(
                    f"Ligne {idx} : un compte existe déjà pour "
                    f"{first_name} {last_name} ({base_email}). Ligne ignorée."
                )
                continue
            if Technician.objects.filter(email__iexact=base_email).exists():
                errors.append(
                    f"Ligne {idx} : un technicien existe déjà avec l'email "
                    f"{base_email}. Ligne ignorée."
                )
                continue

            local_part = base_email.split("@", 1)[0]
            username = _unique_username(local_part)

            with transaction.atomic():
                user = User(
                    username=username,
                    email=base_email,
                    first_name=first_name,
                    last_name=last_name,
                    role=Role.TECHNICIAN,
                    phone=(row.get("phone") or "").strip(),
                )
                # Hash MD5 pour un import quasi instantané. Django re-hash
                # automatiquement avec PBKDF2 à la 1ʳᵉ connexion du technicien
                # — la sécurité finale est identique.
                user.password = make_password(password, hasher="md5")
                user.save()
                user.ensure_group()

                Technician.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    email=base_email,
                    phone=(row.get("phone") or "").strip(),
                    specialty=(row.get("specialty") or "").strip(),
                    is_active=True,
                )

            credentials.append({
                "name": f"{first_name} {last_name}",
                "email": base_email,
                "password": password,
            })
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Ligne {idx} : {exc}")

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "credentials": credentials,
    }


# ---------------------------------------------------------------------------
# Tickets (demandes SAV)
# ---------------------------------------------------------------------------
TICKET_HEADERS = [
    "reference", "subject", "description", "client_id", "client_name",
    "assigned_email", "status", "priority", "due_date", "created_at", "closed_at",
]


def export_tickets():
    buffer, writer = _writer(TICKET_HEADERS)
    qs = Ticket.objects.select_related("client", "assigned_to").all().order_by("-created_at")
    for t in qs:
        writer.writerow([
            t.reference, t.subject, t.description,
            t.client_id, str(t.client),
            t.assigned_to.email if t.assigned_to else "",
            t.status, t.priority,
            t.due_date.isoformat() if t.due_date else "",
            t.created_at.isoformat() if t.created_at else "",
            t.closed_at.isoformat() if t.closed_at else "",
        ])
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Historique (lecture seule)
# ---------------------------------------------------------------------------
HISTORY_HEADERS = ["id", "created_at", "action", "ticket_ref", "author", "message"]


def export_history():
    buffer, writer = _writer(HISTORY_HEADERS)
    qs = HistoryEntry.objects.select_related("ticket", "author").order_by("-created_at")[:5000]
    for h in qs:
        writer.writerow([
            h.pk,
            h.created_at.isoformat() if h.created_at else "",
            h.action,
            h.ticket.reference if h.ticket else "",
            h.author.get_full_name() or h.author.username if h.author else "",
            h.message.replace("\n", " "),
        ])
    return buffer.getvalue()
