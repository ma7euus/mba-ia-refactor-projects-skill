#!/usr/bin/env python3
"""Verify additive schema preparation and explicit CLI/seed lifetimes."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[1]


def source_hashes():
    return {str(path.relative_to(PROJECT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(PROJECT.rglob('*.py'))
            if not any(part in path.relative_to(PROJECT).parts
                       for part in ('.venv', '.agents', '__pycache__', 'instance'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    started_at = datetime.now(timezone.utc).isoformat()
    before_sources = source_hashes()

    def check(name, condition):
        results.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    with tempfile.TemporaryDirectory(prefix='task-manager-lifecycle-') as directory:
        path = Path(directory) / 'legacy.db'
        uri = f'sqlite:///{path}'
        env = {**os.environ, 'DATABASE_URL': uri, 'FLASK_DEBUG': '0',
               'PYTHONDONTWRITEBYTECODE': '1'}
        for name in ('ADMIN_NAME', 'ADMIN_EMAIL', 'ADMIN_PASSWORD', 'SEED_PASSWORD'):
            env.pop(name, None)

        def run(arguments, extra=None):
            return subprocess.run([sys.executable, '-B', *arguments], cwd=PROJECT,
                                  env={**env, **(extra or {})}, capture_output=True,
                                  text=True, timeout=30)

        imported = run(['-c', 'from app import app; assert not app.debug; assert app.config["HOST"] == "127.0.0.1"'])
        check('Importação e configuração padrão funcionam', imported.returncode == 0)
        check('Importação não cria arquivo SQLite', not path.exists())
        # This is the legacy three-table schema, with synthetic historical rows.
        with sqlite3.connect(path) as connection:
            connection.executescript('''
                CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL UNIQUE, password VARCHAR(255) NOT NULL,
                    role VARCHAR(50), active BOOLEAN, created_at DATETIME);
                CREATE TABLE categories (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL,
                    description VARCHAR(300), color VARCHAR(7), created_at DATETIME);
                CREATE TABLE tasks (id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL,
                    description TEXT, status VARCHAR(50), priority INTEGER,
                    user_id INTEGER REFERENCES users(id), category_id INTEGER REFERENCES categories(id),
                    created_at DATETIME, updated_at DATETIME, due_date DATETIME, tags VARCHAR(500));
            ''')
            connection.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',
                               (7, 'Historical fixture', 'historical@example.test',
                                hashlib.md5(b'synthetic-legacy-password').hexdigest(),
                                'user', 1, '2020-01-01 00:00:00'))
            connection.execute("INSERT INTO categories VALUES (5,'Historical category','Historical description','#123456','2020-01-01 00:00:00')")
            connection.execute("INSERT INTO tasks VALUES (9,'Historical task','Preserve me','pending',3,7,5,'2020-01-01','2020-01-01','2000-01-01','legacy,fixture')")

        def rows(tables=('users', 'categories', 'tasks')):
            with sqlite3.connect(path) as connection:
                return {table: connection.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
                        for table in tables}

        historical = rows()
        prepared = run(['-m', 'flask', '--app', 'app', 'init-db'])
        check('init-db executa sobre schema legado', prepared.returncode == 0)
        check('Todos os valores e IDs legados preservados', rows() == historical)
        with sqlite3.connect(path) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        check('Migração adiciona somente tabela de sessões', tables == {'users', 'categories', 'tasks', 'auth_sessions'})
        check('init-db é idempotente', run(['-m', 'flask', '--app', 'app', 'init-db']).returncode == 0 and rows() == historical)

        check('Provisionamento sem credenciais falha sem escrita',
              run(['-m', 'flask', '--app', 'app', 'create-admin']).returncode != 0 and rows() == historical)
        credentials = {'ADMIN_NAME': 'CLI fixture', 'ADMIN_EMAIL': 'cli.admin@example.test',
                       'ADMIN_PASSWORD': 'synthetic-cli-password'}
        created = run(['-m', 'flask', '--app', 'app', 'create-admin'], credentials)
        check('Provisionamento explícito cria admin', created.returncode == 0)
        with sqlite3.connect(path) as connection:
            stored = connection.execute('SELECT role,password FROM users WHERE email=?',
                                        (credentials['ADMIN_EMAIL'],)).fetchone()
        from werkzeug.security import check_password_hash
        check('Admin recebe hash atual verificável', stored[0] == 'admin' and check_password_hash(stored[1], credentials['ADMIN_PASSWORD']))
        provisioned = rows()
        check('Email existente não é sobrescrito nem promovido',
              run(['-m', 'flask', '--app', 'app', 'create-admin'],
                  {**credentials, 'ADMIN_EMAIL': 'historical@example.test'}).returncode != 0
              and rows() == provisioned)
        check('Comando não imprime senha administrativa', credentials['ADMIN_PASSWORD'] not in created.stdout + created.stderr)

        seeded_path = Path(directory) / 'seed.db'
        seed_uri = f'sqlite:///{seeded_path}'
        seed_env = {'SEED_PASSWORD': 'synthetic-seed-password'}
        check('Seed exige senha externa sem criar banco',
              run(['seed.py', '--database', seed_uri]).returncode != 0 and not seeded_path.exists())
        check('Seed exige escolha explícita de banco', run(['seed.py'], seed_env).returncode != 0)
        seeded = run(['seed.py', '--database', seed_uri], seed_env)
        check('Seed explícito funciona', seeded.returncode == 0)
        with sqlite3.connect(seeded_path) as connection:
            counts = [connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                      for table in ('users', 'categories', 'tasks')]
        check('Seed popula 3 usuários, 4 categorias e 10 tarefas', counts == [3, 4, 10])
        path = seeded_path
        fixtures = rows()
        check('Seed recusa banco populado sem reset',
              run(['seed.py', '--database', seed_uri], seed_env).returncode != 0 and rows() == fixtures)
        with sqlite3.connect(path) as connection:
            connection.executescript('''CREATE TRIGGER fail_seed BEFORE INSERT ON tasks
                BEGIN INSERT INTO synthetic_missing_table VALUES(1); END;''')
        check('Reset e seed falhos fazem rollback de todos os dados',
              run(['seed.py', '--database', seed_uri, '--reset'], seed_env).returncode != 0 and rows() == fixtures)
        with sqlite3.connect(path) as connection:
            connection.execute('DROP TRIGGER fail_seed')
        reset = run(['seed.py', '--database', seed_uri, '--reset'], seed_env)
        check('Reset explícito funciona após remover falha', reset.returncode == 0)
        check('Seed não imprime credencial externa', seed_env['SEED_PASSWORD'] not in reset.stdout + reset.stderr)
        with sqlite3.connect(path) as connection:
            check('Fixtures não têm referências órfãs', connection.execute('PRAGMA foreign_key_check').fetchall() == [])

    after_sources = source_hashes()
    check('Fontes permanecem iguais durante a validação de lifecycle', before_sources == after_sources)
    document = {'project': 'task-manager-api', 'started_at_utc': started_at,
                'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Current sources, subprocess CLI, disposable legacy-schema and seed databases',
                'versions': {'python': sys.version.split()[0],
                             **{name: version(name) for name in ('flask', 'flask-sqlalchemy', 'flask-cors', 'sqlalchemy', 'werkzeug')}},
                'sqlite': sqlite3.sqlite_version,
                'source_hashes': before_sources, 'source_hashes_after': after_sources,
                'checks': results, 'passed': all(row['passed'] for row in results)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    print(f'Lifecycle/CLI: {len(results)} checks passed; local database untouched.')


if __name__ == '__main__':
    main()
