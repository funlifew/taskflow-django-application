from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path(
        'create/',
        views.TaskCreateView.as_view(),
        name="create",
    ),
]
