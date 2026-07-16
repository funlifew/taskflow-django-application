from apps.workspaces.tests.base import WorkspaceTestBase

from apps.boards.models import Board


class BoardTestBase(WorkspaceTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.board = Board.objects.create(
            workspace=cls.workspace,
            title="TaskFlow Development",
            description="Main development board",
            created_by=cls.owner,
        )

    def create_board(
        self,
        *,
        workspace=None,
        title="Another Board",
        description="",
        created_by=None,
        is_archived=False,
    ):
        if created_by is None:
            created_by = self.owner

        return Board.objects.create(
            workspace=workspace or self.workspace,
            title=title,
            description=description,
            created_by=created_by,
            is_archived=is_archived,
        )