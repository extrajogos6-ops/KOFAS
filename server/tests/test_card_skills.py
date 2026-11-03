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
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
import local_player as api
import server
import local_auth
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


class CardSkillFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name) / 'player.json'
        for name, value in [('PATH', self.profile), ('GROWTH_LOG', Path(self.temp.name) / 'growth.jsonl')]:
            change = patch.object(api, name, value)
            change.start()
            self.addCleanup(change.stop)
        self.card = {
            'BattleCardNo': 1, 'BattleCardIndex': 50281, 'Grade': 6, 'Exp': 47600,
            'SkillIndex': 3690010, 'SkillLevel': 10, 'SkillExp': 0, 'awaken': 1,
            'awakeBuffIndex': 9332, 'awakeBuffLevel': 1, 'StackFlag': 0, 'Qty': 1,
        }
        self.material = {'BattleCardNo': 2, 'BattleCardIndex': 60639, 'Grade': 1,
                         'StackFlag': 1, 'Qty': 20, 'Lock': False, 'LikeFlag': False}
        self.player = {'CharacterList': [], 'BattleCardList': [self.card, self.material],
                       'AccountMoney': {'Gold': 100000}, 'Unrelated': {'keep': [1, 2, 3]}}
        api.save(self.player)

    def upgrade(self, quantity=1, gold=1000, **fields):
        payload = {'BaseCard': {'battleCardNo': 1},
                   'MaterialCardList': [{'battleCardNo': 2, 'qty': quantity}], 'UsedGold': gold}
        payload.update(fields)
        return api.card_route('/api/card2/cardSkillUp', self.player, payload)

    def reject_without_changes(self, payload):
        api.save(self.player)
        before = copy.deepcopy(self.player)
        result = api.card_route('/api/card2/cardSkillUp', self.player, payload)
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)
        self.assertEqual(api.load(), before)


