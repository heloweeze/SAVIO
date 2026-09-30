from django import forms

from .models import Technician


class TechnicianForm(forms.ModelForm):
    class Meta:
        model = Technician
        fields = ("user", "first_name", "last_name", "email", "phone", "specialty", "is_active")
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "specialty": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TechnicianSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rechercher..."}))
