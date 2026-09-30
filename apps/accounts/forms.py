from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from .models import Role, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Identifiant ou e-mail",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autofocus": True,
                "placeholder": "Identifiant ou e-mail",
            }
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Mot de passe"}),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "address",
            "avatar",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class SavioPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class UserCreateForm(UserCreationForm):
    """Formulaire utilisé par l'admin pour créer un compte (ou self-register)."""

    role = forms.ChoiceField(
        choices=Role.choices,
        initial=Role.USER,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Rôle",
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs.update({"class": "form-control"})
