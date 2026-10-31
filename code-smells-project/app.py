"""Stable launcher; schema creation and migration are explicit CLI commands."""
from src import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=False, use_reloader=False)
