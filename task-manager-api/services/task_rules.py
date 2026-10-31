"""Task and category policies, independent of HTTP and persistence."""

from datetime import datetime
import re

from errors import AppError
from services.text_validation import utf8_text
from utils.helpers import utc_now


VALID_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
FINISHED_STATUSES = ('done', 'cancelled')
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
DEFAULT_COLOR = '#000000'
MAX_ID = 2**63 - 1
MAX_TAGS_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 10000


def is_overdue(due_date, status, now=None):
    return bool(due_date and due_date < (now or utc_now()) and status not in FINISHED_STATUSES)


def require_object(data):
    if not isinstance(data, dict) or not data:
        raise AppError('Dados inválidos', 400)
    return data


def positive_id(value, field, nullable=True):
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_ID:
        raise AppError(f'{field} deve ser um inteiro positivo', 400)
    return value


def task_values(data, creating=False):
    require_object(data)
    values = {}
    if creating or 'title' in data:
        title = data.get('title')
        if not isinstance(title, str) or not title.strip():
            raise AppError('Título é obrigatório', 400)
        if len(title) < MIN_TITLE_LENGTH:
            raise AppError('Título muito curto', 400)
        if len(title) > MAX_TITLE_LENGTH:
            raise AppError('Título muito longo', 400)
        values['title'] = utf8_text(title)
    if creating or 'description' in data:
        description = data.get('description', '')
        if description is not None and (
            not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH
        ):
            raise AppError('Descrição inválida', 400)
        values['description'] = utf8_text(description) if description is not None else None
    if creating or 'status' in data:
        status = data.get('status', 'pending')
        if status not in VALID_STATUSES:
            raise AppError('Status inválido', 400)
        values['status'] = status
    if creating or 'priority' in data:
        priority = data.get('priority', DEFAULT_PRIORITY)
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise AppError('Prioridade deve ser um inteiro', 400)
        if not MIN_PRIORITY <= priority <= MAX_PRIORITY:
            raise AppError('Prioridade deve ser entre 1 e 5', 400)
        values['priority'] = priority
    for field in ('user_id', 'category_id'):
        if creating or field in data:
            values[field] = positive_id(data.get(field), field)
    if creating or 'due_date' in data:
        value = data.get('due_date')
        if value is None or value == '':
            values['due_date'] = None
        else:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise AppError('Formato de data inválido. Use YYYY-MM-DD', 400)
            try:
                values['due_date'] = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                raise AppError('Formato de data inválido. Use YYYY-MM-DD', 400) from None
    if creating or 'tags' in data:
        tags = data.get('tags')
        if isinstance(tags, list):
            if not all(isinstance(tag, str) for tag in tags):
                raise AppError('Tags devem conter apenas textos', 400)
            tags = ','.join(tags)
        if tags is not None and (not isinstance(tags, str) or len(tags) > MAX_TAGS_LENGTH):
            raise AppError('Tags inválidas', 400)
        values['tags'] = utf8_text(tags) if tags is not None else None
    return values


def search_filters(filters):
    result = {}
    query = filters.get('q', '')
    if not isinstance(query, str) or len(query) > MAX_DESCRIPTION_LENGTH:
        raise AppError('Busca inválida', 400)
    if query:
        result['q'] = utf8_text(query)
    status = filters.get('status', '')
    if status:
        if status not in VALID_STATUSES:
            raise AppError('Status inválido', 400)
        result['status'] = status
    for field in ('priority', 'user_id'):
        value = filters.get(field, '')
        if value == '':
            continue
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]+', value):
            raise AppError(f'Filtro {field} inválido', 400)
        try:
            number = int(value)
        except ValueError:
            raise AppError(f'Filtro {field} inválido', 400) from None
        if field == 'priority' and not MIN_PRIORITY <= number <= MAX_PRIORITY:
            raise AppError('Prioridade deve ser entre 1 e 5', 400)
        result[field] = positive_id(number, field, nullable=False)
    return result


def category_values(data, creating=False):
    require_object(data)
    values = {}
    if creating or 'name' in data:
        name = data.get('name')
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise AppError('Nome inválido', 400)
        values['name'] = utf8_text(name)
    if creating or 'description' in data:
        description = data.get('description', '')
        if description is not None and (not isinstance(description, str) or len(description) > 300):
            raise AppError('Descrição inválida', 400)
        values['description'] = utf8_text(description) if description is not None else None
    if creating or 'color' in data:
        color = data.get('color', DEFAULT_COLOR)
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise AppError('Cor inválida. Use #RRGGBB', 400)
        values['color'] = color
    return values
