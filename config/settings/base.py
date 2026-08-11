from pathlib import Path
from decouple import config

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

APPS_DIR = BASE_DIR / 'apps'

def env_list(
    name,
    *,
    default="",
):
    """
    Read a comma-separated environment variable
    and normalize it to a list of non-empty values.
    """
    
    raw_value = config(
        name,
        default=default,
    )
    
    return [
        value.strip()
        for value in raw_value.split(",")
        if value.strip()
    ]
    
# ---------------------------------------------------------
# Core
# ---------------------------------------------------------

# Development-only fallback.
# production.py replaces this with a mandatory env value.
SECRET_KEY = config(
    "SECRET_KEY",
    default='django-insecure-taskflow-development-only-key',
)

# Safe default.
# development.py explicitly enables DEBUG.
DEBUG = False

ALLOWED_HOSTS = []

# ---------------------------------------------------------
# Applications
# ---------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.workspaces',
    'apps.boards',
    'apps.columns',
    'apps.dashboard',
    'apps.tasks',
    'apps.notifications',
]

INSTALLED_APPS = [
    *DJANGO_APPS,
    *LOCAL_APPS,
]

# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------

MIDDLEWARE = [
    (
        "django.middleware.security."
        "SecurityMiddleware"
    ),
    (
        "django.contrib.sessions.middleware."
        "SessionMiddleware"
    ),
    (
        "django.middleware.common."
        "CommonMiddleware"
    ),
    (
        "django.middleware.csrf."
        "CsrfViewMiddleware"
    ),
    (
        "django.contrib.auth.middleware."
        "AuthenticationMiddleware"
    ),
    (
        "django.contrib.messages.middleware."
        "MessageMiddleware"
    ),
    (
        "django.middleware.clickjacking."
        "XFrameOptionsMiddleware"
    ),
]

# ---------------------------------------------------------
# URLs / templates / application
# ---------------------------------------------------------

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        "BACKEND": (
            'django.template.backends.django.'
            'DjangoTemplates'
        ),
        "DIRS": [
            BASE_DIR / 'templates',
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                 (
                    "django.template."
                    "context_processors.request"
                ),
                (
                    "django.contrib.auth."
                    "context_processors.auth"
                ),
                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
                (
                    "django.template."
                    "context_processors.csp"
                ),
                (
                    "apps.notifications."
                    "context_processors."
                    "notifications_context"
                ),
            ],
        },
    },
]

WSGI_APPLICATION = (
    'config.wsgi.application'
)

ASGI_APPLICATION = (
    'config.asgi.application'
)

# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

# Development-safe default.
# production.py replaces this with PostgreSQL.
DATABASES = {
    'default': {
        'ENGINE': (
            'django.db.backends.sqlite3'
        ),
        "NAME": (
            BASE_DIR / 'db.sqlite3'
        ),
    },
}

# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "NumericPasswordValidator"
        ),
    },
]

# ---------------------------------------------------------
# Internationalization
# ---------------------------------------------------------

LANGUAGE_CODE = 'fa-ir'

TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True

# ---------------------------------------------------------
# Static / media
# ---------------------------------------------------------

STATIC_URL = '/static/'

STATIC_ROOT = (
    BASE_DIR / "staticfiles"
)

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"

MEDIA_ROOT = (
    BASE_DIR / "media"
)

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
            "storage.StaticFilesStorage"
        ),
    },
}

# ---------------------------------------------------------
# Cache
# ---------------------------------------------------------

# Base/test-safe cache.
# Production requires Redis explicitly.
CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends."
            "locmem.LocMemCache"
        ),
        "LOCATION": (
            "taskflow-default-cache"
        ),
        "TIMEOUT": 300,
    },
}


# ---------------------------------------------------------
# Authentication redirects
# ---------------------------------------------------------

LOGIN_URL = 'accounts:login'

LOGIN_REDIRECT_URL = (
    'dashboard:dashboard'
)

# ---------------------------------------------------------
# Email defaults
# ---------------------------------------------------------


DEFAULT_FROM_EMAIL = (
    "TaskFlow <noreply@localhost>"
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_TIMEOUT = 10

# ---------------------------------------------------------
# Session / CSRF baseline
# ---------------------------------------------------------


SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SAMESITE = "Lax"

# Important:
# Task/Column drag-and-drop currently reads
# csrftoken from document.cookie.
CSRF_COOKIE_HTTPONLY = False

# ---------------------------------------------------------
# General browser security
# ---------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)

X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------
# Upload limits
# ---------------------------------------------------------

# Files larger than this threshold are streamed
# to temporary storage instead of being kept
# entirely in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = (
    2_621_440
)