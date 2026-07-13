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
]
