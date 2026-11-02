import copy
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vendor'))
import local_player as player_api
import server
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import local_auth
import audit_progression


class ProgressionFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name) / 'player.json'
        for name, value in [('PATH', self.profile), ('GROWTH_LOG', Path(self.temp.name) / 'growth.jsonl')]:
            change = patch.object(player_api, name, value)
            change.start()
            self.addCleanup(change.stop)
        self.character = player_api.new_character(336, 6)
        self.character.update(Exp=399000, LimitBreakGrade=3, LimitBreakProgressCount=30)
        self.player = {
            'CharacterList': [self.character], 'AccountMoney': {'Gold': 100000},
            'ItemList': [{'ItemIndex': 2201, 'Qty': 100, 'Lock': False}],
            'Cores': {'336': []}, 'CoreBoardVersion': 2, 'AwakenCores': {},
        }
        player_api.items(self.player)
        player_api.save(self.player)

    def route(self, name, data):
        return player_api._route_overrides_inner(name, self.player, data)

    def awaken(self, phase=1):
        return self.route('/api/character/awaken', {
            'CharacterIndex': 336, 'Phase': phase, 'UsedGold': 100,
            'ItemList': [{'ItemIndex': 2201, 'Qty': 1}],
        })

    def core_request(self, tree, count=1, level=140):
        return {'CharacterIndex': 336, 'CoreTreeIndex': tree, 'CoreTreeCount': count,
                'CharacterLevel': level, 'UsedCost': 50, 'ItemList': [{'ItemIndex': 2201, 'Qty': 1}]}


class ProgressionTest(ProgressionFixture, unittest.TestCase):
    def test_client_curve_boundaries(self):
        for exp, expected in [(0, 2), (99, 2), (100, 3), (177000, 61),
                              (391599, 89), (391600, 90), (399000, 90), (400500, 91)]:
            with self.subTest(exp=exp):
                self.assertEqual(player_api.character_level(exp), expected)
        self.assertEqual(player_api.exp_for_level(90), 391600)

    def test_level_of_applies_grade_and_limit_break_cap(self):
        self.character.update(Grade=6, Exp=999000, LimitBreakProgressCount=0)
        self.assertEqual(player_api.level_of(self.character), 60)
        self.character['LimitBreakProgressCount'] = 30
        self.assertEqual(player_api.level_of(self.character), 90)

    def test_first_awaken_requires_normal_level_90_without_spending(self):
        self.character['Exp'] = 177000
        player_api.save(self.player)
        before = copy.deepcopy(self.player)
        result = self.awaken()
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)
        self.assertEqual(json.loads(self.profile.read_text()), before)

    def test_valid_client_level_90_can_advance_to_awaken_50_and_reload(self):
        self.assertEqual(player_api.level_of(self.character), 90)
        for phase in range(1, 6):
            self.assertEqual(self.awaken(phase).get('ResultCode', 0), 0)
            if phase < 5:
                before = copy.deepcopy(self.player)
                self.assertNotEqual(self.awaken(phase + 1).get('ResultCode', 0), 0)
                self.assertEqual(self.player, before)
            result = self.route('/api/character/awakenLevelUp', {
                'CharacterIndex': 336, 'AddExp': 999999999, 'ItemList': [],
            })
            self.assertEqual(result.get('ResultCode', 0), 0)
            self.assertEqual(player_api.awaken_level(self.character), phase * 10)
            self.assertEqual(player_api.level_of(self.character), 90)
        persisted = player_api.load()
        self.assertEqual(persisted['CharacterList'][0]['Awaken'], 5)
        self.assertEqual(player_api.awaken_level(persisted['CharacterList'][0]), 50)
        self.assertEqual(persisted['CharacterList'][0]['Exp'], 399000)
        self.assertEqual(persisted['AccountMoney']['Gold'], 99500)
        self.assertEqual(persisted['ItemList'][0]['Qty'], 95)

    def test_legacy_invalid_awaken_cannot_gain_more_awaken_exp(self):
        self.character.update(Exp=177000, Awaken=1, AwakenExp=0)
        before = copy.deepcopy(self.player)
        result = self.route('/api/character/awakenLevelUp', {
            'CharacterIndex': 336, 'AddExp': 10000, 'ItemList': [],
        })
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)

    def test_total_level_cannot_bypass_normal_core_requirement(self):
        self.character.update(Exp=177000, Awaken=5, AwakenExp=240100)
        node = next(row for row in player_api.core_defs()['336'] if row[1] == 62)
        self.player['Cores']['336'] = [node[2]]
        before = copy.deepcopy(self.player)
        result = self.route('/api/core/coreAcquire', self.core_request(node[0]))
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)

    def test_normal_90_core_unlock_persists_and_duplicate_does_not_charge(self):
        node = next(row for row in player_api.core_defs()['336'] if row[1] == 90)
        self.player['Cores']['336'] = [node[2]]
        payload = self.core_request(node[0], level=50)
        result = self.route('/api/core/coreAcquire', payload)
        self.assertEqual(result.get('ResultCode', 0), 0)
        self.assertIn(node[0], result['CoreList'])
        self.assertIn(node[0], player_api.load()['Cores']['336'])
        before = copy.deepcopy(self.player)
        self.route('/api/core/coreAcquire', payload)
        self.assertEqual(self.player, before)

    def test_missing_predecessor_returns_failure_without_cost(self):
        node = next(row for row in player_api.core_defs()['336'] if row[1] == 90)
        before = copy.deepcopy(self.player)
        result = self.route('/api/core/coreAcquire', self.core_request(node[0]))
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)

    def test_unowned_core_request_does_not_create_a_save_entry(self):
        before = copy.deepcopy(self.player)
        result = self.route('/api/core/coreAcquire', {'CharacterIndex': 999999, 'CoreTreeIndex': 1})
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)

    def test_battle_exp_does_not_reduce_an_already_maxed_fighter(self):
        player_api.grant_char_exp(self.player, {'CharacterList': [{'CharacterIndex': 336}]}, 500)
        self.assertEqual(self.character['Exp'], 399000)

    def test_legacy_roster_grade_update_preserves_saved_exp(self):
        self.character.update(Grade=3, LimitBreakProgressCount=0, Exp=399000)
        self.player['TeamDeckList'] = [{'CharacterIndex2': 0, 'CharacterIndex3': 0}]
        roster = Path(self.temp.name) / 'roster.json'
        roster.write_text('[336]')
        with patch.object(player_api, 'ROSTER_PATH', roster):
            player_api.ensure_roster(self.player)
        self.assertEqual(self.character['Grade'], 5)
        self.assertEqual(self.character['Exp'], 399000)
        self.assertEqual(player_api.load()['CharacterList'][0]['Exp'], 399000)

    def test_normal_level_up_caps_at_the_grade_limit(self):
        self.character.update(Exp=10000, Grade=3, LimitBreakProgressCount=0)
        with patch.object(player_api.random, 'random', return_value=0.9):
            result = self.route('/api/character/characterLevelUp', {
                'Character': {'CharacterIndex': 336}, 'AddExp': 999999999, 'ItemList': [],
            })
        self.assertEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.character['Exp'], player_api.exp_for_level(30, 336))
        self.assertEqual(result['Character']['CharacterLevel'], 30)

    def test_negative_exp_and_maxed_phase_do_not_consume_items(self):
        for path in ('characterLevelUp', 'awakenLevelUp'):
            self.character.update(Awaken=1, AwakenExp=0)
            before = copy.deepcopy(self.player)
            result = self.route('/api/character/' + path, {
                'Character': {'CharacterIndex': 336}, 'CharacterIndex': 336, 'AddExp': -1,
                'ItemList': [{'ItemIndex': 2201, 'Qty': 1}],
            })
            self.assertNotEqual(result.get('ResultCode', 0), 0)
            self.assertEqual(self.player, before)
        self.character['AwakenExp'] = 8100
        before = copy.deepcopy(self.player)
        result = self.route('/api/character/awakenLevelUp', {
            'CharacterIndex': 336, 'AddExp': 100, 'ItemList': [{'ItemIndex': 2201, 'Qty': 1}],
        })
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)

    def test_audit_flags_legacy_inconsistency_without_repairing_it(self):
        self.character.update(Exp=177000, Awaken=5, AwakenExp=240100)
        before = copy.deepcopy(self.player)
        result = audit_progression.audit(self.player)
        self.assertEqual(result['CharactersWithIssues'], 1)
        self.assertFalse(result['Modified'])
        self.assertEqual(result['Issues'][0]['NormalLevel'], 61)
        self.assertEqual(self.player, before)


