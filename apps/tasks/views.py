from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from apps.boards.mixins import (
    BOARD_DELETE_ROLES,
    BOARD_WRITE_ROLES,
    BoardDeleteRequiredMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
)
from apps.boards.models import Board
from apps.columns.mixins import (
    ColumnObjectMixin,
)
from apps.columns.models import Column

from .forms import (
    TaskForm,
    TaskMoveForm,
    TaskStatusForm,
)
from .mixins import (
    ArchivedTaskObjectMixin,
    TaskObjectMixin,
)
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

class TaskDetailView(
    TaskObjectMixin,
    BoardReadRequiredMixin,
    DetailView,
):
    model = Task
    template_name = 'tasks/detail.html'
    context_object_name = 'task'
    
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
                'column': self.get_column(),
                'current_user_role': current_user_role,
                'can_update_task': current_user_role in BOARD_WRITE_ROLES,
                'can_archive_task': current_user_role in BOARD_WRITE_ROLES,
                'can_move_task': current_user_role in BOARD_WRITE_ROLES,
                'status_form': TaskStatusForm(instance=self.object),
            }
        )
        
        return context
    

class TaskUpdateView(
    TaskObjectMixin,
    BoardWriteRequiredMixin,
    UpdateView,
):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/update.html'
    context_object_name = 'task'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        kwargs['workspace'] = self.get_workspace()
        return kwargs
    
    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'column': self.get_column(),
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
        
        column = get_object_or_404(
            Column.objects.select_for_update(),
            pk=self.get_column().pk,
            board=board,
            is_archived=False,
        )
        
        locked_task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.object.pk,
            column=column,
            is_archived=False,
        )

        self.object = form.save(
            commit=False
        )

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
                "با موفقیت ویرایش شد."
            ),
        )

        return redirect(
            self.get_success_url()
        )
    
    def get_success_url(self):
        return reverse(
            "tasks:detail",
            kwargs={
                "workspace_pk": (
                    self.get_workspace().pk
                ),
                "board_pk": (
                    self.get_board().pk
                ),
                "column_pk": (
                    self.get_column().pk
                ),
                "task_pk": self.object.pk,
            },
        )


class TaskStatusUpdateView(
    TaskObjectMixin,
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
            pk=self.get_column().pk,
            board=board,
            is_archived=False,
        )

        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.kwargs["task_pk"],
            column=column,
            is_archived=False,
        )
        
        form = TaskStatusForm(
            request.POST,
            instance=task,
        )
        
        if not form.is_valid():
            messages.error(
                request,
                "وضعیت انتخاب‌شده معتبر نیست.",
            )

            return redirect(
                "tasks:detail",
                workspace_pk=board.workspace_id,
                board_pk=board.pk,
                column_pk=column.pk,
                task_pk=task.pk,
            )
        
        
        task = form.save(commit=False)
        task.full_clean()
        task.save(
            update_fields=[
                'status',
                'updated_at',
            ]
        )
        
        column.save(
            update_fields=[
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
                f'وضعیت Task «{task.title}» '
                "به‌روزرسانی شد."
            ),
        )

        return redirect(
            "tasks:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
            column_pk=column.pk,
            task_pk=task.pk,
        )

