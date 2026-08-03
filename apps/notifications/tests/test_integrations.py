from django.test import RequestFactory

from apps.notifications.models import (
    Notification,
)
from apps.tasks.collaboration import (
    TaskCommentService,
)
from apps.tasks.models import Task
from apps.tasks.services import (
    TaskLifecycleService,
)
from apps.workspaces.models import (
    WorkspaceMembership,
)
from apps.workspaces.services import (
    create_workspace_invitation,
    remove_workspace_membership,
    update_workspace_membership_role,
)

from apps.notifications.tests.base import (
    NotificationTestBase,
)


class TaskNotificationIntegrationTests(
    NotificationTestBase
):
    def test_task_create_notifies_assignee(
        self,
    ):
        task, _board, _column = (
            TaskLifecycleService.create(
                workspace=self.workspace,
                board_pk=self.board.pk,
                column_pk=self.column.pk,
                actor=self.owner,
                title="Assigned Task",
                description="",
                priority=(
                    Task.Priority.MEDIUM
                ),
                assignee=self.member,
                due_at=None,
            )
        )

        notification = (
            Notification.objects.get(
                recipient=self.member,
                notification_type=(
                    Notification.Type
                    .TASK_ASSIGNED
                ),
            )
        )

        self.assertEqual(
            notification.metadata[
                "task_id"
            ],
            task.pk,
        )

    def test_actor_is_not_notified_on_self_assignment(
        self,
    ):
        TaskLifecycleService.create(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            actor=self.owner,
            title="Self Assigned",
            description="",
            priority=Task.Priority.MEDIUM,
            assignee=self.owner,
            due_at=None,
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.owner,
            ).exists()
        )

    def test_reassignment_notifies_new_assignee(
        self,
    ):
        TaskLifecycleService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            title=self.task.title,
            description=(
                self.task.description
            ),
            priority=self.task.priority,
            assignee=self.admin,
            due_at=self.task.due_at,
            actor=self.owner,
        )

        notification = (
            Notification.objects.get(
                recipient=self.admin,
                notification_type=(
                    Notification.Type
                    .TASK_REASSIGNED
                ),
            )
        )

        self.assertEqual(
            notification.metadata[
                "previous_assignee_id"
            ],
            self.member.pk,
        )

    def test_unassignment_creates_no_notification(
        self,
    ):
        TaskLifecycleService.update(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            title=self.task.title,
            description=(
                self.task.description
            ),
            priority=self.task.priority,
            assignee=None,
            due_at=self.task.due_at,
            actor=self.owner,
        )

        self.assertFalse(
            Notification.objects.exists()
        )

    def test_status_change_notifies_assignee(
        self,
    ):
        TaskLifecycleService.update_status(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            status=Task.Status.DONE,
            actor=self.owner,
        )

        notification = (
            Notification.objects.get(
                recipient=self.member,
                notification_type=(
                    Notification.Type
                    .TASK_STATUS_CHANGED
                ),
            )
        )

        self.assertEqual(
            notification.metadata[
                "old_status"
            ],
            Task.Status.TODO,
        )
        self.assertEqual(
            notification.metadata[
                "new_status"
            ],
            Task.Status.DONE,
        )

    def test_assignee_does_not_notify_self_on_status_change(
        self,
    ):
        TaskLifecycleService.update_status(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            status=Task.Status.DONE,
            actor=self.member,
        )

        self.assertFalse(
            Notification.objects.exists()
        )

    def test_comment_notifies_creator_and_assignee(
        self,
    ):
        TaskCommentService.create(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=self.task.pk,
            actor=self.admin,
            body="Progress update",
        )

        recipient_ids = set(
            Notification.objects
            .filter(
                notification_type=(
                    Notification.Type
                    .TASK_COMMENTED
                )
            )
            .values_list(
                "recipient_id",
                flat=True,
            )
        )

        self.assertEqual(
            recipient_ids,
            {
                self.owner.pk,
                self.member.pk,
            },
        )

    def test_comment_recipients_are_deduplicated(
        self,
    ):
        task = self.create_task(
            title="Same Recipient",
            assignee=self.owner,
            created_by=self.owner,
        )

        TaskCommentService.create(
            workspace=self.workspace,
            board_pk=self.board.pk,
            column_pk=self.column.pk,
            task_pk=task.pk,
            actor=self.admin,
            body="Comment",
        )

        self.assertEqual(
            Notification.objects.filter(
                recipient=self.owner,
                notification_type=(
                    Notification.Type
                    .TASK_COMMENTED
                ),
            ).count(),
            1,
        )


