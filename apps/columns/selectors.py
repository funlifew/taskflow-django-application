from .models import Column


def get_archived_columns(
    *,
    board,
):
    return (
        Column.objects
        .archived()
        .for_board(board)
        .select_related(
            "board",
            "created_by",
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
    )


def serialize_board_columns(
    *,
    board,
):
    columns = (
        Column.objects
        .active()
        .for_board(board)
        .order_by(
            "position",
            "pk",
        )
        .values(
            "pk",
            "title",
            "position",
        )
    )

    return [
        {
            "id": column["pk"],
            "title": column["title"],
            "position": column[
                "position"
            ],
        }
        for column in columns
    ]