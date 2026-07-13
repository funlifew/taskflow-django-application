from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from apps.workspaces.models import Workspace
class IfAuthenticatedRedirectDashboard:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:dashboard")
        return super().dispatch(request, *args, **kwargs)
    
class AccessibleWorkspaceMixin(LoginRequiredMixin):
    def get_queryset(self):
        return (
            Workspace.objects
            .filter(
                Q(owner=self.request.user)
                | Q(memberships__user=self.request.user)
            )
            .filter(is_archived=False)
            .select_related('owner')
            .distinct()
        )

class OwnerWorkspaceMixin(LoginRequiredMixin):
    def get_queryset(self):
        return Workspace.objects.filter(
            owner=self.request.user,
            is_archived=False,
        )