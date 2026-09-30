from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    request = context.get("request")
    if not request or not request.user.is_authenticated:
        return 0
    from apps.notifications.models import Notification
    return Notification.objects.filter(recipient=request.user, is_read=False).count()
