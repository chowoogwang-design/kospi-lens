import base64
import datetime as dt
import os
import unittest
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from app.autorefresh import schedule_due
from app.main import app

KST = ZoneInfo('Asia/Seoul')


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.old = {k: os.environ.get(k) for k in ('BASIC_AUTH_USER','BASIC_AUTH_PASSWORD','AUTO_REFRESH')}
        os.environ['AUTO_REFRESH'] = '0'
        os.environ.pop('BASIC_AUTH_USER', None)
        os.environ.pop('BASIC_AUTH_PASSWORD', None)

    def tearDown(self):
        for k,v in self.old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v

    def test_demo_route_and_health(self):
        with TestClient(app) as c:
            self.assertEqual(c.get('/').status_code, 200)
            r = c.get('/api/stocks')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['mode'], 'demo')
            self.assertGreater(len(r.json()['companies']), 0)
            self.assertEqual(c.get('/api/health').status_code, 200)

    def test_basic_auth_and_misconfiguration_fail_closed(self):
        os.environ['BASIC_AUTH_USER'] = 'internal'
        os.environ['BASIC_AUTH_PASSWORD'] = 'secret'
        with TestClient(app) as c:
            self.assertEqual(c.get('/').status_code, 401)
            self.assertEqual(c.get('/api/stocks').status_code, 401)
            raw = base64.b64encode(b'internal:secret').decode()
            self.assertEqual(c.get('/',headers={'Authorization':'Basic '+raw}).status_code,200)
            self.assertEqual(c.get('/api/stocks',headers={'Authorization':'Basic !!!'}).status_code,401)
            self.assertEqual(c.get('/api/health').status_code,200)
        del os.environ['BASIC_AUTH_PASSWORD']
        with TestClient(app) as c:
            self.assertEqual(c.get('/').status_code, 503)

    def test_korea_scheduler(self):
        d = dt.datetime(2026, 11, 9, 8, 29, tzinfo=KST)
        self.assertFalse(schedule_due(d,None))
        d = dt.datetime(2026, 11, 9, 8, 30, tzinfo=KST)
        self.assertTrue(schedule_due(d,None))
        self.assertFalse(schedule_due(d,d.date()))
        self.assertFalse(schedule_due(dt.datetime(2026,11,8,9,0,tzinfo=KST),None))


if __name__ == '__main__': unittest.main()
