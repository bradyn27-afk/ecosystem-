"""Driveline local development server. Standard library only."""
import argparse
import base64
import hmac
import logging
import json
import math
import os
from pathlib import Path
import sqlite3
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent
BUSINESSES = {'Auto repair', 'Power washing', 'Car flips'}


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Expected a workspace object')
    def amount(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 100_000_000
    if not amount(data.get('budget')):
        raise ValueError('Invalid budget')
    for key in ('clients', 'jobs', 'transactions', 'flips', 'parts'):
        rows = data.get(key)
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError('Invalid collection: ' + key)
        ids = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or row['id'] in ids:
                raise ValueError('Missing or duplicate record ID')
            ids.add(row['id'])
            for value in row.values():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    raise ValueError('Invalid record value')
            numeric = {'jobs': ('labor', 'parts'), 'transactions': ('amount',), 'flips': ('purchase', 'repairs', 'fees', 'sale'), 'parts': ('quantity', 'cost')}.get(key, ())
            if any(not amount(row.get(field)) for field in numeric):
                raise ValueError('Invalid amount in ' + key)
            if key in ('jobs', 'transactions') and row.get('business') not in BUSINESSES:
                raise ValueError('Invalid business')
    clients = {r['id'] for r in data['clients']}
    jobs = {r['id'] for r in data['jobs']}
    if any(r.get('client') not in clients for r in data['jobs']):
        raise ValueError('Job must reference an existing client')
    if any(r.get('job') not in jobs for r in data['parts']):
        raise ValueError('Part must reference an existing job')
    for service in data.get('services', []):
        if not isinstance(service, dict) or not amount(service.get('rate')) or service.get('business') not in BUSINESSES:
            raise ValueError('Invalid service pricing')
    return data



def configuration():
    public = os.environ.get('PUBLIC_DEPLOYMENT') == '1'
    password = os.environ.get('DRIVELINE_PASSWORD', '')
    username = os.environ.get('DRIVELINE_USERNAME', 'owner')
    if public and (len(password) < 20 or not username):
        raise RuntimeError('Public deployment requires DRIVELINE_PASSWORD (at least 20 characters) and a nonempty username.')
    path = Path(os.environ.get('DRIVELINE_DATA_DIR', '/workspace/driveline-data')) / 'workspace.sqlite3'
    return path, username, password


class WorkspaceApp:
    def __init__(self, db_path, username='', password=''):
        self.db_path = Path(db_path)
        self.username = username
        self.password = password

    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db_path, timeout=15)
        db.execute('CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)')
        return db

    def authorized(self, environ):
        if not self.password:
            return True
        try:
            scheme, encoded = environ.get('HTTP_AUTHORIZATION', '').split(' ', 1)
            if scheme.lower() != 'basic':
                return False
            username, password = base64.b64decode(encoded, validate=True).decode('utf-8').split(':', 1)
            return hmac.compare_digest(username.encode(), self.username.encode()) and hmac.compare_digest(password.encode(), self.password.encode())
        except (ValueError, UnicodeError):
            return False

    def __call__(self, environ, start_response):
        security = [('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'same-origin'), ('Cache-Control', 'no-store'), ('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")]
        def response(status, payload, mime='application/json; charset=utf-8', extra=None):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            start_response(status, [('Content-Type', mime), ('Content-Length', str(len(raw))), *security, *(extra or [])])
            return [raw]
        path = environ.get('PATH_INFO', '/')
        method = environ.get('REQUEST_METHOD', 'GET')
        if path == '/healthz' and method == 'GET':
            return response('200 OK', {'status': 'ok'})
        if not self.authorized(environ):
            return response('401 Unauthorized', {'error': 'Sign in to Driveline HQ'}, extra=[('WWW-Authenticate', 'Basic realm="Driveline HQ", charset="UTF-8"')])
        try:
            if path == '/api/workspace' and method == 'GET':
                with self.connect() as db:
                    row = db.execute('SELECT revision,payload FROM workspace WHERE id=1').fetchone()
                return response('200 OK', {'revision': row[0] if row else 0, 'data': json.loads(row[1]) if row else None})
            if path == '/api/workspace' and method == 'PUT':
                host = environ.get('HTTP_HOST', '')
                origin = environ.get('HTTP_ORIGIN')
                if origin and origin not in ('https://' + host, 'http://' + host):
                    return response('403 Forbidden', {'error': 'Origin not allowed'})
                if environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
                    return response('415 Unsupported Media Type', {'error': 'JSON required'})
                length = int(environ.get('CONTENT_LENGTH') or 0)
                if not 0 < length <= 5_000_000:
                    return response('413 Content Too Large', {'error': 'Workspace must be under 5 MB'})
                request = json.loads(environ['wsgi.input'].read(length))
                data = validate(request.get('data'))
                revision = request.get('revision')
                if type(revision) is not int or revision < 0:
                    raise ValueError('Invalid revision')
                with self.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    current = db.execute('SELECT revision FROM workspace WHERE id=1').fetchone()
                    if revision != (current[0] if current else 0):
                        return response('409 Conflict', {'error': 'Workspace changed in another window. Export your local work, then reload.'})
                    db.execute('INSERT OR REPLACE INTO workspace VALUES (1,?,?)', (revision + 1, json.dumps(data)))
                return response('200 OK', {'revision': revision + 1})
            files = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'), '/style.css': ('style.css', 'text/css'), '/game.js': ('game.js', 'text/javascript')}
            if method == 'GET' and path in files:
                name, mime = files[path]
                return response('200 OK', (ROOT / name).read_bytes(), mime + '; charset=utf-8')
            return response('404 Not Found', {'error': 'Not found'})
        except (ValueError, TypeError, AttributeError):
            return response('400 Bad Request', {'error': 'Invalid workspace data or revision'})
        except sqlite3.Error:
            logging.exception('Database operation failed')
            return response('503 Service Unavailable', {'error': 'Database temporarily unavailable. Export your local work before reloading.'})


app = WorkspaceApp(*configuration())


def serve(db_path, port):
    local = WorkspaceApp(db_path, app.username, app.password)
    print(f'Driveline HQ listening on port {port}; SQLite storage: {db_path}', flush=True)
    with make_server('127.0.0.1', port, local) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', type=Path, default=app.db_path)
    args = parser.parse_args()
    serve(args.db, args.port)
