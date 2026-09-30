"""Services métier pour les demandes SAV."""
from apps.clients.models import Client


def sync_client_from_user(user) -> Client | None:
    """Synchronise la fiche Client miroir d'un User (match sur email).

    Met à jour les nom / prénom / téléphone / adresse du Client à partir du
    profil utilisateur. Crée la fiche si elle n'existe pas encore.
    Retourne ``None`` si :
      - le compte n'est pas un utilisateur simple (admin / technicien) — il
        ne doit pas apparaître dans la liste des clients ;
      - le compte n'a pas d'email (impossible de relier).
    """
    # Seuls les utilisateurs simples ont une fiche Client miroir : un admin
    # ou un technicien qui met à jour son profil ne doit pas se retrouver
    # dans la liste des clients.
    if not getattr(user, "is_plain_user", False):
        return None

    email = (user.email or "").strip()
    if not email:
        return None

    last_name = user.last_name or user.username or "Utilisateur"
    first_name = user.first_name or ""
    phone = getattr(user, "phone", "") or ""
    address = getattr(user, "address", "") or ""

    client = Client.objects.filter(email__iexact=email).first()
    if client is None:
        client = Client.objects.create(
            type=Client.Type.INDIVIDUAL,
            last_name=last_name,
            first_name=first_name,
            email=email,
            phone=phone,
            address=address,
            is_active=True,
            notes=f"Fiche miroir du compte « {user.username} ».",
        )
    else:
        client.last_name = last_name
        client.first_name = first_name
        client.phone = phone or client.phone
        client.address = address or client.address
        client.save(update_fields=["last_name", "first_name", "phone", "address", "updated_at"])
    return client


def get_or_create_client_for_user(user) -> Client:
    """Retourne le Client associé à un User, ou le crée à partir de l'email.

    Logique :
      1. Match sur l'email (insensible à la casse) si disponible.
      2. Sinon, création d'un nouveau Client de type "Particulier"
         avec le nom / prénom / email du compte.

    Garantit qu'une demande SAV déposée par un utilisateur simple est
    toujours rattachée à un Client cohérent, sans que l'utilisateur
    n'ait à choisir dans une liste.
    """
    email = (user.email or "").strip()
    if email:
        existing = Client.objects.filter(email__iexact=email).first()
        if existing:
            return existing

    last_name = user.last_name or user.username or "Utilisateur"
    first_name = user.first_name or ""

    client = Client.objects.create(
        type=Client.Type.INDIVIDUAL,
        last_name=last_name,
        first_name=first_name,
        email=email,
        is_active=True,
        notes=f"Fiche créée automatiquement pour le compte « {user.username} ».",
    )
    return client
