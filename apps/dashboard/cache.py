import logging
import uuid

from collections.abc import (
    Callable,
    Iterable,
)

from django.conf import settings
from django.db import transaction

from apps.core.caching import (
    cache_get_or_compute,
    safe_cache_get,
    safe_cache_set,
)
from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
)


logger = logging.getLogger(
    __name__
)


CACHE_SCHEMA_VERSION = "v1"

DEFAULT_NAMESPACE = "0"


# ---------------------------------------------------------
# Namespace keys
# ---------------------------------------------------------


def user_namespace_key(
    user_id: int,
) -> str:
    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"user:{user_id}:namespace"
    )


def workspace_namespace_key(
    workspace_id: int,
) -> str:
    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"workspace:{workspace_id}:namespace"
    )


def board_namespace_key(
    board_id: int,
) -> str:
    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"board:{board_id}:namespace"
    )


# ---------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------


def _get_namespace(
    key: str,
) -> str:
    hit, value = (
        safe_cache_get(
            key
        )
    )

    if not hit:
        return DEFAULT_NAMESPACE

    return str(value)


def _new_namespace() -> str:
    return uuid.uuid4().hex[:12]


def _invalidate_namespace(
    key: str,
) -> bool:
    return safe_cache_set(
        key,
        _new_namespace(),
        timeout=None,
    )


def get_user_namespace(
    user_id: int,
) -> str:
    return _get_namespace(
        user_namespace_key(
            user_id
        )
    )


def get_workspace_namespace(
    workspace_id: int,
) -> str:
    return _get_namespace(
        workspace_namespace_key(
            workspace_id
        )
    )


def get_board_namespace(
    board_id: int,
) -> str:
    return _get_namespace(
        board_namespace_key(
            board_id
        )
    )


# ---------------------------------------------------------
# Data keys
# ---------------------------------------------------------


def user_dashboard_summary_key(
    *,
    user_id: int,
    due_soon_days: int,
) -> str:
    user_version = (
        get_user_namespace(
            user_id
        )
    )

    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"user:{user_id}:"
        f"summary:"
        f"u{user_version}:"
        f"due:{due_soon_days}"
    )


def user_task_progress_key(
    *,
    user_id: int,
) -> str:
    user_version = (
        get_user_namespace(
            user_id
        )
    )

    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"user:{user_id}:"
        f"task-progress:"
        f"u{user_version}"
    )


def workspace_progress_key(
    *,
    user_id: int,
    workspace_id: int,
) -> str:
    user_version = (
        get_user_namespace(
            user_id
        )
    )

    workspace_version = (
        get_workspace_namespace(
            workspace_id
        )
    )

    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"user:{user_id}:"
        f"workspace:{workspace_id}:"
        f"progress:"
        f"u{user_version}:"
        f"w{workspace_version}"
    )


def board_progress_key(
    *,
    user_id: int,
    board_id: int,
) -> str:
    user_version = (
        get_user_namespace(
            user_id
        )
    )

    board_version = (
        get_board_namespace(
            board_id
        )
    )

    return (
        f"dashboard:{CACHE_SCHEMA_VERSION}:"
        f"user:{user_id}:"
        f"board:{board_id}:"
        f"progress:"
        f"u{user_version}:"
        f"b{board_version}"
    )


# ---------------------------------------------------------
# Cache policy
# ---------------------------------------------------------


def _cache_enabled() -> bool:
    return bool(
        getattr(
            settings,
            "DASHBOARD_CACHE_ENABLED",
            True,
        )
    )


def _cached(
    *,
    key: str,
    factory: Callable,
    timeout: int,
):
    if not _cache_enabled():
        return factory()

    return cache_get_or_compute(
        key=key,
        factory=factory,
        timeout=timeout,
        lock_timeout=getattr(
            settings,
            "DASHBOARD_CACHE_LOCK_TTL",
            5,
        ),
        wait_attempts=getattr(
            settings,
            (
                "DASHBOARD_"
                "CACHE_WAIT_ATTEMPTS"
            ),
            4,
        ),
        wait_interval=getattr(
            settings,
            (
                "DASHBOARD_"
                "CACHE_WAIT_INTERVAL"
            ),
            0.02,
        ),
    )


def get_cached_user_dashboard_summary(
    *,
    user_id: int,
    due_soon_days: int,
    factory: Callable,
):
    return _cached(
        key=(
            user_dashboard_summary_key(
                user_id=user_id,
                due_soon_days=(
                    due_soon_days
                ),
            )
        ),
        factory=factory,
        timeout=getattr(
            settings,
            (
                "DASHBOARD_"
                "SUMMARY_CACHE_TTL"
            ),
            60,
        ),
    )


def get_cached_user_task_progress(
    *,
    user_id: int,
    factory: Callable,
):
    return _cached(
        key=(
            user_task_progress_key(
                user_id=user_id,
            )
        ),
        factory=factory,
        timeout=getattr(
            settings,
            (
                "DASHBOARD_"
                "PROGRESS_CACHE_TTL"
            ),
            300,
        ),
    )


