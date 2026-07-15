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
        'resend-activation/',
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
        views.LoginView.as_view(),
        name="login",
    ),
    path(
        "password-reset/",
        views.PasswordResetView.as_view(),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),

    path(
        "password-reset/confirm/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),

    path(
        "password-reset/complete/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        'change-password/',
        views.PasswordChangeView.as_view(),
        name="change_password",
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(
            next_page="accounts:login",
        ),
        name="logout",
    ),
]
