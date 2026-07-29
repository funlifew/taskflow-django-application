from django.db.models import (
    Case,
    CharField,
    Count,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.utils import timezone

from .models import (
    WorkspaceInvitation,
    WorkspaceMembership,
)

def get_workspace_list_queryset(
    *,
    queryset,
    user,
    search_query="",
    selected_role="",
):
    search_query = search_query.strip()
    selected_role = selected_role.strip()
    
    membership_role = (
        WorkspaceMembership.objects
        .filter(
            workspace=OuterRef('pk'),
            user=user,
        )
        .values('role')[:1]
    )
    
    queryset = (
        queryset
        .select_related('owner')
        .annotate(
            members_count=Count(
                'memberships',
                distinct=True,
            ),
            current_user_role=Case(
                When(
                    owner=user,
                    then=Value(
                        WorkspaceMembership.Role.OWNER
                    ),
                ),
                default=Subquery(
                    membership_role
                ),
                output_field=CharField(),
            ),
        )
        .order_by('-updated_at')
    )
    
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(owner__username__icontains=search_query)
            | Q(owner__first_name__icontains=search_query)
            | Q(owner__last_name__icontains=search_query)
        )
    
    if selected_role in WorkspaceMembership.Role.values:
        queryset = queryset.filter(
            current_user_role=selected_role,
        )
    
    return queryset.distinct()


def get_workspace_list_summary(
    *,
    queryset,
    user,
):
    return {
        'total_workspaces': queryset.count(),
        'owned_workspaces_count': queryset.filter(owner=user).count(),
        'joined_workspaces_count': queryset.exclude(owner=user).count(),
    }

def get_pending_invitations_for_user(
    *,
    user,
):
    return (
        WorkspaceInvitation.objects
        .filter(
            email__iexact=user.email,
            status=WorkspaceInvitation.Status.PENDING,
            expires_at__gt=timezone.now(),
            workspace__is_archived=False,
        )
        .select_related(
            'workspace',
            'invited_by',
        )
        .order_by(
            '-created_at',
        )
    )

def get_active_workspace_boards(
    *,
    workspace,
):
    return (
        workspace.boards
        .filter(
            is_archived=False,
        )
        .select_related(
            'created_by',
        )
        .order_by(
            '-updated_at',
            '-pk',
        )
    )

def get_workspace_memberships(
    *,
    workspace,
):
    return (
        workspace.memberships
        .select_related(
            'user',
            'workspace',
        )
        .order_by(
            'role',
            'created_at',
        )
    )

def get_pending_workspace_invitations(
    *,
    workspace,
):
    return (
        workspace.invitations
        .filter(
            status=WorkspaceInvitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        )
        .select_related(
            'invited_by',
            'workspace',
        )
        .order_by(
            '-created_at',
        )
    )

def get_manageable_workspace_memberships(
    *,
    workspace,
    requester_role,
):
    queryset = (
        WorkspaceMembership.objects
        .filter(
            workspace=workspace,
        )
        .exclude(
            role=WorkspaceMembership.Role.OWNER,
        )
        .select_related(
            'user',
            'workspace',
        )
    )
    
    if requester_role == WorkspaceMembership.Role.ADMIN:
        queryset = queryset.exclude(
            role=WorkspaceMembership.Role.ADMIN,
        )
    
    return queryset