class CardSkillTest(CardSkillFixture, unittest.TestCase):
    def test_option_card_skill_updates_passive_levels_in_reply_and_on_disk(self):
        self.card.update(BattleCardIndex=60491, SkillIndex=0, SkillLevel=1,
                         awaken=0, awakeBuffIndex=0, awakeBuffLevel=0,
                         PassiveIndex1=910002, PassiveLevel1=1,
                         PassiveIndex2=910031, PassiveLevel2=1,
                         PassiveIndex3=0, PassiveLevel3=0)
        result = self.upgrade(quantity=2, gold=40)
        self.assertEqual(result['battleCard']['skillLevel'], 3)
        self.assertEqual(result['battleCard']['passiveLevel1'], 3)
        self.assertEqual(result['battleCard']['passiveLevel2'], 3)
        self.assertEqual(result['battleCard']['passiveLevel3'], 0)
        stored = api.load()['BattleCardList'][0]
        self.assertEqual((stored['PassiveLevel1'], stored['PassiveLevel2']), (3, 3))
        self.assertEqual(self.material['Qty'], 18)
        self.assertEqual(self.player['AccountMoney']['Gold'], 99960)

    def test_max_normal_skill_does_not_consume_materials_or_gold(self):
        self.card.update(awaken=0, awakeBuffIndex=0, awakeBuffLevel=0)
        self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                     'MaterialCardList': [{'battleCardNo': 2, 'qty': 10}],
                                     'UsedGold': 200})

    def test_profile_repairs_previously_paid_passive_levels_once_without_charging(self):
        self.card.update(BattleCardIndex=60491, SkillIndex=0, SkillLevel=10,
                         awaken=0, awakeBuffIndex=0, awakeBuffLevel=0,
                         PassiveIndex1=910002, PassiveLevel1=1,
                         PassiveIndex2=910031, PassiveLevel2=1,
                         PassiveIndex3=0, PassiveLevel3=0)
        definitions = [dict(BattleCardIndex=60491, SkillIndex=0, Grade=6,
                            Passive=[[910002, 1], [910031, 1]]),
                       dict(BattleCardIndex=60639, SkillIndex=0, Grade=1)]
        definition_path = Path(self.temp.name) / 'cards.json'
        definition_path.write_text(json.dumps(definitions))
        self.player.update(CardsVersion='stable:2', CardsGranted=[60491, 60639])
        for slot in (1, 2, 3):
            self.material.update({'PassiveIndex%d' % slot: 0, 'PassiveLevel%d' % slot: 0})
        money, material = copy.deepcopy(self.player['AccountMoney']), copy.deepcopy(self.material)
        with patch.object(api, 'CARDS_PATH', definition_path), patch.object(api, 'auto_equip_cards', return_value=False):
            api.battle_cards(self.player)
            stored = api.load()
            self.assertEqual((stored['BattleCardList'][0]['PassiveLevel1'],
                              stored['BattleCardList'][0]['PassiveLevel2']), (10, 10))
            self.assertEqual(stored['AccountMoney'], money)
            self.assertEqual(stored['BattleCardList'][1], material)
            self.assertEqual(stored['Unrelated'], self.player['Unrelated'])
            with patch.object(api, 'save') as save_again:
                api.battle_cards(self.player)
                save_again.assert_not_called()

    def test_awaken_skill_one_to_two_persists_without_changing_normal_skill(self):
        before = copy.deepcopy(self.card)
        response = self.upgrade()
        self.assertEqual(response.get('ResultCode', 0), 0)
        self.assertEqual(response['battleCard']['awakeBuffLevel'], 2)
        self.assertEqual(response['battleCard']['skillLevel'], 10)
        self.assertEqual(response['battleCard']['skillExp'], 0)
        self.assertEqual(response['levelUpSuccess'], 1)
        self.assertEqual(self.material['Qty'], 19)
        self.assertEqual(self.player['AccountMoney']['Gold'], 99000)
        self.assertEqual(api.load()['BattleCardList'][0]['awakeBuffLevel'], 2)
        self.assertEqual({k: self.card[k] for k in before if k != 'awakeBuffLevel'},
                         {k: before[k] for k in before if k != 'awakeBuffLevel'})
        self.assertEqual(self.player['Unrelated'], {'keep': [1, 2, 3]})

    def test_partial_awaken_exp_survives_reload_and_next_material_finishes_level(self):
        self.card.update(awaken=2, awakeBuffLevel=2)
        self.upgrade()
        self.assertEqual((self.card['awakeBuffLevel'], self.card['SkillExp']), (2, 100))
        self.player = api.load()
        self.card, self.material = self.player['BattleCardList']
        self.upgrade()
        self.assertEqual((self.card['awakeBuffLevel'], self.card['SkillExp']), (3, 0))

    def test_maximum_awaken_skill_rejects_without_consumption(self):
        self.card['awakeBuffLevel'] = 2
        self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                     'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 1000})

    def test_invalid_missing_or_insufficient_materials_reject_atomically(self):
        for materials in [[], [{'battleCardNo': 9999, 'qty': 1}],
                          [{'battleCardNo': 1, 'qty': 1}], [{'battleCardNo': 2, 'qty': 0}],
                          [{'battleCardNo': 2, 'qty': -1}], [{'battleCardNo': 2, 'qty': 21}],
                          [{'battleCardNo': 2, 'qty': 15}, {'battleCardNo': 2, 'qty': 15}]]:
            with self.subTest(materials=materials):
                self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                             'MaterialCardList': materials, 'UsedGold': 1000})

    def test_wrong_type_and_locked_materials_reject_without_charge(self):
        for index, locked in [(60636, False), (60593, False), (60639, True)]:
            with self.subTest(index=index, locked=locked):
                self.material.update(BattleCardIndex=index, Lock=locked)
                self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                             'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 1000})

    def test_negative_cost_and_insufficient_gold_reject_without_changes(self):
        for gold in [-1, 100001]:
            with self.subTest(gold=gold):
                self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                             'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': gold})

    def test_favorite_and_equipped_materials_are_preserved(self):
        for favorite, equipped in [(True, False), (False, True)]:
            with self.subTest(favorite=favorite, equipped=equipped):
                self.material['LikeFlag'] = favorite
                self.player['CharacterList'] = [{'BattleCardNo7': 2}] if equipped else []
                self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                             'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 20})

    def test_captured_client_request_with_big_special_skill_material(self):
        self.material['BattleCardIndex'] = 60606
        response = self.upgrade(gold=20,
                                BaseCard={'battleCardNo': 1, 'battleCardIndex': 50281, 'qty': 0, 'count': 0},
                                MaterialCardList=[{'battleCardNo': 2, 'battleCardIndex': 60606, 'qty': 1, 'count': 0}],
                                CharacterIndex=369, CharacterLevel=140, CharacterPower=200044)
        self.assertEqual(response['battleCard']['awakeBuffLevel'], 2)
        self.assertEqual(response['battleCard']['skillExp'], 0)
        self.assertEqual(self.material['Qty'], 19)
        self.assertEqual(api.load()['AccountMoney']['Gold'], 99980)

    def test_missing_card_and_noninteger_quantities_do_not_consume_materials(self):
        self.reject_without_changes({'BaseCard': {'battleCardNo': 9999},
                                     'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 1000})
        for qty in [True, 1.5, '1', None]:
            with self.subTest(qty=qty):
                self.reject_without_changes({'BaseCard': {'battleCardNo': 1},
                                             'MaterialCardList': [{'battleCardNo': 2, 'qty': qty}], 'UsedGold': 1000})

    def test_request_cannot_supply_a_free_predicted_awaken_level(self):
        self.upgrade(BaseCard={'battleCardNo': 1, 'awakeBuffLevel': 99, 'skillExp': 999999})
        self.assertEqual((self.card['awakeBuffLevel'], self.card['SkillExp']), (2, 0))

    def test_fifth_awaken_caps_skill_at_six(self):
        self.card.update(awaken=5, awakeBuffLevel=5)
        self.upgrade(quantity=5, gold=5000)
        self.assertEqual((self.card['awakeBuffLevel'], self.card['SkillExp']), (6, 0))
        self.assertEqual(self.material['Qty'], 15)

    def test_oversized_selection_only_consumes_needed_quantity(self):
        self.upgrade(quantity=10, gold=10000)
        self.assertEqual(self.material['Qty'], 19)
        self.assertEqual(self.player['AccountMoney']['Gold'], 99000)
        self.assertEqual(self.card['awakeBuffLevel'], 2)

    def test_unawakened_skill_upgrade_keeps_existing_behavior(self):
        self.card.update(awaken=0, awakeBuffIndex=0, awakeBuffLevel=0, SkillLevel=1)
        self.upgrade()
        self.assertEqual(self.card['SkillLevel'], 2)
        self.assertEqual(self.card['awakeBuffLevel'], 0)

    def test_normal_card_exp_upgrade_does_not_change_awaken_skill(self):
        self.card['Exp'] = 0
        self.material['BattleCardIndex'] = 60593
        result = api.card_route('/api/card2/cardLevelUp', self.player, {
            'BaseCard': {'battleCardNo': 1},
            'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 1000})
        self.assertEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.card['Exp'], 6000)
        self.assertEqual(self.card['awakeBuffLevel'], 1)

    def test_camel_and_pascal_case_payloads_share_awaken_behavior(self):
        response = api.card_route('/api/card2/cardSkillUp', self.player, {
            'BaseBattleCard': {'BattleCardNo': 1},
            'BattleCardList': [{'BattleCardNo': 2, 'Qty': 1}], 'UsedGold': 1000})
        self.assertEqual(response['BattleCard']['awakeBuffLevel'], 2)

    def test_second_awaken_requires_skill_two_then_succeeds_after_upgrade(self):
        awaken_material = dict(self.material, BattleCardNo=3, BattleCardIndex=60592)
        self.player['BattleCardList'].append(awaken_material)
        request = {'BaseCard': {'battleCardNo': 1},
                   'MaterialCardList': [{'battleCardNo': 3, 'qty': 2}]}
        before = copy.deepcopy(self.player)
        result = api.card_awaken(self.player, request)
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)
        self.upgrade()
        result = api.card_awaken(self.player, request)
        self.assertEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(result['battleCard']['awaken'], 2)
        self.assertEqual(result['battleCard']['awakeBuffLevel'], 2)
        self.assertEqual(result['battleCard']['skillLevel'], 10)
        self.assertEqual(result['battleCard']['exp'], 47600)
        self.assertEqual(awaken_material['Qty'], 18)
        self.assertEqual(self.player['AccountMoney']['Gold'], 59000)
        self.assertEqual(api.load()['BattleCardList'][0]['awaken'], 2)

    def test_second_awaken_requires_the_current_card_level_cap(self):
        self.card.update(awakeBuffLevel=2, Exp=0)
        before = copy.deepcopy(self.player)
        result = api.card_awaken(self.player, {'BaseCard': {'battleCardNo': 1}, 'MaterialCardList': []})
        self.assertNotEqual(result.get('ResultCode', 0), 0)
        self.assertEqual(self.player, before)

    def test_ordinary_grade_up_still_resets_exp_and_preserves_skill(self):
        self.card.update(Grade=5, Exp=24000, awaken=0, awakeBuffIndex=0, awakeBuffLevel=0)
        result = api.card_route('/api/card2/cardGradeUp', self.player, {
            'BaseCard': {'battleCardNo': 1}, 'MaterialCardList': [], 'UsedGold': 0})
        self.assertEqual(result.get('ResultCode', 0), 0)
        self.assertEqual((self.card['Grade'], self.card['Exp'], self.card['SkillLevel']), (6, 0, 10))

    def test_lock_and_sell_other_cards_preserve_target_and_awaken_state(self):
        before = copy.deepcopy(self.card)
        result = api.card_route('/api/card2/cardLock', self.player, {'BattleCardNo': 1, 'Lock': True})
        self.assertTrue(result['BattleCard']['Lock'])
        before['Lock'] = True
        api.card_route('/api/card2/cardSell', self.player, {'BattleCardList': [{'BattleCardNo': 2, 'Qty': 1}]})
        self.assertEqual(self.card, before)


class CardSkillHTTPTest(CardSkillFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.player['AccountMoney'].update(ActivePoint=100, ActivePointMax=100,
                                           ActivePointUpdateTime=api.now_ms())
        api.save(self.player)
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
            connection.request('POST', '/api/card2/' + path, data, {'Content-Type': content_type})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            return json.loads(response.read())
        finally:
            connection.close()

    def test_encrypted_upgrade_then_second_awaken_and_disk_reload(self):
        self.player['BattleCardList'].append(dict(self.material, BattleCardNo=3, BattleCardIndex=60592))
        api.save(self.player)
        request = {'BaseCard': {'battleCardNo': 1},
                   'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 1000}
        result = self.post('cardSkillUp', request, encrypted=True)
        self.assertEqual(result['ResultCode'], 0)
        self.assertEqual(result['levelUpSuccess'], 1)
        self.assertEqual(result['battleCard']['awakeBuffLevel'], 2)
        result = self.post('cardAwaken', {'BaseCard': {'battleCardNo': 1},
                                        'MaterialCardList': [{'battleCardNo': 3, 'qty': 2}]}, encrypted=True)
        self.assertEqual(result['ResultCode'], 0)
        self.assertEqual(result['battleCard']['awaken'], 2)
        row = api.load()['BattleCardList'][0]
        self.assertEqual((row['awaken'], row['awakeBuffLevel'], row['SkillLevel']), (2, 2, 10))
        self.assertEqual(api.load()['AccountMoney']['Gold'], 59000)

    def test_http_maxed_skill_does_not_charge_or_return_success(self):
        self.card['awakeBuffLevel'] = 2
        api.save(self.player)
        before = api.load()
        result = self.post('cardSkillUp', {'BaseCard': {'battleCardNo': 1},
                                         'MaterialCardList': [{'battleCardNo': 2, 'qty': 1}], 'UsedGold': 1000})
        self.assertNotEqual(result['ResultCode'], 0)
        self.assertEqual(result['levelUpSuccess'], 0)
        self.assertEqual(api.load(), before)

    def test_encrypted_option_card_upgrade_returns_levels_used_by_client(self):
        self.card.update(BattleCardIndex=60491, SkillIndex=0, SkillLevel=1,
                         awaken=0, awakeBuffIndex=0, awakeBuffLevel=0,
                         PassiveIndex1=910002, PassiveLevel1=1,
                         PassiveIndex2=910031, PassiveLevel2=1)
        api.save(self.player)
        result = self.post('cardSkillUp', {
            'BaseCard': {'battleCardNo': 1, 'battleCardIndex': 60491, 'qty': 0, 'count': 0},
            'MaterialCardList': [{'battleCardNo': 2, 'qty': 2, 'count': 0}],
            'UsedGold': 40}, encrypted=True)
        self.assertEqual(result['levelUpSuccess'], 1)
        self.assertEqual((result['battleCard']['passiveLevel1'],
                          result['battleCard']['passiveLevel2']), (3, 3))
        self.assertEqual(api.load()['BattleCardList'][0]['PassiveLevel1'], 3)


if __name__ == '__main__':
    unittest.main()
