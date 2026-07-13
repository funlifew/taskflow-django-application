from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel

# Create your models here.

class Workspace(TimeStampedModel):
    name = models.CharField(
        max_length=150
    )
