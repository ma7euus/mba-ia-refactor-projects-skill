"""Environment-dependent settings, loaded only by the composition root."""

import os
from pathlib import Path


def _enabled(name):
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}


def load_config():
    return {
        "DATABASE": str(Path(os.environ.get("DATABASE_PATH", "loja.db")).resolve()),
        "HOST": os.environ.get("HOST", "127.0.0.1"),
        "PORT": int(os.environ.get("PORT", "5000")),
        "DEBUG": False,
        "ENABLE_DB_RESET": _enabled("ENABLE_DB_RESET"),
        "DISPOSABLE_DATABASE": _enabled("DISPOSABLE_DATABASE"),
        "MAX_CONTENT_LENGTH": 1_048_576,
    }
