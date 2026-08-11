from decouple import config
from django.core.exceptions import (
    ImproperlyConfigured,
)
from django.utils.csp import CSP

from .base import *


# ---------------------------------------------------------
# Core production settings
# ---------------------------------------------------------

DEBUG = False

# No fallback is allowed in production.
SECRET_KEY = config(
    "SECRET_KEY"
)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS"
)

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must contain at "
        "least one production hostname."
    )


CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
)


# ---------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------

DB_SSLMODE = config(
    "DB_SSLMODE",
    default="prefer",
)

DATABASE_OPTIONS = {}

if DB_SSLMODE:
    DATABASE_OPTIONS[
        "sslmode"
    ] = DB_SSLMODE


DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends.postgresql"
        ),
        "NAME": config(
            "DB_NAME"
        ),
        "USER": config(
            "DB_USER"
        ),
        "PASSWORD": config(
            "DB_PASSWORD"
        ),
        "HOST": config(
            "DB_HOST"
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
        "OPTIONS": (
            DATABASE_OPTIONS
        ),
    },
}

# ---------------------------------------------------------
# Redis
# ---------------------------------------------------------

REDIS_URL = config(
    "REDIS_URL"
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
            default="taskflow",
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
# HTTPS / cookies
# ---------------------------------------------------------

SECURE_SSL_REDIRECT = config(
    "SECURE_SSL_REDIRECT",
    cast=bool,
    default=True,
)

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

# Must remain False because frontend
# JavaScript reads csrftoken.
CSRF_COOKIE_HTTPONLY = False

SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SAMESITE = "Lax"


# ---------------------------------------------------------
# Reverse proxy
# ---------------------------------------------------------

TRUST_PROXY_SSL_HEADER = config(
    "TRUST_PROXY_SSL_HEADER",
    cast=bool,
    default=False,
)

if TRUST_PROXY_SSL_HEADER:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )
    
# ---------------------------------------------------------
# HSTS
# ---------------------------------------------------------

SECURE_HSTS_SECONDS = config(
    "SECURE_HSTS_SECONDS",
    cast=int,
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    config(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        cast=bool,
        default=False,
    )
)

SECURE_HSTS_PRELOAD = config(
    "SECURE_HSTS_PRELOAD",
    cast=bool,
    default=False,
)

# ---------------------------------------------------------
# Additional response security
# ---------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)

X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------
# Content Security Policy
# ---------------------------------------------------------

MIDDLEWARE.insert(
    1,
    (
        "django.middleware.csp."
        "ContentSecurityPolicyMiddleware"
    ),
)

CDN_JSDELIVR = (
    "https://cdn.jsdelivr.net"
)

SECURE_CSP = {
    "default-src": [
        CSP.SELF,
    ],

    "script-src": [
        CSP.SELF,
        CSP.NONCE,
        CDN_JSDELIVR,
    ],

    "style-src": [
        CSP.SELF,
        CSP.UNSAFE_INLINE,
        CDN_JSDELIVR,
    ],

    "font-src": [
        CSP.SELF,
        CDN_JSDELIVR,
        "data:",
    ],

    "img-src": [
        CSP.SELF,
        "data:",
        "blob:",
    ],

    "media-src": [
        CSP.SELF,
    ],

    "connect-src": [
        CSP.SELF,
        CDN_JSDELIVR,
    ],

    "worker-src": [
        CSP.SELF,
        "blob:",
    ],

    "object-src": [
        CSP.NONE,
    ],

    "frame-ancestors": [
        CSP.NONE,
    ],

    "base-uri": [
        CSP.SELF,
    ],

    "form-action": [
        CSP.SELF,
    ],
}

# ---------------------------------------------------------
# Production static files
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

# ---------------------------------------------------------
# Production logging
# ---------------------------------------------------------

DJANGO_LOG_LEVEL = config(
    "DJANGO_LOG_LEVEL",
    default="INFO",
).upper()

APP_LOG_LEVEL = config(
    "APP_LOG_LEVEL",
    default="INFO",
).upper()


LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "production": {
            "format": (
                "{asctime} "
                "{levelname} "
                "{name} "
                "{message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": (
                "logging.StreamHandler"
            ),
            "formatter": (
                "production"
            ),
        },
    },

    "root": {
        "handlers": [
            "console",
        ],
        "level": "WARNING",
    },

    "loggers": {
        "django": {
            "handlers": [
                "console",
            ],
            "level": (
                DJANGO_LOG_LEVEL
            ),
            "propagate": False,
        },

        "django.request": {
            "handlers": [
                "console",
            ],
            "level": "WARNING",
            "propagate": False,
        },

        "django.security": {
            "handlers": [
                "console",
            ],
            "level": "WARNING",
            "propagate": False,
        },

        "apps": {
            "handlers": [
                "console",
            ],
            "level": (
                APP_LOG_LEVEL
            ),
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------
# SMTP email
# ---------------------------------------------------------

EMAIL_BACKEND = (
    "django.core.mail.backends."
    "smtp.EmailBackend"
)

EMAIL_HOST = config(
    "EMAIL_HOST"
)

EMAIL_PORT = config(
    "EMAIL_PORT",
    cast=int,
    default=587,
)

EMAIL_HOST_USER = config(
    "EMAIL_HOST_USER",
    default="",
)

EMAIL_HOST_PASSWORD = config(
    "EMAIL_HOST_PASSWORD",
    default="",
)

EMAIL_USE_TLS = config(
    "EMAIL_USE_TLS",
    cast=bool,
    default=True,
)

EMAIL_USE_SSL = config(
    "EMAIL_USE_SSL",
    cast=bool,
    default=False,
)

if (
    EMAIL_USE_TLS
    and EMAIL_USE_SSL
):
    raise ImproperlyConfigured(
        "EMAIL_USE_TLS and "
        "EMAIL_USE_SSL cannot both "
        "be enabled."
    )

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL"
)

SERVER_EMAIL = config(
    "SERVER_EMAIL",
    default=DEFAULT_FROM_EMAIL,
)

EMAIL_TIMEOUT = config(
    "EMAIL_TIMEOUT",
    cast=int,
    default=10,
)