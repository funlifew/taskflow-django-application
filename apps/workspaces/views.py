from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.core.mixins import (
    AccessibleWorkspaceMixin,
    OwnerWorkspaceMixin,
    WorkspaceAdminRequiredMixin,
    WorkspacePermissionMixin,
)

from .forms import (
    WorkspaceForm,
    WorkspaceInviteForm,
    WorkspaceMembershipUpdateForm,
)
from .models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from .services import (
    accept_workspace_invitation,
    decline_workspace_invitation,
    send_workspace_invitation_email,
    expire_stale_workspace_invitations,
)


class WorkspaceListView(
    AccessibleWorkspaceMixin,
    ListView,
):
    model = Workspace
    template_name = "workspaces/list.html"
    context_object_name = "workspaces"
    paginate_by = 9

    def get_base_queryset(self):
        current_user_role = (
            WorkspaceMembership.objects
            .filter(
                workspace=OuterRef("pk"),
                user=self.request.user,
            )
            .values("role")[:1]
        )

        return (
            super()
            .get_queryset()
            .select_related("owner")
            .annotate(
                members_count=Count(
                    "memberships",
                    distinct=True,
                ),
                current_user_role=Subquery(
                    current_user_role
                ),
            )
            .order_by("-updated_at")
        )

    def get_queryset(self):
        queryset = self.get_base_queryset()

        search_query = (
            self.request.GET.get("q", "").strip()
        )
        selected_role = (
            self.request.GET.get("role", "").strip()
        )

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(owner__username__icontains=search_query)
                | Q(owner__first_name__icontains=search_query)
                | Q(owner__last_name__icontains=search_query)
            )

        if selected_role in WorkspaceMembership.Role.values:
            queryset = queryset.filter(
                memberships__user=self.request.user,
                memberships__role=selected_role,
            )

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        accessible_workspaces = self.get_base_queryset()

        pending_invitations = (
            WorkspaceInvitation.objects
            .filter(
                email__iexact=user.email,
                status=WorkspaceInvitation.Status.PENDING,
                expires_at__gt=timezone.now(),
                workspace__is_archived=False,
            )
            .select_related(
                "workspace",
                "invited_by",
            )
            .order_by("-created_at")
        )

        context.update(
            {
                "total_workspaces": (
                    accessible_workspaces.count()
                ),
                "owned_workspaces_count": (
                    accessible_workspaces
                    .filter(owner=user)
                    .count()
                ),
                "joined_workspaces_count": (
                    accessible_workspaces
                    .exclude(owner=user)
                    .count()
                ),
                "pending_invitations": (
                    pending_invitations
                ),
                "pending_invitations_count": (
                    pending_invitations.count()
                ),
                "search_query": (
                    self.request.GET.get("q", "").strip()
                ),
                "selected_role": (
                    self.request.GET
                    .get("role", "")
                    .strip()
                ),
                "role_choices": (
                    WorkspaceMembership.Role.choices
                ),
            }
        )

        return context


class WorkspaceDetailView(
    AccessibleWorkspaceMixin,
    DetailView,
):
    model = Workspace
    template_name = "workspaces/detail.html"
    context_object_name = "workspace"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("owner")
            .prefetch_related(
                "memberships__user",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        workspace = self.object
        user = self.request.user

        membership = (
            workspace.memberships
            .filter(user=user)
            .first()
        )

        if workspace.owner_id == user.id:
            current_user_role = (
                WorkspaceMembership.Role.OWNER
            )
        elif membership:
            current_user_role = membership.role
        else:
            current_user_role = None

        can_manage_members = current_user_role in {
            WorkspaceMembership.Role.OWNER,
            WorkspaceMembership.Role.ADMIN,
        }

        is_owner = (
            workspace.owner_id == user.id
        )

        context.update(
            {
                "current_user_membership": membership,
                "current_user_role": current_user_role,
                "can_manage_members": can_manage_members,

                # UpdateView و DeleteView فعلاً فقط Owner هستند.
                "can_edit_workspace": is_owner,
                "can_delete_workspace": is_owner,

                "members_count": (
                    workspace.memberships.count()
                ),
                "pending_invitations_count": (
                    workspace.invitations.filter(
                        status=(
                            WorkspaceInvitation
                            .Status
                            .PENDING
                        ),
                        expires_at__gt=timezone.now(),
                    ).count()
                    if can_manage_members
                    else 0
                ),
            }
        )

        return context


class WorkspaceCreateView(
    LoginRequiredMixin,
    CreateView,
):
    model = Workspace
    form_class = WorkspaceForm
    template_name = "workspaces/create.html"

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
            "Workspace با موفقیت ساخته شد.",
        )

        return redirect(
            "workspaces:detail",
            pk=self.object.pk,
        )


