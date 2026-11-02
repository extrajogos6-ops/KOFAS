import base64
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vendor'))
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
import server
import local_auth


class Migration117Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = patch.object(server, 'record')
        cls.record.start()
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        cls.record.stop()

    def request(self, method, path, payload=None):
        connection = http.client.HTTPConnection(*self.httpd.server_address, timeout=5)
        headers = {}
        body = None
        if payload is not None:
            body = AES.new(local_auth.KEY, AES.MODE_CBC, local_auth.IV).encrypt(
                pad(json.dumps(payload).encode(), 16))
            headers['Content-Type'] = 'application/cipher'
        try:
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_client_configuration_is_117_and_all_services_are_isolated(self):
        status, body = self.request('GET', '/xxxxxxxx/config_1.17.0_win.json')
        self.assertEqual(status, 200)
        plain = unpad(AES.new(b'neo4567neo123456', AES.MODE_CBC,
                             b'neo4567890neo456').decrypt(base64.b64decode(body)), 16)
        config = json.loads(plain)
        self.assertEqual(config['minVersion'], '1.17.0')
        self.assertEqual(config['newVersion'], '1.17.0')
        for key in ('cdnServer', 'tableDataServer', 'webServer'):
            self.assertTrue(config['local'][key].startswith('http://127.0.0.1:18775/'))
        self.assertEqual(config['local']['tcpPort'], 18776)

    def test_encrypted_auth_and_start_session_use_a_fixture_profile(self):
        profile = {'Route': {'Pid': '1000001', 'Usn': 1000001, 'NickName': 'MigrationTest'}}
        status, body = self.request('POST', '/api/session/pcAuth',
                                    {'id': 'migration@local.invalid', 'pw': 'fixture-only', 'deviceKey': 'fixture'})
        self.assertEqual(status, 200)
        auth = json.loads(body)
        self.assertEqual(auth['ResultCode'], 0)
        token = json.loads(auth['resultData'])['accessToken']
        try:
            with patch.object(server.local_player, 'load', return_value=profile):
                status, body = self.request('POST', '/api/session/start',
                                            {'Pid': '1000001', 'GameToken': token})
            self.assertEqual(status, 200)
            session = json.loads(body)
            self.assertEqual(session['ResultCode'], 0)
            self.assertEqual(session['Route'], profile['Route'])
            self.assertEqual(session['SecurityDataTable'], local_auth.SECURITY['SecurityDataTable'])
        finally:
            with local_auth.SESSION_LOCK:
                local_auth.SESSIONS.pop(token, None)

    def test_unknown_session_token_is_rejected(self):
        status, body = self.request('POST', '/api/session/start',
                                    {'Pid': '1000001', 'GameToken': 'not-issued'})
        self.assertEqual(status, 200)
        self.assertNotEqual(json.loads(body)['ResultCode'], 0)

    def test_new_character_asset_is_served_without_legacy_override(self):
        name = 'prefabs_character_sf6_juri'
        entry = server.ASSET_INDEX[name]
        expected = (server.ASSET_ROOT / entry['file']).read_bytes()
        status, body = self.request('GET', '/cdn/assets/win/r0/dxt/' + name)
        self.assertEqual(status, 200)
        self.assertEqual(body, expected)
        self.assertTrue(body.startswith(b'UnityFS'))
        self.assertEqual(server.MOD_BUNDLES, {})


if __name__ == '__main__':
    unittest.main()
