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
    allowed_roles = ()

    def get_workspace_queryset(self):
        return (
            Workspace.objects
            .filter(
                is_archived=False,
            )
            .select_related(
                "owner",
            )
        )
    
    def get_workspace(self):
        if not hasattr(
            self,
            "_workspace",
        ):
            self._workspace = (
                get_object_or_404(
                    self.get_workspace_queryset(),
                    pk=self.kwargs[
                        self.workspace_url_kwarg
                    ],
                )
            )

        return self._workspace
    
    def get_membership(self):
        if not hasattr(self, "_membership"):
            workspace = self.get_workspace()

            self._membership = (
                WorkspaceMembership.objects
                .filter(
                    workspace=workspace,
                    user=self.request.user,
                )
                .select_related(
                    'workspace',
                    'user',
                )
                .first()
            )
        
        return self._membership
    
    def get_current_user_role(self):
        workspace = self.get_workspace()

        if workspace.owner_id == self.request.user.id:
            return WorkspaceMembership.Role.OWNER
        
        membership = self.get_membership()

        if membership is None:
            return None
        
        return membership.role
    
    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):
        if not request.user.is_authenticated:
            return super().dispatch(
                request,
                *args,
                **kwargs,
            )
        
        current_user_role = self.get_current_user_role()

        if current_user_role is None:
            raise PermissionDenied(
                "شما به این Workspace دسترسی ندارید."
            )
        
        if (
            self.allowed_roles
            and current_user_role not in self.allowed_roles
        ):
            raise PermissionDenied(
                "شما اجازه انجام این عملیات را ندارید."
            )
        
        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

class WorkspaceAdminRequiredMixin(WorkspacePermissionMixin):
    allowed_roles = (
        WorkspaceMembership.Role.OWNER,
        WorkspaceMembership.Role.ADMIN,
    )

class WorkspaceOwnerRequiredMixin(WorkspacePermissionMixin):
    allowed_roles = (
        WorkspaceMembership.Role.OWNER,
    )