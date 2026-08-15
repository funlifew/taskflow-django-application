from .base import *


SECRET_KEY = (
    "taskflow-test-secret-key-"
    "not-for-production"
)

DEBUG = False

ALLOWED_HOSTS = [
    "testserver",
    "localhost",
    "127.0.0.1",
]


# ---------------------------------------------------------
# Test database
# ---------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends.sqlite3"
        ),
        "NAME": ":memory:",
    },
}


# ---------------------------------------------------------
# Test cache
# ---------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends."
            "locmem.LocMemCache"
        ),
        "LOCATION": (
            "taskflow-test-cache"
        ),
    },
}

# Application-level caching is disabled by
# default for existing unit tests.
#
# Dedicated cache tests explicitly enable it.
DASHBOARD_CACHE_ENABLED = False

# ---------------------------------------------------------
# Test email
# ---------------------------------------------------------

EMAIL_BACKEND = (
    "django.core.mail.backends."
    "locmem.EmailBackend"
)


# ---------------------------------------------------------
# Test static files
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
            "storage.StaticFilesStorage"
        ),
    },
}


MEDIA_ROOT = (
    BASE_DIR / "test-media"
)