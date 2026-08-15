from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import (
    override_settings,
)
from django.utils import timezone

from apps.dashboard.cache import (
    get_user_namespace,
    invalidate_board_progress_cache,
    invalidate_dashboard_metrics,
    invalidate_user_dashboard_cache,
    invalidate_workspace_progress_cache,
)
from apps.dashboard.metrics import (
    get_board_progress,
    get_user_dashboard_summary,
    get_user_task_progress,
    get_workspace_progress,
)
from apps.notifications.models import (
    Notification,
)
from apps.tasks.models import (
    Task,
)
from apps.tasks.services import (
    TaskLifecycleService,
)
from apps.tasks.tests.base import (
    TaskTestBase,
)


CACHE_SETTINGS = {
    "DASHBOARD_CACHE_ENABLED": True,
    "DASHBOARD_SUMMARY_CACHE_TTL": 60,
    "DASHBOARD_PROGRESS_CACHE_TTL": 300,
    "DASHBOARD_CACHE_LOCK_TTL": 1,
    "DASHBOARD_CACHE_WAIT_ATTEMPTS": 0,
    "DASHBOARD_CACHE_WAIT_INTERVAL": 0,
}


@override_settings(
    **CACHE_SETTINGS
)
class DashboardCacheTests(
    TaskTestBase
):
    def setUp(self):
        super().setUp()

        cache.clear()

    def tearDown(self):
        cache.clear()

        super().tearDown()

    def test_user_progress_is_cached(
        self,
    ):
        first = (
            get_user_task_progress(
                user=self.member,
            )
        )

        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        second = (
            get_user_task_progress(
                user=self.member,
            )
        )

        self.assertEqual(
            second,
            first,
        )

    def test_user_progress_refreshes_after_invalidation(
        self,
    ):
        first = (
            get_user_task_progress(
                user=self.member,
            )
        )

        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        invalidate_user_dashboard_cache(
            self.member.pk
        )

        second = (
            get_user_task_progress(
                user=self.member,
            )
        )

        self.assertNotEqual(
            first,
            second,
        )

        self.assertEqual(
            second["total"],
            2,
        )

        self.assertEqual(
            second["completed"],
            1,
        )

    def test_workspace_progress_refreshes_after_namespace_invalidation(
        self,
    ):
        first = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        stale = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        self.assertEqual(
            first,
            stale,
        )

        invalidate_workspace_progress_cache(
            self.workspace.pk
        )

        refreshed = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        self.assertEqual(
            refreshed["total"],
            2,
        )

        self.assertEqual(
            refreshed["completed"],
            1,
        )

    def test_board_progress_refreshes_after_namespace_invalidation(
        self,
    ):
        first = (
            get_board_progress(
                user=self.member,
                board=self.board,
            )
        )

        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        stale = (
            get_board_progress(
                user=self.member,
                board=self.board,
            )
        )

        self.assertEqual(
            first,
            stale,
        )

        invalidate_board_progress_cache(
            self.board.pk
        )

        refreshed = (
            get_board_progress(
                user=self.member,
                board=self.board,
            )
        )

        self.assertEqual(
            refreshed["total"],
            2,
        )

        self.assertEqual(
            refreshed["completed"],
            1,
        )

    def test_notifications_are_not_stale_when_summary_core_is_cached(
        self,
    ):
        now = timezone.now()

        first = (
            get_user_dashboard_summary(
                user=self.member,
                now=now,
            )
        )

        self.assertEqual(
            first[
                "unread_notifications_count"
            ],
            0,
        )

        Notification.objects.create(
            recipient=self.member,
            actor=self.owner,
            notification_type=(
                Notification.Type
                .TASK_ASSIGNED
            ),
            title="New notification",
            is_read=False,
            read_at=None,
        )

        second = (
            get_user_dashboard_summary(
                user=self.member,
                now=now,
            )
        )

        self.assertEqual(
            second[
                "unread_notifications_count"
            ],
            1,
        )

    def test_due_date_change_service_invalidates_user_summary(
        self,
    ):
        now = timezone.now()

        first = (
            get_user_dashboard_summary(
                user=self.member,
                now=now,
            )
        )

        self.assertEqual(
            first[
                "overdue_tasks_count"
            ],
            0,
        )

        with (
            self.captureOnCommitCallbacks(
                execute=True
            )
        ):
            (
                TaskLifecycleService
                .update(
                    workspace=(
                        self.workspace
                    ),
                    board_pk=(
                        self.board.pk
                    ),
                    column_pk=(
                        self.column.pk
                    ),
                    task_pk=(
                        self.task.pk
                    ),
                    title=(
                        self.task.title
                    ),
                    description=(
                        self.task.description
                    ),
                    priority=(
                        self.task.priority
                    ),
                    assignee=(
                        self.member
                    ),
                    due_at=(
                        now
                        - timedelta(days=1)
                    ),
                    actor=(
                        self.owner
                    ),
                )
            )

        second = (
            get_user_dashboard_summary(
                user=self.member,
                now=now,
            )
        )

        self.assertEqual(
            second[
                "overdue_tasks_count"
            ],
            1,
        )

    def test_status_change_service_invalidates_progress_namespaces(
        self,
    ):
        first_user_progress = (
            get_user_task_progress(
                user=self.member,
            )
        )

        first_workspace_progress = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        first_board_progress = (
            get_board_progress(
                user=self.member,
                board=self.board,
            )
        )

        self.assertEqual(
            first_user_progress[
                "completed"
            ],
            0,
        )

        with (
            self.captureOnCommitCallbacks(
                execute=True
            )
        ):
            (
                TaskLifecycleService
                .update_status(
                    workspace=(
                        self.workspace
                    ),
                    board_pk=(
                        self.board.pk
                    ),
                    column_pk=(
                        self.column.pk
                    ),
                    task_pk=(
                        self.task.pk
                    ),
                    status=(
                        Task.Status.DONE
                    ),
                    actor=(
                        self.owner
                    ),
                )
            )

        user_progress = (
            get_user_task_progress(
                user=self.member,
            )
        )

        workspace_progress = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        board_progress = (
            get_board_progress(
                user=self.member,
                board=self.board,
            )
        )

        self.assertEqual(
            user_progress[
                "completed"
            ],
            1,
        )

        self.assertEqual(
            workspace_progress[
                "completed"
            ],
            1,
        )

        self.assertEqual(
            board_progress[
                "completed"
            ],
            1,
        )

    @patch(
        (
            "apps.core.caching."
            "cache.get"
        ),
        side_effect=RuntimeError(
            "Redis unavailable"
        ),
    )
    def test_cache_failure_falls_back_to_live_calculation(
        self,
        mocked_get,
    ):
        progress = (
            get_user_task_progress(
                user=self.member,
            )
        )

        self.assertEqual(
            progress["total"],
            1,
        )

        self.assertEqual(
            progress["completed"],
            0,
        )

    def test_user_namespace_change_invalidates_workspace_progress_for_that_user(
        self,
    ):
        first = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        self.create_task(
            title="Done",
            assignee=self.member,
            status=Task.Status.DONE,
        )

        invalidate_user_dashboard_cache(
            self.member.pk
        )

        refreshed = (
            get_workspace_progress(
                user=self.member,
                workspace=self.workspace,
            )
        )

        self.assertNotEqual(
            first,
            refreshed,
        )
        
    
    def test_workspace_participant_invalidation_rotates_all_user_namespaces(
        self,
    ):
        owner_before = (
            get_user_namespace(
                self.owner.pk
            )
        )

        member_before = (
            get_user_namespace(
                self.member.pk
            )
        )

        invalidate_dashboard_metrics(
            participant_workspace_ids=(
                self.workspace.pk,
            ),
        )

        owner_after = (
            get_user_namespace(
                self.owner.pk
            )
        )

        member_after = (
            get_user_namespace(
                self.member.pk
            )
        )

        self.assertNotEqual(
            owner_before,
            owner_after,
        )

        self.assertNotEqual(
            member_before,
            member_after,
        )