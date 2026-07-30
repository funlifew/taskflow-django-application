from django.shortcuts import get_object_or_404
from apps.columns.mixins import ColumnObjectMixin
from .models import Task, TaskComment


class TaskObjectMixin(
    ColumnObjectMixin
):
    task_url_kwarg = 'task_pk'
    pk_url_kwarg = 'task_pk'
    include_archived_tasks = False
    
    
    def get_task_queryset(self):
        queryset = (
            Task.objects
            .filter(
                column=self.get_column(),
            )
            .select_related(
                'column',
                'column__board',
                'column__board__workspace',
                'assignee',
                'created_by',
            )
        )
        
        if not self.include_archived_tasks:
            queryset = queryset.filter(
                is_archived=False,
            )
        
        return queryset
    
    def get_queryset(self):
        return self.get_task_queryset()
    
    def get_task(self):
        if not hasattr(self, "_task"):
            self._task = get_object_or_404(
                self.get_task_queryset(),
                pk=self.kwargs[self.task_url_kwarg],
            )
        
        return self._task

    def get_task_context(
        self,
        *,
        task=None,
    ):
        if task is None:
            task = self.get_task()
        
        return {
            "workspace": self.get_workspace(),
            "board": self.get_board(),
            "column": self.get_column(),
            "task": task,
            "current_user_role": (
                self.get_current_user_role()
            ),
        }


class ArchivedTaskObjectMixin(
    TaskObjectMixin
):
    include_archived_tasks = True
    
    def get_task_queryset(self):
        return (
            super()
            .get_task_queryset()
            .filter(
                is_archived=True,
            )
        )

class TaskCommentObjectMixin(
    TaskObjectMixin
):
    comment_url_kwarg = 'comment_pk'

    pk_url_kwarg = 'comment_pk'

    include_deleted_comments = False
    
    def get_comment_queryset(
        self,
    ):
        queryset = (
            TaskComment.objects
            .for_task(
                self.get_task()
            )
            .select_related(
                "author",
                'deleted_by',
                'task',
            )
        )
        
        if not (
            self
            .include_deleted_comments
        ):
            queryset = queryset.visible()
        
        return queryset
    
    def get_queryset(self):
        return (
            self.get_comment_queryset()
        )
    
    def get_comment(self):
        if not hasattr(
            self,
            '_comment',
        ):
            self._comment = (
                get_object_or_404(
                    self
                    .get_comment_queryset(),
                    pk=self.kwargs[
                        self
                        .comment_url_kwarg
                    ],
                )
            )

        return self._comment