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
]
