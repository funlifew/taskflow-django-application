from django.shortcuts import get_object_or_404

from apps.boards.mixins import (
    BoardObjectMixin,
)

from .models import Column

class ColumnObjectMixin(
    BoardObjectMixin
):
    column_url_kwarg = 'column_pk'
    pk_url_kwarg = 'column_pk'
    include_archived_columns = False
    
    def get_column_queryset(self):
        queryset = (
            Column.objects
            .filter(
                board=self.get_board(),
            )
            .select_related(
                'board',
                'board__workspace',
                'created_by',
            )
        )
        
        if not self.include_archived_columns:
            queryset = queryset.filter(
                is_archived=False,
            )
        
        return queryset
    
    def get_queryset(self):
        return self.get_column_queryset()
    
    def get_column(self):
        if not hasattr(self, '_column'):
            self._column = get_object_or_404(
                self.get_column_queryset(),
                pk=self.kwargs[
                    self.column_url_kwarg
                ],
            )
        
        return self._column


class ArchivedColumnObjectMixin(
    ColumnObjectMixin
):
    include_archived_columns = True
    
    def get_column_queryset(self):
        return (
            super()
            .get_column_queryset()
            .filter(
                is_archived=True,
            )
        )