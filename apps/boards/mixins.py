from django.shortcuts import get_object_or_404

from apps.core.mixins import WorkspacePermissionMixin
from apps.workspaces.models import WorkspaceMembership

from .models import Board


BOARD_WRITE_ROLES = (
    WorkspaceMembership.Role.OWNER,
    WorkspaceMembership.Role.ADMIN,
    WorkspaceMembership.Role.MEMBER,
)

BOARD_DELETE_ROLES = (
    WorkspaceMembership.Role.OWNER,
    WorkspaceMembership.Role.ADMIN,
)


class WorkspaceBoardPermissionMixin(
    WorkspacePermissionMixin
):
    workspace_url_kwarg = 'workspace_pk'
    
    def get_current_user_role(self):
        workspace = self.get_workspace()
        
        if (
            workspace.owner_id
            == self.request.user.id
        ):
            return WorkspaceMembership.Role.OWNER
        
        membership = self.get_membership()
        
        if membership is None:
            return None
        
        return membership.role

class BoardReadRequiredMixin(
    WorkspaceBoardPermissionMixin
):
    allowed_roles = []

class BoardWriteRequiredMixin(
    WorkspaceBoardPermissionMixin
):
    allowed_roles = BOARD_WRITE_ROLES

class BoardDeleteRequiredMixin(
    WorkspaceBoardPermissionMixin
):
    allowed_roles = BOARD_DELETE_ROLES


class BoardObjectMixin:
    board_url_kwarg = 'board_pk'
    pk_url_kwarg = 'board_pk'
    
    include_archived_boards = False
    
    def get_board_queryset(self):
        queryset = (
            Board.objects.filter(
                workspace=self.get_workspace(),
            )
            .select_related(
                'workspace',
                'workspace__owner',
                'created_by',
            )
        )
        
        if not self.include_archived_boards:
            queryset = queryset.filter(
                is_archived=False,
            )
        
        return queryset
    
    def get_queryset(self):
        return self.get_board_queryset()
    
    def get_board(self):
        if not hasattr(self, '_board'):
            self._board = get_object_or_404(
                self.get_board_queryset(),
                pk=self.kwargs[self.board_url_kwarg],
            )
        
        return self._board


class ArchiveBoardObjectMixin(
    BoardObjectMixin
):
    include_archived_boards = True
    
    def get_board_queryset(self):
        return (
            super().get_board_queryset()
            .filter(
                is_archived=True,
            )
        )