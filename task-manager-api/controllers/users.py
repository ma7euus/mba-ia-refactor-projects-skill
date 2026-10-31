"""User use cases; HTTP and presentation live in the views/routes layer."""

from sqlalchemy.exc import IntegrityError

from errors import AppError
from models.user import User
from models.user_repository import UserRepository
from services.task_rules import positive_id
from services.user_validation import login_fields, user_fields


def require_admin(actor):
    if actor.role != 'admin':
        raise AppError('Acesso não permitido', 403)


def own_or_admin(actor, user_id):
    if actor.role != 'admin' and actor.id != user_id:
        raise AppError('Acesso não permitido', 403)


class UserController:
    def __init__(self, session, auth_service):
        self.session = session
        self.auth = auth_service
        self.users = UserRepository(session)

    def _get(self, user_id):
        positive_id(user_id, 'user_id', nullable=False)
        user = self.users.get(user_id)
        if user is None:
            raise AppError('Usuário não encontrado', 404)
        return user

    def _commit_email(self, email):
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            if self.users.by_email(email) is not None:
                raise AppError('Email já cadastrado', 409) from None
            raise

    def list_users(self, actor):
        require_admin(actor)
        return self.users.with_task_counts()

    def get_user(self, actor, user_id):
        own_or_admin(actor, user_id)
        return self._get(user_id), self.users.tasks(user_id)

    def create_user(self, data):
        fields = user_fields(data, creating=True)
        if fields.get('role', 'user') != 'user' or 'active' in fields:
            raise AppError('Cadastro público não concede privilégios administrativos', 403)
        if self.users.by_email(fields['email']) is not None:
            raise AppError('Email já cadastrado', 409)
        user = User(name=fields['name'], email=fields['email'], role='user', active=True)
        user.set_password(fields['password'])
        self.users.add(user)
        self._commit_email(user.email)
        return user

    def update_user(self, actor, user_id, data):
        own_or_admin(actor, user_id)
        user = self._get(user_id)
        fields = user_fields(data)
        if 'role' in fields or 'active' in fields:
            require_admin(actor)
        if 'email' in fields:
            existing = self.users.by_email(fields['email'])
            if existing is not None and existing.id != user.id:
                raise AppError('Email já cadastrado', 409)
        # Validate every field and permission before applying any mutation.
        for field, value in fields.items():
            if field == 'password':
                user.set_password(value)
                self.auth.revoke(user.id)
            else:
                setattr(user, field, value)
        self._commit_email(user.email)
        return user

    def delete_user(self, actor, user_id):
        require_admin(actor)
        user = self._get(user_id)
        self.users.delete(user)
        self.session.commit()

    def get_user_tasks(self, actor, user_id):
        own_or_admin(actor, user_id)
        self._get(user_id)
        return self.users.tasks(user_id)

    def login(self, data):
        return self.auth.login(*login_fields(data))
