from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.workspaces.models import Workspace

# Create your models here.

class Board(TimeStampedModel):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='boards',
    )
    
    title = models.CharField(
        max_length=150,
    )
    
    description = models.TextField(
        blank=True,
        default="",
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_boards',
    )
    
    is_archived = models.BooleanField(
        default=False,
    )
    
    class Meta:
        ordering = (
            '-updated_at',
            '-pk',
        )
        
        indexes = [
            models.Index(
                fields=(
                    'workspace',
                    'is_archived',
                ),
                name='boards_ws_archive_idx',
            ),
        ]
        
        verbose_name = 'برد'
        verbose_name_plural = 'بردها'
    
    def __str__(self):
        return self.title
