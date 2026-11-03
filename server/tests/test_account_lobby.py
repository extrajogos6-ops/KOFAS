import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor'), str(ROOT.parent / 'scripts')]
import local_player as api
import local_account_preset as preset
import local_lobby_account_setup as setup
import local_awaken_balance as codec
from local_progression import _fields


def rows(data):
    return [dict(_fields(value)) for number, value in _fields(data) if number == 1]


class AccountLobbyTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = setup.build_patch(ROOT)
        cls.key = json.loads((ROOT / 'packs-claude/security.json').read_text())['SecurityDataTable']

    def table(self, name):
        return rows(codec._unpack(self.files['packs-claude/table.dat'], name, self.key))

    def test_native_level_lookup_reaches_500_with_correct_exp_interval(self):
        levels = self.table('accountlevelingtable.bin')
        self.assertEqual([r[2] for r in levels], list(range(1, 501)))
        # Native GetAccountLevel returns the first row whose cumulative EXP exceeds current EXP.
        level = lambda exp: next((r[2] for r in levels if exp < r[4]), 1)
        self.assertEqual(level(18780), 19)
        self.assertEqual(level(12474999), 499)
        self.assertEqual(level(12475000), 500)
        self.assertEqual(level(12524999), 500)
        self.assertEqual(levels[-1][2], 500)

    def test_horizontal_and_hide_ui_backgrounds_use_existing_landscape_half(self):
        for row in self.table('lobbybgsettingtable.bin'):
            self.assertEqual(row[3].decode(), setup.BACKGROUND)
            self.assertEqual(row[7].decode(), setup.BACKGROUND)
            self.assertEqual((row.get(6, 0), row.get(8, 0)), (1, 1))

    def test_other_tables_and_previous_account_levels_are_untouched(self):
        from io import BytesIO
        from zipfile import ZipFile
        before = (ROOT / 'packs-claude/table.dat').read_bytes()
        with ZipFile(BytesIO(before)) as old, ZipFile(BytesIO(self.files['packs-claude/table.dat'])) as new:
            self.assertEqual(old.namelist(), new.namelist())
            for name in old.namelist():
                if name not in ('accountlevelingtable.bin', 'lobbybgsettingtable.bin'):
                    self.assertEqual(old.read(name), new.read(name), name)
        original = rows(codec._unpack(before, 'accountlevelingtable.bin', self.key))
        self.assertEqual(self.table('accountlevelingtable.bin')[:100], original)

    def test_preset_and_updated_manifest_are_coherent(self):
        import hashlib
        meta = json.loads(codec._crypt(self.files['packs-claude/table.kof'], self.key))
        for row in meta:
            name = row['name'].lower() + '.bin'
            plain = codec._unpack(self.files['packs-claude/table.dat'], name, self.key)
            self.assertEqual(hashlib.md5(plain).hexdigest(), row['hash'])
        config = json.loads(self.files.get('account-preset.json', b'{}'))
        self.assertEqual((config.get('rank'), config.get('tier'), config.get('rating')), (500, 25, 3400))
        self.assertEqual((config['exp_min'], config['exp_max']), (12475000, 12524999))

    def test_second_generation_does_not_increment_versions_or_change_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in self.files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            (root / 'packs-claude/security.json').write_bytes((ROOT / 'packs-claude/security.json').read_bytes())
            self.assertEqual(setup.build_patch(root), self.files)

    def test_setup_preserves_installed_linear_awaken_effects(self):
        from io import BytesIO
        from zipfile import ZipFile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linear = codec.build_patch(ROOT)
            for name, content in linear.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            (root / 'packs-claude/security.json').write_bytes((ROOT / 'packs-claude/security.json').read_bytes())
            changed = setup.build_patch(root)
            with ZipFile(BytesIO(linear['packs-claude/table.dat'])) as before, \
                    ZipFile(BytesIO(changed['packs-claude/table.dat'])) as after:
                for name in ('bufftable.bin', 'battlecardawakebufftable.bin'):
                    self.assertEqual(before.read(name), after.read(name))


class AccountPresetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.settings = directory / 'preset.json'
        self.config = {'usn': 1000001, 'rank': 500, 'exp_min': 12475000, 'exp_max': 12524999,
                       'tier': 25, 'rating': 3400, 'revision': 'rank500-diamond1-v1'}
        self.settings.write_text(json.dumps(self.config))
        self.player = {'PlayerAccount': {'Usn': 1000001, 'Exp': 18780}, 'LastAccountLevel': 19,
                       'AllOut': {'Rating': 1023, 'Best': 1023, 'PrevGrade': 1, 'AtkWin': 1},
                       'AccountMoney': {'Gold': 12345}, 'CharacterList': [{'CharacterIndex': 338, 'Exp': 456}],
                       'BattleCardList': [{'BattleCardNo': 1, 'awakeBuffLevel': 6}], 'AccountGrowthStat': {'11': 20}}
        for obj, name, value in [(preset, 'SETTINGS_PATH', self.settings),
                                  (api, 'PATH', directory / 'player.json')]:
            handle = patch.object(obj, name, value)
            handle.start()
            self.addCleanup(handle.stop)

    def test_rank_and_diamond_promotion_preserve_inventory_and_other_progress(self):
        before = copy.deepcopy(self.player)
        self.assertTrue(preset.apply(self.player))
        self.assertEqual(self.player['PlayerAccount']['Exp'], 12475000)
        self.assertEqual(self.player['LastAccountLevel'], 500)
        self.assertEqual(self.player['AllOut'], dict(before['AllOut'], Rating=3400, Best=3400, PrevGrade=25))
        for field in ('AccountMoney', 'CharacterList', 'BattleCardList', 'AccountGrowthStat'):
            self.assertEqual(self.player[field], before[field])
        self.assertEqual(api.allout_grade(api.allout_cfg(), self.player['AllOut']['Rating']), 25)

    def test_diamond_one_uses_real_account_bonus_not_just_a_display_label(self):
        from local_progression import _table_rows
        preset.apply(self.player)
        extra = {row['Key']: row['Value'] for row in api.fame_extras(self.player)}
        self.assertEqual(extra['mode209Tier'], '25')
        grade = next(r for r in _table_rows('alloutfightgradetable.bin') if r[2] == 25)
        self.assertTrue(grade[11].endswith(b'/Diamond1'))
        self.assertEqual(grade[5], 3400)
        bonus = next(r for r in _table_rows('accounttierbonustable.bin') if r[3] == 25)
        self.assertEqual([bonus[n] for n in (8, 9, 10, 11)], [100, 1000, 50, 100])

    def test_real_save_and_reload_apply_preset_and_cap_future_exp(self):
        api.save(self.player)
        self.assertEqual(api.load()['PlayerAccount']['Exp'], 12475000)
        self.player['PlayerAccount']['Exp'] = 12525030
        api.save(self.player)
        self.assertEqual(api.load()['PlayerAccount']['Exp'], 12524999)

    def test_promotion_does_not_reset_later_play_and_repeated_calls_are_stable(self):
        preset.apply(self.player)
        self.player['AllOut']['Rating'] = 3350
        self.player['AllOut']['AtkWin'] = 2
        before = copy.deepcopy(self.player)
        self.assertFalse(preset.apply(self.player))
        self.assertEqual(self.player, before)

    def test_no_config_or_different_account_is_untouched(self):
        self.player['PlayerAccount']['Usn'] = 999
        before = copy.deepcopy(self.player)
        self.assertFalse(preset.apply(self.player))
        self.assertEqual(self.player, before)
        self.settings.unlink()
        self.assertFalse(preset.apply(self.player))
        self.assertEqual(self.player, before)
