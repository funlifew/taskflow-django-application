from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import (
    reverse,
    reverse_lazy,
)
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
from .selectors import (
    get_active_workspace_boards,
    get_manageable_workspace_memberships,
    get_pending_invitations_for_user,
    get_pending_workspace_invitations,
    get_workspace_list_queryset,
    get_workspace_list_summary,
    get_workspace_memberships,
)
from .services import (
    accept_workspace_invitation,
    create_workspace,
    create_workspace_invitation,
    decline_workspace_invitation,
    expire_stale_workspace_invitations,
    remove_workspace_membership,
    update_workspace_membership_role,
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
        return get_workspace_list_queryset(
            queryset=super().get_queryset(),
            user=self.request.user,
        )

    def get_queryset(self):
        return get_workspace_list_queryset(
            queryset=super().get_queryset(),
            user=self.request.user,
            search_query=self.request.GET.get(
                'q',
                '',
            ),
            selected_role=self.request.GET.get(
                'role',
                '',
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        base_queryset = self.get_base_queryset()

        pending_invitations = (
            get_pending_invitations_for_user(
                user=user,
            )
        )

        context.update(
            get_workspace_list_summary(
                queryset=base_queryset,
                user=user,
            )
        )
        
        context.update(
            {
                "pending_invitations": (
                    pending_invitations
                ),
                "pending_invitations_count": (
                    pending_invitations.count()
                ),
                "search_query": (
                    self.request.GET
                    .get("q", "")
                    .strip()
                ),
                "selected_role": (
                    self.request.GET
                    .get("role", "")
                    .strip()
                ),
                "role_choices": (
                    WorkspaceMembership
                    .Role
                    .choices
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

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

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
        elif membership is not None:
            current_user_role = membership.role
        else:
            current_user_role = None

        can_manage_members = (
            current_user_role
            in {
                WorkspaceMembership.Role.OWNER,
                WorkspaceMembership.Role.ADMIN,
            }
        )

        can_create_board = (
            current_user_role
            in {
                WorkspaceMembership.Role.OWNER,
                WorkspaceMembership.Role.ADMIN,
                WorkspaceMembership.Role.MEMBER,
            }
        )

        is_owner = (
            current_user_role
            == WorkspaceMembership.Role.OWNER
        )

        active_boards = (
            get_active_workspace_boards(
                workspace=workspace,
            )
        )

        pending_invitations_count = 0

        if can_manage_members:
            pending_invitations_count = (
                get_pending_workspace_invitations(
                    workspace=workspace,
                )
                .count()
            )

        context.update(
            {
                "current_user_membership": membership,
                "current_user_role": current_user_role,
                "can_manage_members": can_manage_members,
                "can_edit_workspace": is_owner,
                "can_delete_workspace": is_owner,
                "can_create_board": can_create_board,
                "active_boards_count": (
                    active_boards.count()
                ),
                "recent_boards": active_boards[:4],
                "members_count": (
                    workspace.memberships.count()
                ),
                "pending_invitations_count": (
                    pending_invitations_count
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
        self.object = create_workspace(
            owner=self.request.user,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
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

        create_workspace_invitation(
            request=self.request,
            workspace=workspace,
            invited_by=self.request.user,
            email=form.cleaned_data['email'],
            role=form.cleaned_data['role'],
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

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        workspace = self.get_workspace()
        current_user_role = (
            self.get_current_user_role()
        )

        can_manage_members = (
            current_user_role
            in {
                WorkspaceMembership.Role.OWNER,
                WorkspaceMembership.Role.ADMIN,
            }
        )

        memberships = (
            get_workspace_memberships(
                workspace=workspace,
            )
        )

        if can_manage_members:
            pending_invitations = (
                get_pending_workspace_invitations(
                    workspace=workspace,
                )
            )
        else:
            pending_invitations = (
                WorkspaceInvitation
                .objects
                .none()
            )

        context.update(
            {
                "workspace": workspace,
                "memberships": memberships,
                "members_count": (
                    memberships.count()
                ),
                "pending_invitations": (
                    pending_invitations
                ),
                "pending_invitations_count": (
                    pending_invitations.count()
                ),
                "current_user_role": (
                    current_user_role
                ),
                "can_manage_members": (
                    can_manage_members
                ),
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

    def get_queryset(self):
        return (
            get_manageable_workspace_memberships(
                workspace=self.get_workspace(),
                requester_role=(
                    self.get_current_user_role()
                ),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs["requester_role"] = (
            self.get_current_user_role()
        )

        return kwargs

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context["workspace"] = (
            self.get_workspace()
        )

        return context

    def form_valid(
        self,
        form,
    ):
        self.object = (
            update_workspace_membership_role(
                workspace=self.get_workspace(),
                membership=self.object,
                requester_role=(
                    self.get_current_user_role()
                ),
                new_role=(
                    form.cleaned_data["role"]
                ),
                actor=self.request.user,
            )
        )

        messages.success(
            self.request,
            "نقش عضو با موفقیت تغییر کرد.",
        )

        return redirect(
            self.get_success_url()
        )

    def get_success_url(self):
        return reverse(
            "workspaces:members",
            kwargs={
                "pk": (
                    self.get_workspace().pk
                ),
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
        return (
            get_manageable_workspace_memberships(
                workspace=self.get_workspace(),
                requester_role=(
                    self.get_current_user_role()
                ),
            )
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context["workspace"] = (
            self.get_workspace()
        )

        return context

    def form_valid(
        self,
        form,
    ):
        member_name = (
            remove_workspace_membership(
                workspace=self.get_workspace(),
                membership=self.object,
                requester_role=(
                    self.get_current_user_role()
                ),
                actor=self.request.user,
            )
        )

        messages.success(
            self.request,
            (
                f"«{member_name}» "
                "از Workspace حذف شد."
            ),
        )

        return redirect(
            self.get_success_url()
        )

    def get_success_url(self):
        return reverse(
            "workspaces:members",
            kwargs={
                "pk": (
                    self.get_workspace().pk
                ),
            },
        )