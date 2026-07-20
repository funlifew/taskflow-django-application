from django.urls import path

from . import views

app_name = 'columns'

urlpatterns = [
    path(
        'archived/',
        views.ArchivedColumnListView.as_view(),
        name='archived_list',
    ),
    path(
        'create/',
        views.ColumnCreateView.as_view(),
        name='create',
    ),
    path(
        '<int:column_pk>/update/',
        views.ColumnUpdateView.as_view(),
        name='update',
    ),
    path(
        '<int:column_pk>/archive/',
        views.ColumnArchiveView.as_view(),
        name='archive',
    ),
    path(
        '<int:column_pk>/restore/',
        views.ColumnRestoreView.as_view(),
        name='restore',
    ),
    path(
        '<int:column_pk>/delete/',
        views.ColumnDeleteView.as_view(),
        name="delete",
    ),
]