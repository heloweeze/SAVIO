from django import forms


class CsvUploadForm(forms.Form):
    """Formulaire d'import (CSV ou Excel)."""

    file = forms.FileField(
        label="Fichier à importer",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": (
                    ".csv,text/csv,"
                    ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            }
        ),
        help_text=(
            "Formats acceptés : .csv (séparateur ';' ou ',', UTF-8 recommandé) "
            "ou .xlsx (Excel)."
        ),
    )
