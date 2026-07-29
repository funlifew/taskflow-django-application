from django.core.exceptions import (
    ValidationError,
    PermissionDenied,
)
from django.contrib import messages
from django.db import transaction
from django.http import (
    Http404,
    JsonResponse,
)
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
    TaskReorderForm,
    TaskDragReorderForm,
    TaskCommentForm,
)
from .mixins import (
    ArchivedTaskObjectMixin,
    TaskObjectMixin,
    TaskCommentObjectMixin,
)
from .models import (
    Task,
    TaskComment,
    TaskActivity,
)
from .services import (
    TaskLifecycleService,
)
from .reordering import (
    TaskReorderingService,
)
from .collaboration import (
    COMMENT_MODERATOR_ROLES,
    TaskCommentService,
)

import json

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
        context = super().get_context_data(
            **kwargs
        )
        
        current_user_role = self.get_current_user_role()
        column = self.get_column()
        
        can_write = current_user_role in BOARD_WRITE_ROLES
        
        has_previous_task = (
            Task.objects
            .active()
            .for_column(column)
            .filter(
                position__lt=self.object.position
            )
            .exists()
        )
        
        has_next_task = (
            Task.objects
            .active()
            .for_column(column)
            .filter(
                position__gt=self.object.position,
            )
            .exists()
        )
        
        comments = (
            TaskComment.objects
            .for_task(self.object)
            .select_related(
                'author',
                'deleted_by',
            )
            .order_by(
                'created_at',
                'pk',
            )
        )
        
        activities = (
            TaskActivity.objects
            .filter(
                task=self.object,
            )
            .select_related(
                'actor',
            )
            .order_by(
                '-created_at',
                '-pk',
            )[:50]
        )
        
        can_comment = can_write
        can_moderate_comments = (
            current_user_role
            in COMMENT_MODERATOR_ROLES
        )
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'column': column,
                'current_user_role': current_user_role,
                'can_update_task': can_write,
                'can_archive_task': can_write,
                'can_move_task': can_write,
                'can_reorder_task': can_write,
                'can_move_up': can_write and has_previous_task,
                'can_move_down': can_write and has_next_task,
                'can_comment': can_comment,
                'can_moderate_comments': can_moderate_comments,
                'comments': comments,
                'comments_count': (
                    comments
                    .visible()
                    .count()
                ),
                'activities': activities,
                'comment_form': TaskCommentForm(),
                'status_form': TaskStatusForm(instance=self.object),
            }
        )
        
        return context

class TaskCommentCreateView(
    TaskObjectMixin,
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
        form = TaskCommentForm(
            request.POST
        )
        
        if not form.is_valid():
            messages.error(
                request,
                (
                    "متن دیدگاه معتبر "
                    "نیست."
                ),
            )
            
            return redirect(
                "tasks:detail",
                workspace_pk=self.get_workspace().pk,
                board_pk=self.get_board().pk,
                column_pk=self.get_column().pk,
                task_pk=self.get_task().pk,
            )
        (
            comment,
            task,
            board,
            column,
        ) = TaskCommentService.create(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=self.get_task().pk,
            actor=request.user,
            body=form.cleaned_data['body'],
        )
        
        messages.success(
            request,
            'دیدگاه ثبت شد.',
        )
        
        return redirect(
            'tasks:detail',
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
            column_pk=column.pk,
            task_pk=task.pk,
        )
        

class TaskCommentUpdateView(
    TaskCommentObjectMixin,
    BoardWriteRequiredMixin,
    UpdateView,
):
    model = TaskComment
    form_class = TaskCommentForm
    
    template_name = 'tasks/comments/update.html'
    context_object_name = 'comment'

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
                'task': self.get_task(),
                'current_user_role': self.get_current_user_role(),
            }
        )
        
        return context
    
    
    def form_valid(
        self,
        form,
    ):
        (
            comment,
            task,
            board,
            column,
        ) = TaskCommentService.update(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=self.get_task().pk,
            comment_pk=self.get_comment().pk,
            actor=self.request.user,
            body=form.cleaned_data['body'],
        )
        
        self.object = comment
        
        messages.success(
            self.request,
            'دیدگاه ویرایش شد.',
        )
        
        return redirect(
            'tasks:detail',
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
            column_pk=column.pk,
            task_pk=task.pk,
        )
    
    def get_object(
        self,
        queryset=None,
    ):
        comment = self.get_comment()
        
        if (
            comment.author_id
            != self.request.user.id
        ):
            raise PermissionDenied(
                "فقط نویسنده دیدگاه "
                "می‌تواند آن را ویرایش کند."
            )
        
        return comment
        