def get_cached_workspace_progress(
    *,
    user_id: int,
    workspace_id: int,
    factory: Callable,
):
    return _cached(
        key=(
            workspace_progress_key(
                user_id=user_id,
                workspace_id=(
                    workspace_id
                ),
            )
        ),
        factory=factory,
        timeout=getattr(
            settings,
            (
                "DASHBOARD_"
                "PROGRESS_CACHE_TTL"
            ),
            300,
        ),
    )


def get_cached_board_progress(
    *,
    user_id: int,
    board_id: int,
    factory: Callable,
):
    return _cached(
        key=(
            board_progress_key(
                user_id=user_id,
                board_id=board_id,
            )
        ),
        factory=factory,
        timeout=getattr(
            settings,
            (
                "DASHBOARD_"
                "PROGRESS_CACHE_TTL"
            ),
            300,
        ),
    )


# ---------------------------------------------------------
# Participant discovery
# ---------------------------------------------------------


def get_workspace_participant_user_ids(
    workspace_id: int,
) -> tuple[int, ...]:
    """
    Return all users who currently have
    access to the workspace.

    Owner membership may already exist
    in memberships, so IDs are deduplicated.
    """

    user_ids: set[int] = set()

    owner_id = (
        Workspace.objects
        .filter(
            pk=workspace_id
        )
        .values_list(
            "owner_id",
            flat=True,
        )
        .first()
    )

    if owner_id is not None:
        user_ids.add(
            owner_id
        )

    membership_user_ids = (
        WorkspaceMembership.objects
        .filter(
            workspace_id=workspace_id
        )
        .values_list(
            "user_id",
            flat=True,
        )
    )

    user_ids.update(
        membership_user_ids
    )

    return tuple(
        sorted(user_ids)
    )


# ---------------------------------------------------------
# Immediate invalidation
# ---------------------------------------------------------


def invalidate_user_dashboard_cache(
    user_id: int,
) -> bool:
    return _invalidate_namespace(
        user_namespace_key(
            user_id
        )
    )


def invalidate_workspace_progress_cache(
    workspace_id: int,
) -> bool:
    return _invalidate_namespace(
        workspace_namespace_key(
            workspace_id
        )
    )


def invalidate_board_progress_cache(
    board_id: int,
) -> bool:
    return _invalidate_namespace(
        board_namespace_key(
            board_id
        )
    )


def invalidate_dashboard_metrics(
    *,
    user_ids: Iterable[int] = (),
    workspace_ids: Iterable[int] = (),
    board_ids: Iterable[int] = (),
    participant_workspace_ids: (
        Iterable[int]
    ) = (),
) -> None:
    """
    Invalidate metric namespaces.

    participant_workspace_ids means:
    invalidate the user-level Dashboard
    namespace for every current participant
    of those workspaces.
    """

    normalized_user_ids = {
        int(user_id)
        for user_id in user_ids
        if user_id is not None
    }

    normalized_workspace_ids = {
        int(workspace_id)
        for workspace_id
        in workspace_ids
        if workspace_id is not None
    }

    normalized_board_ids = {
        int(board_id)
        for board_id in board_ids
        if board_id is not None
    }

    for workspace_id in (
        participant_workspace_ids
    ):
        if workspace_id is None:
            continue

        normalized_user_ids.update(
            get_workspace_participant_user_ids(
                int(workspace_id)
            )
        )

    for user_id in (
        normalized_user_ids
    ):
        invalidate_user_dashboard_cache(
            user_id
        )

    for workspace_id in (
        normalized_workspace_ids
    ):
        invalidate_workspace_progress_cache(
            workspace_id
        )

    for board_id in (
        normalized_board_ids
    ):
        invalidate_board_progress_cache(
            board_id
        )


# ---------------------------------------------------------
# Transaction-safe invalidation
# ---------------------------------------------------------


def schedule_dashboard_cache_invalidation(
    *,
    user_ids: Iterable[int] = (),
    workspace_ids: Iterable[int] = (),
    board_ids: Iterable[int] = (),
    participant_workspace_ids: (
        Iterable[int]
    ) = (),
) -> None:
    """
    Register cache invalidation after the
    surrounding database transaction has
    successfully committed.

    A rolled-back mutation must never
    invalidate otherwise valid cache data.
    """

    captured_user_ids = tuple(
        user_id
        for user_id in user_ids
        if user_id is not None
    )

    captured_workspace_ids = tuple(
        workspace_id
        for workspace_id in workspace_ids
        if workspace_id is not None
    )

    captured_board_ids = tuple(
        board_id
        for board_id in board_ids
        if board_id is not None
    )

    captured_participant_workspace_ids = (
        tuple(
            workspace_id
            for workspace_id
            in participant_workspace_ids
            if workspace_id is not None
        )
    )

    transaction.on_commit(
        lambda: invalidate_dashboard_metrics(
            user_ids=(
                captured_user_ids
            ),
            workspace_ids=(
                captured_workspace_ids
            ),
            board_ids=(
                captured_board_ids
            ),
            participant_workspace_ids=(
                captured_participant_workspace_ids
            ),
        )
    )