"""Optional settings for the single local account, applied by normal profile I/O."""
from pathlib import Path
import json

SETTINGS_PATH = Path(__file__).with_name('account-preset.json')


def apply(player):
    if not SETTINGS_PATH.exists():
        return False
    config = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
    account = player.get('PlayerAccount', {})
    if str(account.get('Usn')) != str(config['usn']):
        return False
    for name in ('rank', 'exp_min', 'exp_max', 'tier', 'rating'):
        if type(config[name]) is not int or config[name] < 0:
            raise ValueError('invalid local account preset')
    if config['exp_min'] > config['exp_max'] or not config.get('revision'):
        raise ValueError('invalid account EXP interval or revision')
    changed = False

    def assign(row, key, value):
        nonlocal changed
        if row.get(key) != value:
            row[key] = value
            changed = True

    if player.get('LocalAccountPresetRevision') != config['revision']:
        state = player.setdefault('AllOut', {})
        for key in ('Rating', 'Best'):
            assign(state, key, max(int(state.get(key, 0)), config['rating']))
        assign(state, 'PrevGrade', config['tier'])
        assign(player, 'LocalAccountPresetRevision', config['revision'])
    # At maximum rank, the client must stay inside the last table row's EXP interval.
    exp = min(config['exp_max'], max(config['exp_min'], int(account.get('Exp', 0))))
    assign(account, 'Exp', exp)
    assign(player, 'LastAccountLevel', config['rank'])
    return changed
