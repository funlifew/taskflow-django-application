import json

from django.contrib import messages
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.http import JsonResponse
from django.shortcuts import redirect
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
from apps.columns.mixins import (
    ColumnObjectMixin,
)

from .collaboration import (
    COMMENT_MODERATOR_ROLES,
    TaskCommentService,
)
from .forms import (
    TaskCommentForm,
    TaskDragReorderForm,
    TaskForm,
    TaskMoveForm,
    TaskReorderForm,
    TaskStatusForm,
)
from .mixins import (
    ArchivedTaskObjectMixin,
    TaskCommentObjectMixin,
    TaskObjectMixin,
)
from .models import (
    Task,
    TaskComment,
)
from .reordering import (
    TaskReorderingService,
)
from .selectors import (
    get_archived_tasks,
    get_recent_task_activities,
    get_task_comments,
    get_task_navigation,
    get_visible_task_comments_count,
    serialize_task_columns,
)
from .services import (
    TaskLifecycleService,
)

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
    
    
    def form_valid(
        self,
        form,
    ):
        (
            self.object,
            board,
            column,
        ) = TaskLifecycleService.create(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            actor=self.request.user,
            title=form.cleaned_data["title"],
            description=(
                form.cleaned_data[
                    "description"
                ]
            ),
            priority=(
                form.cleaned_data["priority"]
            ),
            assignee=(
                form.cleaned_data["assignee"]
            ),
            due_at=form.cleaned_data["due_at"],
        )

        messages.success(
            self.request,
            (
                f"Task «{self.object.title}» "
                "با موفقیت ساخته شد."
            ),
        )

        return redirect(
            "boards:detail",
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

        current_user_role = (
            self.get_current_user_role()
        )

        can_write = (
            current_user_role
            in BOARD_WRITE_ROLES
        )

        (
            has_previous_task,
            has_next_task,
        ) = get_task_navigation(
            task=self.object,
        )

        comments = get_task_comments(
            task=self.object,
        )

        activities = (
            get_recent_task_activities(
                task=self.object,
            )
        )

        context.update(
            self.get_task_context(
                task=self.object,
            )
        )

        context.update(
            {
                "can_update_task": can_write,
                "can_archive_task": can_write,
                "can_move_task": can_write,
                "can_reorder_task": can_write,
                "can_move_up": (
                    can_write
                    and has_previous_task
                ),
                "can_move_down": (
                    can_write
                    and has_next_task
                ),
                "can_comment": can_write,
                "can_moderate_comments": (
                    current_user_role
                    in COMMENT_MODERATOR_ROLES
                ),
                "comments": comments,
                "comments_count": (
                    get_visible_task_comments_count(
                        task=self.object,
                    )
                ),
                "activities": activities,
                "comment_form": (
                    TaskCommentForm()
                ),
                "status_form": (
                    TaskStatusForm(
                        instance=self.object,
                    )
                ),
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
            _comment,
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
            self.get_task_context()
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
            _comment,
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
        context = super().get_context_data(
            **kwargs
        )

        context.update(
            self.get_task_context(
                task=self.object,
            )
        )

        return context
    
    
    def form_valid(
    self,
    form,
    ):
        (
            self.object,
            board,
            column,
        ) = TaskLifecycleService.update(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=self.get_task().pk,
            title=form.cleaned_data["title"],
            description=(
                form.cleaned_data["description"]
            ),
            priority=form.cleaned_data["priority"],
            assignee=form.cleaned_data["assignee"],
            due_at=form.cleaned_data["due_at"],
            actor=self.request.user,
        )

        messages.success(
            self.request,
            (
                f"Task «{self.object.title}» "
                "با موفقیت ویرایش شد."
            ),
        )

        return redirect(
            "tasks:detail",
            workspace_pk=board.workspace_id,
            board_pk=board.pk,
            column_pk=column.pk,
            task_pk=self.object.pk,
        )

class TaskStatusUpdateView(
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
        scoped_task = self.get_task()

        form = TaskStatusForm(
            request.POST,
            instance=scoped_task,
        )

        if not form.is_valid():
            messages.error(
                request,
                "وضعیت انتخاب‌شده معتبر نیست.",
            )

            return redirect(
                "tasks:detail",
                workspace_pk=(
                    self.get_workspace().pk
                ),
                board_pk=self.get_board().pk,
                column_pk=(
                    self.get_column().pk
                ),
                task_pk=scoped_task.pk,
            )

        (
            task,
            board,
            column,
        ) = TaskLifecycleService.update_status(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=scoped_task.pk,
            status=form.cleaned_data["status"],
            actor=request.user,
        )

        messages.success(
            request,
            (
                f"وضعیت Task «{task.title}» "
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
            self.get_task_context()
        )
        return context
    
    def form_valid(self, form):
        selected_target_column = (
            form.cleaned_data["target_column"]
        )

        (
            task,
            board,
            _source_column,
            target_column,
        ) = TaskReorderingService.move_to_column(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            source_column_pk=(
                self.get_column().pk
            ),
            target_column_pk=(
                selected_target_column.pk
            ),
            task_pk=self.get_task().pk,
            actor=self.request.user,
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
            self.get_task_context()
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
            _source_column,
            target_column,
        ) = service_method(
            workspace=self.get_workspace(),
            board_pk=self.get_board().pk,
            column_pk=self.get_column().pk,
            task_pk=self.get_task().pk,
            actor=request.user,
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
        return get_archived_tasks(
            column=self.get_column(),
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
        task, board, _column = (
            TaskLifecycleService.archive(
                workspace=self.get_workspace(),
                board_pk=self.get_board().pk,
                column_pk=self.get_column().pk,
                task_pk=self.get_task().pk,
                actor=request.user,
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
                task_pk=self.get_task().pk,
                actor=request.user,
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
            self.get_task_context()
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
            ) = TaskReorderingService.reorder(
                workspace=self.get_workspace(),
                board_pk=board.pk,
                source_column_pk=(
                    source_column.pk
                ),
                target_column_pk=(
                    selected_target_column.pk
                ),
                task_pk=scoped_task.pk,
                target_position=target_position,
                actor=request.user,
            )

        except ValidationError as error:
            return self._error_response(
                self._serialize_validation_error(
                    error
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
                "columns": serialize_task_columns(
                    source_column,
                    target_column,
                ),
            }
        )