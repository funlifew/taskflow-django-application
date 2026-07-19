from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import (
    CreateView,
)

from apps.boards.mixins import (
    BoardObjectMixin,
    BoardWriteRequiredMixin,
)
from apps.boards.models import Board

from .forms import ColumnForm
from .models import Column

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
        