from apps.boards.models import Board

from apps.boards.tests.base import BoardTestBase


class BoardModelTests(BoardTestBase):
    def test_board_string_representation(self):
        self.assertEqual(
            str(self.board),
            "TaskFlow Development",
        )

    def test_board_belongs_to_workspace(self):
        self.assertEqual(
            self.board.workspace,
            self.workspace,
        )

    def test_workspace_can_access_its_boards(self):
        self.assertIn(
            self.board,
            self.workspace.boards.all(),
        )

    def test_board_tracks_creator(self):
        self.assertEqual(
            self.board.created_by,
            self.owner,
        )

    def test_user_can_access_created_boards(self):
        self.assertIn(
            self.board,
            self.owner.created_boards.all(),
        )

    def test_board_is_not_archived_by_default(self):
        board = Board.objects.create(
            workspace=self.workspace,
            title="Default Board",
            created_by=self.owner,
        )

        self.assertFalse(board.is_archived)

    def test_board_description_is_empty_by_default(self):
        board = Board.objects.create(
            workspace=self.workspace,
            title="Board Without Description",
            created_by=self.owner,
        )

        self.assertEqual(
            board.description,
            "",
        )

    def test_board_creator_can_be_null(self):
        board = Board.objects.create(
            workspace=self.workspace,
            title="Imported Board",
            created_by=None,
        )

        self.assertIsNone(board.created_by)

    def test_deleting_creator_does_not_delete_board(self):
        board = self.create_board(
            title="Member Board",
            created_by=self.member,
        )

        board_pk = board.pk

        self.member.delete()

        board.refresh_from_db()

        self.assertTrue(
            Board.objects.filter(pk=board_pk).exists()
        )
        self.assertIsNone(board.created_by)

    def test_deleting_workspace_deletes_its_boards(self):
        board_pk = self.board.pk

        self.workspace.delete()

        self.assertFalse(
            Board.objects.filter(pk=board_pk).exists()
        )

    def test_board_inherits_timestamps(self):
        self.assertIsNotNone(self.board.created_at)
        self.assertIsNotNone(self.board.updated_at)

    def test_board_default_ordering(self):
        self.assertEqual(
            Board._meta.ordering,
            (
                "-updated_at",
                "-pk",
            ),
        )

    def test_archived_board_can_be_stored(self):
        board = self.create_board(
            title="Archived Board",
            is_archived=True,
        )

        self.assertTrue(board.is_archived)