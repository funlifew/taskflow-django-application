from .selectors import get_unread_notifications

def notifications_context(request):
    if not request.user.is_authenticated:
        return {
            (
                "unread_"
                "notifications_count"
            ): 0,
        }
    
    return {
        (
            'unread_'
            'notifications_count'
        ): (
            get_unread_notifications(
                user=request.user
            )
        ),
    }