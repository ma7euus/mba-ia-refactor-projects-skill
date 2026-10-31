"""Server-side bearer authentication with password migration and expiry."""

from datetime import timedelta
import hashlib
import secrets

from sqlalchemy import select

from errors import AppError
from models.auth_session import AuthSession
from models.user import User
from models.user_repository import UserRepository
from utils.helpers import utc_now


class AuthService:
    def __init__(self, session, session_seconds=3600):
        self.session = session
        self.session_seconds = session_seconds
        self.users = UserRepository(session)

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def login(self, email, password):
        user = self.users.by_email(email)
        if user is None or not user.check_password(password):
            raise AppError('Credenciais inválidas', 401)
        if not user.active:
            raise AppError('Usuário inativo', 403)
        if user.has_legacy_password():
            user.set_password(password)
        token = secrets.token_urlsafe(32)
        self.session.add(AuthSession(
            user_id=user.id, token_digest=self.digest(token),
            expires_at=utc_now() + timedelta(seconds=self.session_seconds),
        ))
        # Password upgrade and session creation must either both succeed or roll back.
        self.session.commit()
        return user, token

    def authenticate(self, token):
        if not isinstance(token, str) or not token or len(token) > 256:
            raise AppError('Autenticação necessária', 401)
        user = self.session.scalar(
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(AuthSession.token_digest == self.digest(token),
                   AuthSession.expires_at > utc_now())
        )
        if user is None:
            raise AppError('Credencial inválida ou expirada', 401)
        if not user.active:
            raise AppError('Usuário inativo', 403)
        return user

    def revoke(self, user_id):
        self.users.revoke_sessions(user_id)
