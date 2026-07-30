from .models import (
    Task,
    TaskActivity,
    TaskComment,
)

def get_task_navigation(
    *,
    task,
):
    column_tasks = (
        Task.objects
        .active()
        .for_column(task.column)
    )
    
    has_previous = column_tasks.filter(
        position__lt=task.position,
    ).exists()

    has_next = column_tasks.filter(
        position__gt=task.position,
    ).exists()

    return has_previous, has_next


def get_task_comments(
    *,
    task,
):
    return (
        TaskComment.objects
        .for_task(task)
        .select_related(
            'author',
            'deleted_by',
        )
        .order_by(
            'created_at',
            'pk',
        )
    )

def get_visible_task_comments_count(
    *,
    task,
):
    return (
        TaskComment.objects
        .for_task(task)
        .visible()
        .count()
    )

def get_recent_task_activities(
    *,
    task,
    limit=50,
):
    return (
        TaskActivity.objects
        .filter(task=task)
        .select_related('actor')
        .order_by(
            '-created_at',
            '-pk',
        )[:limit]
    )

def get_archived_tasks(
    *,
    column,
):
    return (
        Task.objects
        .archived()
        .for_column(column)
        .select_related(
            'column',
            'assignee',
            'created_by',
        )
        .order_by(
            '-archived_at',
            '-pk',
        )
    )

def serialize_task_columns(
    *columns,
):
    column_map = {
        column.pk: column
        for column in columns
    }
    
    ordered_column_ids = list(
        dict.fromkeys(
            column.pk
            for column in columns
        )
    )
    
    task_ids_by_column = {
        column_id: []
        for column_id in ordered_column_ids
    }
    
    task_rows = (
        Task.objects
        .active()
        .filter(
            column_id__in=ordered_column_ids,
        )
        .order_by(
            'column_id',
            'position',
            'pk',
        )
        .values_list(
            'column_id',
            'pk',
        )
    )
    
    for column_id, task_id in task_rows:
        task_ids_by_column[
            column_id
        ].append(task_id)
        
    
    return [
        {
            "id": column_id,
            "title": (
                column_map[column_id].title
            ),
            "task_ids": (
                task_ids_by_column[
                    column_id
                ]
            ),
            "count": len(
                task_ids_by_column[
                    column_id
                ]
            ),
        }
        for column_id in ordered_column_ids
    ]