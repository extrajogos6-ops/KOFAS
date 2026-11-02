from dataclasses import dataclass
from functools import lru_cache

from local_progression import _table_rows


@lru_cache(maxsize=1)
def _tables():
    cards = {row[2]: row for row in _table_rows('battlecardtable.bin')}
    gauges = {(row[10], row[2]): row[12] for row in _table_rows('battleskilluptable.bin')}
    config = next(row for row in _table_rows('configtable.bin') if row[2] == 4036)
    return cards, gauges, int(config[4])


def integer(value, minimum=0):
    if type(value) is not int or value < minimum or value > 2147483647:
        raise ValueError('invalid card quantity, level or cost')
    return value


def material_key(row, names, default=None):
    for name in names:
        if name in row:
            return row[name]
    return default


def awaken_skill_max(row):
    return integer(row.get('awaken', 0), 1) + _tables()[2]


def _gauges(row):
    cards, gauges, _ = _tables()
    definition = cards.get(row['BattleCardIndex'])
    if definition is None:
        raise ValueError('unknown battle card')
    grade = definition[7]
    maximum = awaken_skill_max(row)
    result = [integer(gauges[(grade, level)], 1) for level in range(1, maximum)]
    return definition, result


@dataclass(frozen=True)
class SkillUpgrade:
    level: int
    exp: int
    materials: tuple[tuple[int, int], ...]
    gold: int


def plan_awaken_skill(player, row, materials, used_gold):
    used_gold = integer(used_gold)
    definition, gauges = _gauges(row)
    level = integer(row.get('awakeBuffLevel', 0), 1)
    exp = integer(row.get('SkillExp', 0))
    maximum = len(gauges) + 1
    if level >= maximum:
        raise ValueError('already max awaken skill for this awakening')
    if not materials or not isinstance(materials, list):
        raise ValueError('no skill materials selected')
    requested = {}
    for material in materials:
        if not isinstance(material, dict):
            raise ValueError('invalid skill material')
        no = integer(material_key(material, ('BattleCardNo', 'battleCardNo')), 1)
        qty = integer(material_key(material, ('Qty', 'qty', 'count'), 1), 1)
        requested[no] = integer(requested.get(no, 0) + qty, 1)
    cards = {card['BattleCardNo']: card for card in player['BattleCardList']}
    equipped = {character.get('BattleCardNo%d' % slot)
                for character in player.get('CharacterList', []) for slot in range(1, 9)}
    table_cards = _tables()[0]
    sources = []
    for no, qty in requested.items():
        source = cards.get(no)
        if source is None or no == row['BattleCardNo']:
            raise ValueError('missing or invalid skill material')
        if source.get('Lock') or source.get('LikeFlag') or no in equipped:
            raise ValueError('protected skill material')
        available = source.get('Qty', 1) if source.get('StackFlag') else 1
        if qty > integer(available, 1):
            raise ValueError('not enough skill materials')
        material_definition = table_cards.get(source['BattleCardIndex'], {})
        if material_definition.get(5) != 7 or material_definition.get(61) != definition[5]:
            raise ValueError('wrong skill material type')
        gain = integer(material_definition.get(47), 1)
        sources.append((no, qty, gain))
    room = sum(gauges[level - 1:]) - exp
    if room <= 0:
        raise ValueError('inconsistent awaken skill EXP')
    selected = []
    gained = 0
    for no, quantity, gain in sources:
        used = min(quantity, (room + gain - 1) // gain)
        if used:
            selected.append((no, used))
            gained += gain * used
            room -= gain * used
        if room <= 0:
            break
    count = sum(quantity for _, quantity in selected)
    gold = used_gold * count // sum(requested.values())
    if integer(player['AccountMoney']['Gold']) < gold:
        raise ValueError('not enough gold')
    exp += gained
    while level < maximum and exp >= gauges[level - 1]:
        exp -= gauges[level - 1]
        level += 1
    if level == maximum:
        exp = 0
    return SkillUpgrade(level, exp, tuple(selected), gold)
