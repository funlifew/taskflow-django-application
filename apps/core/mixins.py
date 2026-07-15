from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from apps.workspaces.models import Workspace, WorkspaceMembership

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

class WorkspacePermissionMixin(LoginRequiredMixin):
    workspace_url_kwarg = 'pk'
    allowed_roles = []
    
    def get_workspace(self):
        if not hasattr(self, '_workspace'):
            self._workspace = get_object_or_404(
                Workspace.objects.select_related('owner'),
                pk = self.kwargs[self.workspace_url_kwarg],
                is_archived=False,
            )
        
        return self._workspace
    
    def get_membership(self):
        workspace = self.get_workspace()
        
        return WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=self.request.user,
        ).first()
    
    
    def dispatch(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        membership = self.get_membership()
        
        if workspace.owner_id == request.user.id:
            return super().dispatch(request, *args, **kwargs)
        
        if membership is None:
            raise PermissionDenied(
                'شما به این Workspace دسترسی ندارید.'
            )
        
        if (
            self.allowed_roles
            and membership.role not in self.allowed_roles
        ):
            raise PermissionDenied(
                'شما اجازه انجام این عملیات را ندارید.'
            )
        
        return super().dispatch(request, *args, **kwargs)

class WorkspaceAdminRequiredMixin(WorkspacePermissionMixin):
    allowed_roles = [
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN,
    ]

class WorkspaceOwnerRequiredMixin(WorkspacePermissionMixin):
    allowed_roles = [
        WorkspaceMembership.Role.OWNER,
    ]