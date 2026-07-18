from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from apps.workspaces.models import WorkspaceMembership

from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
)

from .models import Board
from .forms import BoardForm
from .mixins import (
    BoardObjectMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
)

# Create your views here.

class BoardListView(
    BoardReadRequiredMixin,
    ListView,
):
    model = Board
    template_name = 'boards/list.html'
    context_object_name = 'boards'
    paginate_by = 12
    
    def get_queryset(self):
        return (
            Board.objects
            .filter(
                workspace=self.get_workspace(),
                is_archived=False,
            )
            .select_related(
                'workspace',
                'created_by',
            )
            .order_by(
                '-updated_at',
                '-pk',
            )
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )
        
        current_user_role = self.get_current_user_role()
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'current_user_role': current_user_role,
                'can_create_board': (
                    current_user_role
                    in {
                        WorkspaceMembership.Role.OWNER,
                        WorkspaceMembership.Role.ADMIN,
                        WorkspaceMembership.Role.MEMBER
                    }
                ),
            }
        )
        
        return context

class BoardCreateView(
    BoardWriteRequiredMixin,
    CreateView,
):
    model = Board
    form_class = BoardForm
    template_name = 'boards/create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )
        
        context['workspace'] = self.get_workspace()
        
        return context
    
    def form_valid(self, form):
        workspace = self.get_workspace()
        
        self.object = form.save(commit=False)
        self.object.workspace = workspace
        self.object.created_by = self.request.user
        self.object.is_archived = False
        
        self.object.save()
        
        messages.success(
            self.request,
            (
                f'Board «{self.object.title}» '
                'با موفقیت ساخته شد.'
            )
        )
        
        return redirect(
            'boards:list',
            workspace_pk=workspace.pk,
        )

class BoardDetailView(
    BoardObjectMixin,
    BoardReadRequiredMixin,
    DetailView,
):
    model = Board
    template_name = 'boards/detail.html'
    context_object_name = 'board'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        current_user_role = self.get_current_user_role()
        
        can_edit_board = current_user_role in {
            WorkspaceMembership.Role.OWNER,
            WorkspaceMembership.Role.ADMIN,
            WorkspaceMembership.Role.MEMBER,
        }
        
        can_delete_board = current_user_role in {
            WorkspaceMembership.Role.OWNER,
            WorkspaceMembership.Role.ADMIN,
        }
        
        context.update({
            'workspace': self.get_workspace(),
            'current_user_role': current_user_role,
            'can_edit_board': can_edit_board,
            'can_delete_board': can_delete_board,
            'can_archive_board': can_edit_board,
        })
        
        return context

class BoardUpdateView(
    BoardObjectMixin,
    BoardWriteRequiredMixin,
    UpdateView,
):
    model = Board
    form_class = BoardForm
    template_name = 'boards/update.html'
    context_object_name = 'board'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context.update({
            'workspace': self.get_workspace(),
            'current_user_role': self.get_current_user_role(),
        })
        
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            (
                'Board «{self.object.title}» '
                'با موفقیت ویرایش شد.'
            ),
        )
        
        return response
    
    def get_success_url(self):
        return reverse(
            'boards:detail',
            kwargs={
                'workspace_pk': self.object.workspace_id,
                'board_pk': self.object.pk,
            },
        )