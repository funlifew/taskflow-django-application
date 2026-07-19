from django.urls import path

from . import views

app_name = 'columns'

urlpatterns = [
    path(
        'create/',
        views.ColumnCreateView.as_view(),
        name='create',
    ),
]