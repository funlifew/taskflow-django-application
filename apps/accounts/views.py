from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import CreateView, FormView, TemplateView
from django.contrib.auth.views import LoginView as OldLoginView
from django.contrib.auth import views as auth_views

from apps.core.mixins import IfAuthenticatedRedirectDashboard


from .forms import RegisterForm, ResendActivationEmailForm
from .tokens import account_activation_token
from .services import (
    can_send_activation_email,
    mark_activation_email_send,
    send_activation_email,
)


User = get_user_model()
# Create your views here.

class LoginView(IfAuthenticatedRedirectDashboard, OldLoginView):
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy("dashboard:profile")
    
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
        self.object = form.save(commit=False)

        self.object.email = (
            self.object.email.lower().strip()
        )
        self.object.is_active = False
        self.object.email_verified = False
        self.object.save()

        user = self.object

        transaction.on_commit(
            lambda: self._send_activation_email_after_commit(
                user
            )
        )

        messages.success(
            self.request,
            "حساب ساخته شد. لینک فعال‌سازی به ایمیلت ارسال شد.",
        )

        return redirect(self.success_url)
    
    def _send_activation_email_after_commit(self, user):
        if can_send_activation_email(user):
            send_activation_email(self.request, user)
            mark_activation_email_send(user)

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
            email=email,
            email_verified=False,
            is_active=False,
        ).first()

        if user is None:
            messages.info(
                self.request,
                'اگر حسابی با این ایمیل وجود داشته باشد، لینک فعالسازی ارسال میشود.'
            )
            return redirect(self.success_url)
        
        if not can_send_activation_email(user):
            messages.warning(
                self.request,
                'لینک فعالسازی اخیرا ارسال شده، لطفا کمی صبر کنید.'
            )
            return redirect(self.success_url)
        
        send_activation_email(self.request, user)
        mark_activation_email_send(user)
        
        
        messages.success(
            self.request,
            'اگر حسابی با این ایمیل وجود داشته باشد، لینک فعالسازی ارسال میشود.'
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