import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from utils.helpers import utc_now

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        if self.has_legacy_password():
            # Only verification of existing records uses MD5. A successful login
            # replaces this digest with a salted password hash in its transaction.
            candidate = hashlib.md5(pwd.encode(), usedforsecurity=False).hexdigest()
            return hmac.compare_digest(self.password.lower(), candidate)
        return check_password_hash(self.password, pwd)

    def has_legacy_password(self):
        return bool(re.fullmatch(r'[0-9a-fA-F]{32}', self.password or ''))

    def is_admin(self):
        return self.role == 'admin'
