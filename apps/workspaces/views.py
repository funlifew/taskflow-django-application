from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    FormView,
    View,
)

from .forms import (
    WorkspaceForm,
    WorkspaceMembershipUpdateForm,
    WorkspaceInviteForm,
)
from .models import Workspace, WorkspaceMembership, WorkspaceInvitation

from apps.core.mixins import (
    AccessibleWorkspaceMixin,
    OwnerWorkspaceMixin,
    WorkspaceAdminRequiredMixin
)

from .services import (
    accept_workspace_invitation,
    send_workspace_invitation_email,
)

from datetime import timedelta


User = get_user_model()
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

class WorkspaceInvitationCreate(
    WorkspaceAdminRequiredMixin,
    FormView
):
    template_name = 'workspaces/member_invite.html'
    form_class = WorkspaceInviteForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['workspace'] = self.get_workspace()
        kwargs['request_user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        workspace = self.get_workspace()
        
        with transaction.atomic():
            invitation = form.save(commit=False)
            invitation.workspace = workspace
            invitation.invited_by = self.request.user
            invitation.expires_at = (
                timezone.now() + timedelta(days=3)
            )
            invitation.save()
            
            transaction.on_commit(
                lambda: send_workspace_invitation_email(
                    self.request,
                    invitation,
                )
            )
        
        messages.success(
            self.request,
            'دعوتنامه با موفقیت ارسال شد.',
        )
        
        return redirect(
            'workspaces:members',
            pk=workspace.pk,
        )

class WorkspaceInvitationDetailView(
    LoginRequiredMixin,
    DetailView
):
    model = WorkspaceInvitation
    template_name = (
        'workspaces/invitation_detail.html'
    )
    context_object_name = 'invitation'
    slug_field = 'token'
    slug_url_kwarg = 'token'

    def get_queryset(self):
        return (
            WorkspaceInvitation.objects.select_related(
                'workspace',
                'invited_by',
            )
        )

class WorkspaceInvitationAcceptView(
    LoginRequiredMixin,
    View
):
    def post(self, request, token):
        invitation = get_object_or_404(
            WorkspaceInvitation.objects.select_related(
                'workspace',
            ),
            token=token,
        )
        
        try:
            accept_workspace_invitation(
                invitation=invitation,
                user=request.user,
            )
        except PermissionError as error:
            messages.error(
                request,
                str(error),
            )
            
            return redirect(
                'workspace:invitation_detail',
                token=token,
            )
        
        except ValueError as error:
            messages.warning(
                request,
                str(error),
            )
            
            return redirect(
                'workspace:invitation_detail',
                token=token,
            )
        
        messages.success(
            request,
            'دعوت را پذیرفتی و به Workspace اضافه شدی.'
        )
        return redirect(
            'workspace:detail',
            pk=invitation.workspace_id,
        )