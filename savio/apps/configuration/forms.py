from django import forms

from .models import AppSetting, PriorityItem, StatusItem


class AppSettingForm(forms.ModelForm):
    class Meta:
        model = AppSetting
        fields = (
            "site_name", "site_tagline", "support_email",
            "enable_notifications",
        )
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-control"}),
            "site_tagline": forms.TextInput(attrs={"class": "form-control"}),
            "support_email": forms.EmailInput(attrs={"class": "form-control"}),
            "enable_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StatusItemForm(forms.ModelForm):
    class Meta:
        model = StatusItem
        fields = ("code", "label", "color", "order", "is_active")
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control form-control-color", "type": "color"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PriorityItemForm(forms.ModelForm):
    class Meta:
        model = PriorityItem
        fields = ("code", "label", "color", "order", "is_active")
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control form-control-color", "type": "color"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
