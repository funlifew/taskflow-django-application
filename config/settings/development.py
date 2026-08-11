from decouple import config

from .base import *


DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
    *env_list(
        "DEV_ALLOWED_HOSTS",
    ),
]


# ---------------------------------------------------------
# Development tooling
# ---------------------------------------------------------

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE.insert(
    0,
    (
        "debug_toolbar.middleware."
        "DebugToolbarMiddleware"
    ),
)

INTERNAL_IPS = [
    "127.0.0.1",
]


if config(
    "ENABLE_REDISBOARD",
    cast=bool,
    default=False,
):
    INSTALLED_APPS += [
        "redisboard",
    ]


# ---------------------------------------------------------
# Email
# ---------------------------------------------------------

EMAIL_BACKEND = (
    "django.core.mail.backends."
    "console.EmailBackend"
)


# ---------------------------------------------------------
# Optional Redis during development
# ---------------------------------------------------------

if config(
    "DEV_USE_REDIS",
    cast=bool,
    default=False,
):
    REDIS_URL = config(
        "REDIS_URL",
        default=(
            "redis://localhost:6379/1"
        ),
    )

    CACHES = {
        "default": {
            "BACKEND": (
                "django_redis.cache."
                "RedisCache"
            ),
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": (
                "taskflow-dev"
            ),
            "TIMEOUT": 300,
            "OPTIONS": {
                "CLIENT_CLASS": (
                    "django_redis.client."
                    "DefaultClient"
                ),
                "SOCKET_CONNECT_TIMEOUT": 3,
                "SOCKET_TIMEOUT": 3,
            },
        },
    }