class WorkspaceNotificationIntegrationTests(
    NotificationTestBase
):
    def setUp(self):
        super().setUp()

        self.request = (
            RequestFactory().get("/")
        )

    def test_existing_user_receives_invitation_notification(
        self,
    ):
        invitation = (
            create_workspace_invitation(
                request=self.request,
                workspace=self.workspace,
                invited_by=self.owner,
                email=(
                    self.invited_user.email
                ),
                role=(
                    WorkspaceMembership
                    .Role
                    .MEMBER
                ),
            )
        )

        notification = (
            Notification.objects.get(
                recipient=(
                    self.invited_user
                ),
                notification_type=(
                    Notification.Type
                    .WORKSPACE_INVITED
                ),
            )
        )

        self.assertEqual(
            notification.metadata[
                "invitation_id"
            ],
            invitation.pk,
        )

    def test_unknown_email_receives_no_in_app_notification(
        self,
    ):
        create_workspace_invitation(
            request=self.request,
            workspace=self.workspace,
            invited_by=self.owner,
            email="unknown@example.com",
            role=(
                WorkspaceMembership
                .Role
                .MEMBER
            ),
        )

        self.assertFalse(
            Notification.objects.exists()
        )

    def test_role_change_notifies_member(
        self,
    ):
        update_workspace_membership_role(
            workspace=self.workspace,
            membership=(
                self.member_membership
            ),
            requester_role=(
                WorkspaceMembership
                .Role
                .OWNER
            ),
            new_role=(
                WorkspaceMembership
                .Role
                .VIEWER
            ),
            actor=self.owner,
        )

        notification = (
            Notification.objects.get(
                recipient=self.member,
                notification_type=(
                    Notification.Type
                    .WORKSPACE_ROLE_CHANGED
                ),
            )
        )

        self.assertEqual(
            notification.metadata[
                "old_role"
            ],
            (
                WorkspaceMembership
                .Role
                .MEMBER
            ),
        )

        self.assertEqual(
            notification.metadata[
                "new_role"
            ],
            (
                WorkspaceMembership
                .Role
                .VIEWER
            ),
        )

    def test_noop_role_change_creates_no_notification(
        self,
    ):
        update_workspace_membership_role(
            workspace=self.workspace,
            membership=(
                self.member_membership
            ),
            requester_role=(
                WorkspaceMembership
                .Role
                .OWNER
            ),
            new_role=(
                WorkspaceMembership
                .Role
                .MEMBER
            ),
            actor=self.owner,
        )

        self.assertFalse(
            Notification.objects.exists()
        )

    def test_removal_notifies_removed_member(
        self,
    ):
        remove_workspace_membership(
            workspace=self.workspace,
            membership=(
                self.member_membership
            ),
            requester_role=(
                WorkspaceMembership
                .Role
                .OWNER
            ),
            actor=self.owner,
        )

        notification = (
            Notification.objects.get(
                recipient=self.member,
                notification_type=(
                    Notification.Type
                    .WORKSPACE_REMOVED
                ),
            )
        )

        self.assertEqual(
            notification.metadata[
                "workspace_id"
            ],
            self.workspace.pk,
        )

        self.assertFalse(
            WorkspaceMembership.objects
            .filter(
                pk=(
                    self.member_membership
                    .pk
                ),
            )
            .exists()
        )