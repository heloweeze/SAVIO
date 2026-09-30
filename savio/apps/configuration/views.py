from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import admin_required

from .forms import AppSettingForm, PriorityItemForm, StatusItemForm
from .models import AppSetting, PriorityItem, StatusItem


@admin_required
def configuration_home(request):
    setting = AppSetting.get_solo()
    if request.method == "POST" and request.POST.get("form") == "general":
        form = AppSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "Paramètres généraux mis à jour.")
            return redirect("configuration:home")
    else:
        form = AppSettingForm(instance=setting)

    return render(request, "configuration/home.html", {
        "setting": setting,
        "form": form,
        "statuses": StatusItem.objects.all(),
        "priorities": PriorityItem.objects.all(),
    })


# --- Statuts ---------------------------------------------------------------
@admin_required
def status_create(request):
    if request.method == "POST":
        form = StatusItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Statut créé.")
            return redirect("configuration:home")
    else:
        form = StatusItemForm()
    return render(request, "configuration/status_form.html", {"form": form, "is_create": True})


@admin_required
def status_update(request, pk):
    item = get_object_or_404(StatusItem, pk=pk)
    if request.method == "POST":
        form = StatusItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Statut mis à jour.")
            return redirect("configuration:home")
    else:
        form = StatusItemForm(instance=item)
    return render(request, "configuration/status_form.html", {"form": form, "item": item})


@admin_required
def status_delete(request, pk):
    item = get_object_or_404(StatusItem, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Statut supprimé.")
    return redirect("configuration:home")


# --- Priorités -------------------------------------------------------------
@admin_required
def priority_create(request):
    if request.method == "POST":
        form = PriorityItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Priorité créée.")
            return redirect("configuration:home")
    else:
        form = PriorityItemForm()
    return render(request, "configuration/priority_form.html", {"form": form, "is_create": True})


@admin_required
def priority_update(request, pk):
    item = get_object_or_404(PriorityItem, pk=pk)
    if request.method == "POST":
        form = PriorityItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Priorité mise à jour.")
            return redirect("configuration:home")
    else:
        form = PriorityItemForm(instance=item)
    return render(request, "configuration/priority_form.html", {"form": form, "item": item})


@admin_required
def priority_delete(request, pk):
    item = get_object_or_404(PriorityItem, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Priorité supprimée.")
    return redirect("configuration:home")
