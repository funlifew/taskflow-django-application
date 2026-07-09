from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from random import randint
import os

def user_directory_path(instance, filename):
    return os.path.join('avatars', instance.user.username, filename)

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
        null=True,
        blank=True
    )
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']
    
    def __str__(self):
        return self.username