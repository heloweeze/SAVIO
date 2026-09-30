from .models import AppSetting


def app_settings(request):
    """Expose le paramètre global dans tous les templates sous `app_settings`."""
    try:
        return {"app_settings": AppSetting.get_solo()}
    except Exception:
        return {"app_settings": None}
