import logging
import time
from collections.abc import (
    Callable,
)

from django.core.cache import (
    cache,
)

logger = logging.getLogger(
    __name__
)


_CACHE_MISS = object()


def safe_cache_get(
    key: str,
) -> tuple[
    bool,
    object | None,
]:
    """
    Read a cache value without allowing
    cache backend failures to break the
    application.

    Returns:

        (True, value)
            cache hit

        (False, None)
            cache miss or unavailable cache
    """

    try:
        value = cache.get(
            key,
            _CACHE_MISS,
        )

    except Exception:
        logger.exception(
            (
                "Cache read failed. "
                "key=%s"
            ),
            key,
        )

        return False, None

    if value is _CACHE_MISS:
        return False, None

    return True, value


def safe_cache_set(
    key: str,
    value,
    *,
    timeout,
) -> bool:
    """
    Store a cache value using fail-open
    behavior.
    """

    try:
        cache.set(
            key,
            value,
            timeout=timeout,
        )

    except Exception:
        logger.exception(
            (
                "Cache write failed. "
                "key=%s"
            ),
            key,
        )

        return False

    return True


def safe_cache_add(
    key: str,
    value,
    *,
    timeout,
) -> bool | None:
    """
    Attempt an atomic cache.add().

    True:
        lock/value was created.

    False:
        key already existed.

    None:
        cache backend was unavailable.
    """

    try:
        return cache.add(
            key,
            value,
            timeout=timeout,
        )

    except Exception:
        logger.exception(
            (
                "Cache add failed. "
                "key=%s"
            ),
            key,
        )

        return None


def cache_get_or_compute[T](
    *,
    key: str,
    factory: Callable[[], T],
    timeout: int,
    lock_timeout: int = 5,
    wait_attempts: int = 4,
    wait_interval: float = 0.02,
) -> T:
    """
    Return a cached value or calculate it.

    A short population lock reduces the
    dogpile effect when multiple requests
    miss the same expensive cache entry.

    Cache failures always fail open:
    the value is calculated directly.
    """

    hit, cached_value = (
        safe_cache_get(
            key
        )
    )

    if hit:
        return cached_value

    lock_key = (
        f"{key}:populate-lock"
    )

    lock_acquired = (
        safe_cache_add(
            lock_key,
            True,
            timeout=lock_timeout,
        )
    )

    if lock_acquired is None:
        return factory()

    if lock_acquired:
        value = factory()

        safe_cache_set(
            key,
            value,
            timeout=timeout,
        )

        return value

    for _ in range(
        max(
            wait_attempts,
            0,
        )
    ):
        if wait_interval > 0:
            time.sleep(
                wait_interval
            )

        hit, cached_value = (
            safe_cache_get(
                key
            )
        )

        if hit:
            return cached_value

    return factory()