class ProgressionHTTPTest(ProgressionFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.player['AccountMoney'].update(ActivePoint=100, ActivePointMax=100,
                                           ActivePointUpdateTime=player_api.now_ms())
        player_api.save(self.player)
        recording = patch.object(server, 'record')
        recording.start()
        self.addCleanup(recording.stop)
        self.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.worker = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.worker.join()

    def post(self, path, payload, encrypted=False):
        data = json.dumps(payload).encode()
        content_type = 'application/json'
        if encrypted:
            data = AES.new(local_auth.KEY, AES.MODE_CBC, local_auth.IV).encrypt(pad(data, 16))
            content_type = 'application/cipher'
        connection = http.client.HTTPConnection(*self.httpd.server_address, timeout=10)
        try:
            connection.request('POST', path, data, {'Content-Type': content_type})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            return json.loads(response.read())
        finally:
            connection.close()

    def test_http_rejects_premature_awaken_without_charging(self):
        self.character['Exp'] = 177000
        player_api.save(self.player)
        result = self.post('/api/character/awaken', {
            'CharacterIndex': 336, 'Phase': 1, 'UsedGold': 100,
            'ItemList': [{'ItemIndex': 2201, 'Qty': 1}],
        })
        self.assertNotEqual(result['ResultCode'], 0)
        persisted = player_api.load()
        self.assertEqual(persisted['CharacterList'][0]['Awaken'], 0)
        self.assertEqual(persisted['AccountMoney']['Gold'], 100000)
        self.assertEqual(persisted['ItemList'][0]['Qty'], 100)

    def test_encrypted_http_awaken_core_acquire_and_disk_reload(self):
        node = next(row for row in player_api.core_defs()['336'] if row[1] == 90)
        self.player['Cores']['336'] = [node[2]]
        player_api.save(self.player)
        result = self.post('/api/character/awaken', {
            'CharacterIndex': 336, 'Phase': 1, 'UsedGold': 100,
            'ItemList': [{'ItemIndex': 2201, 'Qty': 1}],
        }, encrypted=True)
        self.assertEqual(result['ResultCode'], 0)
        self.assertEqual(result['Character']['Awaken'], 1)
        result = self.post('/api/core/coreAcquire', self.core_request(node[0], level=140), encrypted=True)
        self.assertEqual(result['ResultCode'], 0)
        self.assertIn(node[0], result['CoreList'])
        persisted = player_api.load()
        self.assertEqual(persisted['CharacterList'][0]['Awaken'], 1)
        self.assertEqual(persisted['CharacterList'][0]['Exp'], 399000)
        self.assertIn(node[0], persisted['Cores']['336'])
        self.assertEqual(persisted['AccountMoney']['Gold'], 99850)
        self.assertEqual(persisted['ItemList'][0]['Qty'], 98)


if __name__ == '__main__':
    unittest.main()
