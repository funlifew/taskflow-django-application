from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path("profile/", views.ProfileView.as_view(), name='profile'),
    path(
        'profile/update/',
        views.ProfileUpdateView.as_view(),
        name='profile_update',
    ),
]
