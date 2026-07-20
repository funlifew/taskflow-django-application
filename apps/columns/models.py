from django.conf import settings
from django.db import models
from django.db.models import Max, Q


from apps.boards.models import Board
from apps.core.models import TimeStampedModel

# Create your models here.

class ColumnQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            is_archived=False,
        )
    
    def archived(self):
        return self.filter(
            is_archived=True,
        )
    
    def for_board(self, board):
        return self.filter(
            board=board,
        )

class ColumnManager(
    models.Manager.from_queryset(
        ColumnQuerySet
    )
):
    def next_position(self, *, board):
        max_position = (
            self.get_queryset()
            .active()
            .for_board(board)
            .aggregate(
                value=Max('position')
            )['value']
        )
        
        if max_position is None:
            return 0
        
        return max_position + 1
    
    def normalize_positions(
        self,
        *,
        board,
    ):
        columns = list(
            self.get_queryset()
            .select_for_update()
            .active()
            .for_board(board)
            .order_by(
                'position',
                'pk'
            )
        )
        
        for expected_position, column in enumerate(columns):
            if column.position == expected_position:
                continue
            
            column.position = expected_position
            column.save(
                update_fields=[
                    'position',
                    'updated_at',
                ]
            )

class Column(TimeStampedModel):
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='columns',
    )
    title = models.CharField(
        max_length=100,
    )
    position = models.PositiveIntegerField()
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_columns',
    )
    
    is_archived = models.BooleanField(
        default=False
    )
    
    objects = ColumnManager()
    
    class Meta:
        ordering = (
            'position',
            'pk',
        )
        
        constraints = [
            models.UniqueConstraint(
                fields=(
                    'board',
                    'position',
                ),
                condition=Q(
                    is_archived=False,
                ),
                name=(
                    'columns_active_board_pos_unique'
                ),
            ),
        ]
        
        indexes = [
            models.Index(
                fields=(
                    'board',
                    'is_archived',
                    'position',
                ),
                name=(
                    'columns_board_state_pos_idx'
                ),
            ),
        ]
        
        verbose_name = "ستون"
        verbose_name_plural = "ستون‌ها"
    
    def __str__(self):
        return self.title