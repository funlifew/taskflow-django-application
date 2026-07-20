from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import Prefetch

from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    DeleteView,
    View,
)

from .models import Board
from .forms import BoardForm
from .mixins import (
    BOARD_DELETE_ROLES,
    BOARD_WRITE_ROLES,
    BoardObjectMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
    BoardDeleteRequiredMixin,
    ArchiveBoardObjectMixin,
)

from apps.columns.models import Column
from apps.tasks.models import Task

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
        workspace = self.get_workspace()
        current_user_role = self.get_current_user_role()
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'current_user_role': current_user_role,
                'can_create_board': (
                    current_user_role
                    in BOARD_WRITE_ROLES
                ),
                'archived_boards_count': (
                    Board.objects.filter(
                        workspace=workspace,
                        is_archived=True,
                    ).count()
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
    
    def get_board_queryset(self):
        return (
            super()
            .get_board_queryset()
            .prefetch_related(
                Prefetch(
                    "columns",
                    queryset=(
                        Column.objects
                        .active()
                        .select_related(
                            "created_by",
                        )
                        .prefetch_related(
                            Prefetch(
                                "tasks",
                                queryset=(
                                    Task.objects
                                    .active()
                                    .select_related(
                                        "assignee",
                                        "created_by",
                                    )
                                    .order_by(
                                        "position",
                                        "pk",
                                    )
                                ),
                                to_attr=(
                                    "active_tasks"
                                ),
                            )
                        )
                        .order_by(
                            "position",
                            "pk",
                        )
                    ),
                    to_attr="active_columns",
                )
            )
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        current_user_role = self.get_current_user_role()
        
        can_edit_board = current_user_role in BOARD_WRITE_ROLES
        can_delete_board = current_user_role in BOARD_DELETE_ROLES
        
        columns = self.object.active_columns
        
        tasks_count = sum(
            len(column.active_tasks)
            for column in columns
        )
        
        context.update({
            'workspace': self.get_workspace(),
            'current_user_role': current_user_role,
            'can_edit_board': can_edit_board,
            'can_delete_board': can_delete_board,
            'can_archive_board': can_edit_board,
            'can_create_column': can_edit_board,
            'can_update_columns': can_edit_board,
            'can_archive_columns': can_edit_board,
            "can_create_tasks": can_edit_board,
            'columns': columns,
            'columns_count': len(columns),
            'archived_columns_count': (
                Column.objects
                .archived()
                .for_board(
                    self.object
                )
                .count()
            ),
            'tasks_count': tasks_count,
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
                f'Board «{self.object.title}» '
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

class ArchivedBoardListView(
    BoardReadRequiredMixin,
    ListView,
):
    model = Board
    template_name = 'boards/archived_list.html'
    context_object_name = 'boards'
    paginate_by = 12
    
    def get_queryset(self):
        return (
            Board.objects
            .filter(
                workspace=self.get_workspace(),
                is_archived=True,
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
        context = super().get_context_data(**kwargs)
        
        current_user_role = self.get_current_user_role()
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'current_user_role': current_user_role,
                'can_restore_boards': current_user_role in BOARD_WRITE_ROLES,
                'can_delete_boards': current_user_role in BOARD_DELETE_ROLES,
            }
        )
        
        return context

class BoardArchiveView(
    BoardObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        board = self.get_board()
        
        board.is_archived = True
        board.save(
            update_fields=[
                'is_archived',
                'updated_at',
            ]
        )
        
        messages.success(
            request,
            (
                f'Board «{board.title}» '
                'با موفقیت آرشیو شد.'
            )
        )
        
        return redirect(
            'boards:list',
            workspace_pk=board.workspace_id,
        )

class BoardRestoreView(
    ArchiveBoardObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        board = self.get_board()
        
        board.is_archived = False
        board.save(
            update_fields=[
                'is_archived',
                'updated_at',
            ]
        )
        
        messages.success(
            request,
            (
                f'Board «{board.title}» '
                'با موفقیت بازیابی شد.'
            )
        )
        
        return redirect(
            'boards:detail',
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )

class BoardDeleteView(
    ArchiveBoardObjectMixin,
    BoardDeleteRequiredMixin,
    DeleteView,
):
    model = Board
    template_name = 'boards/confirm_delete.html'
    context_object_name = 'board'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'current_user_role': self.get_current_user_role(),
            }
        )
        
        return context
    
    
    def form_valid(self, form):
        board_title = self.object.title
        
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            (
                f'Board «{board_title}» '
                "برای همیشه حذف شد."
            ),
        )
        
        return response
    
    def get_success_url(self):
        return reverse(
            'boards:archived_list',
            kwargs={
                'workspace_pk': self.get_workspace().pk
            },
        )