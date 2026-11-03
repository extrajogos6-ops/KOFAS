import hashlib
import http.client
from io import BytesIO
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor'), str(ROOT.parent / 'scripts')]
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from local_progression import _fields
import local_awaken_balance as balance
import server


def decrypt(data, security):
    return unpad(AES.new(bytes.fromhex(security['EncryptionKey']), AES.MODE_CBC,
                         bytes.fromhex(security['Iv'])).decrypt(data), 16)


def payload(archive, name, security):
    with ZipFile(BytesIO(archive)) as outer:
        with ZipFile(BytesIO(decrypt(outer.read(name), security))) as inner:
            assert inner.testzip() is None
            return inner.read(name)


def rows(data):
    return [dict(_fields(value)) for field, value in _fields(data) if field == 1]


class AwakenBalanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.security = json.loads((ROOT / 'packs-claude/security.json').read_text())
        cls.original = {name: (ROOT / name).read_bytes() for name in balance.FILES}
        cls.patched = balance.build_patch(ROOT)

    def table(self, name, patched=True):
        files = self.patched if patched else self.original
        return rows(payload(files['packs-claude/table.dat'], name, self.security['SecurityDataTable']))

    def test_every_awaken_effect_is_exclusive_and_linear_at_six_levels(self):
        old_buffs = {r[2]: r for r in self.table('bufftable.bin', False)}
        new_buffs = {r[2]: r for r in self.table('bufftable.bin')}
        old_awake = {r[2]: r for r in self.table('battlecardawakebufftable.bin', False)}
        for option in self.table('battlecardawakebufftable.bin'):
            source = old_buffs[int(old_awake[option[2]][5])]
            target_id = int(option[5])
            self.assertNotIn(target_id, old_buffs, 'awakening must not modify a shared ordinary effect')
            target = new_buffs[target_id]
            base = struct.unpack('<f', source[29])[0]
            for level in range(1, 7):
                actual = min(struct.unpack('<f', target[31])[0],
                             struct.unpack('<f', target[29])[0] +
                             (level - 1) * struct.unpack('<f', target[30])[0])
                self.assertAlmostEqual(actual, base * level, places=5)
            self.assertEqual({k: v for k, v in source.items() if k not in (2, 3, 4, 30, 31, 76)},
                             {k: v for k, v in target.items() if k not in (2, 3, 4, 30, 31, 76)})

    def test_atk80_option_has_160_at_level_two(self):
        option = next(r for r in self.table('battlecardawakebufftable.bin') if r[2] == 9321)
        effect = next(r for r in self.table('bufftable.bin') if r[2] == int(option[5]))
        value = struct.unpack('<f', effect[29])[0] + struct.unpack('<f', effect[30])[0]
        self.assertEqual(value, 160)

    def test_ordinary_effects_and_card_definitions_are_untouched(self):
        old = {r[2]: r for r in self.table('bufftable.bin', False)}
        new = {r[2]: r for r in self.table('bufftable.bin')}
        self.assertTrue(all(new[index] == row for index, row in old.items()))
        self.assertEqual(self.table('battlecardtable.bin'), self.table('battlecardtable.bin', False))
        for file in ('packs-claude/table.dat', 'packs-claude/lang_global.dat'):
            with ZipFile(BytesIO(self.original[file])) as a, ZipFile(BytesIO(self.patched[file])) as b:
                self.assertEqual(a.namelist(), b.namelist())
                for name in a.namelist():
                    if name not in ('bufftable.bin', 'battlecardawakebufftable.bin'):
                        self.assertEqual(a.read(name), b.read(name), name)

    def test_dynamic_descriptions_cover_flat_and_percent_statuses(self):
        language = rows(payload(self.patched['packs-claude/lang_global.dat'], 'bufftable.bin',
                                self.security['SecurityLocalizing']))
        texts = {r[2].decode(): r[4].decode() for r in language}
        buffs = {r[2]: r for r in self.table('bufftable.bin')}
        for option in self.table('battlecardawakebufftable.bin'):
            effect = buffs[int(option[5])]
            desc = texts[effect[76].decode()]
            self.assertIn('{buffPower', desc)
            base = struct.unpack('<f', effect[29])[0]
            self.assertEqual('%' in desc, base < 1)
            if base < 1:
                self.assertIn('*100', desc)

    def test_manifests_match_plaintext_and_only_versions_of_changed_packs_increase(self):
        for pack, meta, key in [('table.dat', 'table.kof', 'SecurityDataTable'),
                                ('lang_global.dat', 'lang_en.kof', 'SecurityLocalizing')]:
            security = self.security[key]
            manifest = json.loads(decrypt(self.patched['packs-claude/' + meta], security))
            for row in manifest:
                name = row['name'].lower() + '.bin'
                data = payload(self.patched['packs-claude/' + pack], name, security)
                self.assertEqual(row['hash'], hashlib.md5(data).hexdigest(), name)
        before = json.loads(self.original['table-versions.json'])
        after = json.loads(self.patched['table-versions.json'])
        self.assertEqual(after, dict(before, table=before['table'] + 1,
                                    lang_global=before['lang_global'] + 1))

    def test_second_run_is_byte_identical_and_does_not_increment_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, data in self.patched.items():
                target = root / name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(data)
            (root / 'packs-claude/security.json').write_text(json.dumps(self.security))
            self.assertEqual(balance.build_patch(root), self.patched)

    def test_installer_verifies_backups_preserves_profile_and_runs_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root, backup = Path(directory) / 'runtime', Path(directory) / 'backup'
            for name, data in self.original.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            (root / 'packs-claude/security.json').write_text(json.dumps(self.security))
            profile = b'{"unrelated":"preserve", "Gold":12345}'
            (root / 'player.json').write_bytes(profile)
            result = balance.install(root, backup)
            self.assertTrue(result['changed'])
            for name, expected in self.original.items():
                self.assertEqual((backup / name).read_bytes(), expected)
                self.assertEqual((root / name).read_bytes(), self.patched[name])
            for record in json.loads((backup / 'manifest.json').read_text()):
                self.assertEqual(hashlib.sha256((backup / record['path']).read_bytes()).hexdigest(), record['sha256'])
            self.assertEqual((root / 'player.json').read_bytes(), profile)
            self.assertEqual((backup / 'player.json').read_bytes(), profile)
            self.assertFalse(balance.install(root, Path(directory) / 'unused')['changed'])
            self.assertFalse((Path(directory) / 'unused').exists())

    def test_isolated_http_serves_patched_packs_manifests_and_portuguese_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, data in self.patched.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            with patch.object(server, 'ROOT', root), patch.object(server, 'record'):
                httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
                worker = threading.Thread(target=httpd.serve_forever, daemon=True)
                worker.start()
                try:
                    routes = {'version.kof': 'table-versions.json', 'table.dat': 'packs-claude/table.dat',
                              'table.kof': 'packs-claude/table.kof', 'lang_pt.dat': 'packs-claude/lang_global.dat',
                              'lang_pt.kof': 'packs-claude/lang_en.kof'}
                    for route, name in routes.items():
                        connection = http.client.HTTPConnection(*httpd.server_address, timeout=5)
                        try:
                            connection.request('GET', '/tables/common/table/' + route)
                            response = connection.getresponse()
                            self.assertEqual(response.status, 200)
                            self.assertEqual(response.read(), self.patched[name])
                        finally:
                            connection.close()
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    worker.join()


if __name__ == '__main__':
    unittest.main()
