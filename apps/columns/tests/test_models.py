from django.contrib.auth import (
    get_user_model,
)
from django.core.exceptions import (
    ValidationError,
)
from django.db import (
    IntegrityError,
    transaction,
)

from apps.columns.models import Column

from apps.columns.tests.base import ColumnTestBase


User = get_user_model()


class ColumnModelTests(ColumnTestBase):
    def test_column_belongs_to_board(self):
        self.assertEqual(
            self.column.board,
            self.board,
        )

        self.assertIn(
            self.column,
            self.board.columns.all(),
        )

    def test_column_defaults_to_active(self):
        self.assertFalse(
            self.column.is_archived
        )

    def test_column_creator_is_stored(self):
        self.assertEqual(
            self.column.created_by,
            self.owner,
        )

    def test_column_string_representation(self):
        self.assertEqual(
            str(self.column),
            self.column.title,
        )

    def test_columns_are_ordered_by_position(self):
        second_column = self.create_column(
            title="در حال انجام",
            position=1,
        )

        third_column = self.create_column(
            title="انجام‌شده",
            position=2,
        )

        columns = list(
            Column.objects
            .for_board(self.board)
        )

        self.assertEqual(
            columns,
            [
                self.column,
                second_column,
                third_column,
            ],
        )

    def test_active_queryset_returns_only_active(
        self
    ):
        archived_column = self.create_column(
            title="آرشیوشده",
            position=5,
            is_archived=True,
        )

        active_columns = (
            Column.objects.active()
        )

        self.assertIn(
            self.column,
            active_columns,
        )
        self.assertNotIn(
            archived_column,
            active_columns,
        )

    def test_archived_queryset_returns_only_archived(
        self
    ):
        archived_column = self.create_column(
            title="آرشیوشده",
            position=5,
            is_archived=True,
        )

        archived_columns = (
            Column.objects.archived()
        )

        self.assertIn(
            archived_column,
            archived_columns,
        )
        self.assertNotIn(
            self.column,
            archived_columns,
        )

    def test_next_position_returns_zero_for_empty_board(
        self
    ):
        other_board = self.create_board(
            title="Empty Board",
        )

        position = (
            Column.objects.next_position(
                board=other_board,
            )
        )

        self.assertEqual(
            position,
            0,
        )

    def test_next_position_appends_after_last_active(
        self
    ):
        self.create_column(
            title="در حال انجام",
            position=1,
        )

        self.create_column(
            title="انجام‌شده",
            position=2,
        )

        position = (
            Column.objects.next_position(
                board=self.board,
            )
        )

        self.assertEqual(
            position,
            3,
        )

    def test_next_position_ignores_archived_columns(
        self
    ):
        self.create_column(
            title="آرشیوشده",
            position=50,
            is_archived=True,
        )

        position = (
            Column.objects.next_position(
                board=self.board,
            )
        )

        self.assertEqual(
            position,
            1,
        )

    def test_active_positions_must_be_unique_per_board(
        self
    ):
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                self.create_column(
                    title="Duplicate Position",
                    position=0,
                )

    def test_archived_columns_may_keep_duplicate_positions(
        self
    ):
        first_archived = self.create_column(
            title="Archived One",
            position=8,
            is_archived=True,
        )

        second_archived = self.create_column(
            title="Archived Two",
            position=8,
            is_archived=True,
        )

        self.assertEqual(
            first_archived.position,
            second_archived.position,
        )

    def test_same_position_is_allowed_in_different_boards(
        self
    ):
        other_board = self.create_board(
            title="Other Board",
        )

        other_column = self.create_column(
            board=other_board,
            title="Other Todo",
            position=0,
        )

        self.assertEqual(
            other_column.position,
            self.column.position,
        )

    def test_position_cannot_be_negative(self):
        column = Column(
            board=self.board,
            title="Invalid Column",
            position=-1,
            created_by=self.owner,
        )

        with self.assertRaises(
            ValidationError
        ):
            column.full_clean()

    def test_deleting_board_deletes_columns(self):
        other_board = self.create_board(
            title="Temporary Board",
        )

        column = self.create_column(
            board=other_board,
            title="Temporary Column",
            position=0,
        )

        column_pk = column.pk

        other_board.delete()

        self.assertFalse(
            Column.objects.filter(
                pk=column_pk,
            ).exists()
        )

    def test_deleting_creator_keeps_column(self):
        creator = User.objects.create_user(
            username="column-creator",
            first_name="Column",
            last_name="Creator",
            email="column-creator@example.com",
            password="StrongPassword123!",
        )

        column = self.create_column(
            title="Creator Column",
            position=7,
            created_by=creator,
        )

        creator.delete()

        column.refresh_from_db()

        self.assertIsNone(
            column.created_by
        )

    def test_column_has_timestamps(self):
        self.assertIsNotNone(
            self.column.created_at
        )
        self.assertIsNotNone(
            self.column.updated_at
        )