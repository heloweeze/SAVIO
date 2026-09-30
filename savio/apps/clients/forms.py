from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = (
            "type", "last_name", "first_name", "company",
            "email", "phone", "address", "postal_code", "city", "country",
            "notes", "is_active",
        )
        widgets = {
            "type": forms.Select(attrs={"class": "form-select"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "company": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        data = super().clean()
        if data.get("type") == Client.Type.COMPANY and not data.get("company"):
            self.add_error("company", "Une entreprise doit avoir un nom de société.")
        return data


class ClientSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rechercher..."}))
    type = forms.ChoiceField(required=False, choices=[("", "Tous les types")] + list(Client.Type.choices),
                             widget=forms.Select(attrs={"class": "form-select"}))
