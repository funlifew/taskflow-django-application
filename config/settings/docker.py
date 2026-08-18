from decouple import config

from .base import *


# ---------------------------------------------------------
# Core
# ---------------------------------------------------------

DEBUG = False

SECRET_KEY = config(
    "SECRET_KEY",
    default=(
        "django-insecure-"
        "taskflow-docker-local-only"
    ),
)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=(
        "localhost,"
        "127.0.0.1"
    ),
)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=(
        "http://localhost:8000,"
        "http://127.0.0.1:8000"
    ),
)


# ---------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends."
            "postgresql"
        ),
        "NAME": config(
            "DB_NAME",
            default="taskflow",
        ),
        "USER": config(
            "DB_USER",
            default="taskflow",
        ),
        "PASSWORD": config(
            "DB_PASSWORD",
            default="taskflow",
        ),
        "HOST": config(
            "DB_HOST",
            default="db",
        ),
        "PORT": config(
            "DB_PORT",
            cast=int,
            default=5432,
        ),
        "CONN_MAX_AGE": config(
            "DB_CONN_MAX_AGE",
            cast=int,
            default=60,
        ),
        "CONN_HEALTH_CHECKS": True,
    },
}


# ---------------------------------------------------------
# Redis
# ---------------------------------------------------------

REDIS_URL = config(
    "REDIS_URL",
    default="redis://redis:6379/1",
)

CACHES = {
    "default": {
        "BACKEND": (
            "django_redis.cache."
            "RedisCache"
        ),
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": config(
            "CACHE_KEY_PREFIX",
            default="taskflow-docker",
        ),
        "TIMEOUT": config(
            "CACHE_TIMEOUT",
            cast=int,
            default=300,
        ),
        "OPTIONS": {
            "CLIENT_CLASS": (
                "django_redis.client."
                "DefaultClient"
            ),
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    },
}


# ---------------------------------------------------------
# Email
# ---------------------------------------------------------

EMAIL_BACKEND = (
    "django.core.mail.backends."
    "console.EmailBackend"
)


# ---------------------------------------------------------
# Local Docker HTTP
# ---------------------------------------------------------

SECURE_SSL_REDIRECT = False

SESSION_COOKIE_SECURE = False

CSRF_COOKIE_SECURE = False


# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles."
            "storage."
            "ManifestStaticFilesStorage"
        ),
    },
}