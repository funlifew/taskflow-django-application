from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path(
        'archived/',
        views.ArchivedTaskListView.as_view(),
        name='archived_list',
    ),
    path(
        'create/',
        views.TaskCreateView.as_view(),
        name="create",
    ),
    path(
        '<int:task_pk>/',
        views.TaskDetailView.as_view(),
        name='detail',
    ),
    path(
        '<int:task_pk>/update/',
        views.TaskUpdateView.as_view(),
        name='update',
    ),
    path(
        '<int:task_pk>/status/',
        views.TaskStatusUpdateView.as_view(),
        name='status',
    ),
    path(
        '<int:task_pk>/move/',
        views.TaskMoveView.as_view(),
        name='move',
    ),
    path(
        '<int:task_pk>/archive/',
        views.TaskArchiveView.as_view(),
        name='archive',
    ),
    path(
        '<int:task_pk>/restore/',
        views.TaskRestoreView.as_view(),
        name='restore',
    ),
    path(
        '<int:task_pk>/delete/',
        views.TaskDeleteView.as_view(),
        name='delete',
    ),
]
