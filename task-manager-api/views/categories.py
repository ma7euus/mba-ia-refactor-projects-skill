def serialize_category(category, task_count=None):
    result = {
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'color': category.color,
        'created_at': str(category.created_at),
    }
    if task_count is not None:
        result['task_count'] = task_count
    return result
