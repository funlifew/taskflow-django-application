from django.shortcuts import get_object_or_404
from apps.columns.mixins import ColumnObjectMixin
from .models import Task


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