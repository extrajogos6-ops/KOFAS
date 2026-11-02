import http.client
import io
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class LanguageRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record_patch = patch.object(server, 'record')
        cls.record_patch.start()
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.worker = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.worker.join()
        cls.record_patch.stop()

    def get(self, path):
        connection = http.client.HTTPConnection(*self.httpd.server_address, timeout=5)
        try:
            connection.request('GET', path)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_portuguese_downloads_use_existing_english_resources(self):
        pairs = (
            ('/tables/common/table/lang_pt.dat', '/tables/common/table/lang_en.dat'),
            ('/tables/common/table/lang_pt.kof', '/tables/common/table/lang_en.kof'),
            ('/tables/common/table/prohibited_pt_text_words.dat', '/tables/common/table/prohibited_en_text_words.dat'),
            ('/tables/common/table/prohibited_pt_text_words.kof', '/tables/common/table/prohibited_en_text_words.kof'),
            ('/tables/common/banner/pt.dat', '/tables/common/banner/en.dat'),
        )
        for portuguese, english in pairs:
            with self.subTest(path=portuguese):
                expected_status, expected_body = self.get(english)
                status, body = self.get(portuguese)
                self.assertEqual(expected_status, 200)
                self.assertEqual(status, 200)
                self.assertEqual(body, expected_body)
                if portuguese.endswith('.dat'):
                    with zipfile.ZipFile(io.BytesIO(body)) as archive:
                        self.assertIsNone(archive.testzip())

    def test_unknown_resource_still_fails(self):
        status, _ = self.get('/tables/common/table/missing.dat')
        self.assertEqual(status, 501)


if __name__ == '__main__':
    unittest.main()
