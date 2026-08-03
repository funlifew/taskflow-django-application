from .models import Notification

def get_user_notifications(
    *,
    user,
):
    return (
        Notification.objects
        .for_recipient(user)
        .select_related(
            'recipient',
            'actor',
        )
        .order_by(
            '-created_at',
            '-pk',
        )
    )
    

def get_unread_notifications(
    *,
    user,
):
    return (
        get_user_notifications(user=user)
        .unread()
    )

def get_unread_notifications_count(
    *,
    user,
):
    return (
        Notification.objects
        .for_recipient(user)
        .unread()
        .count()
    )

def get_recent_notifications(
    *,
    user,
    limit=10,
):
    
    return (
        get_user_notifications(
            user=user,
        )[:limit]
    )
