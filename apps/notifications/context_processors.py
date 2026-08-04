from .selectors import (
    get_recent_notifications,
    get_unread_notifications_count,
)


HEADER_NOTIFICATIONS_LIMIT = 6

def notifications_context(request):
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'header_notifications': (),
        }
    
    header_notifications = list(
        get_recent_notifications(
            user=request.user,
            limit=HEADER_NOTIFICATIONS_LIMIT,
        )
    )
    
    return {
        'unread_notifications_count': (
            get_unread_notifications_count(
                user=request.user,
            )
        ),
        'header_notifications': (
            header_notifications
        ),
    }