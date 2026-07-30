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