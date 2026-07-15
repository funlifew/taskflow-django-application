from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from random import randint
from uuid import uuid4
from pathlib import Path
import os

def user_directory_path(instance, filename):
    extension = Path(filename).suffix.lower()
    user_id = instance.pk or "new"

    return (
        f"avatars/{user_id}/"
        f"{uuid4().hex}{extension}"
    )

def create_random_avatar():
    random_number = randint(1, 10)
    return f'avatars/default/{random_number}.png'

# Create your models here.

class User(AbstractUser):
    last_name = models.CharField(_('نام خانوادگی'), null=False, blank=False)
    email = models.EmailField(_("ایمیل"), unique=True)
    email_verified = models.BooleanField(_("تایید ایمیل"), default=False)

    
    avatar = models.ImageField(
        upload_to=user_directory_path,
        default=create_random_avatar
    )
    bio = models.TextField(
        blank=True,
        default='',
    )
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='accounts_user_email_ci_unique',
            ),
        ]
    
    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
            
        super().save(*args, **kwargs)