from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from apps.boards.mixins import (
    BOARD_DELETE_ROLES,
    BOARD_WRITE_ROLES,
    BoardDeleteRequiredMixin,
    BoardObjectMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
)
from apps.boards.models import Board

from .forms import ColumnForm
from .models import Column
from .mixins import (
    ArchivedColumnObjectMixin,
    ColumnObjectMixin,
)

# Create your views here.

class ColumnCreateView(
    BoardObjectMixin,
    BoardWriteRequiredMixin,
    CreateView,
):
    model = Column
    form_class = ColumnForm
    template_name = 'columns/create.html'
    
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'current_user_role': self.get_current_user_role(),
                'next_position': Column.objects.next_position(board=self.get_board()),
            }
        )
        
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        board = (
            Board.objects
            .select_for_update()
            .get(
                pk=self.get_board().pk,
                workspace=self.get_workspace(),
                is_archived=False,
            )
        )
        
        self.object = form.save(
            commit=False
        )
        
        self.object.board = board
        self.object.position = (
            Column.objects.next_position(
                board=board,
            )
        )
        
        self.object.created_by = self.request.user
        
        self.object.is_archived = False
        
        self.object.save()
        
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        messages.success(
            self.request,
            (
                f'ستون «{self.object.title}» '
                'با موفقیت ساخته شد.'
            ),
        )
        
        return redirect(
            'boards:detail',
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )

class ColumnUpdateView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    UpdateView,
):
    model = Column
    form_class = ColumnForm
    template_name = 'columns/update.html'
    context_object_name = 'column'
    
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'current_user_role': self.get_current_user_role(),
            }
        )
        
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        board = get_object_or_404(
            Board.objects.select_for_update(),
            pk=self.get_board().pk,
            workspace=self.get_workspace(),
            is_archived=False,
        )
        
        response = super().form_valid(form)
        
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        messages.success(
            self.request,
            (
                f'ستون «{self.object.title}» '
                "با موفقیت ویرایش شد."
            ),
        )
        
        return response
    
    def get_success_url(self):
        return reverse(
            'boards:detail',
            kwargs={
                'workspace_pk': self.get_workspace().pk,
                'board_pk': self.get_board().pk,
            },
        )

class ArchivedColumnListView(
    BoardObjectMixin,
    BoardReadRequiredMixin,
    ListView,
):
    model = Column
    template_name = 'columns/archived_list.html'
    context_object_name = 'columns'
    paginate_by = 12
    
    def get_queryset(self):
        return (
            Column.objects
            .archived()
            .for_board(
                self.get_board()
            )
            .select_related(
                'board',
                'created_by',
            )
            .order_by(
                '-updated_at',
                '-pk',
            )
        )
    
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)
        
        current_user_role = self.get_current_user_role()
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'current_user_role': current_user_role,
                'can_restore_columns': (
                    current_user_role
                    in BOARD_WRITE_ROLES
                ),
                'can_delete_columns': (
                    current_user_role
                    in BOARD_DELETE_ROLES
                ),
            }
        )
        
        return context

class ColumnArchiveView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    @transaction.atomic
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        board = get_object_or_404(
            Board.objects.select_for_update(),
            pk=self.get_board().pk,
            workspace=self.get_workspace(),
            is_archived=False,
        )
        
        column = get_object_or_404(
            Column.objects.select_for_update(),
            pk=self.kwargs['column_pk'],
            board=board,
            is_archived=False,
        )
        
        column.is_archived = True
        column.save(
            update_fields=[
                'is_archived',
                'updated_at',
            ]
        )
        
        Column.objects.normalize_positions(
            board=board,
        )
        
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        messages.success(
            request,
            (
                f'ستون «{column.title}» '
                "با موفقیت آرشیو شد."
            ),
        )
        
        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )

class ColumnRestoreView(
    ArchivedColumnObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    @transaction.atomic
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        board = get_object_or_404(
            Board.objects.select_for_update(),
            pk=self.get_board().pk,
            workspace=self.get_workspace(),
            is_archived=False,
        )
        
        column = get_object_or_404(
            Column.objects.select_for_update(),
            pk=self.kwargs['column_pk'],
            board=board,
            is_archived=True,
        )
        
        column.position = (
            Column.objects.next_position(
                board=board,
            )
        )
        
        column.is_archived = False
        
        column.save(
            update_fields=[
                "position",
                "is_archived",
                "updated_at",
            ]
        )

        board.save(
            update_fields=[
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                f'ستون «{column.title}» '
                "با موفقیت بازیابی شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )

class ColumnDeleteView(
    ArchivedColumnObjectMixin,
    BoardDeleteRequiredMixin,
    DeleteView,
):
    model = Column
    template_name = 'columns/confirm_delete.html'
    context_object_name = 'column'

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'current_user_role': self.get_current_user_role()
            }
        )
        
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        board = get_object_or_404(
            Board.objects.select_for_update(),
            pk=self.get_board().pk,
            workspace=self.get_workspace(),
            is_archived=False,
        )
        
        self.object = get_object_or_404(
            Column.objects.select_for_update(),
            pk=self.object.pk,
            board=board,
            is_archived=True,
        )
        
        column_title = self.object.title
        
        response = super().form_valid(form)
        
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        messages.success(
            self.request,
            (
                f'ستون «{column_title}» '
                "برای همیشه حذف شد."
            ),
        )
        
        return response
    
    def get_success_url(self):
        return reverse(
            'columns:archived_list',
            kwargs={
                'workspace_pk': self.kwargs['workspace_pk'],
                'board_pk': self.kwargs['board_pk'],
            },
        )
        
        