from django.shortcuts import redirect
class IfAuthenticatedRedirectDashboard:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:dashboard")
        return super().dispatch(request, *args, **kwargs)