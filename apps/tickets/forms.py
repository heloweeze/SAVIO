from django import forms

from apps.clients.models import Client
from apps.technicians.models import Technician

from .models import Comment, PriorityChoices, StatusChoices, Ticket


class TicketForm(forms.ModelForm):
    """Formulaire complet réservé aux admins/techniciens."""

    class Meta:
        model = Ticket
        fields = (
            "client", "subject", "description",
            "status", "priority", "assigned_to", "due_date",
        )
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = Technician.objects.filter(is_active=True)
        self.fields["client"].queryset = Client.objects.filter(is_active=True)
        self.fields["assigned_to"].required = False


class TechnicianTicketUpdateForm(forms.ModelForm):
    """Formulaire de modification réservé aux techniciens.

    Le technicien ne peut faire évoluer que les champs opérationnels
    (statut, priorité, affectation, échéance). Le contenu déposé par le
    client (objet, description) et la fiche client elle-même restent
    intouchables — seul l'admin peut y revenir via ``TicketForm`` complet.
    """

    class Meta:
        model = Ticket
        fields = ("status", "priority", "assigned_to", "due_date")
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = Technician.objects.filter(is_active=True)
        self.fields["assigned_to"].required = False


class UserTicketForm(forms.ModelForm):
    """Formulaire réduit pour les utilisateurs simples.

    Le champ ``client`` est retiré : il est déduit automatiquement du compte
    connecté côté vue (cf. ``apps.tickets.services.get_or_create_client_for_user``).
    """

    class Meta:
        model = Ticket
        fields = ("subject", "description", "priority")
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }


class AssignTechnicianForm(forms.Form):
    technician = forms.ModelChoiceField(
        queryset=Technician.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Technicien",
        required=True,
    )


class ChangeStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Nouveau statut",
    )


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body", "is_internal")
        widgets = {
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Votre message..."}),
            "is_internal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TicketFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Référence, objet..."}))
    status = forms.ChoiceField(required=False,
                               choices=[("", "Tous les statuts")] + list(StatusChoices.choices),
                               widget=forms.Select(attrs={"class": "form-select"}))
    priority = forms.ChoiceField(required=False,
                                 choices=[("", "Toutes les priorités")] + list(PriorityChoices.choices),
                                 widget=forms.Select(attrs={"class": "form-select"}))
    assigned_to = forms.ModelChoiceField(required=False, queryset=Technician.objects.all(),
                                         empty_label="Tous les techniciens",
                                         widget=forms.Select(attrs={"class": "form-select"}))
    client = forms.ModelChoiceField(required=False, queryset=Client.objects.all(),
                                    empty_label="Tous les clients",
                                    widget=forms.Select(attrs={"class": "form-select"}))
