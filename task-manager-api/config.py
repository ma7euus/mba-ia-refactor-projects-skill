"""Read environment-dependent settings only at composition time."""

import os


def configuration():
    return {
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///tasks.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'DEBUG': os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true'),
        'HOST': os.environ.get('HOST', '127.0.0.1'),
        'PORT': int(os.environ.get('PORT', '5000')),
        'SESSION_TTL_SECONDS': 3600,
        'MAX_CONTENT_LENGTH': 1024 * 1024,
        'CORS_ORIGINS': os.environ.get('CORS_ORIGINS', '*').split(','),
    }
