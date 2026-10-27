import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('server', Path(__file__).parents[1] / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = dict(clients=[dict(id='c', name='Customer')], jobs=[dict(id='j', client='c', business='Auto repair', labor=10, parts=20)], transactions=[], flips=[], parts=[], budget=100)

    def test_linked_workspace(self):
        self.assertEqual(server.validate(self.data), self.data)

    def test_reject_invalid_money(self):
        for value in [-1, float('nan'), float('inf'), '100', True]:
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data['jobs'][0]['labor'] = value
                with self.assertRaises(ValueError):
                    server.validate(data)

    def test_reject_orphans_and_duplicates(self):
        for edit in [lambda d: d['clients'].clear(), lambda d: d['jobs'].append(d['jobs'][0].copy())]:
            data = copy.deepcopy(self.data)
            edit(data)
            with self.assertRaises(ValueError):
                server.validate(data)

if __name__ == '__main__':
    unittest.main()

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = server.WorkspaceApp(Path(self.temp.name) / 'hq.sqlite3', 'owner', 'test-password-only-for-unit-tests')

    def request(self, path, method='GET', payload=None, auth=True, origin=None):
        import io, json, base64
        raw = json.dumps(payload).encode() if payload is not None else b''
        environ = {'PATH_INFO': path, 'REQUEST_METHOD': method, 'wsgi.input': io.BytesIO(raw), 'CONTENT_LENGTH': str(len(raw)), 'CONTENT_TYPE': 'application/json', 'HTTP_HOST': 'hq.example.com'}
        if auth:
            environ['HTTP_AUTHORIZATION'] = 'Basic ' + base64.b64encode(b'owner:test-password-only-for-unit-tests').decode()
        if origin:
            environ['HTTP_ORIGIN'] = origin
        captured = {}
        def start(status, headers):
            captured.update(status=int(status.split()[0]), headers=dict(headers))
        captured['body'] = b''.join(self.app(environ, start))
        return captured

    def test_auth_protects_data_and_app(self):
        for path in ['/', '/game.js', '/api/workspace']:
            self.assertEqual(self.request(path, auth=False)['status'], 401)
        self.assertEqual(self.request('/api/workspace', method='PUT', payload={}, auth=False)['status'], 401)
        self.assertEqual(self.request('/healthz', auth=False)['status'], 200)
        self.assertEqual(self.request('/')['status'], 200)

    def test_persistence_conflict_and_https_origin(self):
        import json
        data = dict(clients=[], jobs=[], parts=[], transactions=[], flips=[], budget=100)
        self.assertEqual(self.request('/api/workspace', 'PUT', {'revision': 0, 'data': data}, origin='https://hq.example.com')['status'], 200)
        self.assertEqual(json.loads(self.request('/api/workspace')['body'])['data'], data)
        self.assertEqual(self.request('/api/workspace', 'PUT', {'revision': 0, 'data': data})['status'], 409)
        self.assertEqual(self.request('/api/workspace', 'PUT', {'revision': 1, 'data': data}, origin='https://other.example.com')['status'], 403)
        self.assertEqual(self.request('/server.py')['status'], 404)

    def test_public_mode_refuses_missing_password(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {'PUBLIC_DEPLOYMENT': '1', 'DRIVELINE_PASSWORD': ''}):
            with self.assertRaises(RuntimeError):
                server.configuration()
