from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.shortcuts import render

from .forms import ProfileUpdateForm

# Create your views here.

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'



class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/profile.html'


class ProfileUpdateView(
    LoginRequiredMixin,
    SuccessMessageMixin,
    UpdateView
):
    form_class = ProfileUpdateForm
    template_name = 'dashboard/profile_update.html'
    success_url = reverse_lazy('dashboard:profile')
    success_message = 'پروفایل شما با موفقیت به روزرسانی شد.'

    def get_object(self, queryset=None):
        return self.request.user
    