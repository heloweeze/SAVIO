"""Services métier pour les techniciens."""
from .models import Technician


def sync_technician_from_user(user) -> Technician | None:
    """Synchronise la fiche Technician liée à un User.

    Met à jour les nom / prénom / email / téléphone de la fiche Technician
    à partir du profil utilisateur. Ne crée jamais une nouvelle fiche : si le
    compte n'a pas de fiche associée, retourne ``None``.

    Cas particuliers :
      - utilisateur non-technicien → ``None`` (rien à faire) ;
      - email modifié dans le profil → l'email du Technician est aligné si la
        nouvelle adresse n'est pas déjà utilisée par un autre technicien.
    """
    if not getattr(user, "is_technician_role", False):
        return None

    tech = Technician.objects.filter(user=user).first()
    if tech is None:
        # Match secondaire sur l'email actuel (au cas où user_id n'aurait
        # pas encore été renseigné dans la fiche Technician).
        if user.email:
            tech = Technician.objects.filter(email__iexact=user.email).first()
            if tech is not None:
                tech.user = user
        if tech is None:
            return None

    new_email = (user.email or "").strip()
    update_fields = []

    if user.first_name and tech.first_name != user.first_name:
        tech.first_name = user.first_name
        update_fields.append("first_name")
    if user.last_name and tech.last_name != user.last_name:
        tech.last_name = user.last_name
        update_fields.append("last_name")

    if new_email and new_email.lower() != (tech.email or "").lower():
        already_taken = (
            Technician.objects.filter(email__iexact=new_email)
            .exclude(pk=tech.pk).exists()
        )
        if not already_taken:
            tech.email = new_email
            update_fields.append("email")

    user_phone = getattr(user, "phone", "") or ""
    if user_phone and tech.phone != user_phone:
        tech.phone = user_phone
        update_fields.append("phone")

    if update_fields:
        update_fields.append("updated_at")
        tech.save(update_fields=update_fields)
    elif tech.user_id is None:
        tech.save(update_fields=["user", "updated_at"])

    return tech
