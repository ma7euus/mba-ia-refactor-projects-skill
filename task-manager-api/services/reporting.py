"""Pure report construction from model aggregates."""

from services.task_rules import VALID_STATUSES
from utils.helpers import calculate_percentage


def task_statistics(aggregate):
    return {
        'total': aggregate['total'],
        **{status: aggregate[status] for status in VALID_STATUSES},
        'overdue': aggregate['overdue'],
        'completion_rate': calculate_percentage(aggregate['done'], aggregate['total']),
    }


def user_statistics(user, aggregate):
    statistics = task_statistics(aggregate)
    statistics['total_tasks'] = statistics.pop('total')
    statistics['high_priority'] = aggregate['high_priority']
    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': statistics,
    }


def summary_report(aggregate, counts, overdue_tasks, productivity, now):
    users = []
    for row in productivity:
        item = dict(row)
        item['completion_rate'] = calculate_percentage(item['completed_tasks'], item['total_tasks'])
        users.append(item)
    overdue = [{
        'id': task.id, 'title': task.title, 'due_date': str(task.due_date),
        'days_overdue': (now - task.due_date).days,
    } for task in overdue_tasks]
    return {
        'generated_at': str(now),
        'overview': {'total_tasks': aggregate['total'], **dict(counts)},
        'tasks_by_status': {status: aggregate[status] for status in VALID_STATUSES},
        'tasks_by_priority': {
            name: aggregate[f'priority_{priority}']
            for priority, name in enumerate(('critical', 'high', 'medium', 'low', 'minimal'), 1)
        },
        'overdue': {'count': len(overdue), 'tasks': overdue},
        'recent_activity': {
            'tasks_created_last_7_days': aggregate['recent_created'],
            'tasks_completed_last_7_days': aggregate['recent_done'],
        },
        'user_productivity': users,
    }
