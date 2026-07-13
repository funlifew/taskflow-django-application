from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import WorkspaceForm
from .models import Workspace, WorkspaceMembership

from apps.core.mixins import AccessibleWorkspaceMixin, OwnerWorkspaceMixin

# Create your views here.

class WorkspaceListView(AccessibleWorkspaceMixin, ListView):
    model = Workspace
    template_name = 'workspaces/list.html'
    context_object_name = 'workspaces'
    paginate_by = 12

class WorkspaceDetailView(AccessibleWorkspaceMixin, DetailView):
    model = Workspace
    template_name = 'workspaces/detail.html'
    context_object_name = 'workspace'
    
    def get_queryset(self):
        return(
            super()
            .get_queryset()
            .prefetch_related('memberships__user')
        )

class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    model = Workspace
    form_class = WorkspaceForm
    template_name = 'workspaces/create.html'
    
    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.owner = self.request.user
            self.object.save()
            
            WorkspaceMembership.objects.create(
                workspace=self.object,
                user=self.request.user,
                role=WorkspaceMembership.Role.OWNER,
            )
        
        messages.success(
            self.request,
            'Workspace با موفقیت ساخته شد.'
        )
        
        return redirect(
            'workspaces:detail',
            pk=self.object.pk,
        )

class WorkspaceUpdateView(OwnerWorkspaceMixin, UpdateView):
    model = Workspace
    form_class = WorkspaceForm
    template_name = 'workspaces/update.html'
    context_object_name = 'workspace'
    
    def form_valid(self, form):
        messages.success(
            self.request,
            'Workspace با موفقیت ویرایش شد.'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'workspaces:detail',
            kwargs={'pk': self.object.pk},
        )
    

class WorkspaceDeleteView(OwnerWorkspaceMixin, DeleteView):
    model = Workspace
    template_name = "workspaces/delete_confirm.html"
    context_object_name = "workspace"
    success_url = reverse_lazy("workspaces:list")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Workspace با موفقیت حذف شد.",
        )
        return super().form_valid(form)