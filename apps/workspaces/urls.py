from django.urls import path
from . import views

app_name = 'workspaces'

urlpatterns = [
    path(
        "",
        views.WorkspaceListView.as_view(),
        name='list',
    ),
    path(
        'create/',
        views.WorkspaceCreateView.as_view(),
        name='create',
    ),
    path(
        '<int:pk>/',
        views.WorkspaceDetailView.as_view(),
        name='detail',
    ),
    path(
        '<int:pk>/update/',
        views.WorkspaceUpdateView.as_view(),
        name="update",
    ),
    path(
        '<int:pk>/delete/',
        views.WorkspaceDeleteView.as_view(),
        name='delete',
    ),
    
    
    path(
        "<int:pk>/members/",
        views.WorkspaceMemberListView.as_view(),
        name='members',
    ),
    path(
        '<int:pk>/members/invite/',
        views.WorkspaceInvitationCreateView.as_view(),
        name='member_invite',
    ),
    path(
        '<int:pk>/members/<int:membership_pk>/update/',
        views.WorkspaceMembershipUpdateView.as_view(),
        name='member_update',
    ),
    path(
        '<int:pk>/members/<int:membership_pk>/remove/',
        views.WorkspaceMembershipDeleteView.as_view(),
        name='member_remove',
    ),
    path(
        'invitations/<uuid:token>/',
        views.WorkspaceInvitationDetailView.as_view(),
        name='invitation_detail',
    ),
    path(
        'invitations/<uuid:token>/accept/',
        views.WorkspaceInvitationAcceptView.as_view(),
        name='invitation_accept',
    ),
    path(
        'invitations/<uuid:token>/decline/',
        views.WorkspaceInvitationDeclineView.as_view(),
        name="invitation_decline",
    ),
]
