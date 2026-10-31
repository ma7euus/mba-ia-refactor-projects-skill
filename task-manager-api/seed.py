"""Explicit demo fixtures. Never run implicitly during application startup."""

import argparse
from datetime import timedelta
import os

from app import create_app
from database import db
from errors import AppError
from models.auth_session import AuthSession
from models.category import Category
from models.task import Task
from models.user import User
from services.user_validation import validate_password
from utils.helpers import utc_now


def seed_data(application, password, reset=False):
    validate_password(password)
    with application.app_context():
        db.create_all()
        populated = any(db.session.scalar(db.select(db.func.count()).select_from(model))
                        for model in (User, Category, Task))
        if populated and not reset:
            raise ValueError('Banco contém dados; use --reset somente em banco descartável.')
        try:
            if reset:
                for model in (AuthSession, Task, User, Category):
                    db.session.execute(db.delete(model))
            users = [
                User(name='João Silva', email='joao@email.com', role='admin'),
                User(name='Maria Santos', email='maria@email.com', role='user'),
                User(name='Pedro Oliveira', email='pedro@email.com', role='manager'),
            ]
            for user in users:
                user.set_password(password)
            categories = [
                Category(name='Backend', description='Tarefas de backend', color='#3498db'),
                Category(name='Frontend', description='Tarefas de frontend', color='#2ecc71'),
                Category(name='DevOps', description='Tarefas de infraestrutura', color='#e74c3c'),
                Category(name='Bug', description='Correção de bugs', color='#e67e22'),
            ]
            db.session.add_all([*users, *categories])
            db.session.flush()
            u1, u2, u3 = users
            c1, c2, c3, c4 = categories
            tasks_data = [
                {'title': 'Implementar autenticação JWT', 'description': 'Adicionar autenticação real com JWT', 'status': 'pending', 'priority': 1, 'user_id': u1.id, 'category_id': c1.id, 'due_date': utc_now() - timedelta(days=3)},
                {'title': 'Criar tela de login', 'description': 'Tela de login responsiva', 'status': 'in_progress', 'priority': 2, 'user_id': u2.id, 'category_id': c2.id, 'due_date': utc_now() + timedelta(days=5)},
                {'title': 'Configurar CI/CD', 'description': 'Pipeline com GitHub Actions', 'status': 'done', 'priority': 2, 'user_id': u3.id, 'category_id': c3.id, 'tags': 'devops,ci,github'},
                {'title': 'Corrigir bug no filtro de busca', 'description': 'Filtro não funciona com caracteres especiais', 'status': 'pending', 'priority': 1, 'user_id': u1.id, 'category_id': c4.id, 'due_date': utc_now() - timedelta(days=1)},
                {'title': 'Adicionar paginação na API', 'description': 'Endpoints retornam todos os registros', 'status': 'pending', 'priority': 3, 'user_id': u1.id, 'category_id': c1.id, 'due_date': utc_now() + timedelta(days=10)},
                {'title': 'Escrever testes unitários', 'description': 'Cobertura mínima de 80%', 'status': 'pending', 'priority': 2, 'user_id': u2.id, 'category_id': c1.id},
                {'title': 'Documentar API com Swagger', 'description': 'Gerar documentação automática', 'status': 'cancelled', 'priority': 4, 'user_id': u3.id, 'category_id': c1.id},
                {'title': 'Refatorar models', 'description': 'Melhorar organização dos models', 'status': 'in_progress', 'priority': 3, 'user_id': u2.id, 'category_id': c1.id, 'tags': 'refactor,tech-debt'},
                {'title': 'Configurar monitoramento', 'description': 'Prometheus + Grafana', 'status': 'pending', 'priority': 4, 'user_id': u3.id, 'category_id': c3.id, 'due_date': utc_now() + timedelta(days=20)},
                {'title': 'Melhorar validações de input', 'description': 'Usar marshmallow ou pydantic', 'status': 'pending', 'priority': 3, 'user_id': u1.id, 'category_id': c1.id, 'tags': 'improvement,validation'},
            ]

            db.session.add_all(Task(**data) for data in tasks_data)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        print('Seed concluído: 3 usuários, 4 categorias, 10 tarefas.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='URI explícita do banco descartável')
    parser.add_argument('--reset', action='store_true', help='Apagar dados do banco explicitamente escolhido')
    args = parser.parse_args()
    password = os.environ.get('SEED_PASSWORD', '')
    try:
        validate_password(password)
    except AppError:
        parser.error('Defina SEED_PASSWORD com uma senha válida.')
    application = create_app({'SQLALCHEMY_DATABASE_URI': args.database})
    try:
        seed_data(application, password, reset=args.reset)
    except Exception as error:
        # No exception values/SQL parameters or credentials in console output.
        parser.exit(1, 'Seed não aplicado: ' + type(error).__name__ + '\n')


if __name__ == '__main__':
    main()