class WorkspaceUpdateView(
    OwnerWorkspaceMixin,
    UpdateView,
):
    model = Workspace
    form_class = WorkspaceForm
    template_name = "workspaces/update.html"
    context_object_name = "workspace"

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "Workspace با موفقیت ویرایش شد.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "workspaces:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )


class WorkspaceDeleteView(
    OwnerWorkspaceMixin,
    DeleteView,
):
    model = Workspace
    template_name = (
        "workspaces/delete_confirm.html"
    )
    context_object_name = "workspace"
    success_url = reverse_lazy("workspaces:list")

    def form_valid(self, form):
        workspace_name = self.object.name

        response = super().form_valid(form)

        messages.success(
            self.request,
            f'Workspace «{workspace_name}» حذف شد.',
        )

        return response


class WorkspaceInvitationCreateView(
    WorkspaceAdminRequiredMixin,
    FormView,
):
    template_name = (
        "workspaces/member_invite.html"
    )
    form_class = WorkspaceInviteForm

    def get_form_kwargs(self):
        workspace = self.get_workspace()
        expire_stale_workspace_invitations(
            workspace=workspace
        )
        
        kwargs = super().get_form_kwargs()
        kwargs["workspace"] = self.get_workspace()
        kwargs["request_user"] = self.request.user

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["workspace"] = self.get_workspace()

        return context

    def form_valid(self, form):
        workspace = self.get_workspace()

        with transaction.atomic():
            invitation = form.save(commit=False)
            invitation.workspace = workspace
            invitation.invited_by = self.request.user
            invitation.expires_at = (
                timezone.now()
                + timedelta(days=3)
            )
            invitation.save()

            transaction.on_commit(
                lambda: (
                    send_workspace_invitation_email(
                        self.request,
                        invitation,
                    )
                )
            )

        messages.success(
            self.request,
            "دعوت‌نامه با موفقیت ارسال شد.",
        )

        return redirect(
            "workspaces:members",
            pk=workspace.pk,
        )


