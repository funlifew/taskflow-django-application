from django.urls import path

from . import views


app_name = 'boards'

urlpatterns = [
    path(
        "",
        views.BoardListView.as_view(),
        name="list",
    ),
    path(
        "create/",
        views.BoardCreateView.as_view(),
        name="create",
    ),
    path(
        '<int:board_pk>/',
        views.BoardDetailView.as_view(),
        name='detail',
    ),
    path(
        '<int:board_pk>/update/',
        views.BoardUpdateView.as_view(),
        name="update",
    ),
]
