from .models import Message, Notification


def unread_notifications(request):
    if not request.user.is_authenticated:
        return {
            'navbar_unread_notifications_count': 0,
            'navbar_unread_messages_count': 0,
        }

    return {
        'navbar_unread_notifications_count': Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count(),
        'navbar_unread_messages_count': Message.objects.filter(
            receiver=request.user,
            is_read=False,
        ).count(),
    }