class TaskMoveView(
    TaskObjectMixin,
    BoardWriteRequiredMixin,
    FormView,
):
    form_class = TaskMoveForm
    template_name = 'tasks/move.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        kwargs.update(
            {
                'board': self.get_board(),
                'current_column': self.get_column(),
            }
        )
        
        return kwargs
    
    
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
                'column': self.get_column(),
                'task': self.get_task(),
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
        
        source_column_pk = self.get_column().pk
        
        target_column_pk = form.cleaned_data['target_column'].pk
        
        locked_columns = {
            column.pk: column
            for column in (
                Column.objects
                .select_for_update()
                .filter(
                    board=board,
                    is_archived=False,
                    pk__in=[
                        source_column_pk,
                        target_column_pk,
                    ],
                )
                .order_by('pk')
            )
        }
        
        if (
            source_column_pk
            not in locked_columns
            or target_column_pk
            not in locked_columns
        ):
            raise Http404
        
        source_column = locked_columns[source_column_pk]
        target_column = locked_columns[target_column_pk]
        
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.kwargs['task_pk'],
            column=source_column,
            is_archived=False,
        )
        
        task.column = target_column
        task.position = (
            Task.objects.next_position(
                column=target_column,
            )
        )
        
        task.save(
            update_fields=[
                'column',
                'position',
                'updated_at',
            ]
        )
        
        Task.objects.normalize_positions(
            column=source_column,
        )
        
        source_column.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        target_column.save(
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
                f'Task «{task.title}» به ستون '
                f'«{target_column.title}» منتقل شد.'
            ),
        )

        return redirect(
            "tasks:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
            column_pk=target_column.pk,
            task_pk=task.pk,
        )


class ArchivedTaskListView(
    ColumnObjectMixin,
    BoardReadRequiredMixin,
    ListView,
):
    model = Task
    template_name = 'tasks/archived_list.html'
    context_object_name = 'tasks'
    paginate_by = 12
    
    def get_queryset(self):
        return (
            Task.objects
            .archived()
            .for_column(
                self.get_column()
            )
            .select_related(
                'column',
                'assignee',
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
                'column': self.get_board(),
                'current_user_role': current_user_role,
                'can_restore_tasks': current_user_role in BOARD_WRITE_ROLES,
                'can_delete_tasks': current_user_role in BOARD_DELETE_ROLES,
            }
        )
        
        return context

class TaskArchiveView(
    TaskObjectMixin,
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
            pk=self.get_column().pk,
            board=board,
            is_archived=False,
        )
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.kwargs['task_pk'],
            column=column,
            is_archived=False,
        )
        
        task.is_archived = True
        task.save(
            update_fields=[
                'is_archived',
                'updated_at',
            ]
        )
        
        Task.objects.normalize_positions(
            column=column,
        )
        
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
            request,
            (
                f'Task «{task.title}» '
                "با موفقیت آرشیو شد."
            ),
        )

        return redirect(
            "boards:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
        )

class TaskRestoreView(
    ArchivedTaskObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post'
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
            pk=self.get_column().pk,
            board=board,
            is_archived=False,
        )
        
        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.kwargs['task_pk'],
            column=column,
            is_archived=True,
        )

        task.position = (
            Task.objects.next_position(
                column=column,
            )
        )
        
        task.is_archived = False
        
        task.save(
            update_fields=[
                'position',
                'is_archived',
                'updated_at',
            ]
        )
        
        board.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        column.save(
            update_fields=[
                'updated_at',
            ]
        )
        
        messages.success(
            request,
            (
                f'Task «{task.title}» '
                "با موفقیت بازیابی شد."
            ),
        )

        return redirect(
            "tasks:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
            column_pk=column.pk,
            task_pk=task.pk,
        )


class TaskDeleteView(
    ArchivedTaskObjectMixin,
    BoardDeleteRequiredMixin,
    DeleteView,
):
    model = Task
    template_name = 'tasks/confirm_delete.html'
    context_object_name = 'task'

    def get_context_data(
        self,
        **kwargs
    ):
        context = super().get_context_data(
            **kwargs
        )
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'column': self.get_column(),
                'current_user_role': self.get_current_user_role(),
            }
        )
    
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

        task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.object.pk,
            column=column,
            is_archived=True,
        )
        
        task_title = task.title
        task.delete()
        
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
                f'Task «{task_title}» '
                "برای همیشه حذف شد."
            ),
        )

        return redirect(
            self.get_success_url()
        )
    
    def get_success_url(self):
        return reverse(
            "tasks:archived_list",
            kwargs={
                "workspace_pk": (
                    self.kwargs[
                        "workspace_pk"
                    ]
                ),
                "board_pk": (
                    self.kwargs[
                        "board_pk"
                    ]
                ),
                "column_pk": (
                    self.kwargs[
                        "column_pk"
                    ]
                ),
            },
        )