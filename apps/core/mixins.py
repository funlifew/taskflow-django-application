from django.shortcuts import redirect
class IfAuthenticatedRedirectDashboard:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("landing")
        return super().dispatch(request, *args, **kwargs)