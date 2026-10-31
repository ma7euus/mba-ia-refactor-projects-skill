"""Public task representations; no implicit ORM column dumping."""


def serialize_task(task, overdue=False, names=False, compact=False):
    result = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'created_at': str(task.created_at),
        'due_date': str(task.due_date) if task.due_date else None,
    }
    if not compact:
        result.update({
            'user_id': task.user_id,
            'category_id': task.category_id,
            'updated_at': str(task.updated_at),
            'tags': task.tags.split(',') if task.tags else [],
        })
    if overdue or compact:
        result['overdue'] = task.is_overdue()
    if names:
        result['user_name'] = task.user.name if task.user else None
        result['category_name'] = task.category.name if task.category else None
    return result
