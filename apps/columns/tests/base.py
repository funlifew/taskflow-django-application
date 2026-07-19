from apps.boards.tests.base import (
    BoardTestBase,
)

from apps.columns.models import Column


class ColumnTestBase(BoardTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.column = Column.objects.create(
            board=cls.board,
            title="برای انجام",
            position=0,
            created_by=cls.owner,
        )

    def create_column(
        self,
        *,
        board=None,
        title="ستون جدید",
        position=None,
        created_by=None,
        is_archived=False,
    ):
        board = board or self.board

        if position is None:
            position = (
                Column.objects.next_position(
                    board=board,
                )
            )

        if created_by is None:
            created_by = self.owner

        return Column.objects.create(
            board=board,
            title=title,
            position=position,
            created_by=created_by,
            is_archived=is_archived,
        )