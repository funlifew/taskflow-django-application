from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'


urlpatterns = [
    path(
        'register/',
        views.RegisterView.as_view(),
        name='register',
    ),
    path(
        'verification-sent/',
        views.VerificationSentView.as_view(),
        name='verification_sent',
    ),
    path(
        'resend-activation',
        views.ResendActivationEmailView.as_view(),
        name='resend_verification',
    ),
    path(
        'activate/<uidb64>/<token>/',
        views.ActivationAccountView.as_view(),
        name='activate',
    ),
    path(
        'login/',
        views.LoginView.as_view(
            template_name='accounts/login.html',
        ),
        name="login",
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