class TaskCommentDeleteView(
    TaskCommentObjectMixin,
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
        (
            comment,
            task,
            board,
            column,
        ) = TaskCommentService.delete(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=self.get_task().pk,
            comment_pk=self.get_comment().pk,
            actor=request.user,
        )
        
        messages.success(
            request,
            "دیدگاه حذف شد.",
        )

        return redirect(
            "tasks:detail",
            workspace_pk=(
                board.workspace_id
            ),
            board_pk=board.pk,
            column_pk=column.pk,
            task_pk=task.pk,
        )

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
        
        editable_fields = (
            'title',
            'description',
            'priority',
            'assignee',
            'due_at',
        )
        
        locked_task = get_object_or_404(
            Task.objects.select_for_update(),
            pk=self.object.pk,
            column=column,
            is_archived=False,
        )
        
        for field_name in editable_fields:
            setattr(
                locked_task,
                field_name,
                form.cleaned_data[field_name],
            )
        
        locked_task.full_clean()
        locked_task.save(
            update_fields=[
                *editable_fields,
                'updated_at',
            ]
        )
        
        self.object = locked_task


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
    
    def form_valid(self, form):
        target_column = form.cleaned_data['target_column']
        
        (
            task,
            board,
            source_column,
            target_column,
        ) = TaskLifecycleService.move(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            source_column_pk=self.get_column().pk,
            target_column_pk=target_column.pk,
            task_pk=self.kwargs['task_pk'],
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

class TaskReorderView(
    TaskObjectMixin,
    BoardWriteRequiredMixin,
    FormView,
):
    form_class = TaskReorderForm
    template_name = (
        "tasks/reorder.html"
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update(
            {
                "board": self.get_board(),
                "task": self.get_task(),
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
                "workspace": (
                    self.get_workspace()
                ),
                "board": self.get_board(),
                "column": (
                    self.get_column()
                ),
                "task": self.get_task(),
                "current_user_role": (
                    self
                    .get_current_user_role()
                ),
            }
        )

        return context

    def form_valid(self, form):
        selected_target_column = (
            form.cleaned_data[
                "target_column"
            ]
        )

        target_position = (
            form.cleaned_data[
                "target_position"
            ]
        )

        (
            task,
            board,
            source_column,
            target_column,
        ) = TaskReorderingService.reorder(
            workspace=(
                self.get_workspace()
            ),
            board_pk=(
                self.get_board().pk
            ),
            source_column_pk=(
                self.get_column().pk
            ),
            target_column_pk=(
                selected_target_column.pk
            ),
            task_pk=(
                self.kwargs[
                    "task_pk"
                ]
            ),
            target_position=(
                target_position
            ),
        )

        messages.success(
            self.request,
            (
                f'Task «{task.title}» '
                f'به ستون '
                f'«{target_column.title}» '
                f'و جایگاه '
                f'{task.position + 1} منتقل شد.'
            ),
        )

        return redirect(
            "tasks:detail",
            workspace_pk=(
                board.workspace_id
            ),
            board_pk=board.pk,
            column_pk=(
                target_column.pk
            ),
            task_pk=task.pk,
        )

class TaskRelativeMoveView(
    TaskObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    service_method_name = None
    success_message = None
    
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        service_method = getattr(TaskReorderingService, self.service_method_name)
        
        (
            task,
            board,
            source_column,
            target_column,
        ) = service_method(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=self.kwargs['task_pk'],
        )
        
        messages.success(
            request,
            self.success_message.format(
                title=task.title,
            ),
        )
        
        return redirect(
            "tasks:detail",
            workspace_pk=(
                board.workspace_id
            ),
            board_pk=board.pk,
            column_pk=(
                target_column.pk
            ),
            task_pk=task.pk,
        )

class TaskMoveUpView(
    TaskRelativeMoveView,
):
    service_method_name = 'move_up'
    
    success_message = (
        'Task «{title}» یک جایگاه '
        "به بالا منتقل شد."
    )

class TaskMoveDownView(
    TaskRelativeMoveView,
):
    service_method_name = "move_down"

    success_message = (
        'Task «{title}» یک جایگاه '
        "به پایین منتقل شد."
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
                '-archived_at',
                '-pk',
            )
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        current_user_role = self.get_current_user_role()
        
        context.update(
            {
                'workspace': self.get_workspace(),
                'board': self.get_board(),
                'column': self.get_column(),
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
    
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        task, board, column = (
            TaskLifecycleService.archive(
                workspace=self.get_workspace(),
                board_pk=self.get_board().pk,
                column_pk=self.get_column().pk,
                task_pk=self.kwargs['task_pk'],
            )
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


    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        task, board, column = (
            TaskLifecycleService.restore(
                workspace=self.get_workspace(),
                board_pk=self.get_board().pk,
                column_pk=self.get_column().pk,
                task_pk=self.kwargs['task_pk'],
            )
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
        
        return context
    
    def form_valid(self, form):
        task_title, board, column = (
            TaskLifecycleService.delete_archived(
                workspace=self.get_workspace(),
                board_pk=self.get_board().pk,
                column_pk=self.get_column().pk,
                task_pk=self.object.pk,
            )
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

class TaskDragReorderView(
    TaskObjectMixin,
    BoardWriteRequiredMixin,
    View,
):
    http_method_names = [
        'post',
    ]
    
    @staticmethod
    def _error_response(
        errors,
        *,
        status=400
    ):
        return JsonResponse(
            {
                'ok': False,
                'errors': errors,
            },
            status=status,
        )
    
    @classmethod
    def _parse_payload(
        cls,
        request,
    ):
        try:
            raw_body = (
                request.body
                .decode('utf-8')
                .strip()
            )
        except UnicodeDecodeError:
            return (
                None,
                {
                    "__all__": [
                        (
                            "بدنه درخواست "
                            "قابل خواندن نیست."
                        ),
                    ],
                },
            )
        
        if not raw_body:
            return {}, None
        
        try:
            payload = json.loads(
                raw_body
            )
        except json.JSONDecodeError:
            return (
                None,
                {
                    "__all__": [
                        (
                            "ساختار JSON "
                            "درخواست معتبر نیست."
                        ),
                    ],
                },
            )
        
        if not isinstance(
            payload,
            dict,
        ):
            return (
                None,
                {
                    "__all__": [
                        (
                            "بدنه درخواست باید "
                            "یک JSON object باشد."
                        ),
                    ],
                },
            )
        
        return payload, None
    
    @staticmethod
    def _serializer_form_errors(
        form,
    ):
        return {
            field_name: [
                str(error)
                for error in error_list
            ]
            for (
                field_name,
                error_list,
            ) in form.errors.items()
        }
    
    @staticmethod
    def _serialize_validation_error(
        error,
    ):
        try:
            message_dict = (
                error.message_dict
            )
        except AttributeError:
            return {
                "__all__": [
                    str(message)
                    for message in (
                        error.messages
                    )
                ],
            }

        return {
            field_name: [
                str(message)
                for message in messages
            ]
            for (
                field_name,
                messages,
            ) in message_dict.items()
        }
    
    @staticmethod
    def _serialize_columns(
        *columns,
    ):
        column_map = {
            column.pk: column
            for column in columns
        }
        
        ordered_column_ids = list(
            dict.fromkeys(
                column.pk
                for column in columns
            )
        )
        
        task_ids_by_column = {
            column_id: []
            for column_id in ordered_column_ids
        }
        
        task_rows = (
            Task.objects
            .active()
            .filter(
                column_id__in=ordered_column_ids,
            )
            .order_by(
                'column_id',
                'position',
                'pk',
            )
            .values_list(
                'column_id',
                'pk',
            )
        )
        
        for (
            column_id,
            task_id,
        ) in task_rows:
            task_ids_by_column[column_id].append(task_id)
        
        return [
            {
                "id": column_id,
                "title": (
                    column_map[
                        column_id
                    ].title
                ),
                "task_ids": (
                    task_ids_by_column[
                        column_id
                    ]
                ),
                "count": len(
                    task_ids_by_column[
                        column_id
                    ]
                ),
            }
            for column_id in (
                ordered_column_ids
            )
        ]
    
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        board = self.get_board()
        source_column = self.get_column()
        
        scoped_task = self.get_task()
        
        (
            payload,
            payload_errors,
        ) = self._parse_payload(
            request
        )
        
        if payload_errors:
            return self._error_response(
                payload_errors,
            )
        
        form = TaskDragReorderForm(
            data=payload,
            board=board,
        )
        
        if not form.is_valid():
            return self._error_response(
                self._serializer_form_errors(
                    form
                ),
            )
        
        selected_target_column = form.cleaned_data['target_column']
        target_position = form.cleaned_data['target_position']

        try:
            (
                task,
                board,
                source_column,
                target_column,
            ) = (
                TaskReorderingService
                .reorder(
                    workspace=self.get_workspace(),
                    board_pk=board.pk,
                    source_column_pk=source_column.pk,
                    target_column_pk=selected_target_column.pk,
                    task_pk=scoped_task.pk,
                    target_position=target_position,
                )
            )
        except ValidationError as error:
            return self._error_response(
                (
                    self
                    ._serialize_validation_error(
                        error
                    )
                ),
            )
        
        
        reorder_url = reverse(
            'tasks:drag_reorder',
            kwargs={
                'workspace_pk': board.workspace_id,
                'board_pk': board.pk,
                'column_pk': target_column.pk,
                'task_pk': task.pk,
            }
        )
        
        return JsonResponse(
            {
                "ok": True,
                "message": (
                    f'Task «{task.title}» '
                    "با موفقیت جابه‌جا شد."
                ),
                "task": {
                    "id": task.pk,
                    "column_id": (
                        task.column_id
                    ),
                    "position": (
                        task.position
                    ),
                    "reorder_url": (
                        reorder_url
                    ),
                },
                "columns": (
                    self._serialize_columns(
                        source_column,
                        target_column,
                    )
                ),
            }
        )