class WorkspaceInvitationDetailView(
    LoginRequiredMixin,
    DetailView,
):
    model = WorkspaceInvitation
    template_name = (
        "workspaces/invitation_detail.html"
    )
    context_object_name = "invitation"
    slug_field = "token"
    slug_url_kwarg = "token"

    def get_queryset(self):
        """
        فقط صاحب ایمیلی که دعوت برای او فرستاده شده
        اجازه مشاهده دعوت را دارد.
        """

        return (
            WorkspaceInvitation.objects
            .filter(
                email__iexact=self.request.user.email,
            )
            .select_related(
                "workspace",
                "invited_by",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["invitation_is_expired"] = (
            self.object.expires_at
            <= timezone.now()
        )

        return context


class WorkspaceInvitationAcceptView(
    LoginRequiredMixin,
    View,
):
    def post(self, request, token):
        invitation = get_object_or_404(
            WorkspaceInvitation.objects.select_related(
                "workspace",
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
                "workspaces:invitation_detail",
                token=token,
            )

        except ValueError as error:
            messages.warning(
                request,
                str(error),
            )

            return redirect(
                "workspaces:invitation_detail",
                token=token,
            )

        messages.success(
            request,
            "دعوت را پذیرفتی و به Workspace اضافه شدی.",
        )

        return redirect(
            "workspaces:detail",
            pk=invitation.workspace_id,
        )


class WorkspaceInvitationDeclineView(
    LoginRequiredMixin,
    View,
):
    def post(self, request, token):
        invitation = get_object_or_404(
            WorkspaceInvitation,
            token=token,
            status=WorkspaceInvitation.Status.PENDING,
        )

        try:
            decline_workspace_invitation(
                invitation=invitation,
                user=request.user
            )
            
        except PermissionError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "workspaces:invitation_detail",
                token=token,
            )
        
        except ValueError as error:
            messages.warning(
                request,
                str(error),
            )

            return redirect(
                "workspaces:invitation_detail",
                token=token,
            )

        messages.info(
            request,
            'دعوت Workspace رد شد.',
        )
        
        return redirect(
            'dashboard:dashboard',
        )

class WorkspaceMemberListView(
    WorkspacePermissionMixin,
    TemplateView,
):
    template_name = "workspaces/members.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        workspace = self.get_workspace()
        requester_membership = self.get_membership()

        if workspace.owner_id == self.request.user.id:
            current_user_role = (
                WorkspaceMembership.Role.OWNER
            )
        elif requester_membership:
            current_user_role = (
                requester_membership.role
            )
        else:
            current_user_role = None

        can_manage_members = current_user_role in {
            WorkspaceMembership.Role.OWNER,
            WorkspaceMembership.Role.ADMIN,
        }

        memberships = (
            workspace.memberships
            .select_related("user")
            .order_by(
                "role",
                "created_at",
            )
        )

        if can_manage_members:
            pending_invitations = (
                workspace.invitations
                .filter(
                    status=(
                        WorkspaceInvitation
                        .Status
                        .PENDING
                    ),
                    expires_at__gt=timezone.now(),
                )
                .select_related("invited_by")
                .order_by("-created_at")
            )
        else:
            pending_invitations = (
                WorkspaceInvitation.objects.none()
            )

        context.update(
            {
                "workspace": workspace,
                "memberships": memberships,
                "members_count": memberships.count(),
                "pending_invitations": (
                    pending_invitations
                ),
                "pending_invitations_count": (
                    pending_invitations.count()
                ),
                "current_user_role": current_user_role,
                "can_manage_members": can_manage_members,
            }
        )

        return context


class WorkspaceMembershipUpdateView(
    WorkspaceAdminRequiredMixin,
    UpdateView,
):
    model = WorkspaceMembership
    form_class = (
        WorkspaceMembershipUpdateForm
    )
    template_name = (
        "workspaces/member_update.html"
    )
    context_object_name = "membership"
    pk_url_kwarg = "membership_pk"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        workspace = self.get_workspace()
        requester_membership = self.get_membership()
        
        if workspace.owner_id == self.request.user.id:
            requester_role = WorkspaceMembership.Role.OWNER
        else:
            requester_role = requester_membership.role
        
        
        kwargs['requester_role'] = requester_role
        
        
        return kwargs
    
    def get_queryset(self):
        queryset = (
            WorkspaceMembership.objects
            .filter(
                workspace=self.get_workspace(),
            )
            .exclude(
                role=WorkspaceMembership.Role.OWNER,
            )
            .select_related(
                "user",
                "workspace",
            )
        )

        requester_membership = (
            self.get_membership()
        )

        # Admin اجازه تغییر نقش Admin دیگری را ندارد.
        if (
            requester_membership
            and requester_membership.role
            == WorkspaceMembership.Role.ADMIN
        ):
            queryset = queryset.exclude(
                role=WorkspaceMembership.Role.ADMIN,
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["workspace"] = self.get_workspace()

        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "نقش عضو با موفقیت تغییر کرد.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "workspaces:members",
            kwargs={
                "pk": self.get_workspace().pk,
            },
        )


class WorkspaceMembershipDeleteView(
    WorkspaceAdminRequiredMixin,
    DeleteView,
):
    model = WorkspaceMembership
    template_name = (
        "workspaces/member_remove_confirm.html"
    )
    context_object_name = "membership"
    pk_url_kwarg = "membership_pk"

    def get_queryset(self):
        workspace = self.get_workspace()

        queryset = (
            WorkspaceMembership.objects
            .filter(workspace=workspace)
            .exclude(
                role=WorkspaceMembership.Role.OWNER,
            )
            .select_related(
                "user",
                "workspace",
            )
        )

        requester_membership = (
            self.get_membership()
        )

        # Admin نمی‌تواند Admin دیگری را حذف کند.
        if (
            requester_membership
            and requester_membership.role
            == WorkspaceMembership.Role.ADMIN
        ):
            queryset = queryset.exclude(
                role=WorkspaceMembership.Role.ADMIN,
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["workspace"] = self.get_workspace()

        return context

    def form_valid(self, form):
        member_name = (
            self.object.user.get_full_name()
            or self.object.user.username
        )

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"«{member_name}» از Workspace حذف شد.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "workspaces:members",
            kwargs={
                "pk": self.get_workspace().pk,
            },
        )