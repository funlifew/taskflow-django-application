import os

bind = os.getenv(
    "GUNICORN_BIND",
    "127.0.0.1:8000",
)

workers = int(
    os.getenv(
        "GUNICORN_WORKERS",
        "2",
    )
)

worker_class = "sync"

timeout = int(
    os.getenv(
        "GUNICORN_TIMEOUT",
        "30",
    )
)

graceful_timeout = int(
    os.getenv(
        "GUNICORN_GRACEFUL_TIMEOUT",
        "30",
    )
)

keepalive = int(
    os.getenv(
        "GUNICORN_KEEPALIVE",
        "5",
    )
)

max_requests = int(
    os.getenv(
        "GUNICORN_MAX_REQUESTS",
        "1000",
    )
)

max_requests_jitter = int(
    os.getenv(
        "GUNICORN_MAX_REQUESTS_JITTER",
        "100",
    )
)

accesslog = "-"

errorlog = "-"

capture_output = True

loglevel = os.getenv(
    "GUNICORN_LOG_LEVEL",
    "info",
)

forwarded_allow_ips = os.getenv(
    "GUNICORN_FORWARDED_ALLOW_IPS",
    "127.0.0.1",
)

preload_app = False