from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    CreateView
)

from apps.boards.mixins import (
    BoardWriteRequiredMixin,
)
from apps.boards.models import Board
from apps.columns.mixins import (
    ColumnObjectMixin,
)
from apps.columns.models import Column

from .forms import TaskForm
from .models import Task

# Create your views here.

class TaskCreateView(
    ColumnObjectMixin,
    BoardWriteRequiredMixin,
    CreateView,
):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/create.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        kwargs['workspace'] = self.get_workspace()
        
        return kwargs
    
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)
        
        column = self.get_column()
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'column': column,
                'current_user_role': self.get_current_user_role(),
                'next_position': (
                    Task.objects.next_position(
                        column=column,
                    )
                ),
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
        
        column = get_object_or_404(
            Column.objects.select_for_update(),
            pk=self.get_column().pk,
            board=board,
            is_archived=False,
        )
        
        self.object = form.save(
            commit=False
        )
        
        self.object.column = column
        self.object.position = (
            Task.objects.next_position(
                column=column,
            )
        )
        
        self.object.status = (
            Task.Status.TODO
        )
        
        self.object.created_by = self.request.user
        
        self.object.is_archived = False
        
        self.object.full_clean()
        self.object.save()
        
        column.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        messages.success(
            self.request,
            (
                f'Task «{self.object.title}» '
                "با موفقیت ساخته شد."
            ),
        )
        
        
        return redirect(
            'boards:detail',
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )