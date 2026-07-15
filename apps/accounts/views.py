from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import CreateView, FormView, TemplateView
from django.contrib.auth import views as auth_views

from apps.core.mixins import IfAuthenticatedRedirectDashboard


from .forms import RegisterForm, ResendActivationEmailForm
from .tokens import account_activation_token
from .services import (
    send_activation_email_with_cooldown,
)

import logging

logger = logging.getLogger(__name__)
User = get_user_model()
# Create your views here.

class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        for field in form.fields.values():
            field.widget.attrs.update({
                'class': 'input',
            })

        form.fields['username'].widget.attrs.update({
            'placeholder': 'نام کاربری...',
            'autocomplete': 'username',
        })
        form.fields['password'].widget.attrs.update({
            'placeholder': 'رمز عبور...',
            'autocomplete': 'password',
        })
        
        return form

class RegisterView(
    IfAuthenticatedRedirectDashboard,
    CreateView,
):
    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy(
        "accounts:verification_sent"
    )

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.is_active = False
                self.object.email_verified = False
                self.object.save()
        
        except IntegrityError:
            form.add_error(
                None,
                'این نام کاربری یا ایمیل قبلا ثبت شده است.'
            )
            return self.form_invalid(form)
        
        try:
            sent = send_activation_email_with_cooldown(
                self.request,
                self.object,
            )
        except Exception:
            logger.exception(
                "Activation email could not sent for user %s",
                self.object.pk,
            )
            messages.warning(
                self.request,
                'حساب ساخته شد، اما ارسال ایمیل فعال سازی موفق نبود'
                'از بخش ارسال مجدد لینک استفاده کن.'
            )
        else:
            if sent:
                messages.success(
                    self.request,
                    'حساب ساخته شد و لینک فعالسازی ارسال شد.'
                )
        
        return redirect(self.success_url)

class ActivationAccountView(IfAuthenticatedRedirectDashboard, View):
    template_name = 'accounts/activation_invalid.html'
    
    def get(self, request, uidb64, token):
        user = self.get_user(uidb64)
        
        if user is not None and account_activation_token.check_token(user, token):
            if user.email_verified and user.is_active:
                messages.info(request, 'اکانت شما قبلا فعال شده است.')
                return redirect('accounts:login')
            
            user.is_active = True
            user.email_verified = True
            user.save(update_fields=['is_active', 'email_verified'])
            
            messages.success(
                request,
                'اکانت شما با موفقیت فعال شد. حالا میتوانید وارد شوید.'
            )
            
            return redirect('accounts:login')
        return render(request, self.template_name)
    
    def get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

class VerificationSentView(IfAuthenticatedRedirectDashboard, TemplateView):
    template_name = 'accounts/verification_sent.html'
    
class ResendActivationEmailView(IfAuthenticatedRedirectDashboard, FormView):
    template_name = 'accounts/resend_activation_email.html'
    form_class = ResendActivationEmailForm
    success_url = reverse_lazy('accounts:verification_sent')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        
        user = User.objects.filter(
            email__iexact=email,
            email_verified=False,
            is_active=False,
        ).first()
        
        if user is not None:
            try:
                send_activation_email_with_cooldown(
                    self.request,
                    user,
                )
            except Exception:
                logger.exception(
                    'Resending activation email failed for user %s',
                    user.pk,
                )
            
        
        messages.info(
            self.request,
            "اگر حساب تأییدنشده‌ای با این ایمیل وجود داشته باشد "
            "و محدودیت زمانی اجازه بدهد، لینک فعال‌سازی ارسال می‌شود.",
        )
        return redirect(self.success_url)
    
# Password Resets
class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/emails/password_reset_email.txt'
    html_email_template_name = 'accounts/emails/password_reset_email.html'
    subject_template_name = 'accounts/emails/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'

class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
    

# Password Change

class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('dashboard:profile')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            'رمز عبور شما با موفقیت تغییر کرد.'
        )
        
        return response