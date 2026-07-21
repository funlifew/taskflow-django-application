from django.http import HttpResponse
from django.test import override_settings
from django.urls import path, reverse
from django.views import View

from apps.boards.mixins import (
    BoardDeleteRequiredMixin,
    BoardObjectMixin,
    BoardReadRequiredMixin,
    BoardWriteRequiredMixin,
)
from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
)

from apps.boards.tests.base import BoardTestBase


class BoardReadProbeView(
    BoardReadRequiredMixin,
    View,
):
    def get(self, request, *args, **kwargs):
        return HttpResponse("read allowed")


class BoardWriteProbeView(
    BoardWriteRequiredMixin,
    View,
):
    def get(self, request, *args, **kwargs):
        return HttpResponse("write allowed")


class BoardDeleteProbeView(
    BoardDeleteRequiredMixin,
    View,
):
    def get(self, request, *args, **kwargs):
        return HttpResponse("delete allowed")


class BoardObjectProbeView(
    BoardObjectMixin,
    BoardReadRequiredMixin,
    View,
):
    def get(self, request, *args, **kwargs):
        board = self.get_board()

        return HttpResponse(
            f"board:{board.pk}"
        )


class ArchivedBoardObjectProbeView(
    BoardObjectMixin,
    BoardReadRequiredMixin,
    View,
):
    include_archived_boards = True

    def get(self, request, *args, **kwargs):
        board = self.get_board()

        return HttpResponse(
            f"board:{board.pk}"
        )


urlpatterns = [
    path(
        (
            "workspaces/<int:workspace_pk>/"
            "boards/read-probe/"
        ),
        BoardReadProbeView.as_view(),
        name="board_read_probe",
    ),
    path(
        (
            "workspaces/<int:workspace_pk>/"
            "boards/write-probe/"
        ),
        BoardWriteProbeView.as_view(),
        name="board_write_probe",
    ),
    path(
        (
            "workspaces/<int:workspace_pk>/"
            "boards/delete-probe/"
        ),
        BoardDeleteProbeView.as_view(),
        name="board_delete_probe",
    ),
    path(
        (
            "workspaces/<int:workspace_pk>/"
            "boards/<int:board_pk>/object-probe/"
        ),
        BoardObjectProbeView.as_view(),
        name="board_object_probe",
    ),
    path(
        (
            "workspaces/<int:workspace_pk>/"
            "boards/<int:board_pk>/"
            "archived-object-probe/"
        ),
        ArchivedBoardObjectProbeView.as_view(),
        name="archived_board_object_probe",
    ),
]


@override_settings(
    ROOT_URLCONF=__name__,
    LOGIN_URL="/login/",
)
class BoardPermissionMixinTests(BoardTestBase):
    def get_read_url(self):
        return reverse(
            "board_read_probe",
            kwargs={
                "workspace_pk": self.workspace.pk,
            },
        )

    def get_write_url(self):
        return reverse(
            "board_write_probe",
            kwargs={
                "workspace_pk": self.workspace.pk,
            },
        )

    def get_delete_url(self):
        return reverse(
            "board_delete_probe",
            kwargs={
                "workspace_pk": self.workspace.pk,
            },
        )

    def get_object_url(
        self,
        *,
        workspace=None,
        board=None,
    ):
        return reverse(
            "board_object_probe",
            kwargs={
                "workspace_pk": (
                    workspace or self.workspace
                ).pk,
                "board_pk": (
                    board or self.board
                ).pk,
            },
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            self.get_read_url()
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertRedirects(
            response,
            (
                f"/login/?next="
                f"{self.get_read_url()}"
            ),
            fetch_redirect_response=False,
        )

    def test_all_workspace_roles_can_read_boards(self):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
            self.viewer,
        ]

        for user in allowed_users:
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(
                    self.get_read_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_outsider_cannot_read_boards(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            self.get_read_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_admin_and_member_can_write(self):
        allowed_users = [
            self.owner,
            self.admin,
            self.member,
        ]

        for user in allowed_users:
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(
                    self.get_write_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_viewer_cannot_write(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            self.get_write_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_cannot_write(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            self.get_write_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_and_admin_can_delete(self):
        allowed_users = [
            self.owner,
            self.admin,
        ]

        for user in allowed_users:
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(
                    self.get_delete_url()
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.client.logout()

    def test_member_cannot_delete(self):
        self.client.force_login(self.member)

        response = self.client.get(
            self.get_delete_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_viewer_cannot_delete(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            self.get_delete_url()
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_accessible_board_can_be_retrieved(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            self.get_object_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            f"board:{self.board.pk}",
        )

    def test_board_from_another_workspace_returns_404(
        self
    ):
        other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=self.outsider,
        )

        WorkspaceMembership.objects.create(
            workspace=other_workspace,
            user=self.outsider,
            role=WorkspaceMembership.Role.OWNER,
        )

        other_board = self.create_board(
            workspace=other_workspace,
            title="Other Board",
            created_by=self.outsider,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_object_url(
                workspace=self.workspace,
                board=other_board,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_archived_board_returns_404_by_default(
        self
    ):
        archived_board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_object_url(
                board=archived_board,
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_archived_board_can_be_included_explicitly(
        self
    ):
        archived_board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )

        self.client.force_login(self.owner)

        url = reverse(
            "archived_board_object_probe",
            kwargs={
                "workspace_pk": self.workspace.pk,
                "board_pk": archived_board.pk,
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_archived_workspace_returns_404(self):
        self.workspace.is_archived = True
        self.workspace.save(
            update_fields=[
                "is_archived",
                "updated_at",
            ]
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.get_read_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )
    
    def test_workspace_owner_role_is_detected_directly(
        self
    ):
        self.client.force_login(self.owner)

        view = BoardReadProbeView()
        view.request = type(
            "Request",
            (),
            {
                "user": self.owner,
            },
        )()
        view.kwargs = {
            "workspace_pk": self.workspace.pk,
        }

        self.assertEqual(
            view.get_current_user_role(),
            WorkspaceMembership.Role.OWNER,
        )