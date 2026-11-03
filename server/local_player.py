"""Single local player profile, persisted in player.json next to this file.

Shapes follow NEO.Kof.Api.Protocol (UseProtoToJSON=y -> PascalCase JSON). Values are local defaults.
"""
import json
import os
import random
import math
import threading
import time
from pathlib import Path
import local_poll
import local_progression
import local_card_progression
import local_account_preset

# KOFAS_PLAYER=<file>: run on another profile (in-game item tests on a fixture account) without moving the real player.json
PATH = Path(os.environ['KOFAS_PLAYER']).resolve() if os.environ.get('KOFAS_PLAYER') else Path(__file__).resolve().parent / 'player.json'
LOCK = threading.Lock()
PID = '1000001'
USN = 1000001


def now_ms():
    return int(time.time() * 1000)


def load():
    with LOCK:
        if PATH.exists():
            player = json.loads(PATH.read_text(encoding='utf-8'))
        else:
            return None
    if local_account_preset.apply(player):
        save(player)
    return player


def save(player):
    local_account_preset.apply(player)
    with LOCK:
        tmp = PATH.with_suffix('.tmp')
        tmp.write_text(json.dumps(player, indent=1, ensure_ascii=False), encoding='utf-8')
        tmp.replace(PATH)


def new_character(index, grade=3):   # original fighters start at 3 stars
    return {'CharacterIndex': index, 'Grade': grade, 'Exp': 0, 'LikeFlag': False,
            'BattleCardNo1': 0, 'BattleCardNo2': 0, 'BattleCardNo3': 0, 'BattleCardNo4': 0,
            'BattleCardNo5': 0, 'BattleCardNo6': 0, 'BattleCardNo7': 0, 'BattleCardNo8': 0,
            'CreateTime': now_ms(), 'LimitBreakGrade': 0, 'LimitBreakProgressCount': 0,
            'EnchantHp': 0, 'EnchantAtk': 0, 'EnchantDef': 0, 'AffectionExp': 0, 'RewardList': '',
            'Awaken': 0, 'AwakenExp': 0, 'ex': 0, 'ImprintStoneNo1': 0, 'ImprintStoneNo2': 0,
            'ImprintStoneNo3': 0, 'ImprintStoneNo4': 0, 'ImprintStoneNo5': 0, 'corePoint': 0}


def create(nickname, character_index):
    t = now_ms()
    player = {
        'Route': {'Pid': PID, 'Usn': USN, 'GameDb': 1, 'CertKey': 'local', 'CountryCode': 'US',
                  'RegionCode': 'local', 'NickName': nickname, 'FirstConnectDatetime': t,
                  'LastConnectDatetime': t, 'AccountId': PID},
        'ProfileCharacter': {'CharacterIndex': character_index, 'Message': '', 'TeamDeck': 1,
                             'CharacterIndex2': 0, 'CharacterIndex3': 0},
        'PlayerAccount': {'Usn': USN, 'Exp': 0},
        'AccountMoney': {'ActivePoint': 100, 'ActivePointMax': 100, 'ActivePointUpdateTime': t,
                         'ActivePointGiveClientTime': t, 'DeltaActivePoint': 0, 'Gold': 100000,
                         'BuffGold': 0, 'Cash': 1000, 'PaymentCash': 0, 'FriendPoint': 0, 'SoulToken': 0,
                         'ColosseumCoin': 0, 'ColosseumTicket': 0, 'Topaz': 0, 'SoulDust': 0,
                         'ArenaLeagueCoin': 0, 'ArenaLeagueTicket': 0, 'GuildCoin': 0, 'ExpirationCash': 0},
        'CharacterList': [new_character(character_index)],
        'TeamDeckList': [{'DeckNo': 1, 'CharacterIndex1': character_index, 'CharacterIndex2': 0,
                          'CharacterIndex3': 0, 'SupportCharacterIndex1': 0, 'SupportCharacterIndex2': 0,
                          'SupportCharacterIndex3': 0, 'DeckName': '', 'TeamRelationIndex': 0,
                          'GroupGrowthIndex': 0}],
        'BattleCardInvenSize': {'Qty': 0, 'MaxSize': 200},
        'QuestList': [],
        'OptionInfoList': [],
    }
    save(player)
    return player


ROSTER_PATH = Path(__file__).resolve().parent / 'roster.json'   # written by make_data.py (every playable fighter)
TEAM_JAPAN = (101, 104, 110)   # Kyo, Benimaru, Goro (indices follow make_data's sorted roster)


START_ITEMS = {1000: 200, 1001: 100, 1002: 50, 1003: 20, 1093: 100, 1094: 100, 1095: 100, 2001: 300,
               # evolution materials (make_data): Jade 2101-2103, Sword 2111-2113, Mirror 2121-2123 (lower/middle/upper),
               # rainbow 2110/2120/2130. Starter stock is my choice.
               2101: 80, 2111: 80, 2121: 80, 2102: 50, 2112: 50, 2122: 50, 2103: 30, 2113: 30, 2123: 30,
               2110: 6, 2120: 6, 2130: 6,
               # core items (make_data): Ruby 2201-2203, Sapphire 2211-2213, Emerald 2221-2223, Amethyst 2231-2233,
               # Rainbow 2241-2243 (triangle/square/hexagon). Starter stock is my choice.
               **{b + t: q for b in (2201, 2211, 2221, 2231) for t, q in ((0, 200), (1, 120), (2, 60))},
               2241: 20, 2242: 20, 2243: 20,
               # affection gifts (make_data): 4001 Cup of Tea, 4002 Fruit Tart, 4003 Party Gift Box. Starter stock is my choice.
               4001: 50, 4002: 30, 4003: 10,
               # awaken materials (make_data): Awaken Tier 1-5 EXP Capsules 4101/4103-4106, Element Memories 61031-61095
               # (frameGrade*10 + element), Dimensional Invitations 61105/61109. Fighter Memories 60000 + index (items()).
               # Starter stock is my choice (generous, like the rest of this save).
               4101: 60, 4103: 9999, 4104: 9999, 4105: 9999, 4106: 9999,
               # limit break substitutes (make_data): Element Souls 30901-30905, Rainbow 30999, Tier Souls 31103-31309
               4311: 300, 4312: 100, 4313: 30,   # Fame medals (bronze/silver/gold, make_data FAME_MEDALS)
               4321: 20, 4322: 20,   # Dispatch Ticket / Speed Up Ticket (make_data DISPATCH_*)
               **{30900 + e: 999 for e in range(1, 6)}, 30999: 99, **{31000 + y * 100 + g: 99 for y in (1, 2, 3) for g in (3, 4, 5, 9)},
               **{61000 + g * 10 + s: 999 for g in (3, 4, 5, 9) for s in range(1, 6)}, 61105: 999, 61109: 999,
               # imprint enchant kits (make_data): S 4301, M 4302, L 4303. Starter stock is my choice.
               4301: 30, 4302: 15, 4303: 5,
               # imprint polishing material (make_data): Polishing Core 4304. Starter stock is my choice.
               4304: 40}
CORE_ITEM_BASE = (2201, 2211, 2221, 2231)
EVO_BASE = (2101, 2111, 2121)
BASE_MAX_LEVEL = local_progression.BASE_MAX_LEVEL


def exp_for_level(lv, character_index=None):
    return local_progression.exp_for_level(lv, character_index)
GROWTH_LOG = Path(__file__).resolve().parent / 'growth-requests.jsonl'


SOUL_BASE, START_SOULS = 30000, 60
MEM_BASE, START_MEMORIES = 60000, 5   # fighter Memory item = 60000 + CharacterIndex (make_data)
RETIRED_ITEMS = {4102}   # soul item per fighter = 30000 + CharacterIndex (limit break material)
# Soul Dust (make_data SOUL_DUST_ITEM): an item of ItemType 18 in PC 1.11.2 - the client never reads GoodsType 33 SoulDust
SOUL_DUST_ITEM = 4400


def items(player):
    inv = player.setdefault('ItemList', [])
    have = {i['ItemIndex'] for i in inv}
    roster = json.loads(ROSTER_PATH.read_text()) if ROSTER_PATH.exists() else []
    wanted = dict(START_ITEMS)
    wanted.update({SOUL_BASE + c: START_SOULS for c in roster})
    wanted.update({MEM_BASE + c: START_MEMORIES for c in roster})   # each fighter's own Memory (awakening material)
    added = False
    if any(i['ItemIndex'] in RETIRED_ITEMS for i in inv):   # items no longer in the tables (old Awaken Shard)
        inv[:] = [i for i in inv if i['ItemIndex'] not in RETIRED_ITEMS]; added = True
    money = player.get('AccountMoney') or {}
    if int(money.get('SoulDust') or 0) > 0:   # Soul Dust moved from the (unread) GoodsType 33 currency to the item SOUL_DUST_ITEM
        row = next((i for i in inv if i['ItemIndex'] == SOUL_DUST_ITEM), None)
        if row is None:
            row = {'ItemIndex': SOUL_DUST_ITEM, 'Qty': 0, 'Lock': False}; inv.append(row)
        row['Qty'] = int(row['Qty']) + int(money['SoulDust']); money['SoulDust'] = 0; added = True
    for k, v in wanted.items():   # starter stock for items this save has never had
        if k not in have:
            inv.append({'ItemIndex': k, 'Qty': v, 'Lock': False})
            added = True
    if added:
        save(player)
    return inv


QTY_MAX = 2 ** 31 - 1   # the client's Item.Qty is an int32


def item_need(entries):
    """Request item entries [{ItemIndex, Qty}] -> ({index: summed Qty}, error or None). Every Qty must be a whole number in
    0..QTY_MAX (0 entries are ignored); an index listed twice is summed. Changes nothing. (Before: a negative Qty passed the
    stock checks and take_items then ADDED it; a repeated index was checked entry by entry and could go negative.)"""
    need = {}
    for u in entries or []:
        try:
            idx, qty = int(u.get('ItemIndex') or 0), int(u.get('Qty') or 0)
        except (TypeError, ValueError, AttributeError):
            return {}, 'bad item entry'
        if not 0 <= qty <= QTY_MAX:
            return {}, 'bad quantity'
        if qty:
            if idx <= 0:
                return {}, 'bad item'
            need[idx] = need.get(idx, 0) + qty
    return need, None


def req_count(payload, *keys, default=1):
    """A count from the request: the first present key's value, which must be 1..QTY_MAX; `default` when no key is present;
    None when invalid (0, negative, not a number). These counts used to be forced to >= 1 (a 0 or -3 opened / bought 1)."""
    for k in keys:
        v = payload.get(k) if isinstance(payload, dict) else None
        if v is not None:
            try:
                v = int(v)
            except (TypeError, ValueError):
                return None
            return v if 1 <= v <= QTY_MAX else None
    return default


def item_short(player, need):
    """First item index of `need` the inventory cannot pay, else None."""
    inv = {i['ItemIndex']: int(i['Qty']) for i in items(player)}
    return next((k for k, q in need.items() if inv.get(k, 0) < q), None)


def item_error(player, entries):
    """Error message when the request entries are invalid or not affordable, else None (nothing is changed)."""
    need, err = item_need(entries)
    if err:
        return err
    return 'not enough items' if item_short(player, need) is not None else None


def take_items(player, used):
    """Subtract request Item entries (ItemIndex/Qty = amount used, repeated indices summed) and return the updated rows; None
    with nothing changed when an entry is invalid or the stock cannot pay (it used to clamp at 0 and succeed anyway)."""
    need, err = item_need(used)
    if err or item_short(player, need) is not None:
        return None
    inv = {i['ItemIndex']: i for i in items(player)}
    out = []
    for k, q in need.items():
        inv[k]['Qty'] = int(inv[k]['Qty']) - q
        out.append(inv[k])
    return out


def character(player, idx):
    return next((c for c in player['CharacterList'] if c['CharacterIndex'] == idx), None)


CARDS_PATH = Path(__file__).resolve().parent / 'battlecards.json'   # written by make_data.py
GROUPS_PATH = Path(__file__).resolve().parent / 'char_groups.json'   # written by make_data.py (year version -> base fighter)
SERIES_PATH = Path(__file__).resolve().parent / 'series.json'   # written by make_data.py (story series indices)
STORY_ROWS_PATH = Path(__file__).resolve().parent / 'story_rows_index.json'   # written by make_data.py: [[story row, next stage], ...]
SERIES_OF_YEAR = {94: 1, 95: 2, 96: 3, 97: 4, 98: 5, 99: 6, 100: 7, 101: 8, 102: 9}   # stage index = Y*10000 + chapter*100 + stage, Y = YY (2000-2002: 100-102), make_data story block


def stage_meta(idx):
    """(SeriesIndex, Chapter, StageDifficulty) of a story stage index. make_data offsets harder difficulties by
    DIFF_STAGE_OFF = 200000000 * (d - 1) on the stage and DIFF_CH_OFF = 2000000 * (d - 1) on the chapter."""
    d = idx // 200000000 + 1; base = idx % 200000000
    return SERIES_OF_YEAR.get(base // 10000, 1), base // 100 + 2000000 * (d - 1), d


def battle_cards(player):
    """One copy of every generated skill card (BattleCardNo = 1..n). Saves when cards were added."""
    defs = json.loads(CARDS_PATH.read_text()) if CARDS_PATH.exists() else []
    # card indices are positions in battlecards.json: when that list changes, old card rows would point at other cards,
    # so rebuild the collection and clear equipment (auto_equip_cards refills slots 7/8 below).
    sig = 'stable:%d' % len(defs)
    # since 2026-10-14 card indices are frozen (make_data card_index.json): a changed list only adds cards, so the
    # collection is kept; the one-time rebuild below is for saves from the old position-based numbering.
    if player.get('CardsVersion') != sig:
        if not str(player.get('CardsVersion', '')).startswith('stable'):
            player['BattleCardList'] = []
            for ch in player['CharacterList']:
                for k in range(1, 9):
                    ch['BattleCardNo%d' % k] = 0
            player['CardsGranted'] = []
        player['CardsVersion'] = sig
    lst = player.setdefault('BattleCardList', [])
    # each card definition is granted once; sold / consumed cards do not come back
    have = set(player.setdefault('CardsGranted', [])) | {c['BattleCardIndex'] for c in lst}
    no = max([c['BattleCardNo'] for c in lst] + [0])
    added = False
    for d in defs:
        if d['BattleCardIndex'] in have:
            continue
        no += 1
        player['CardsGranted'].append(d['BattleCardIndex'])
        lst.append({'BattleCardNo': no, 'BattleCardIndex': d['BattleCardIndex'], 'Grade': d.get('Grade', 1), 'Status': 0, 'Exp': 0,
                    'Lock': False, 'LikeFlag': False, 'SkillIndex': d['SkillIndex'], 'SkillLevel': 1,
                    'PassiveIndex1': 0, 'PassiveLevel1': 0, 'PassiveIndex2': 0, 'PassiveLevel2': 0,
                    'PassiveIndex3': 0, 'PassiveLevel3': 0, 'CreateTime': now_ms(), 'Stat': d.get('Stat', ''),
                    'StackFlag': d.get('Stack', 0), 'Qty': d.get('Qty', 1), 'SkillExp': 0})
        added = True
    # year versions (Kyo '95...) equip their base fighter's cards; the base has one copy of each, so every version
    # gets two extra copies once (different cards per version where the base has enough)
    groups = {int(k): v for k, v in json.loads(GROUPS_PATH.read_text()).items()} if GROUPS_PATH.exists() else {}
    vdone = player.setdefault('VariantCardsGranted', [])
    owned = {ch['CharacterIndex'] for ch in player['CharacterList']}
    per_base = {}
    for vci in sorted(groups):
        base = groups[vci]
        n_before = per_base.get(base, 0); per_base[base] = n_before + 1
        if vci in vdone or vci not in owned:
            continue
        pool = sorted((d for d in defs if d.get('Character') == base and d.get('SkillIndex')),
                      key=lambda d: (not d.get('Extra'), d['BattleCardIndex']))
        for d in [pool[(2 * n_before + i) % len(pool)] for i in range(2)] if pool else []:
            no += 1
            lst.append({'BattleCardNo': no, 'BattleCardIndex': d['BattleCardIndex'], 'Grade': d.get('Grade', 1), 'Status': 0,
                        'Exp': 0, 'Lock': False, 'LikeFlag': False, 'SkillIndex': d['SkillIndex'], 'SkillLevel': 1,
                        'PassiveIndex1': 0, 'PassiveLevel1': 0, 'PassiveIndex2': 0, 'PassiveLevel2': 0,
                        'PassiveIndex3': 0, 'PassiveLevel3': 0, 'CreateTime': now_ms(), 'Stat': d.get('Stat', ''),
                        'StackFlag': d.get('Stack', 0), 'Qty': d.get('Qty', 1), 'SkillExp': 0})
        vdone.append(vci)
        added = True
    by_idx = {d['BattleCardIndex']: d for d in defs}
    gone = [c for c in lst if c['BattleCardIndex'] not in by_idx]   # cards removed from the table: drop + unequip
    for c in gone:
        lst.remove(c)
        for ch in player['CharacterList']:
            for k in range(1, 9):
                if ch.get('BattleCardNo%d' % k) == c['BattleCardNo']:
                    ch['BattleCardNo%d' % k] = 0
        added = True
    for c in lst:   # keep rows in line with battlecards.json: base stats, option skills, minimum grade
        d = by_idx.get(c['BattleCardIndex'], {})
        st = d.get('Stat', '')
        if st and c.get('Stat') != st:
            c['Stat'] = st
            added = True
        for n in (1, 2, 3):
            pi, pl = (d.get('Passive') or [])[n - 1] if len(d.get('Passive') or []) >= n else (0, 0)
            if c.get('PassiveIndex%d' % n) != pi:
                c['PassiveIndex%d' % n] = pi
                c['PassiveLevel%d' % n] = max(pl, c.get('PassiveLevel%d' % n) or 0) if pi else 0
                added = True
        if c.get('Grade', 1) < d.get('Grade', 1):
            c['Grade'] = d['Grade']
            added = True
        if sync_card_passive_levels(c):
            added = True
    if auto_equip_cards(player, defs):
        added = True
    if added:
        save(player)
    return lst


def card_defs():
    return {d['BattleCardIndex']: d for d in (json.loads(CARDS_PATH.read_text()) if CARDS_PATH.exists() else [])}


def sync_card_passive_levels(row):
    """Option/set cards display their passive level, not the saved SkillLevel.

    Reconcile levels already earned with the old handler; never charge again or
    touch active skills, absent passive slots, or awakening buff levels.
    """
    if row.get('SkillIndex', 0):
        return False
    level = min(10, max(1, int(row.get('SkillLevel', 1))))
    changed = False
    for slot in (1, 2, 3):
        field = 'PassiveLevel%d' % slot
        if row.get('PassiveIndex%d' % slot) and int(row.get(field, 0)) < level:
            row[field] = level
            changed = True
    return changed


def consume_cards(player, used):
    """Remove material/fodder cards (MaterialCard or BattleCardVO dicts); stacked rows lose Qty. Returns
    (exp value, gold value) of what was used (battlecards.json Exp / Price; skill cards count 100 exp, 1000 gold)."""
    defs = card_defs()
    lst = player.get('BattleCardList', [])
    exp = gold = 0
    for u in used or []:
        no = int(u.get('BattleCardNo') or u.get('battleCardNo') or 0)
        qty = int(u.get('Qty') or u.get('qty') or u.get('count') or 1)
        row = next((c for c in lst if c['BattleCardNo'] == no), None)
        if row is None:
            continue
        d = defs.get(row['BattleCardIndex'], {})
        if row.get('StackFlag'):
            qty = min(qty, row['Qty'])
            row['Qty'] -= qty
            if row['Qty'] <= 0:
                lst.remove(row)
        else:
            qty = 1
            lst.remove(row)
            for ch in player['CharacterList']:
                for k in range(1, 9):
                    if ch.get('BattleCardNo%d' % k) == no:
                        ch['BattleCardNo%d' % k] = 0
        exp += qty * d.get('Exp', 100)
        gold += qty * d.get('Price', 1000)
    return exp, gold


CARD_END_GRADE = 6   # make_data BattleCardTable cardEndGrade


def card_max_exp(row):
    """Exp at the card's max level (make_data cardlevel.json): row (MaxLevel - 1) of the leveling curve, MaxLevel = growth
    maxLv by grade + 5 per card awaken (BattleCardStatCalculator.MaxLevel). None when the config is missing."""
    path = Path(__file__).with_name('cardlevel.json')
    if not path.exists():
        return None
    cfg = json.loads(path.read_text())
    mx = int(cfg['maxLv'].get(str(row.get('Grade', 1)), 10)) + int(cfg.get('awakenAddLv', 5)) * int(row.get('awaken') or 0)
    rows = cfg['rowExp']
    return int(rows[max(0, min(len(rows), mx - 1) - 1)])


def lc_card(row):
    """card2/* responses are read by NetworkManagerWEB.MakeBattleCardInfo with camelCase keys (battleCardNo, grade...)."""
    return {k[:1].lower() + k[1:]: v for k, v in row.items()}


def new_card_row(player, d, grade=None):
    lst = player.setdefault('BattleCardList', [])
    no = max([c['BattleCardNo'] for c in lst] + [0]) + 1
    row = {'BattleCardNo': no, 'BattleCardIndex': d['BattleCardIndex'], 'Grade': grade or d.get('Grade', 1), 'Status': 0,
           'Exp': 0, 'Lock': False, 'LikeFlag': False, 'SkillIndex': d.get('SkillIndex', 0), 'SkillLevel': 1,
           'PassiveIndex1': 0, 'PassiveLevel1': 0, 'PassiveIndex2': 0, 'PassiveLevel2': 0, 'PassiveIndex3': 0,
           'PassiveLevel3': 0, 'CreateTime': now_ms(), 'Stat': d.get('Stat', ''), 'StackFlag': d.get('Stack', 0),
           'Qty': 1, 'SkillExp': 0}
    for n, (pi, pl) in enumerate(d.get('Passive') or [], 1):
        row['PassiveIndex%d' % n], row['PassiveLevel%d' % n] = pi, pl
    lst.append(row)
    return row


def card_combine(player, payload):
    """card2/cardCombine. Original (namu/appmedia): combine 5 cards of 3-4 stars -> low chance of one card a star higher;
    since 2020 it always also gives a skill-up card. Here: 25% chance of a random card of the materials' kind at
    combineGrade+1, plus always one skill-up card stack (+1). Rates are mine."""
    defs = card_defs()
    mats = payload.get('materialCardList') or payload.get('MaterialCardList') or []
    lst = player.get('BattleCardList', [])
    kinds = [defs.get(next((c['BattleCardIndex'] for c in lst if c['BattleCardNo'] == int(m.get('battleCardNo') or m.get('BattleCardNo') or 0)), 0), {}).get('Type', 3) for m in mats]
    consume_cards(player, mats)
    grade = int(payload.get('combineGrade') or 3)
    kind = max(set(kinds), key=kinds.count) if kinds else 3
    rewards = []
    if random.random() < 0.25:
        pool = [d for d in defs.values() if d.get('Type', 3) == kind]
        if pool:
            rewards.append(new_card_row(player, random.choice(pool), min(6, grade + 1)))
    skill_up = {3: 'Special', 4: 'Set', 2: 'Passive'}.get(kind, 'Special')
    for c in lst:   # +1 to the matching skill-up card stack (largest size owned)
        d = defs.get(c['BattleCardIndex'], {})
        if c.get('StackFlag') and d.get('SkillUp') == skill_up:
            c['Qty'] += 1
            rewards.append(c)
            break
    save(player)
    return {'levelUpSuccess': 1 if len(rewards) > 1 else 0, 'accountMoney': player['AccountMoney'],
            'AccountMoney': player['AccountMoney'], 'rewardBattleCardList': [lc_card(r) for r in rewards],
            'combineRewardList': [dict(goods(n, 12, 1), ContentsIndex=r['BattleCardIndex'], ContentsGrade=r.get('Grade', 1),
                                       ContentsCount=1) for n, r in enumerate(rewards, 1)], 'postSendFlag': False}


def dispatch_cfg():
    f = Path(__file__).with_name('dispatch.json')
    return json.loads(f.read_text()) if f.exists() else None


def dispatch_state(player, cfg):
    """player['Dispatch']: Ticket (+1 per ticketMinutes up to ticketMax), FreeReset (2 a day), Spots [{dispatchSpot, status 1
    available / 2 in progress, characterArray, endTime ms}]; offers refilled up to cfg offers."""
    st = player.setdefault('Dispatch', {})
    now = now_ms(); per = int(cfg['ticketMinutes']) * 60000
    st.setdefault('Ticket', int(cfg['ticketMax'])); st.setdefault('TicketTime', now); st.setdefault('Spots', [])
    if st.get('Day') != _today():
        st['Day'] = _today(); st['FreeReset'] = int(cfg['resetFree'])
    if int(st['Ticket']) >= int(cfg['ticketMax']):
        st['TicketTime'] = now
    else:
        gain = (now - int(st['TicketTime'])) // per
        if gain > 0:
            st['Ticket'] = min(int(cfg['ticketMax']), int(st['Ticket']) + int(gain)); st['TicketTime'] = int(st['TicketTime']) + gain * per
    for s in st['Spots']:   # UIUnit_DispatchUnit.SetFighterSelectUI: any non-null characterArray = 'has a leader' (NRE on '')
        if not s.get('characterArray'): s['characterArray'] = None
    spots = cfg['spots']; have = {int(s['dispatchSpot']) for s in st['Spots']}
    pool = [int(k) for k in spots if int(k) not in have]
    while len(st['Spots']) < int(cfg['offers']) and pool:
        k = random.choices(pool, weights=[spots[str(x)]['weight'] for x in pool])[0]; pool.remove(k)
        st['Spots'].append({'dispatchSpot': k, 'status': 1, 'characterArray': None, 'endTime': 0})
    return st


def dispatch_info(cfg, st):
    full = int(st['Ticket']) >= int(cfg['ticketMax'])
    return {'dispatchIndex': int(cfg['main']), 'ticket': int(st['Ticket']), 'ticketRefreshTime': int(st['TicketTime']),
            'nextTicketRefreshTime': 0 if full else int(st['TicketTime']) + int(cfg['ticketMinutes']) * 60000,
            'freeResetCount': int(cfg['resetFree']) - int(st.get('FreeReset', 0))}   # client: free resets USED (Model_DispatchLobby.OnClickMissionReset)


def dispatch_route(op, player, payload):
    """dispatch/* (Dispatch, official guide page 1786; tables and numbers from make_data dispatch.json)."""
    cfg = dispatch_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'dispatch not set up'}
    st = dispatch_state(player, cfg); money = player['AccountMoney']
    spot_no = int(payload.get('dispatchSpot') or 0)
    spot = next((s for s in st['Spots'] if int(s['dispatchSpot']) == spot_no), None)
    fail = lambda msg: {'info': dispatch_info(cfg, st), 'ResultCode': 1, 'ResultMessage': msg}
    if op == 'list':
        save(player)
        return {'info': dispatch_info(cfg, st), 'spotList': st['Spots']}
    if op == 'start':
        chars = [int(c) for c in payload.get('CharacterList') or [] if int(c)]
        busy = {int(c) for s in st['Spots'] if s['status'] == 2 for c in (s['characterArray'] or '').split(',') if c}
        need = 1 + int(cfg['spots'].get(str(spot_no), {}).get('fighters', 1))   # leader + dispatchSupportCount supports
        if not spot or spot['status'] != 1:
            return fail('mission not available')
        if sum(1 for s in st['Spots'] if s['status'] == 2) >= int(cfg['maxRunning']):
            return fail('3 missions are already running')
        if int(st['Ticket']) < 1:
            return fail('no Dispatch Ticket')
        if not chars or len(chars) > need or busy & set(chars) or any(not character(player, c) for c in chars):
            return fail('choose free fighters')
        if int(st['Ticket']) >= int(cfg['ticketMax']):
            st['TicketTime'] = now_ms()
        st['Ticket'] = int(st['Ticket']) - 1
        spot.update({'status': 2, 'characterArray': ','.join(map(str, chars)),
                     'endTime': now_ms() + int(cfg['spots'][str(spot_no)]['minutes']) * 60000})
        save(player)
        return {'info': dispatch_info(cfg, st), 'spot': spot}
    if op == 'acceleration':
        used = payload.get('UsedItem') or {}
        q = int(used.get('Qty') or 1)
        if not spot or spot['status'] != 2:
            return fail('mission not running')
        inv = {i['ItemIndex']: i for i in items(player)}
        it = inv.get(int(cfg['speedItem']))
        if not it or int(it['Qty']) < q:
            return fail('no Speed Up Ticket')
        it['Qty'] -= q
        spot['endTime'] = max(now_ms(), int(spot['endTime']) - q * int(cfg['speedMinutes']) * 60000)
        save(player)
        return {'spot': spot, 'RemainItem': it}
    if op == 'complete':
        if not spot or spot['status'] != 2:
            return fail('mission not running')
        cash = int(payload.get('usedCash') or 0)
        if int(spot['endTime']) > now_ms():
            if cash < int(cfg['clearPrice']) or int(money.get('Cash', 0)) < cash:
                return fail('mission not finished')
            money['Cash'] = int(money['Cash']) - cash
        sc = cfg['spots'][str(spot_no)]; rewards = []; got = []
        money['Gold'] = int(money['Gold']) + int(sc['gold']); rewards.append(goods(1, 1, int(sc['gold'])))
        inv = {i['ItemIndex']: i for i in items(player)}
        for ix, q in sc['items']:
            if ix not in inv:
                inv[ix] = {'ItemIndex': ix, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[ix])
            inv[ix]['Qty'] += q; got.append(inv[ix])
            rewards.append(dict(goods(len(rewards) + 1, 13, q), ContentsIndex=ix, ContentsType=1, ContentsCount=q))
        # Receive_DispatchComplete opens the end popup (UIPopup_DispatchEnd: leader EXP) only when CharacterList has the leader.
        lead = character(player, int((spot['characterArray'] or '0').split(',')[0]))
        simple = []
        if lead:
            grant_char_exp(player, {'CharacterList': [{'CharacterIndex': lead['CharacterIndex']}]}, int(sc.get('leaderExp', 300)))
            simple = [dict(character_simple(lead), **{'ImprintStoneNo%d' % k: lead.get('ImprintStoneNo%d' % k, 0) for k in range(1, 6)})]
        st['Spots'].remove(spot)
        dispatch_state(player, cfg)   # a new offer takes its place
        save(player)
        return {'AccountMoney': money, 'CharacterList': simple, 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': got,
                'RewardImprintStoneList': [], 'completeRewardList': rewards, 'PostSendFlag': False, 'presetCharacterList': [],
                'presetCharacterCoreList': [], 'successType': 1}
    if op == 'reset':
        cash = int(payload.get('usedCash') or 0)
        if int(st.get('FreeReset', 0)) > 0:
            st['FreeReset'] -= 1
        elif cash >= int(cfg['resetPrice']) and int(money.get('Cash', 0)) >= cash:
            money['Cash'] = int(money['Cash']) - cash
        else:
            return {'AccountMoney': money, 'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'ResultCode': 1, 'ResultMessage': 'no free reset'}
        st['Spots'] = [s for s in st['Spots'] if s['status'] == 2]   # guide: running missions are kept
        dispatch_state(player, cfg)
        save(player)
        return {'AccountMoney': money, 'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}}
    if op == 'ticketRecharge':
        inv = {i['ItemIndex']: i for i in items(player)}
        it = inv.get(int(cfg['ticketItem'])); q = max(1, int((payload.get('UsedItem') or {}).get('Qty') or 1))
        if not it or int(it['Qty']) < q:
            return {'info': dispatch_info(cfg, st), 'RemainItem': {'ItemIndex': int(cfg['ticketItem']), 'Qty': 0, 'Lock': False},
                    'ResultCode': 1, 'ResultMessage': 'no Dispatch Ticket item'}
        it['Qty'] -= q; st['Ticket'] = int(st['Ticket']) + q
        save(player)
        return {'info': dispatch_info(cfg, st), 'RemainItem': it}
    return {}


def card_awaken(player, payload):
    """card2/cardAwaken: awaken +1 (max 5) using Awaken cards; gold 20000 x step (make_data BattleCardAwakeTable goodsValue);
    offers one random awaken buff of the card's kind (BattleCardAwakeBuffTable rows group*10+n, group = 930 + cardType).
    Client (UIPopup_BattleCardAwakenMaterial.RecvCardAwaken): awakenSkillList = the offered buff, chosen later with
    cardAwakenSkill. A card with no buff yet takes the offer at once. Values are mine."""
    defs = card_defs()
    base = payload.get('BaseCard') or payload.get('baseCard') or {}
    no = int(base.get('battleCardNo') or base.get('BattleCardNo') or 0)
    row = next((c for c in player.get('BattleCardList', []) if c['BattleCardNo'] == no), None)
    money = player['AccountMoney']
    if row is None:
        return {'accountMoney': money, 'ResultCode': 1, 'ResultMessage': 'no such card'}
    step = int(row.get('awaken') or 0) + 1
    if step > 5:
        return {'accountMoney': money, 'AccountMoney': money, 'battleCard': lc_card(row), 'awakenSkillList': [],
                'ResultCode': 1, 'ResultMessage': 'already max awaken'}
    if step > 1:
        cap = card_max_exp(row)
        if cap is not None and int(row.get('Exp', 0)) < cap:
            return {'accountMoney': money, 'battleCard': lc_card(row), 'awakenSkillList': [],
                    'ResultCode': 1, 'ResultMessage': 'the card must be max level'}
        if int(row.get('awakeBuffLevel', 0)) < local_card_progression.awaken_skill_max(row):
            return {'accountMoney': money, 'battleCard': lc_card(row), 'awakenSkillList': [],
                    'ResultCode': 1, 'ResultMessage': 'the awaken skill must be max level'}
    consume_cards(player, payload.get('MaterialCardList') or payload.get('materialCardList'))
    money['Gold'] = max(0, money['Gold'] - 20000 * step)
    grp = 930 + defs.get(row['BattleCardIndex'], {}).get('Type', 3)
    offer = grp * 10 + random.randrange(3)
    row['awaken'] = step
    row['awakeBuffLevel'] = step
    if not row.get('awakeBuffIndex'):
        row['awakeBuffIndex'] = offer
    player.setdefault('CardAwakenOffers', {})[str(no)] = offer   # kept off the card row (client BattleCard fields)
    save(player)
    return {'accountMoney': money, 'AccountMoney': money, 'battleCard': lc_card(row),
            'awakenSkillList': [{'battleCardNo': no, 'battleCardIndex': row['BattleCardIndex'], 'awakeBuffIndex': offer}]}


def card_awaken_skill(player, payload):
    """card2/cardAwakenSkill {BaseCard, changeSkill}: the Keep Buff / Change Buff choice for the buff offered by the last
    awaken (UIPopup_BattleCardAwakenSkillSelect). changeSkill 1 takes the offer, 0 keeps the current buff. Free, no step;
    the offer is cleared and the response's awakenSkillList is empty so the client drops the pending choice. (It used to
    run card_awaken: every press awakened +1 and charged gold, and re-offered a buff forever; seen 2026-10-18.)"""
    base = payload.get('BaseCard') or payload.get('baseCard') or {}
    no = int(base.get('battleCardNo') or base.get('BattleCardNo') or 0)
    row = next((c for c in player.get('BattleCardList', []) if c['BattleCardNo'] == no), None)
    if row is None:
        return {'battleCard': None, 'awakenSkillList': [], 'ResultCode': 1, 'ResultMessage': 'no such card'}
    offer = player.setdefault('CardAwakenOffers', {}).pop(str(no), None)
    if offer and int(payload.get('changeSkill') or 0) == 1:
        row['awakeBuffIndex'] = offer
    save(player)
    return {'battleCard': lc_card(row), 'awakenSkillList': []}


def card_route(path, player, payload):
    """card2/* routes: level up (exp from material cards), skill up (+1 level per material, max 10), grade up (+1 grade,
    max 6, exp reset like the original card evolution), sell (gold), lock. Amounts come from battlecards.json."""
    with GROWTH_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    money = player['AccountMoney']
    lst = player.setdefault('BattleCardList', [])
    if path.endswith('cardSell'):
        _, gold = consume_cards(player, payload.get('BattleCardList'))
        money['Gold'] += gold
        save(player)
        return {'AccountMoney': money}
    if path.endswith('cardLock'):
        row = next((c for c in lst if c['BattleCardNo'] == int(payload.get('BattleCardNo') or 0)), None)
        if row:
            row['Lock'] = bool(payload.get('Lock'))
            save(player)
        return {'BattleCard': row} if row else {}
    base = payload.get('BaseBattleCard') or payload.get('baseCard') or payload.get('BaseCard') or {}
    no = int(base.get('BattleCardNo') or base.get('battleCardNo') or 0)
    row = next((c for c in lst if c['BattleCardNo'] == no), None)
    mats = payload.get('BattleCardList') or payload.get('materialCardList') or payload.get('MaterialCardList') or []
    if path.endswith('cardSkillUp') and row is None:
        return {'ResultCode': 1, 'ResultMessage': 'no such card', 'AccountMoney': money, 'accountMoney': money}
    if path.endswith('cardSkillUp') and row.get('awaken', 0) > 0 and row.get('awakeBuffIndex', 0) > 0:
        try:
            upgrade = local_card_progression.plan_awaken_skill(player, row, mats, payload.get('UsedGold', 0))
        except (ValueError, KeyError) as error:
            return {'ResultCode': 1, 'ResultMessage': str(error), 'levelUpSuccess': 0,
                    'AccountMoney': money, 'accountMoney': money, 'BattleCard': row, 'battleCard': lc_card(row)}
        consume_cards(player, [{'BattleCardNo': no, 'Qty': qty} for no, qty in upgrade.materials])
        money['Gold'] -= upgrade.gold
        row['awakeBuffLevel'] = upgrade.level
        row['SkillExp'] = upgrade.exp
        save(player)
        return {'ResultCode': 0, 'LevelUpSuccess': 0, 'SkillUpSuccess': 1, 'levelUpSuccess': 1,
                'AccountMoney': money, 'accountMoney': money, 'BattleCard': row, 'battleCard': lc_card(row)}
    if path.endswith('cardSkillUp') and int(row.get('SkillLevel', 1)) >= 10:
        return {'ResultCode': 1, 'ResultMessage': 'already max normal skill', 'levelUpSuccess': 0,
                'AccountMoney': money, 'accountMoney': money, 'BattleCard': row, 'battleCard': lc_card(row)}
    mats = [m for m in mats if int(m.get('BattleCardNo') or m.get('battleCardNo') or 0) != no]
    if row is not None and path.endswith('cardGradeUp'):
        # evolve: cards go to 6 stars (make_data cardEndGrade 6, growth rows 1-6) and need max level (Evolve "Max Level");
        # refuse without taking materials/gold otherwise (the old cap of 5 ate a 5->6 evolve, 2026-10-18)
        cap = card_max_exp(row)
        if int(row.get('Grade', 1)) >= CARD_END_GRADE or (cap is not None and int(row.get('Exp', 0)) < cap):
            return {'AccountMoney': money, 'BattleCard': row, 'accountMoney': money, 'battleCard': lc_card(row), 'ResultCode': 1,
                    'ResultMessage': 'already max grade' if int(row.get('Grade', 1)) >= CARD_END_GRADE else 'the card must be max level'}
    count = sum(int(m.get('Qty') or m.get('qty') or m.get('count') or 1) for m in mats)
    used_gold = int(payload.get('UsedGold') or 0)
    cap = card_max_exp(row) if row is not None and path.endswith('cardLevelUp') else None
    if cap is not None:
        # level up stops at the card's max level: only the material cards needed are used, gold charged per card used
        room, defs, keep = max(0, cap - int(row.get('Exp', 0))), card_defs(), []
        for m in mats:
            if room <= 0:
                break
            src = next((c for c in lst if c['BattleCardNo'] == int(m.get('BattleCardNo') or m.get('battleCardNo') or 0)), None)
            per = max(1, int(defs.get(src['BattleCardIndex'], {}).get('Exp', 100))) if src else 100
            q = int(m.get('Qty') or m.get('qty') or m.get('count') or 1)
            n = min(q, -(-room // per))
            keep.append(dict(m, Qty=n, qty=n)); room -= n * per
        used = sum(int(m['Qty']) for m in keep)
        used_gold = used_gold * used // count if count else 0
        mats = keep
    exp, _ = consume_cards(player, mats)
    money['Gold'] = max(0, money['Gold'] - used_gold)
    if row is None:
        save(player)
        return {'AccountMoney': money}
    if path.endswith('cardSkillUp'):
        row['SkillLevel'] = min(10, row.get('SkillLevel', 1) + max(1, count))
        sync_card_passive_levels(row)
        save(player)
        return {'LevelUpSuccess': 0, 'SkillUpSuccess': 1, 'AccountMoney': money, 'BattleCard': row, 'battleCard': lc_card(row),
                'levelUpSuccess': 1, 'accountMoney': money}
    if path.endswith('cardGradeUp'):
        row['Grade'] = min(CARD_END_GRADE, row.get('Grade', 1) + 1)
        row['Exp'] = 0
        save(player)
        return {'AccountMoney': money, 'BattleCard': row, 'accountMoney': money, 'battleCard': lc_card(row)}
    row['Exp'] = row.get('Exp', 0) + exp
    if cap is not None:
        row['Exp'] = min(row['Exp'], cap)
    save(player)
    return {'LevelUpSuccess': 1, 'SkillUpSuccess': 0, 'AccountMoney': money, 'BattleCard': row,
            'levelUpSuccess': 1, 'accountMoney': money, 'battleCard': lc_card(row)}


def auto_equip_cards(player, defs):
    """Fill empty card slots 7/8 (the 2 ULTIMATE buttons) with the fighter's own cards, 'Extra' skills first, never the same
    skill in both slots. An empty slot shows a placeholder ULTIMATE button that does nothing (the user's "extra button",
    2026-10-17), so each empty slot is filled; version fighters share their base fighter's cards (char_groups.json) and a card
    copy can sit on one fighter only, so when the group's copies are all in use a new copy is made. Returns True on change."""
    owner = {d['BattleCardIndex']: d for d in defs}
    used = {c.get('BattleCardNo%d' % k) for c in player['CharacterList'] for k in range(1, 9)} - {0, None}
    groups = {int(k): v for k, v in json.loads(GROUPS_PATH.read_text()).items()} if GROUPS_PATH.exists() else {}
    cards = {c['BattleCardNo']: c for c in player.get('BattleCardList', [])}
    changed = False
    for ch in player['CharacterList']:
        c7, c8 = cards.get(ch.get('BattleCardNo7') or 0), cards.get(ch.get('BattleCardNo8') or 0)
        if c7 and c8 and owner.get(c7['BattleCardIndex'], {}).get('SkillIndex') == owner.get(c8['BattleCardIndex'], {}).get('SkillIndex'):
            used.discard(ch['BattleCardNo8']); ch['BattleCardNo8'] = 0; changed = True   # the same move twice: refill slot 8
        empty = [s for s in (7, 8) if not ch.get('BattleCardNo%d' % s)]
        if not empty:
            continue
        group = groups.get(ch['CharacterIndex'], ch['CharacterIndex'])
        pool = sorted((d for d in defs if d.get('Character') == group and d.get('SkillIndex')), key=lambda d: (not d.get('Extra'), d['BattleCardIndex']))
        for slot in empty:
            other = cards.get(ch.get('BattleCardNo%d' % (15 - slot)) or 0)
            other_sk = owner.get(other['BattleCardIndex'], {}).get('SkillIndex') if other else None
            pick = None
            for d in pool:
                if d.get('SkillIndex') == other_sk:
                    continue
                free = next((c for c in player.get('BattleCardList', []) if c['BattleCardIndex'] == d['BattleCardIndex']
                             and c['BattleCardNo'] not in used and not c.get('StackFlag')), None)
                pick = free or new_card_row(player, d)
                break
            if pick is None:
                continue
            cards[pick['BattleCardNo']] = pick
            ch['BattleCardNo%d' % slot] = pick['BattleCardNo']; used.add(pick['BattleCardNo']); changed = True
    return changed


BASE_STARS_PATH = Path(__file__).resolve().parent / 'base_stars.json'   # original rarity per fighter (make_data)
CORES_PATH = Path(__file__).resolve().parent / 'cores.json'   # written by make_data.py (core tree indices per fighter)


def level_of(ch):
    return local_progression.normal_level(ch)


def core_defs():
    """cores.json (make_data): per fighter [[treeIndex, level, prevTreeIndex, kind], ...] on the original 63-node board."""
    return json.loads(CORES_PATH.read_text()) if CORES_PATH.exists() else {}


def unlocked_cores(player):
    """player['Cores'] = {characterIndex: [treeIndex...]}, opened on the Core page (coreAcquire). First run of the 63-node
    board: open the paths to the skill cores (Finish Lv5, 3rd active Lv22) the fighter's level already allows, so the
    battle HUD keeps those skills; everything else is opened by the player."""
    cores = player.get('Cores')
    if cores is None or not isinstance(cores, dict) or player.get('CoreBoardVersion') != 2:
        cores = {}
        defs = core_defs()
        for ch in player['CharacterList']:
            nodes = {n[0]: n for n in defs.get(str(ch['CharacterIndex']), [])}
            lv, opened = level_of(ch), []
            for t, n in nodes.items():
                if n[3] in ('finish', 'active3') and n[1] <= lv:
                    path, cur = [], t
                    while cur:
                        path.append(cur); cur = nodes[cur][2]
                    opened += [x for x in reversed(path) if x not in opened]
            cores[str(ch['CharacterIndex'])] = opened
        player['Cores'] = cores
        player['CoreBoardVersion'] = 2
        save(player)
    return cores


def character_cores(player):
    cores = unlocked_cores(player)
    return [{'CharacterIndex': ch['CharacterIndex'], 'CoreTreeIndexList': cores.get(str(ch['CharacterIndex']), [])}
            for ch in player['CharacterList']]


def ensure_roster(player):
    """Local play: own every fighter in roster.json; fill an empty team with Team Japan. Saves when it changes."""
    roster = json.loads(ROSTER_PATH.read_text()) if ROSTER_PATH.exists() else []
    changed = False
    if roster:   # fighters dropped from the roster (e.g. duplicate year versions) leave the save and every team slot
        keep = set(roster)
        if any(c['CharacterIndex'] not in keep for c in player['CharacterList']):
            player['CharacterList'] = [c for c in player['CharacterList'] if c['CharacterIndex'] in keep]; changed = True
        for d in player.get('TeamDeckList', []):
            for n in (1, 2, 3):
                if d.get('CharacterIndex%d' % n) and d['CharacterIndex%d' % n] not in keep:
                    d['CharacterIndex%d' % n] = 0; changed = True
    have = {c['CharacterIndex'] for c in player['CharacterList']}
    for idx in roster:
        if idx not in have:
            player['CharacterList'].append(new_character(idx)); changed = True
    stars = {int(k): v for k, v in json.loads(BASE_STARS_PATH.read_text()).items()} if BASE_STARS_PATH.exists() else {}
    for ch in player['CharacterList']:
        base = stars.get(ch['CharacterIndex'], 3)
        if ch['Grade'] < base:
            ch['Grade'] = base
            changed = True
    deck = player['TeamDeckList'][0]
    if deck['CharacterIndex2'] == 0 and all(i in roster for i in TEAM_JAPAN):
        deck['CharacterIndex1'], deck['CharacterIndex2'], deck['CharacterIndex3'] = TEAM_JAPAN; changed = True
    if changed:
        save(player)
    return player


def session_create_response(player):
    ensure_roster(player)
    keys = ('Route', 'ProfileCharacter', 'PlayerAccount', 'AccountMoney', 'CharacterList',
            'TeamDeckList', 'BattleCardInvenSize', 'QuestList', 'OptionInfoList')
    return {'ResultCode': 0, 'ResultMessage': '', **{k: player[k] for k in keys}, 'RouletteEventList': roulette_schedules(),
            'ImprintStoneInvenSize': {'MaxSize': 200}, 'TeamDeckExtraSize': {'extraSize': int(player.get('TeamDeckExtraSize') or 0)}}


IMPRINT_STONES = (4201, 4202, 4203, 4204, 4205)   # make_data ImprintStoneTable: Circle/Square/Hexagon/Moon/Star


def imprint_stones(player):
    """ImprintStoneWEBData list (dump field names); grants one of each shape once, numbered 1..n."""
    lst = player.setdefault('ImprintStoneList', [])
    if player.get('ImprintStarterGiven') or lst:   # once only: stones can be sold / disassembled now
        player['ImprintStarterGiven'] = True
        return lst
    player['ImprintStarterGiven'] = True
    have = {s['ImprintStoneIndex'] for s in lst}
    for idx in IMPRINT_STONES:
        if idx not in have:
            lst.append({'ImprintStoneNo': max([s['ImprintStoneNo'] for s in lst] + [0]) + 1, 'ImprintStoneIndex': idx,
                        'CreateTime': now_ms(), 'Enchant': 0, 'Status': 0, 'VestedCharacterIndex': 0, 'LikeFlag': 0,
                        'BonusWeight': 0, 'Polishing': 0})
    return lst


def awaken_cfg():
    f = Path(__file__).resolve().parent / 'awaken.json'
    return json.loads(f.read_text()) if f.exists() else {}


def awaken_level(ch):
    """Awaken level from AwakenExp (awaken.json levelExp = accumulated thresholds); 0 before the first awakening."""
    if not int(ch.get('Awaken') or 0):
        return 0
    return min(50, 1 + sum(1 for e in awaken_cfg().get('levelExp', []) if int(ch.get('AwakenExp') or 0) >= e))


def awaken_cores(player, ci):
    """player['AwakenCores'] = {characterIndex: {awakenCoreIndex: level}}"""
    return player.setdefault('AwakenCores', {}).setdefault(str(ci), {})


def awaken_core_points(player, ch):
    """Remaining awaken core points (Character.corePoint): getPoint per awaken level minus the levels spent; kept on the row."""
    spent = sum(int(v) for v in awaken_cores(player, ch['CharacterIndex']).values())
    got = sum(1 for lv in awaken_cfg().get('corePointLevels', []) if awaken_level(ch) >= lv)   # 1 point per listed awaken level
    ch['corePoint'] = max(0, got - spent)
    return ch['corePoint']


def awaken_core_list(player):
    """AccountProfileResponse.characterAwakenCoreList (AwakenCoreBoardWEBData)."""
    return [{'characterIndex': int(ci), 'coreList': [{'coreIndex': int(k), 'coreLevel': int(v)} for k, v in sorted(cores.items()) if int(v)]}
            for ci, cores in sorted(player.get('AwakenCores', {}).items()) if any(int(v) for v in cores.values())]


def account_profile_response(player):
    """player/lobby -> AccountProfileResponse (only the parts the local profile models; the rest stay default)."""
    ensure_roster(player)
    for _c in player['CharacterList']:
        awaken_core_points(player, _c)
    stones = imprint_stones(player)
    t = now_ms()
    return {'ResultCode': 0, 'ResultMessage': '',
            'ProfileCharacter': player['ProfileCharacter'], 'PlayerAccount': player['PlayerAccount'],
            'AccountMoney': regen_active_point(player), 'CharacterList': player['CharacterList'],
            'TeamDeckList': player['TeamDeckList'], 'ItemList': items(player), 'BattleCardList': battle_cards(player),
            'TeamDeckExtraSize': {'extraSize': int(player.get('TeamDeckExtraSize') or 0)},
            'ImprintStoneList': stones, 'ImprintStoneInvenSize': {'MaxSize': 200},   # unset = '5/0' on the stone page
            'BattleCardInvenSize': {'Qty': len(battle_cards(player)), 'MaxSize': 3000}, 'CharacterCoreList': character_cores(player),
            'TutorialList': player.get('TutorialList', []), 'GachaDefaultList': [], 'QuestList': quest_rows(player),
            'BuffList': [], 'SeriesIndex': 0, 'BookStatusList': book_status(player),
            'BattleCardBookList': sorted({int(c['BattleCardIndex']) for c in battle_cards(player)}),   # picture book: cards collected
            'AgeInfo': {'AgeLevel': 0, 'AgeLevelUpdateTime': t}, 'AccumulateLogin': 1,
            'OptionInfoList': player['OptionInfoList'], 'RouletteEventList': roulette_schedules(), 'InAppPackageMonthRewardList': [],
            'CraftInfo': [], 'UserType': {'UserType': 0, 'RegDate': player['Route']['FirstConnectDatetime'],
                                          'ReturnShowFlag': 0, 'ReturnCharacterIndex': 0},
            'HotTimeInfoList': [], 'InitialCharacterGroupIndex': 1, 'WithdrawCharacterIndexList': [],
            'ChallengePoint': 0, 'GuildDetailInfo': guild_detail(player), 'characterAwakenCoreList': awaken_core_list(player),
            'AccountGrowthStatList': fame_stats(player), 'AccountExtraList': fame_extras(player),
            'SuperMissionList': super_open_data(player),   # LobbyResponse: open Super Missions (lobby icon)
            'PassList': pass_web_list(player),   # LobbyResponse: Battle Pass seasons (lobby icon)
            'bingoList': bingo_lobby(player),
            'teamEventList': team_lobby(player),
            'characterSelectionList': select_lobby(player),
            'RedDotList': red_dots(player),   # LobbyResponse: lobby icon red dots (mail)
            'questPointList': qpoint_list(player)}   # LobbyResponse: Mission Points   # LobbyResponse: Select Fighter offer   # LobbyResponse: Team Event icon gate (FindTeamEvent)   # LobbyResponse: a bingo missing here reads as complete (icon hidden)


STAGE_GOLD, STAGE_ACCOUNT_EXP, STAGE_CHARACTER_EXP, FIRST_CLEAR_CASH = 300, 30, 250, 50
TEAM_SLOT_COSTS = [100]   # rubies per extra team slot (mine; keep equal to make_data TEAM_SLOT_COSTS)
TEAM_SLOT_MAX = 30   # extra team slots cap (make_data TEAM_SLOT_MAX / ConfigTable TeamSlotExtraCountMax)
# story win gold per stage from the original RESULT pages (make_data -> story_gold.json); STAGE_GOLD for anything else
try:
    STORY_GOLD = {int(k): int(v) for k, v in json.loads((Path(__file__).parent / 'story_gold.json').read_text()).items()}
except (OSError, ValueError):
    STORY_GOLD = {}
CHAPTER_REWARD_CASH = 50


def goods(no, goods_type, count):
    """RewardContents (GoodsType: 1 gold, 2 cash)."""
    return {'No': no, 'GoodsType': goods_type, 'Reason': 0, 'Count': count, 'ContentsIndex': 0, 'ContentsGrade': 0,
            'ContentsCount': count, 'ContentsType': 0, 'ContentsValue': ''}


def character_level(exp, character_index=None):
    return local_progression.level_from_exp(exp, character_index)


def grant_char_exp(player, payload, amount=None):
    """Fighter EXP for the fighters who played (request CharacterList / Character / playFighterInfo; fall back to team 1),
    capped at the fighter's level cap (BASE_MAX_LEVEL + limit break). Returns the indices that got EXP."""
    played = {int(c.get('CharacterIndex') or 0) for c in payload.get('CharacterList') or []}
    played |= {int((payload.get('Character') or {}).get('CharacterIndex') or 0)}
    played |= {int(c.get('characterIndex') or 0) for c in (payload.get('playFighterInfo') or {}).get('characterList') or []}
    played -= {0}
    if not played:
        d = player['TeamDeckList'][0]
        played = {d['CharacterIndex1'], d['CharacterIndex2'], d['CharacterIndex3']} - {0}
    for ch in player['CharacterList']:
        if ch['CharacterIndex'] in played:
            cap = BASE_MAX_LEVEL.get(min(int(ch.get('Grade', 3)), 6), 60) + ch.get('LimitBreakProgressCount', 0)
            cap_exp = exp_for_level(cap, ch['CharacterIndex'])
            if ch['Exp'] < cap_exp:
                ch['Exp'] = min(ch['Exp'] + (amount or STAGE_CHARACTER_EXP), cap_exp)
    return played


def character_simple(c):
    return {'CharacterIndex': c['CharacterIndex'], 'Grade': c['Grade'], 'Exp': c['Exp'], 'BuffExp': 0,
            'AffectionExp': c.get('AffectionExp', 0), 'Awaken': c.get('Awaken', 0), 'AwakenExp': c.get('AwakenExp', 0),
            'Ex': 0, 'ImprintStoneNo1': 0, 'ImprintStoneNo2': 0, 'ImprintStoneNo3': 0, 'ImprintStoneNo4': 0,
            'ImprintStoneNo5': 0, 'CharacterLevel': level_of(c), 'CharacterPower': 0, 'corePoint': 0}


AP_REGEN_MS = 3 * 60 * 1000   # placeholder: 1 AP per 3 minutes up to ActivePointMax


def regen_active_point(player):
    """Refill AP for the time passed since ActivePointUpdateTime (the server owns AP; nothing else refills it)."""
    money, t = player['AccountMoney'], now_ms()
    last = money.get('ActivePointUpdateTime') or t
    gained = (t - last) // AP_REGEN_MS
    if money['ActivePoint'] >= money['ActivePointMax']:
        money['ActivePointUpdateTime'] = t
    elif gained > 0:
        money['ActivePoint'] = min(money['ActivePointMax'], money['ActivePoint'] + gained)
        money['ActivePointUpdateTime'] = last + gained * AP_REGEN_MS
    return money


def character_simple6(c):
    return {'CharacterIndex': c['CharacterIndex'], 'Grade': c['Grade'], 'LimitBreakGrade': c.get('LimitBreakGrade', 0),
            'LimitBreakProgressCount': c.get('LimitBreakProgressCount', 0), 'AffectionExp': c.get('AffectionExp', 0),
            'SupportCharacterIndex': 0, 'Awaken': c.get('Awaken', 0), 'AwakenExp': c.get('AwakenExp', 0),
            'corePoint': c.get('corePoint', 0), 'Ex': 0, 'ImprintStoneNo1': 0, 'ImprintStoneNo2': 0, 'ImprintStoneNo3': 0,
            'ImprintStoneNo4': 0, 'ImprintStoneNo5': 0}


TEAMDECK_FIELDS = ('DeckNo', 'CharacterIndex1', 'CharacterIndex2', 'CharacterIndex3',
                   'SupportCharacterIndex1', 'SupportCharacterIndex2', 'SupportCharacterIndex3',
                   'DeckName', 'TeamRelationIndex', 'GroupGrowthIndex', 'TeamPower', 'LeaderPower')


# ---- Gacha (standard summon). PC 1.11.2 calls /api/gacha/gachaInfo then /api/gacha/gachaDefaultPlay (paths from
#      api-defaults.json; response/request field layout from the Android 1.17 il2cpp dump: GachaType, Gacha,
#      CharacterReward, GachaDefaultPlayRequest). Banner + odds ship in the tables (GachaTypeTable / GachaDefaultTable
#      / GachaGradeRateTable); gacha_pool.json lists the fighter pool per grade. ensure_roster() already grants every
#      fighter, so every pull is a duplicate -> we hand out the fighter's Soul via the game's own
#      CharacterReward.ExCharacterSoul / ExCharacterSoulQty fields instead of a second copy.
GACHA_POOL_PATH = Path(__file__).resolve().parent / 'gacha_pool.json'
_GACHA_POOL = None
def gacha_pool():
    global _GACHA_POOL
    if _GACHA_POOL is None:
        _GACHA_POOL = json.loads(GACHA_POOL_PATH.read_text()) if GACHA_POOL_PATH.exists() else {'grades': {}, 'pool': {}, 'price': {}}
    return _GACHA_POOL
GACHA_DUP_SOULS = {3: 5, 4: 15, 5: 30, 6: 50}   # souls for a duplicate pull, by rolled grade (local balance choice)
GACHA_DEFAULTS = {1: 1, 2: 10}                  # gachaDefaultIndex -> pull count (from GachaDefaultTable gachaGoodsCount)
GACHA_PRICE = {1: 150, 2: 1500}                 # gachaDefaultIndex -> Cash cost (GachaDefaultTable gachaPriceValue)


def gacha_schedules():
    """OperateSchedule list for open gacha banners (PC client: Category 20, Index = gachaMainIndex, NetworkManagerWEB.TakeGachaTypeDataList; OffOnSched 1 = ALWAYS). The summon
    screen lists only banners whose index is in OpsRepository.GetGachaScheduleIndexList. Detail times are seconds."""
    return [{'Version': 1, 'Category': 20, 'SubCategory': 0, 'Index': 1, 'Custom': '', 'TagList': [],
             'Detail': {'SubGroup': [], 'OffOnSched': 1, 'Weekly': [], 'Hourly': [], 'StartTs': 1600000000,
                        'EndTs': 4102444800, 'Offset': 0, 'estimatedTime': 0}}]


def gacha_roll_one(pool, grades):
    """Pick a grade by its probability (per 10000), then a uniform fighter index of that grade."""
    r = random.randrange(10000); acc = 0; chosen = None
    for g in sorted(grades, key=int):
        acc += int(grades[g])
        if r < acc:
            chosen = int(g); break
    if chosen is None:
        chosen = max((int(g) for g in grades), default=5)
    cands = pool.get(str(chosen)) or pool.get(chosen) or []
    return (random.choice(cands) if cands else None), chosen


def gacha_play(player, default_index):
    """Run `count` pulls. Every fighter is already owned, so each result is a Soul reward (ExCharacterSoul)."""
    gp = gacha_pool(); grades = gp.get('grades', {}); pool = gp.get('pool', {})
    count = GACHA_DEFAULTS.get(default_index, 1); cost = GACHA_PRICE.get(default_index, 150)
    money = player['AccountMoney']
    if int(money.get('Cash', 0)) < cost:
        return {'ResultCode': 1, 'ResultMessage': 'not enough Cash', 'AccountMoney': money,
                'RewardCharacterList': [], 'GachaDefault': {'GachaTypeIndex': 1, 'GachaDefaultIndex': default_index,
                'GachaDiscountBuyCount': 0, 'GachaBuyCount': 0, 'GachaFreeTime': 0, 'GachaDiscountBuyTime': 0}}
    money['Cash'] = int(money.get('Cash', 0)) - cost
    inv = {i['ItemIndex']: i for i in items(player)}
    rewards = []
    for _ in range(count):
        idx, grade = gacha_roll_one(pool, grades)
        if idx is None:
            continue
        soul_idx = SOUL_BASE + idx; qty = GACHA_DUP_SOULS.get(grade, 10)
        row = inv.get(soul_idx)
        if row is None:
            row = {'ItemIndex': soul_idx, 'Qty': 0, 'Lock': False}
            player.setdefault('ItemList', []).append(row); inv[soul_idx] = row
        row['Qty'] = int(row.get('Qty', 0)) + qty
        mem = inv.get(MEM_BASE + idx)   # official guide: a duplicate fighter gives 1 Memory of that fighter
        if mem is None:
            mem = {'ItemIndex': MEM_BASE + idx, 'Qty': 0, 'Lock': False}
            player.setdefault('ItemList', []).append(mem); inv[MEM_BASE + idx] = mem
        mem['Qty'] = int(mem.get('Qty', 0)) + 1
        rewards.append({'CharacterIndex': idx, 'Grade': grade, 'Exp': 0,
                        'ExCharacterSoul': soul_idx, 'ExCharacterSoulQty': qty,
                        'fighterMemoryIndex': MEM_BASE + idx, 'fighterMemoryIndexQty': 1})
    save(player)
    return {'ResultCode': 0, 'ResultMessage': '', 'AccountMoney': money,
            'GachaDefault': {'GachaTypeIndex': 1, 'GachaDefaultIndex': default_index, 'GachaDiscountBuyCount': 0,
                             'GachaBuyCount': 0, 'GachaFreeTime': 0, 'GachaDiscountBuyTime': 0},
            'RewardCharacterList': rewards, 'RewardBattleCardList': [], 'RewardItemList': [], 'RewardCurrencyList': [],
            'Item': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'Mileage': 0, 'ResetMileage': 0, 'PostSendFlag': False,
            'GachaStepUpList': [], 'GachaReset': 0, 'RewardBonusContentsList': [], 'RewardImprintStoneList': [],
            'presetCharacterReward': [], 'presetCharacterCoreReward': []}


# ---- Daily attendance. PC 1.11.2 calls /api/attendance/info (AttendanceInfoResponse schema from api-defaults.json:
#      DailyAttendanceAccumulate) and /api/attendance/give. The 28-day schedule ships in attendance.json (make_data);
#      the server tracks the day in player['Attendance'] and grants the reward with the same goods()/AccountMoney
#      convention as the working chapterMissionComplete route. One claim per local calendar day.
ATTENDANCE_PATH = Path(__file__).resolve().parent / 'attendance.json'
_ATTENDANCE = None
def attendance_cfg():
    global _ATTENDANCE
    if _ATTENDANCE is None:
        _ATTENDANCE = json.loads(ATTENDANCE_PATH.read_text()) if ATTENDANCE_PATH.exists() else {'group': 0, 'rewards': []}
    return _ATTENDANCE


def _today():
    return time.strftime('%Y-%m-%d', time.localtime())


def attendance_accumulate(player):
    cfg = attendance_cfg(); st = player.setdefault('Attendance', {'day': 0, 'lastDate': ''})
    pending = st.get('lastDate') != _today()   # today's reward not given yet: count today, flag it as waiting
    # AttendanceReward.GiveTime / LastGiveTime are int32 DAY numbers: GiveTime = today's day, LastGiveTime = days already
    # claimed (AttendanceData.SetAttendanceData: IsAllGetRewardsComplete = GiveTime == LastGiveTime; the reward popup lists
    # days > LastGiveTime). LastGiveTime used to be 0 (popup listed every day so far) or a ms timestamp (int32 overflow:
    # the reply no longer parsed, traced live 2026-10-19).
    return {'AttendanceRewardGroup': cfg.get('group', 0), 'GiveTime': st.get('day', 0) + (1 if pending else 0),
            'LastGiveTime': st.get('day', 0), 'RegDate': 0, 'RewardGetFlag': 1 if pending else 0, 'AttendanceIndex': 1}


def attendance_give(player):
    cfg = attendance_cfg(); rewards = cfg.get('rewards', [])
    st = player.setdefault('Attendance', {'day': 0, 'lastDate': ''})
    money = player['AccountMoney']
    if not rewards or st.get('lastDate') == _today():
        return {'ResultCode': 1, 'ResultMessage': 'already claimed today' if rewards else 'no attendance config',
                'DailyAttendanceAccumulate': attendance_accumulate(player), 'AccountMoney': money,
                'RewardCurrencyList': [], 'ClearRewardList': []}
    day = st.get('day', 0) % len(rewards)
    _, rt, cidx, cnt = rewards[day]
    given = []
    if rt in (1, 2, 4):                              # rewardType = GoodsType: 1 Gold, 2 Cash (4 = old rows, Cash)
        key = 'Gold' if rt == 1 else 'Cash'
        money[key] = int(money.get(key, 0)) + cnt
        given.append(dict(goods(day + 1, 1 if rt == 1 else 2, cnt), ContentsIndex=cidx, ContentsCount=cnt))
    elif rt == 13:                                   # Item (e.g. a fighter soul)
        inv = {i['ItemIndex']: i for i in items(player)}
        row = inv.get(cidx) or {'ItemIndex': cidx, 'Qty': 0, 'Lock': False}
        if cidx not in inv:
            player.setdefault('ItemList', []).append(row)
        row['Qty'] = int(row.get('Qty', 0)) + cnt
        given.append(dict(goods(day + 1, 0, cnt), ContentsIndex=cidx, ContentsType=1, ContentsCount=cnt))
    st['day'] = st.get('day', 0) + 1
    st['lastDate'] = _today()
    st['lastTime'] = now_ms()
    save(player)
    return {'ResultCode': 0, 'ResultMessage': '', 'AccountMoney': money,
            'DailyAttendanceAccumulate': attendance_accumulate(player), 'RewardCurrencyList': given,
            'RewardItemList': [], 'RewardCharacterList': [], 'ClearRewardList': given, 'PostSendFlag': False}


# ---- Collection book. collection.json (make_data): {'teams': [{index, reward, members}], 'rewards': {rewardIndex: {gold, ruby}},
#      'fighter': [{index, level}]}. Claims (book/bookReward, bookRewardAll) are recorded where the client reads them back:
#      CollectionType 1 (Fighter) in the fighter's own RewardList ('a,b' -> DBData.Character.m_collectionRewardIndex), the others in
#      player['BookStatus'] -> AccountProfile BookStatusList (NetworkManagerWEB.TakeCollectionRewardStatus stores type - 1); team claims
#      hold the TeamCollectionIndex (Parse_BookReward). Prizes are mailed. The old 'CollectionClaimed' (teams-only GET ALL of
#      2026-10-18/20) paid nothing, so it is not carried over: those teams can be claimed again.
COLLECTION_PATH = Path(__file__).resolve().parent / 'collection.json'
_COLLECTION = None
def collections_cfg():
    global _COLLECTION
    if _COLLECTION is None:
        c = json.loads(COLLECTION_PATH.read_text()) if COLLECTION_PATH.exists() else {}
        _COLLECTION = c if isinstance(c, dict) else {'teams': c, 'rewards': {}, 'fighter': []}   # a plain list = the old teams-only file
    return _COLLECTION


def book_status(player):
    """AccountProfile BookStatusList: BookRewardStatus {CollectionType (1-based), CollectionRewardList 'a,b'}."""
    return [{'CollectionType': int(t), 'CollectionRewardList': ','.join(str(x) for x in v)}
            for t, v in sorted(player.get('BookStatus', {}).items(), key=lambda kv: int(kv[0])) if v]


def book_claim(player, ctype, ri, ci):
    """One collection reward claim -> (BookRewardResponseVO fields, prize dict) or None if unknown / already claimed. Not saved,
    not mailed (the caller does both, so GET ALL sends one mail per currency)."""
    cfg = collections_cfg(); rw = dict(cfg.get('rewards', {}).get(str(ri)) or {}); team = 0
    if ctype == 1:   # Fighter: the fighter's own list; the client checks the level (collectionRewardValue <= NormalLevel)
        c = next((x for x in player['CharacterList'] if int(x['CharacterIndex']) == ci), None)
        if c is None or ri not in {int(f['index']) for f in cfg.get('fighter', [])}:
            return None
        got = [int(x) for x in str(c.get('RewardList') or '').split(',') if x.strip().isdigit()]
        if ri in got:
            return None
        c['RewardList'] = ','.join(str(x) for x in got + [ri])
    else:
        if ctype == 4:   # Team: recorded by TeamCollectionIndex
            t = next((x for x in cfg.get('teams', []) if int(x['reward']) == ri or int(x['index']) == ri), None)
            if t is None:
                return None
            team = int(t['index'])
        lst = player.setdefault('BookStatus', {}).setdefault(str(ctype), [])
        key = team if ctype == 4 else ri
        if key in lst:
            return None
        lst.append(key)
    shown = [goods(n, gt, int(rw[k])) for n, (k, gt) in enumerate((('gold', 1), ('ruby', 2)), 1) if rw.get(k)]
    return {'CollectionType': ctype, 'CollectionRewardIndex': ri, 'RewardType': 1, 'CharacterIndex': ci,
            'CharacterGrade': 0, 'TeamCollectionIndex': team, 'RewardList': shown}, rw


def book_mail(player, prizes, what):
    tot = {'gold': sum(int(p.get('gold') or 0) for p in prizes), 'ruby': sum(int(p.get('ruby') or 0) for p in prizes)}
    if tot['gold'] or tot['ruby']:
        post_reward(player, tot, 'Collection reward: %s' % what)


# ---- Affection. /api/affection/giveGift (AffectionGiveGiftResponse) consumes gift items and adds their affection
#      value to the fighter's AffectionExp; the client reads the AffectionLevelTable/AffectionBonusGroupTable (shipped)
#      to turn that exp into levels and per-fighter stat bonuses. affection.json maps gift itemIndex -> affection value.
AFFECTION_PATH = Path(__file__).resolve().parent / 'affection.json'
_AFFECTION = None
def affection_cfg():
    global _AFFECTION
    if _AFFECTION is None:
        _AFFECTION = json.loads(AFFECTION_PATH.read_text()) if AFFECTION_PATH.exists() else {'gifts': {}, 'levels': []}
    return _AFFECTION


def affection_give_gift(player, payload):
    gifts = affection_cfg().get('gifts', {})
    # AffectionGiveGiftRequest {Character: CharacterSimple {CharacterIndex, ...}, ItemList} (PC dump): the fighter is inside
    # 'Character'; reading a top-level CharacterIndex refused every gift ('no such character', first real request 2026-10-24)
    ch = character(player, int((payload.get('Character') or {}).get('CharacterIndex') or payload.get('CharacterIndex') or 0))
    money = player['AccountMoney']
    if not ch:
        return {'Character': {}, 'ItemList': [], 'AccountMoney': money, 'ResultCode': 1, 'ResultMessage': 'no such character'}
    inv = {i['ItemIndex']: i for i in items(player)}
    gained = 0; used = []
    # all or nothing: every entry valid and affordable (it used to give what the stock allowed and report success)
    need, err = item_need(payload.get('ItemList'))
    need = {k: q for k, q in need.items() if gifts.get(str(k), gifts.get(k))}
    if err or not need or item_short(player, need) is not None:
        return {'Character': character_simple(ch), 'ItemList': [], 'AccountMoney': money, 'ResultCode': 1,
                'ResultMessage': err or 'not enough gifts'}
    for idx, qty in need.items():
        inv[idx]['Qty'] = int(inv[idx]['Qty']) - qty; gained += int(gifts.get(str(idx), gifts.get(idx))) * qty
        used.append(inv[idx])
    if gained:
        ch['AffectionExp'] = int(ch.get('AffectionExp', 0)) + gained
        save(player)
    return {'Character': character_simple(ch), 'ItemList': used, 'AccountMoney': money, 'RewardBattleCardList': [],
            'PostSendFlag': False, 'RewardCharacterList': [], 'RewardItemList': [], 'RewardImprintStoneList': [],
            'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}


# ---- Event quest. The client polls /api/questEvent/questEventList and renders the event from the shipped tables
#      (QuestEventTable / QuestEventScheduleTable / QuestEventStageTable); the server supplies per-player state as
#      QuestEventWEBData / QuestEventStageWEBData (field names verbatim from the Android dump) and runs the play loop
#      (open / start / end / mopUp / recharge, schemas from api-defaults.json) by reusing the story stageStart/stageEnd
#      logic. questevent.json (make_data) lists the events, their stage indices and reward amounts.
QUESTEVENT_PATH = Path(__file__).resolve().parent / 'questevent.json'
_QUESTEVENT = None
def questevent_cfg():
    global _QUESTEVENT
    if _QUESTEVENT is None:
        _QUESTEVENT = json.loads(QUESTEVENT_PATH.read_text()) if QUESTEVENT_PATH.exists() else {'events': []}
    return _QUESTEVENT


def questevent_event(stage_index):
    return next((e for e in questevent_cfg().get('events', []) if stage_index in e.get('stages', [])), None)


def questevent_stage_rows(player):
    """QuestEventStageWEBData for every event stage (unplayed ones default to BattleResult 0)."""
    st = {r['QuestEventStageIndex']: r for r in player.setdefault('QuestEventStageList', [])}
    out = []
    for e in questevent_cfg().get('events', []):
        for si in e.get('stages', []):
            r = st.get(si, {})
            out.append({'QuestEventIndex': e['index'], 'QuestEventStageIndex': si,
                        'StageDifficulty': int(e.get('difficulty', {}).get(str(si), 1)),
                        'BattleResult': int(r.get('BattleResult', 0)), 'ClearCount': int(r.get('ClearCount', 0)),
                        'Mission1Index': int(r.get('Mission1Index', 0)), 'Mission2Index': int(r.get('Mission2Index', 0)),
                        'Mission3Index': int(r.get('Mission3Index', 0)), 'CoopMission1Index': 0, 'CoopMission2Index': 0,
                        'CoopMission3Index': 0, 'ClearScore': 0})
    return out


def questevent_list_response(player):
    rows = questevent_stage_rows(player)
    evs = []
    for e in questevent_cfg().get('events', []):
        cleared = sum(1 for r in rows if r['QuestEventIndex'] == e['index'] and r['BattleResult'] == 1)
        evs.append({'QuestEventIndex': e['index'], 'ReOpenEndTime': 0, 'ClearCount': cleared, 'mopupCount': 0})
    groups = [{'QuestEventGroup': g, 'ClearCount': sum(x['ClearCount'] for x, e in zip(evs, questevent_cfg().get('events', []))
                                                       if int(e.get('group', 1)) == g)}
              for g in sorted({int(e.get('group', 1)) for e in questevent_cfg().get('events', [])})]
    # Marathons (QuestEvent type 4, questEventGroup = marathon index): the EVENT carousel looks each event's group up in this list
    mr = marathon_cfg() or {}; mst = (player.get('Marathon') or {}).get('Stages', {})
    for m in mr.get('marathons', []):
        cl = sum(1 for k in m['stages'] if (mst.get(str(k)) or {}).get('BattleResult') == 1)
        evs.append({'QuestEventIndex': m['index'], 'ReOpenEndTime': 0, 'ClearCount': cl, 'mopupCount': 0})
        groups.append({'QuestEventGroup': m['index'], 'ClearCount': cl})
    return {'ServerUtcTime': now_ms(), 'QuestEventList': evs, 'QuestEventStageList': rows,
            'QuestEventGroupList': groups,
            'QuestEventTicketRechargeList': [], 'HotTimeEnterList': [], 'MarathonPlayCheckList': [],
            'ResultCode': 0, 'ResultMessage': ''}


def questevent_end(player, payload, mopup=False, first_cash=None):
    """Record the result and grant the event rewards (gold per clear, cash on first clear, EXP + souls as in story)."""
    idx = int(payload.get('QuestEventStageIndex') or payload.get('StageIndex') or 0)
    ev = questevent_event(idx)
    won = mopup or int(payload.get('BattleResult') or 0) == 1
    if not ev or not idx:
        return {'QuestEventStageIndex': idx, 'BattleResult': 0, 'ResultCode': 1, 'ResultMessage': 'unknown event stage',
                'AccountMoney': player['AccountMoney']}
    rows = player.setdefault('QuestEventStageList', [])
    row = next((r for r in rows if r['QuestEventStageIndex'] == idx), None)
    if row is None:
        row = {'QuestEventIndex': ev['index'], 'QuestEventStageIndex': idx, 'BattleResult': 0, 'ClearCount': 0}
        rows.append(row)
    first = won and row['BattleResult'] != 1
    if mopup and row['BattleResult'] != 1:
        return {'QuestEventStageIndex': idx, 'ResultCode': 1, 'ResultMessage': 'clear the stage first',
                'AccountMoney': player['AccountMoney']}
    clear, first_rewards, reward_idx = [], [], set()
    if won:
        row['BattleResult'] = 1; row['ClearCount'] = int(row.get('ClearCount', 0)) + 1
        for k in ('Mission1Index', 'Mission2Index', 'Mission3Index'):
            v = int(payload.get(k) or 0)
            if v:
                row[k] = v
        money = player['AccountMoney']
        money['Gold'] += int(ev.get('gold', 0))
        clear.append(goods(1, 1, int(ev.get('gold', 0))))
        player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP
        played = {int(c.get('CharacterIndex') or 0) for c in payload.get('CharacterList') or []} - {0}
        if not played:
            d = player['TeamDeckList'][0]
            played = {d['CharacterIndex1'], d['CharacterIndex2'], d['CharacterIndex3']} - {0}
        for ch in player['CharacterList']:
            if ch['CharacterIndex'] in played:
                ch['Exp'] += STAGE_CHARACTER_EXP
        inv = {i['ItemIndex']: i for i in items(player)}
        gains = [(1001, 2)] + [(SOUL_BASE + c, 5) for c in sorted(played) if SOUL_BASE + c in inv]
        # Growth Dungeon dailies (make_data DAILY_SETS): the stage's material rewards (EXP capsules, cores, jades, awaken shards)
        for iidx, qty in (ev.get('items') or {}).get(str(idx), []):
            if iidx not in inv:
                player['ItemList'].append({'ItemIndex': int(iidx), 'Qty': 0, 'Lock': False}); inv[iidx] = player['ItemList'][-1]
            gains.append((int(iidx), int(qty)))
        pcfg = pieces_cfg()   # Fighter Pieces: eventDrop pieces of a random fighter per event stage win (make_data pieces.json)
        if pcfg.get('pieces') and int(pcfg.get('eventDrop', 0)):
            pix = int(random.choice(list(pcfg['pieces'])))
            if pix not in inv:
                player['ItemList'].append({'ItemIndex': pix, 'Qty': 0, 'Lock': False}); inv[pix] = player['ItemList'][-1]
            gains.append((pix, int(pcfg['eventDrop'])))
        for no, (iidx, qty) in enumerate(gains, 2):
            inv[iidx]['Qty'] += qty
            clear.append(dict(goods(no, 13, qty), ContentsIndex=iidx, ContentsCount=qty))
        reward_idx = {i for i, _ in gains}
        if first:
            fc = int(ev.get('firstCash', 0) if first_cash is None else first_cash)
            money['Cash'] += fc
            first_rewards.append(goods(1, 2, fc))
    save(player)
    card_rows = []
    if won and ev.get('cardDrop'):   # Battle Card Descended: one random card (grade 3-5) per clear
        pool = [d for d in card_defs().values() if 3 <= int(d.get('Grade', 1)) <= 5]
        if pool:
            card_rows.append(new_card_row(player, random.choice(pool))); save(player)
            c = card_rows[-1]   # also a result-screen row (ClearRewardList; RewardBattleCardList only fills the inventory)
            clear.append(dict(goods(len(clear) + 2, 12, 1), ContentsIndex=c['BattleCardIndex'], ContentsGrade=c['Grade'], ContentsCount=1))
    base = {'QuestEventStageIndex': idx, 'AccountMoney': player['AccountMoney'], 'PlayerAccount': player['PlayerAccount'],
            'CharacterList': [character_simple(c) for c in player['CharacterList']],
            'RewardItemList': [i for i in items(player) if i['ItemIndex'] in reward_idx], 'ResultCode': 0, 'ResultMessage': ''}
    if mopup:
        return dict(base, RewardContentsList=clear, MopupTicketItem={'ItemIndex': 0, 'Qty': 0, 'Lock': False}, RewardBattleCardList=card_rows)
    return dict(base, BattleResult=1 if won else 0, FirstClearFlag=1 if first else 0,
                ClearRewardList=clear, FirstClearRewardList=first_rewards, RewardBattleCardList=card_rows)


# ---- Crucible Tower (/api/questEvent/crucibleTower{Info,Start,End,MopUp}; DTOs CrucibleTower {StageIndex, LastClearStageIndex,
#      MopupTime (ms), ChallengePoint, RegTime, mopupCount} + QuestEventCrucibleTower*Response from the dump). The tower is the
#      questevent.json event with a 'tower' key (make_data, event 106). State in player['CrucibleTower']: LastClear (stage index,
#      kept), Points (refilled to the maximum each local day; a lost run costs one: the client blocks entry at 0) and
#      MopupTime (one sweep a day: UIPage_SPQuestCrucibleTower.CheckValidMopup compares its day with the server's).
#      Floor clears reuse questevent_end (gold, EXP, souls, first-clear rubies: 50 on every 10th floor).
def ct_event():
    return next((e for e in questevent_cfg().get('events', []) if e.get('tower')), None)


def ct_state(player):
    ev = ct_event(); st = player.setdefault('CrucibleTower', {})
    st.setdefault('LastClear', 0); st.setdefault('MopupTime', 0); st.setdefault('RegTime', now_ms())
    if st.get('PointDay') != _today():
        st['PointDay'] = _today(); st['Points'] = int(ev['tower']['cp'])
    return st


def ct_info(player):
    st = ct_state(player)
    swept = st['MopupTime'] and time.strftime('%Y-%m-%d', time.localtime(st['MopupTime'] / 1000)) == _today()
    return {'StageIndex': st['LastClear'], 'LastClearStageIndex': st['LastClear'], 'MopupTime': st['MopupTime'],
            'ChallengePoint': st['Points'], 'RegTime': st['RegTime'], 'mopupCount': 1 if swept else 0}


def ct_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; ev = ct_event(); st = ct_state(player)
    if op == 'crucibleTowerInfo':
        save(player)
        return {'CrucibleTower': ct_info(player), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'crucibleTowerStart':
        save(player)
        return {'StrikerType': 0, 'StrikerUsn': 0, 'StrikerGameDb': 0, 'StrikerNickName': '', 'StrikerBattleCardList': [],
                'CharacterCoresList': [], 'AccountMoney': player['AccountMoney'], 'LuckySpawn': 0, 'DropGoldLucky': 0, 'DropGoldJaco': 0,
                'DropGoldElite': 0, 'DropGoldBoss': 0, 'DropGoldGimmick1': 0, 'DropGoldGimmick2': 0, 'DropGoldGimmick3': 0,
                'DropLuckyList': [], 'DropJacoList': [], 'DropEliteList': [], 'DropBossList': [], 'DropGimmickList': [],
                'QuestEventPlayToken': now_ms(), 'StrikerImprintStoneList': [], 'strikerAwakenCoreList': [],
                'StrikerAccountGrowthStatList': [], 'StrikerAccountExtraList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'crucibleTowerEnd':
        idx = int(payload.get('QuestEventStageIndex') or 0); stages = ev['stages']
        nxt = stages[stages.index(st['LastClear']) + 1] if st['LastClear'] in stages[:-1] else (stages[0] if not st['LastClear'] else 0)
        won = int(payload.get('BattleResult') or 0) == 1
        if idx != nxt:   # only the floor above the last cleared one can be played (the client enforces the same)
            return {'QuestEventStageIndex': idx, 'BattleResult': 0, 'AccountMoney': player['AccountMoney'], 'ResultCode': 1,
                    'ResultMessage': 'not the next floor'}
        if not won:
            st['Points'] = max(0, int(st['Points']) - 1); save(player)
            return {'QuestEventStageIndex': idx, 'BattleResult': 0, 'RewardItemList': [], 'RewardCharacterList': [],
                    'RewardBattleCardList': [], 'PlayerAccount': player['PlayerAccount'], 'AccountMoney': player['AccountMoney'],
                    'CharacterList': [character_simple(c) for c in player['CharacterList']], 'AccountLevelUpFlag': 0,
                    'ClearRewardList': [], 'PostSendFlag': False, 'ResultCode': 0, 'ResultMessage': ''}
        floor = stages.index(idx) + 1
        r = questevent_end(player, dict(payload, BattleResult=1), first_cash=int(ev['tower']['bigCash']) if floor % 10 == 0 else None)
        st['LastClear'] = idx; save(player)
        clear = list(r.get('ClearRewardList') or [])
        for g in r.get('FirstClearRewardList') or []:   # the tower reply has no first-clear list: one result list
            clear.append(dict(g, No=len(clear) + 1))
        return {'QuestEventStageIndex': idx, 'BattleResult': 1, 'RewardItemList': r.get('RewardItemList', []), 'RewardCharacterList': [],
                'RewardBattleCardList': r.get('RewardBattleCardList', []), 'PlayerAccount': player['PlayerAccount'],
                'AccountMoney': player['AccountMoney'], 'CharacterList': r.get('CharacterList', []), 'AccountLevelUpFlag': 0,
                'ClearRewardList': clear, 'PostSendFlag': False, 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'crucibleTowerMopUp':
        info = ct_info(player)
        if not st['LastClear'] or info['mopupCount']:
            return {'QuestEventStageIndex': st['LastClear'], 'AccountMoney': player['AccountMoney'], 'ResultCode': 1,
                    'ResultMessage': 'nothing to sweep today'}
        floors = ev['stages'].index(st['LastClear']) + 1; gold = int(ev['tower']['mopupGold']) * floors
        player['AccountMoney']['Gold'] += gold; st['MopupTime'] = now_ms(); save(player)
        return {'QuestEventStageIndex': st['LastClear'], 'AccountLevelUpFlag': 0, 'RewardContentsList': [goods(1, 1, gold)],
                'RewardItemList': [], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'PlayerAccount': player['PlayerAccount'],
                'AccountMoney': player['AccountMoney'], 'CharacterList': [character_simple(c) for c in player['CharacterList']],
                'PostSendFlag': False, 'GuildBuffList': [], 'AccountLevelUpRewardList': [], 'AdsList': [], 'GlobalDropRewardList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    return None


# ---- Buff Select Dungeon (/api/questEvent/buffDungeon{Info,Character,Start,End,FighterBuff,Revive,RankingList,RankingInfoDetail};
#      DTOs BuffSelectDungeon* from the PC dump). questevent.json event with a 'buffselect' key (make_data, event 111): stages
#      {stageIndex: questEventStageIndex}, picks [[dungeonBuffIndex, weight]], revive item. Client semantics (Ghidra): Dungeon.
#      PlayStageIndex / LastClearStageIndex are stageIndex values; BuffSelectStageIndex + BuffSelectIndexList = the pending pick and
#      its 3 offered dungeonBuffIndex values; StageList = the picks made {StageIndex, BuffIndex}; CharacterList RemainHp is 0-100,
#      Status 0 = dead. State in player['BuffDungeon'] for the season (local calendar month); floor wins pay like event stages.
def bsd_event():
    return next((e for e in questevent_cfg().get('events', []) if e.get('buffselect')), None)


def bsd_season():
    t = time.localtime()
    return max(1, (t.tm_year - 2026) * 12 + t.tm_mon - 9)


def bsd_state(player):
    ev = bsd_event(); st = player.setdefault('BuffDungeon', {})
    if st.get('Season') != bsd_season():   # new season: start over
        st.clear(); st.update({'Season': bsd_season(), 'LastClear': 0, 'PickStage': 0, 'Offer': [], 'Picks': [], 'Hp': {}, 'Team': [],
                               'Best': 0, 'BestTime': 0})
    inv = {i['ItemIndex']: i for i in items(player)}; rv = int(ev['buffselect']['revive'])
    if st.get('ReviveDay') != _today():   # daily revival tickets
        st['ReviveDay'] = _today()
        if rv not in inv:
            player['ItemList'].append({'ItemIndex': rv, 'Qty': 0, 'Lock': False}); inv[rv] = player['ItemList'][-1]
        inv[rv]['Qty'] = max(int(inv[rv]['Qty']), int(ev['buffselect'].get('reviveDaily', 3)))
    return st


def bsd_dungeon(st):
    t = [int(x) for x in st['Team']] + [0] * 6
    return {'Season': st['Season'], 'PlayStageIndex': min(int(st['LastClear']) + 1, len(bsd_event()['buffselect']['stages'])),
            'LastClearStageIndex': int(st['LastClear']), 'BuffSelectStageIndex': int(st['PickStage']),
            'BuffSelectIndexList': ','.join(str(x) for x in st['Offer']), 'CharacterIndex1': t[0], 'CharacterIndex2': t[1],
            'CharacterIndex3': t[2], 'SupportCharacterIndex1': t[3], 'SupportCharacterIndex2': t[4], 'SupportCharacterIndex3': t[5],
            'TeamRelationIndex': 0, 'GroupGrowthIndex': 0, 'BossHpInfo': ''}


def bsd_chars(st):
    return [{'CharacterIndex': int(ci), 'RemainHp': int(h), 'Status': 1 if int(h) > 0 else 0} for ci, h in sorted(st['Hp'].items(), key=lambda x: int(x[0]))]


def bsd_picks(st):
    return [{'StageIndex': int(sg), 'BuffIndex': str(b)} for sg, b in st['Picks']]


def bsd_info(st):
    t = time.localtime(); start = int(time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, -1))) * 1000
    return {'BuffSelectDungeonSeason': {'Season': st['Season'], 'StartDate': start, 'EndDate': league_season()['SeasonEndDate'], 'StageBuffList': []},
            'Dungeon': bsd_dungeon(st), 'StageList': bsd_picks(st), 'CharacterList': bsd_chars(st), 'ResultCode': 0, 'ResultMessage': ''}


def bsd_offer(ev, st):
    pool = [list(x) for x in ev['buffselect']['picks']]; out = []
    while pool and len(out) < 3:   # 3 different options, weighted
        r = random.uniform(0, sum(w for _, w in pool)); acc = 0
        for i, (di, w) in enumerate(pool):
            acc += w
            if r <= acc:
                out.append(int(di)); pool.pop(i); break
    return out


def bsd_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; ev = bsd_event(); st = bsd_state(player); ok = {'ResultCode': 0, 'ResultMessage': ''}
    with open(Path(__file__).resolve().parent / 'bsd_debug.jsonl', 'a') as f:   # first runs: what the client sends
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if op == 'buffDungeonInfo':
        save(player); return bsd_info(st)
    if op == 'buffDungeonCharacter':
        st['Team'] = [int(payload.get(k) or 0) for k in ('CharacterIndex1', 'CharacterIndex2', 'CharacterIndex3', 'supportCharacterIndex1',
                                                             'supportCharacterIndex2', 'supportCharacterIndex3')]
        save(player)
        return dict(ok, Dungeon=bsd_dungeon(st), CharacterList=bsd_chars(st))
    if op == 'buffDungeonStart':
        deck = payload.get('PlayDeckInfo') or {}
        team = ([int(x) for x in deck.get('PlayFighterArray') or deck.get('playFighterArray') or []] + [0, 0, 0])[:3]   # PlayDeckInfo
        if any(team): st['Team'] = team + (st['Team'][3:6] if len(st['Team']) >= 6 else [0, 0, 0])
        for ci in team:
            if ci and str(ci) in st['Hp'] and int(st['Hp'][str(ci)]) <= 0:
                return dict(ok, ResultCode=1, ResultMessage='a fallen fighter is in the team', AccountMoney=player['AccountMoney'])
        save(player)
        return dict(ok, AccountMoney=player['AccountMoney'], LuckySpawn=0, DropGoldLucky=0, DropGoldJaco=0, DropGoldElite=0, DropGoldBoss=0,
                    DropGoldGimmick1=0, DropGoldGimmick2=0, DropGoldGimmick3=0, DropLuckyList=[], DropJacoList=[], DropEliteList=[],
                    DropBossList=[], DropGimmickList=[], QuestEventPlayToken=now_ms())
    if op == 'buffDungeonEnd':
        sidx = int(payload.get('StageIndex') or 0); qsi = int(ev['buffselect']['stages'].get(str(sidx), 0))
        won = int(payload.get('BattleResult') or 0) == 1
        for slot, ci in enumerate(st['Team'][:3], 1):   # HP carries over (percent); 0 = fallen
            if ci:
                st['Hp'][str(ci)] = max(0, min(100, int(payload.get('Character%dHp' % slot) or 0)))
        r = {}
        if won and qsi and sidx == int(st['LastClear']) + 1:
            r = questevent_end(player, {'QuestEventStageIndex': qsi, 'BattleResult': 1, 'CharacterList': [{'CharacterIndex': c} for c in st['Team'][:3] if c]})
            st['LastClear'] = sidx; st['Best'] = max(int(st['Best']), sidx)
            if sidx < len(ev['buffselect']['stages']):
                st['PickStage'] = sidx; st['Offer'] = bsd_offer(ev, st)
        save(player)
        return dict(ok, QuestEventStageIndex=qsi, BattleResult=1 if won else 0, FirstClearFlag=r.get('FirstClearFlag', 0), AccountLevelUpFlag=0,
                    AccountMoney=player['AccountMoney'], PlayerAccount=player['PlayerAccount'],
                    CharacterList=r.get('CharacterList') or [character_simple(c) for c in player['CharacterList']], RewardCharacterList=[],
                    RewardBattleCardList=[], RewardItemList=r.get('RewardItemList', []), RewardImprintStoneList=[],
                    ClearRewardList=list(r.get('ClearRewardList') or []) + [dict(g, No=len(r.get('ClearRewardList') or []) + 1 + k)
                                                                          for k, g in enumerate(r.get('FirstClearRewardList') or [])],
                    PostSendFlag=False, AccountLevelUpRewardList=[], presetCharacterList=[], presetCharacterCoreList=[],
                    Dungeon=bsd_dungeon(st), StageList=bsd_picks(st), DungeonCharacterList=bsd_chars(st))
    if op == 'buffDungeonFighterBuff':
        di = int(payload.get('DungeonBuffIndex') or 0)
        if st['PickStage'] and di in st['Offer']:
            st['Picks'].append([int(st['PickStage']), di]); stage = {'StageIndex': int(st['PickStage']), 'BuffIndex': str(di)}
            st['PickStage'] = 0; st['Offer'] = []
        else:
            stage = {'StageIndex': 0, 'BuffIndex': ''}
        save(player)
        return dict(ok, Dungeon=bsd_dungeon(st), Stage=stage)
    if op == 'buffDungeonRevive':
        ci = str(int(payload.get('CharacterIndex') or 0)); rv = int(ev['buffselect']['revive'])
        it = next((i for i in items(player) if i['ItemIndex'] == rv), None)
        if ci in st['Hp'] and it and int(it['Qty']) > 0:
            it['Qty'] -= 1; st['Hp'][ci] = 100
        save(player)
        return dict(ok, CharacterList=bsd_chars(st), RemainItem=it or {'ItemIndex': rv, 'Qty': 0, 'Lock': False})
    if op == 'buffDungeonRankingList':
        me = {'Rank': 1, 'RankRate': 100, 'Score': float(st['Best']), 'Time': 0}   # RankingDataRank
        return dict(ok, MyRanking=me, RankingList=[], RankingUserList=[], FriendGuildInfoList=[])
    if op == 'buffDungeonRankingInfoDetail':
        return dict(ok, BestRecord=int(st['Best']), BestRecordTime=0, TeamRelationIndex=0, CharacterList=[], BattleCardList=[],
                    CharacterCoresList=[], ImprintStoneList=[], CharacterAwakenCoreList=[], ListBuff=[], AccountGrowthStatList=[], AccountExtraList=[])
    return None


# ---- Team Relay dungeon (/api/relayDungeon/*; paths + DTOs from the Android dump: TeamRelayDungeon, TeamRelayCharacter,
#      TeamRelayMyRankInfoWebData). The table (TeamRelayTable, teamrelay.json) reuses the Gold Rush event stage and the
#      Rugal boss. The server keeps BossHP, best record, play count and the 3 relay decks in player['TeamRelay'].
TEAMRELAY_PATH = Path(__file__).resolve().parent / 'teamrelay.json'
_TEAMRELAY = None
def teamrelay_cfg():
    global _TEAMRELAY
    if _TEAMRELAY is None:
        _TEAMRELAY = json.loads(TEAMRELAY_PATH.read_text()) if TEAMRELAY_PATH.exists() else None
    return _TEAMRELAY


def relay_rows():
    """Relay dungeons: the Team Relay (top-level keys of teamrelay.json, ModeIndex 501) plus make_data's 'relays'
    (High Score 503, Meta Team Relay 502). dungeonInfoList answers by ModeIndex; the other routes carry TeamRelayIndex."""
    cfg = teamrelay_cfg() or {}
    base = {k: v for k, v in cfg.items() if k != 'relays'}; base.setdefault('mode', 501)
    return [base] + [dict(r) for r in cfg.get('relays') or []]


def relay_row(idx):
    rows = relay_rows()
    return next((r for r in rows if int(r.get('index', 0)) == int(idx or 0)), rows[0])


def teamrelay_state(player, cfg=None):
    cfg = cfg or relay_rows()[0]
    if int(cfg.get('index', 0)) == int(relay_rows()[0].get('index', 0)):
        st = player.setdefault('TeamRelay', {})
    else:
        st = player.setdefault('TeamRelays', {}).setdefault(str(int(cfg['index'])), {})
    st.setdefault('BossHP', int(cfg.get('bossHP', 0))); st.setdefault('BestRecord', 0); st.setdefault('PlayCount', 0)
    st.setdefault('LastScore', 0); st.setdefault('Decks', [])
    return st


def teamrelay_dungeon(player, cfg=None):
    cfg = cfg or relay_rows()[0]; st = teamrelay_state(player, cfg)
    return {'TeamRelayIndex': int(cfg.get('index', 0)), 'Point': 99, 'Recharge': 0, 'BestRecord': int(st['BestRecord']),
            'BestRewardIndex': '', 'DeckCount': max(len(st['Decks']), int(cfg.get('decks', 3))),   # open relay decks (0 locked decks 2-3, seen live)
            'StageBuffIndexList': '', 'Season': 1, 'beforeSeason': 0,
            'BestRecordTime': 0, 'BossHP': int(st['BossHP']), 'PlayCount': int(st['PlayCount']),
            'BattleResult': 1 if st['BossHP'] <= 0 else 0, 'seasonStartTime': league_season()['SeasonStartDate'], 'seasonEndTime': league_season()['SeasonEndDate'],
            'NewSeason': 0, 'LastPlayScore': int(st['LastScore']), 'mopupCount': 0, 'clearResult': 1 if st['BossHP'] <= 0 else 0}


def teamrelay_rank(player, cfg=None):
    return {'rank': 1, 'rankRate': 100, 'score': float(teamrelay_state(player, cfg)['BestRecord']), 'time': 0}


def teamrelay_end(player, payload):
    cfg = relay_row(payload.get('TeamRelayIndex') or payload.get('teamRelayIndex')); st = teamrelay_state(player, cfg)
    dmg = int(payload.get('TotalDamage') or 0)
    st['BossHP'] = max(0, int(st['BossHP']) - dmg); st['PlayCount'] += 1; st['LastScore'] = dmg
    st['BestRecord'] = max(int(st['BestRecord']), dmg)
    money = player['AccountMoney']; gold = int(cfg.get('gold', 0)); money['Gold'] += gold
    rewards = [goods(1, 1, gold)]
    pay_coin(player, 31, 40 if st['BossHP'] <= 0 else 10, rewards)   # Soul Token -> Soul Exchange
    if st['BossHP'] <= 0:   # boss down: reset for the next run after paying out
        st['BossHP'] = int(cfg.get('bossHP', 0))
    save(player)
    return {'DungeonInfo': teamrelay_dungeon(player, cfg), 'RewardItemList': [], 'RewardCharacterList': [], 'AccountMoney': money,
            'RewardBattleCardList': [], 'PostSendFlag': False, 'RewardList': rewards, 'GlobalDropRewardList': [],
            'RewardImprintStoneList': [], 'OldRanking': teamrelay_rank(player, cfg), 'NewRanking': teamrelay_rank(player, cfg),
            'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False},
            'ResultCode': 0, 'ResultMessage': ''}


# ---- Epic Quest (/api/epicQuest/*; DTOs EpicQuest {EpicQuestIndex,State}, EpicChapter {.., UnlockFlag, State},
#      EpicStage {.., BattleResult, Mission1-3Index, PaymentPlayCount} from the Android dump). epicquest.json (make_data):
#      {epics: [{index, chapters: [{index, stages}]}], stages: {stage: {epic, chapter, gold, firstCash}}}; state in
#      player['EpicStageList']. ChapterList/StageList requests carry EpicQuestIndex (+ EpicQuestChapterIndex).
EPIC_PATH = Path(__file__).resolve().parent / 'epicquest.json'
_EPIC = None
def epic_cfg():
    global _EPIC
    if _EPIC is None:
        _EPIC = json.loads(EPIC_PATH.read_text()) if EPIC_PATH.exists() else None
        if _EPIC and 'epics' not in _EPIC: _EPIC = None   # old single-epic file: rebuild with make_data
    return _EPIC


def epic_cleared(player):
    return {r['EpicQuestStageIndex'] for r in player.setdefault('EpicStageList', []) if int(r.get('BattleResult', 0)) == 1}


def epic_chapters(player, epic):
    """EpicChapter rows of one epic: chapter 1 open, each next one once every stage of the previous chapter is cleared
    (an epic marked locked in epicquest.json reports every chapter locked)."""
    done = epic_cleared(player); out = []; prev_ok = not epic.get('locked')
    for ch in epic['chapters']:
        out.append({'EpicQuestIndex': epic['index'], 'EpicQuestChapterIndex': ch['index'], 'UnlockFlag': prev_ok, 'State': 1})
        prev_ok = prev_ok and all(s in done for s in ch['stages'])
    return out


def epic_stage_rows(player, epic, chapter):
    st = {r['EpicQuestStageIndex']: r for r in player.setdefault('EpicStageList', [])}
    return [{'EpicQuestIndex': epic['index'], 'EpicQuestChapterIndex': chapter['index'], 'EpicQuestStageIndex': si,
             'BattleResult': int(st.get(si, {}).get('BattleResult', 0)), 'Mission1Index': int(st.get(si, {}).get('Mission1Index', 0)),
             'Mission2Index': int(st.get(si, {}).get('Mission2Index', 0)), 'Mission3Index': int(st.get(si, {}).get('Mission3Index', 0)),
             'PaymentPlayCount': 0} for si in chapter['stages']]


def epic_end(player, payload, mopup=False):
    cfg = epic_cfg() or {}; idx = int(payload.get('EpicQuestStageIndex') or 0); sc = (cfg.get('stages') or {}).get(str(idx))
    if not sc or any(e.get('locked') for e in cfg['epics'] if e['index'] == sc['epic']):
        return {'EpicQuestIndex': int(payload.get('EpicQuestIndex') or 0), 'EpicQuestStageIndex': idx, 'ResultCode': 1,
                'ResultMessage': 'unknown epic stage', 'AccountMoney': player['AccountMoney']}
    rows = player.setdefault('EpicStageList', []); row = next((r for r in rows if r['EpicQuestStageIndex'] == idx), None)
    if row is None:
        row = {'EpicQuestStageIndex': idx, 'BattleResult': 0}; rows.append(row)
    won = mopup or int(payload.get('BattleResult') or 0) == 1
    if mopup and row['BattleResult'] != 1:
        return {'EpicQuestIndex': sc['epic'], 'EpicQuestStageIndex': idx, 'ResultCode': 1, 'ResultMessage': 'clear the stage first',
                'AccountMoney': player['AccountMoney']}
    first = won and row['BattleResult'] != 1; clear, first_rewards = [], []
    if won:
        row['BattleResult'] = 1
        for k in ('Mission1Index', 'Mission2Index', 'Mission3Index'):
            if int(payload.get(k) or 0):
                row[k] = int(payload[k])
        money = player['AccountMoney']; money['Gold'] += int(sc.get('gold', 0)); clear.append(goods(1, 1, int(sc.get('gold', 0))))
        player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP
        grant_char_exp(player, payload)   # fighter EXP like story/events
        if first:
            money['Cash'] += int(sc.get('firstCash', 0)); first_rewards.append(goods(1, 2, int(sc.get('firstCash', 0))))
    save(player)
    base = {'EpicQuestIndex': sc['epic'], 'EpicQuestStageIndex': idx, 'AccountMoney': player['AccountMoney'],
            'PlayerAccount': player['PlayerAccount'], 'CharacterList': [character_simple(c) for c in player['CharacterList']],
            'RewardItemList': [], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if mopup:
        return dict(base, RewardContentsList=clear)
    return dict(base, BattleResult=1 if won else 0, FirstClearFlag=1 if first else 0, ClearRewardList=clear, FirstClearRewardList=first_rewards)


# ---- Marathon (/api/questEvent/marathon{List,Start,End,Story,Ranking,RankingList}; DTOs QuestEventMarathon* + Marathon
#      {MarathonIndex, MarathonStageIndex, BattleResult, Mission1-3Index, ClearTime, bestGrade} from the PC dump). marathon.json
#      (make_data): {marathons: [{index, stages}], stages: {stage: {marathon, gold, firstCash, scoreMin, scoreMax}}, scores:
#      [[need, gold, rubies]]}; state in player['Marathon'] = {Stages: {stage: row}, Score: {marathon: n}, Last: {marathon: stage}}.
MARATHON_PATH = Path(__file__).resolve().parent / 'marathon.json'
_MR = None
def marathon_cfg():
    global _MR
    if _MR is None:
        _MR = json.loads(MARATHON_PATH.read_text()) if MARATHON_PATH.exists() else None
    return _MR


def marathon_state(player):
    st = player.setdefault('Marathon', {}); st.setdefault('Stages', {}); st.setdefault('Score', {}); st.setdefault('Last', {})
    return st


def marathon_route(path, player, payload):
    cfg = marathon_cfg(); st = marathon_state(player); op = path.rsplit('/', 1)[1]; money = player['AccountMoney']
    mi = int(payload.get('MarathonIndex') or 0)
    if op == 'marathonList':
        rows = [dict(r) for k, r in st['Stages'].items() if (cfg['stages'].get(k) or {}).get('marathon') == mi]
        return {'MarathonList': rows, 'LastPlayStageIndex': int(st['Last'].get(str(mi), 0)), 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('marathonRanking', 'marathonRankingList'):
        mine = {'Rank': 1, 'RankRate': 100, 'Score': float(st['Score'].get(str(mi), 0)), 'Time': 0}
        if op == 'marathonRanking':
            return {'Ranking': mine, 'ResultCode': 0, 'ResultMessage': ''}
        return {'TopRankList': [], 'MyRanking': mine, 'MyRankList': [], 'AccountList': [], 'CharacterList': [], 'ColosseumTierList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    si = int(payload.get('MarathonStageIndex') or 0); sc = cfg['stages'].get(str(si))
    if op == 'marathonStart':
        if not sc:
            return {'ResultCode': 1, 'ResultMessage': 'unknown marathon stage', 'AccountMoney': money}
        money = regen_active_point(player)
        money['ActivePoint'] = max(0, money['ActivePoint'] - int(payload.get('UsedActivePoint') or 0))
        st['Last'][str(sc['marathon'])] = si; save(player)
        return {'MarathonPlayToken': now_ms(), 'PlayStrikeTime': now_ms(), 'AccountMoney': money, 'StrikerType': 0, 'StrikerUsn': 0,
                'StrikerGameDb': 0, 'StrikerNickName': '', 'StrikerBattleCardList': [], 'CharacterCoresList': [], 'LuckySpawn': 0,
                'DropGoldLucky': 0, 'DropGoldJaco': 0, 'DropGoldElite': 0, 'DropGoldBoss': 0, 'DropGoldGimmick1': 0, 'DropGoldGimmick2': 0,
                'DropGoldGimmick3': 0, 'DropLuckyList': [], 'DropJacoList': [], 'DropEliteList': [], 'DropBossList': [], 'DropGimmickList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'marathonStory':
        return {'MarathonIndex': mi, 'MarathonStageIndex': si, 'FirstClearFlag': 0, 'AccountMoney': money, 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'RewardItemList': [], 'FirstClearRewardList': [], 'PostSendFlag': False, 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'marathonEnd':
        if not sc:
            return {'ResultCode': 1, 'ResultMessage': 'unknown marathon stage', 'AccountMoney': money}
        mi = sc['marathon']; row = st['Stages'].setdefault(str(si), {'MarathonIndex': mi, 'MarathonStageIndex': si, 'BattleResult': 0,
            'Mission1Index': 0, 'Mission2Index': 0, 'Mission3Index': 0, 'ClearTime': 0, 'bestGrade': 0})
        won = int(payload.get('BattleResult') or 0) == 1; first = won and row['BattleResult'] != 1; clear, first_rewards = [], []; add = 0
        if won:
            row['BattleResult'] = 1
            for k in ('Mission1Index', 'Mission2Index', 'Mission3Index'):
                if int(payload.get(k) or 0): row[k] = int(payload[k])
            ct = int(payload.get('ClearTime') or 0)
            if ct and (not row['ClearTime'] or ct < row['ClearTime']): row['ClearTime'] = ct
            money['Gold'] += int(sc['gold']); clear.append(goods(1, 1, int(sc['gold'])))
            player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP
            grant_char_exp(player, payload)
            if first:
                money['Cash'] += int(sc['firstCash']); first_rewards.append(goods(1, 2, int(sc['firstCash'])))
            # event score (MarathonStageProto clearMarathonScoreMin/Max); crossing a MarathonScoreTable step pays its reward
            add = random.randint(int(sc['scoreMin']), int(sc['scoreMax']))
            before = int(st['Score'].get(str(mi), 0)); after = before + add; st['Score'][str(mi)] = after
            for need, gold, cash in cfg.get('scores', []):
                if before < need <= after:
                    if gold: money['Gold'] += gold; clear.append(goods(1, 1, gold))
                    if cash: money['Cash'] += cash; clear.append(goods(1, 2, cash))
        save(player)
        return {'MarathonIndex': mi, 'MarathonStageIndex': si, 'BattleResult': 1 if won else 0, 'FirstClearFlag': 1 if first else 0,
                'AccountLevelUpFlag': 0, 'AccountMoney': money, 'PlayerAccount': player['PlayerAccount'],
                'CharacterList': [character_simple(c) for c in player['CharacterList']], 'RewardCharacterList': [], 'RewardBattleCardList': [],
                'RewardItemList': [], 'Mission1RewardList': [], 'Mission2RewardList': [], 'Mission3RewardList': [], 'MissionAllRewardList': [],
                'FirstClearRewardList': first_rewards, 'ClearRewardList': clear, 'AffectionRewardList1': [], 'AffectionRewardList2': [],
                'AffectionRewardList3': [], 'PostSendFlag': False, 'AddScore': add, 'AddTimeAttackScore': 0, 'BonusRewardContentsList': [],
                'GlobalDropRewardList': [], 'AccountLevelUpRewardList': [], 'bestGrade': 0, 'ResultCode': 0, 'ResultMessage': ''}
    return {'ResultCode': 0, 'ResultMessage': ''}


# ---- Event Towers (/api/questEvent/eventTower{Info,Start,End,DeckUpdate}; DTOs EventTower* + struct EventTowerInfo
#      {QuestEventIndex, PlayStageIndex, LastClearStageIndex, CharacterIndex1-3, TeamRelationIndex, GroupGrowthIndex} from the PC
#      dump). eventtower.json (make_data): {towers: [{index, stages}], stages: {stage: {tower, floor, gold, firstCash}}}; state in
#      player['EventTower'][tower] = {Last, Play, Deck: [c1, c2, c3], Relation, Growth}.
TOWER_PATH = Path(__file__).resolve().parent / 'eventtower.json'
_TW = None
def tower_cfg():
    global _TW
    if _TW is None:
        _TW = json.loads(TOWER_PATH.read_text()) if TOWER_PATH.exists() else None
    return _TW


def tower_state(player, ti):
    st = player.setdefault('EventTower', {}).setdefault(str(ti), {'Last': 0, 'Play': 0, 'Deck': [0, 0, 0], 'Relation': 0, 'Growth': 0})
    return st


def tower_info(ti, st):
    return {'QuestEventIndex': int(ti), 'PlayStageIndex': int(st['Play']), 'LastClearStageIndex': int(st['Last']),
            'CharacterIndex1': int(st['Deck'][0]), 'CharacterIndex2': int(st['Deck'][1]), 'CharacterIndex3': int(st['Deck'][2]),
            'TeamRelationIndex': int(st['Relation']), 'GroupGrowthIndex': int(st['Growth'])}


def tower_route(path, player, payload):
    cfg = tower_cfg(); op = path.rsplit('/', 1)[1]; money = player['AccountMoney']
    if op in ('eventTowerInfo', 'eventTowerDeckUpdate'):
        ti = int(payload.get('QuestEventIndex') or 0); st = tower_state(player, ti)
        if op == 'eventTowerDeckUpdate':
            st['Deck'] = [int(payload.get('CharacterIndex%d' % k) or 0) for k in (1, 2, 3)]
            st['Relation'] = int(payload.get('TeamRelationIndex') or 0); st['Growth'] = int(payload.get('GroupGrowthIndex') or 0); save(player)
            return {'EventTower': tower_info(ti, st), 'ResultCode': 0, 'ResultMessage': ''}
        return {'EventTower': tower_info(ti, st), 'EntryCharacterIndexList': [], 'ResultCode': 0, 'ResultMessage': ''}
    si = int(payload.get('QuestEventStageIndex') or 0); sc = cfg['stages'].get(str(si))
    if not sc:
        return {'ResultCode': 1, 'ResultMessage': 'unknown tower stage', 'AccountMoney': money}
    st = tower_state(player, sc['tower'])
    if op == 'eventTowerStart':
        if any(int(payload.get('CharacterIndex%d' % k) or 0) for k in (1, 2, 3)):
            st['Deck'] = [int(payload.get('CharacterIndex%d' % k) or 0) for k in (1, 2, 3)]
        st['Play'] = si; save(player)
        return {'EventTowerPlayToken': now_ms(), 'AccountMoney': money, 'StrikerType': 0, 'StrikerUsn': 0, 'StrikerGameDb': 0,
                'StrikerNickName': '', 'StrikerBattleCardList': [], 'CharacterCoresList': [], 'LuckySpawn': 0, 'DropGoldLucky': 0,
                'DropGoldJaco': 0, 'DropGoldElite': 0, 'DropGoldBoss': 0, 'DropGoldGimmick1': 0, 'DropGoldGimmick2': 0, 'DropGoldGimmick3': 0,
                'DropLuckyList': [], 'DropJacoList': [], 'DropEliteList': [], 'DropBossList': [], 'DropGimmickList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'eventTowerEnd':
        won = int(payload.get('BattleResult') or 0) == 1; clear, first_rewards = [], []
        stages = next(t['stages'] for t in cfg['towers'] if t['index'] == sc['tower'])
        first = won and stages.index(si) > (stages.index(st['Last']) if st['Last'] in stages else -1)
        if won:
            money['Gold'] += int(sc['gold']); clear.append(goods(1, 1, int(sc['gold'])))
            player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP
            grant_char_exp(player, payload)
            if first:
                st['Last'] = si; money['Cash'] += int(sc['firstCash']); first_rewards.append(goods(1, 2, int(sc['firstCash'])))
        st['Play'] = 0; save(player)
        return {'QuestEventStageIndex': si, 'BattleResult': 1 if won else 0, 'RewardItemList': [], 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'PlayerAccount': player['PlayerAccount'], 'AccountMoney': money,
                'CharacterList': [character_simple(c) for c in player['CharacterList']], 'AccountLevelUpFlag': 0,
                'ClearRewardList': clear, 'AffectionRewardList1': [], 'AffectionRewardList2': [], 'AffectionRewardList3': [],
                'FirstClearRewardList': first_rewards, 'PostSendFlag': False, 'GlobalDropRewardList': [], 'AccountLevelUpRewardList': [],
                'EventTower': tower_info(sc['tower'], st), 'ResultCode': 0, 'ResultMessage': ''}
    return {'ResultCode': 0, 'ResultMessage': ''}


# ---- Smash / Rush events (/api/smash/{infoList,setDifficulty,start,end,resetPlayInfo}; DTOs SmashQuest {QuestEventIndex,
#      SmashModeDifficultyIndex, UseDifficulty, SmashModeStageIndex, SmashModeStageNo, ClearAll, DailyRewardRemainTime (Unix ms:
#      DateTimeExts.ToDateTime), DifficultyLock (2 = locked, 1 = first-open effect)} and SmashQuestStage {.., SmashModeStageIndex,
#      Mission1-3Index, BattleResult (1 = cleared), PlayCount}). One SmashQuest per difficulty = one card on the difficulty select;
#      start plays SmashQuest.SmashModeStageIndex and end carries no stage index, so the server keeps the stage being played.
#      smash.json (make_data): {events: [{index, schedule, difficulties: [{index, no, stages, dailyGold, clearCash}]}], stages:
#      {stage: {event, diff, no, gold, firstCash}}}. State: player['Smash'][event] = {Use: difficulty in play, Cur: {diff: current
#      stage}, Done: {diff: 1 when the current run is complete}, Clear: {diff: 1 once ever cleared - unlocks the next difficulty},
#      Won: {stage: 1} (current run), Ever: [stages ever cleared - first-clear rubies], Count: {stage: plays}, Daily: {diff: date},
#      Play: stage being played}. Rewards are mine: per stage gold (+5 rubies the first time), per difficulty a daily all-clear gold
#      reward and the first all-clear rubies (the RewardGroup rows make_data writes for the client's reward popups say the same).
SMASH_PATH = Path(__file__).resolve().parent / 'smash.json'
_SM = None
def smash_cfg():
    global _SM
    if _SM is None:
        _SM = json.loads(SMASH_PATH.read_text()) if SMASH_PATH.exists() else None
    return _SM


def smash_state(player, ev):
    st = player.setdefault('Smash', {}).setdefault(str(ev), {})
    for k, d in (('Use', 0), ('Cur', {}), ('Done', {}), ('Clear', {}), ('Won', {}), ('Ever', []), ('Count', {}), ('Daily', {}), ('Play', 0)):
        st.setdefault(k, d)
    return st


def _sm_next_midnight_ms():
    t = time.localtime(); return int(time.mktime((t.tm_year, t.tm_mon, t.tm_mday + 1, 0, 0, 0, 0, 0, -1)) * 1000)


def _sm_diffs(ev):
    e = next((x for x in smash_cfg()['events'] if x['index'] == int(ev)), None)
    return e['difficulties'] if e else []


def smash_quest(ev, st, d, unlocked):
    sdi, stages = d['index'], d['stages']
    cur = int(st['Cur'].get(str(sdi)) or stages[0]); cur = cur if cur in stages else stages[0]
    done = bool(st['Done'].get(str(sdi)))   # the card's 'Stage Count' and the stage list's cleared spots follow SmashModeStageNo
    # (count = No - 1, seen live: a completed 2-stage run read 1/2 and its last spot stayed open), so a completed run reports count + 1
    return {'QuestEventIndex': int(ev), 'SmashModeDifficultyIndex': sdi, 'UseDifficulty': 1 if int(st['Use']) == sdi else 0,
            'SmashModeStageIndex': cur, 'SmashModeStageNo': stages.index(cur) + 1 + done, 'ClearAll': 1 if done else 0,
            'DailyRewardRemainTime': _sm_next_midnight_ms(), 'DifficultyLock': 0 if unlocked else 2}


def smash_stage_row(ev, st, sdi, si):
    return {'QuestEventIndex': int(ev), 'SmashModeDifficultyIndex': sdi, 'SmashModeStageIndex': si, 'Mission1Index': 0, 'Mission2Index': 0,
            'Mission3Index': 0, 'BattleResult': 1 if st['Won'].get(str(si)) else 0, 'PlayCount': int(st['Count'].get(str(si), 0))}


def smash_quests(ev, st):
    out, prev = [], True
    for d in _sm_diffs(ev):   # difficulty n opens once n-1 was cleared at least once
        out.append(smash_quest(ev, st, d, prev)); prev = bool(st['Clear'].get(str(d['index'])))
    return out


def smash_reset_run(st, d):
    sdi = str(d['index']); st['Cur'][sdi] = d['stages'][0]; st['Done'].pop(sdi, None)
    for si in d['stages']: st['Won'].pop(str(si), None)


def smash_route(path, player, payload):
    cfg = smash_cfg(); op = path.rsplit('/', 1)[1]; money = player['AccountMoney']
    ev = int(payload.get('QuestEventIndex') or 0); st = smash_state(player, ev); diffs = _sm_diffs(ev)
    if not diffs:
        return {'ResultCode': 1, 'ResultMessage': 'unknown smash event', 'AccountMoney': money}
    dmap = {d['index']: d for d in diffs}
    if op == 'infoList':
        use = dmap.get(int(st['Use']))
        rows = [smash_stage_row(ev, st, use['index'], si) for si in use['stages']] if use else []
        return {'ServerUtcTime': now_ms(), 'SmashQuestList': smash_quests(ev, st), 'SmashQuestStageList': rows, 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('setDifficulty', 'resetPlayInfo'):
        d = dmap.get(int(payload.get('SmashModeDifficultyIndex') or 0))
        if not d:
            return {'ResultCode': 1, 'ResultMessage': 'unknown smash difficulty', 'AccountMoney': money}
        if op == 'resetPlayInfo' or st['Done'].get(str(d['index'])): smash_reset_run(st, d)
        if op == 'setDifficulty': st['Use'] = d['index']
        save(player)
        q = next(x for x in smash_quests(ev, st) if x['SmashModeDifficultyIndex'] == d['index'])
        return {'ServerUtcTime': now_ms(), 'SmashQuest': q, 'SmashQuestStageList': [smash_stage_row(ev, st, d['index'], si) for si in d['stages']],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'start':
        si = int(payload.get('SmashModeStageIndex') or 0); sc = cfg['stages'].get(str(si))
        if not sc or sc['event'] != ev:
            return {'ResultCode': 1, 'ResultMessage': 'unknown smash stage', 'AccountMoney': money}
        money = regen_active_point(player)
        money['ActivePoint'] = max(0, money['ActivePoint'] - max(0, int(payload.get('UsedActivePoint') or 0)))
        st['Play'] = si; st['Use'] = sc['diff']; save(player)
        return {'PlayToken': now_ms(), 'PlayStrikeTime': now_ms(), 'AccountMoney': money, 'StrikerType': 0, 'StrikerUsn': 0, 'StrikerGameDb': 0,
                'StrikerNickName': '', 'StrikerBattleCardList': [], 'CharacterCoresList': [], 'LuckySpawn': 0, 'DropGoldLucky': 0,
                'DropGoldJaco': 0, 'DropGoldElite': 0, 'DropGoldBoss': 0, 'DropGoldGimmick1': 0, 'DropGoldGimmick2': 0, 'DropGoldGimmick3': 0,
                'DropLuckyList': [], 'DropJacoList': [], 'DropEliteList': [], 'DropBossList': [], 'DropGimmickList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'end':
        si = int(st['Play'] or 0); sc = cfg['stages'].get(str(si))
        if not sc or sc['event'] != ev:
            return {'ResultCode': 1, 'ResultMessage': 'no smash stage in play', 'AccountMoney': money}
        d = dmap[sc['diff']]; sdi = str(d['index']); won = int(payload.get('BattleResult') or 0) == 1
        clear, first, daily, allc = [], [], [], []; first_flag = 0
        st['Count'][str(si)] = int(st['Count'].get(str(si), 0)) + 1
        if won:
            st['Won'][str(si)] = 1
            money['Gold'] += int(sc['gold']); clear.append(goods(1, 1, int(sc['gold'])))
            player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP
            grant_char_exp(player, payload)
            if si not in st['Ever']:
                st['Ever'].append(si); first_flag = 1; money['Cash'] += int(sc['firstCash']); first.append(goods(1, 2, int(sc['firstCash'])))
            k = d['stages'].index(si)
            if k + 1 < len(d['stages']):
                st['Cur'][sdi] = d['stages'][k + 1]
            else:   # rush complete
                st['Done'][sdi] = 1
                today = time.strftime('%Y-%m-%d')
                if st['Daily'].get(sdi) != today:
                    st['Daily'][sdi] = today; money['Gold'] += int(d['dailyGold']); daily.append(goods(1, 1, int(d['dailyGold'])))
                if not st['Clear'].get(sdi):
                    st['Clear'][sdi] = 1; money['Cash'] += int(d['clearCash']); allc.append(goods(1, 2, int(d['clearCash'])))
        st['Play'] = 0; save(player)
        q = next(x for x in smash_quests(ev, st) if x['SmashModeDifficultyIndex'] == d['index'])
        return {'ResultSmashQuest': q, 'ResultSmashQuestStage': smash_stage_row(ev, st, d['index'], si), 'BattleResult': 1 if won else 0,
                'FirstClearFlag': first_flag, 'AccountLevelUpFlag': 0, 'PlayerAccount': player['PlayerAccount'],
                'CharacterList': [character_simple(c) for c in player['CharacterList']], 'RewardCharacterList': [], 'RewardBattleCardList': [],
                'RewardItemList': [], 'Mission1RewardList': [], 'Mission2RewardList': [], 'Mission3RewardList': [], 'MissionAllRewardList': [],
                'FirstClearRewardList': first, 'ClearRewardList': clear, 'DailyAllClearRewardList': daily, 'AllClearRewardList': allc,
                'AffectionRewardList1': [], 'AffectionRewardList2': [], 'AffectionRewardList3': [], 'PostSendFlag': False,
                'GuildBuffList': [], 'BonusRewardContentsList': [], 'GlobalDropRewardList': [], 'AccountLevelUpRewardList': [],
                'AccountMoney': money, 'ResultCode': 0, 'ResultMessage': ''}
    return {'ResultCode': 0, 'ResultMessage': ''}


# ---- Fighter Quest (/api/fighterQuest/*; DTOs FighterQuest, FighterQuestPlayInfo from the Android dump). Duels use
#      "points" (Point/MaxPoint, 1 per duel, local regen); state in player['FighterQuest'] = {Point, List:[...]}.
FQ_PATH = Path(__file__).resolve().parent / 'fighterquest.json'
_FQ = None
def fq_cfg():
    global _FQ
    if _FQ is None:
        _FQ = json.loads(FQ_PATH.read_text()) if FQ_PATH.exists() else None
    return _FQ


def fq_state(player):
    cfg = fq_cfg() or {}; st = player.setdefault('FighterQuest', {})
    st.setdefault('Point', int(cfg.get('maxPoint', 3))); st.setdefault('List', []); st.setdefault('Current', 0)
    if st.get('PointDay') != _today():   # guide: Soul Tokens refill to the max (3) at midnight; more than that is kept
        st['PointDay'] = _today(); st['Point'] = max(int(st['Point']), int(cfg.get('maxPoint', 3)))
    st['Point'] = min(int(st['Point']), max(int(cfg.get('maxPoint', 3)), int(st['Point'])))
    return st


def fq_rows(player):
    st = {r['FighterQuestIndex']: r for r in fq_state(player)['List']}
    return [{'FighterQuestIndex': q, 'BattleResult': int(st.get(q, {}).get('BattleResult', 0)),
             'Mission1Index': int(st.get(q, {}).get('Mission1Index', 0)), 'Mission2Index': int(st.get(q, {}).get('Mission2Index', 0)),
             'Mission3Index': int(st.get(q, {}).get('Mission3Index', 0))} for q in (fq_cfg() or {}).get('quests', [])]


def fq_playinfo(player):
    cfg = fq_cfg() or {}; st = fq_state(player)
    return {'PointUpdateTime': now_ms(), 'Point': int(st['Point']), 'MaxPoint': int(cfg.get('maxPoint', 10)),
            'FighterQuestIndex': int(st.get('Current', 0)), 'MonsterFighterQuestIndex': int(st.get('Monster', 0)) if st.get('Current') else 0,
            'PickResetCount': 0, 'ChargeCount': 0}


def fq_end(player, payload, mopup=False):
    cfg = fq_cfg() or {}; qi = int(payload.get('FighterQuestIndex') or 0)
    if qi not in cfg.get('quests', []):
        return {'FighterQuestIndex': qi, 'ResultCode': 1, 'ResultMessage': 'unknown duel', 'AccountMoney': player['AccountMoney']}
    st = fq_state(player); row = next((r for r in st['List'] if r['FighterQuestIndex'] == qi), None)
    if row is None:
        row = {'FighterQuestIndex': qi, 'BattleResult': 0}; st['List'].append(row)
    won = mopup or int(payload.get('BattleResult') or 0) == 1
    if mopup and row['BattleResult'] != 1:
        return {'FighterQuestIndex': qi, 'ResultCode': 1, 'ResultMessage': 'clear the duel first', 'AccountMoney': player['AccountMoney']}
    first = won and row['BattleResult'] != 1; clear, firsts = [], []
    if won:
        row['BattleResult'] = 1
        for k in ('Mission1Index', 'Mission2Index', 'Mission3Index'):
            if int(payload.get(k) or 0):
                row[k] = int(payload[k])
        money = player['AccountMoney']; money['Gold'] += int(cfg.get('gold', 0)); clear.append(goods(1, 1, int(cfg.get('gold', 0))))
        pay_coin(player, 6, 15, clear)   # Arena Coin -> Arena Exchange
        st['Point'] = max(0, int(st['Point']) - 1)   # a Soul Token per win
        d, me = (qi - 90000000) // 1000000, qi % 1000000   # rows: 90000000 + difficulty*1000000 + the played fighter
        sq = int(cfg.get('souls', {}).get(str(d), 0)); soul = SOUL_BASE + me
        if sq:   # guide: winning pays Fighter Souls of the played fighter, more on harder difficulties
            inv = {i['ItemIndex']: i for i in items(player)}
            if soul not in inv:
                inv[soul] = {'ItemIndex': soul, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[soul])
            inv[soul]['Qty'] += sq
            clear.append(dict(goods(len(clear) + 1, 0, sq), ContentsIndex=soul, ContentsType=1, ContentsCount=sq))
        player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP
        grant_char_exp(player, payload)   # the duel fighter (request Character)
        if first:
            money['Cash'] += int(cfg.get('firstCash', 0)); firsts.append(goods(1, 2, int(cfg.get('firstCash', 0))))
    st['Current'] = 0; save(player)
    base = {'FighterQuestIndex': qi, 'AccountMoney': player['AccountMoney'], 'PlayerAccount': player['PlayerAccount'],
            'CharacterList': [character_simple(c) for c in player['CharacterList']], 'RewardItemList': [], 'RewardCharacterList': [],
            'RewardBattleCardList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if mopup:
        return dict(base, Point=int(st['Point']), RewardContentsList=clear, MopupTicketItem={'ItemIndex': 0, 'Qty': 0, 'Lock': False})
    return dict(base, BattleResult=1 if won else 0, FirstClearFlag=1 if first else 0, GlobalDropRewardList=clear, FirstClearRewardList=firsts,
                Mission1RewardList=[], Mission2RewardList=[], Mission3RewardList=[], MissionAllRewardList=[])


# ---- Arena League vs local bot teams (/api/arenaLeague/*; DTOs from the PC dump: ArenaLeagueInfoResponse,
#      ArenaLeagueMatchingTarget {CharacterIndex1-3, SupportCharacterIndex1-3, TeamPower, NickName, Tier, Rating, ...},
#      ArenaLeagueStart/EndResponse). State in player['League']. Bot teams/values are local.
def league_season():
    """Season = the local calendar month (the screens showed '26739d' left with a year-2100 end). Season number stays 1 so
    no season-change logic runs; MidProcess dates stay at the end (IsMidProcessTime needs MidProcessStart expired)."""
    tm = time.localtime()
    start = int(time.mktime((tm.tm_year, tm.tm_mon, 1, 0, 0, 0, 0, 0, -1)) * 1000)
    end = int(time.mktime((tm.tm_year + (tm.tm_mon == 12), tm.tm_mon % 12 + 1, 1, 0, 0, 0, 0, 0, -1)) * 1000)
    return {'Season': 1, 'SeasonDisplay': 1, 'SeasonStartDate': start, 'SeasonEndDate': end,
            'MidProcessStartDate': end, 'MidProcessEndDate': end}


LEAGUE_BOTS = [('Benimaru Fan', (104, 103, 118)), ('Terry Bogard Club', (123, 121, 162)), ('Ikari Rookie', (173, 104, 123)),
               ('Psycho Soldier', (103, 118, 121)), ('Kusanagi Dojo', (101, 104, 162)), ('South Town Crew', (118, 123, 173))]


LEAGUE_PATH = Path(__file__).resolve().parent / 'league.json'


def league_state(player):
    st = player.setdefault('League', {})
    st.setdefault('Rating', 1000); st.setdefault('Tier', 1); st.setdefault('Ticket', 10); st.setdefault('Wins', 0)
    st.setdefault('Streak', 0); st.setdefault('Refresh', 0); st.setdefault('Target', 0)
    if st.get('Day') != _today():   # DailyWinning and its milestone claims are per day
        st['Day'] = _today(); st['Wins'] = 0; st['DailyClaimed'] = []
    return st


def league_daily(st):
    return {'DailyWinning': int(st['Wins']), 'DailyWinningReward': ','.join(str(n) for n in st.get('DailyClaimed', [])),
            'Ticket': int(st['Ticket']), 'PaymentPlayCount': 0,
            'TicketRefreshTime': now_ms(), 'NextTicketRefreshTime': now_ms() + 3600000, 'TierCheckFlag': False}


def league_season_info(st):
    return {'Rating': int(st['Rating']), 'Tier': int(st['Tier']), 'WinningStreak': int(st['Streak']), 'ArenaLeague': 1}


def league_rank(st):
    return {'Rank': 1, 'RankRate': 100, 'Score': float(st['Rating']), 'Time': 0}


def league_targets(player, st):
    # all 6 bots: UIPage_SingleDuelLeagueTierSlotList.SetUserList reads one target per tier slot and threw out-of-range
    # with 3 when returning from a fight (seen live; the ready scene then stayed on the loading screen)
    n = len(LEAGUE_BOTS); k = int(st['Refresh']) % n; out = []
    for i in range(n):
        name, chars = LEAGUE_BOTS[(k + i) % n]
        out.append({'RevisionIndex': 0, 'TargetUsn': 900001 + (k + i) % n, 'GameDb': 1, 'Rank': 10 + i,
                    'Rating': int(st['Rating']) - 40 + 40 * i, 'UserType': 0, 'TeamPower': 30000 + 8000 * i,
                    'CharacterIndex1': chars[0], 'CharacterIndex2': chars[1], 'CharacterIndex3': chars[2],
                    'SupportCharacterIndex1': 0, 'SupportCharacterIndex2': 0, 'SupportCharacterIndex3': 0,
                    'NickName': name, 'Tier': int(st['Tier']), 'GuildName': '', 'TeamRelationIndex': 0, 'GroupGrowthIndex': 0})
    return out


def league_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; st = league_state(player)
    if op == 'dailyWinningReward':   # ArenaLeagueDailyWinningRewardRequest {RewardWinning} -> milestone of that many wins
        cfg = json.loads(LEAGUE_PATH.read_text()) if LEAGUE_PATH.exists() else {'dailyWins': {}}
        n = int(payload.get('RewardWinning') or 0); ruby = int(cfg['dailyWins'].get(str(n), 0))
        claimed = st.setdefault('DailyClaimed', [])
        if not ruby or int(st['Wins']) < n or n in claimed:
            return {'ResultCode': 1, 'ResultMessage': 'not available', 'AccountMoney': player['AccountMoney'],
                    'ArenaLeagueDailyInfo': league_daily(st)}
        claimed.append(n); player['AccountMoney']['Cash'] += ruby; save(player)
        return {'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [],
                'ArenaLeagueDailyInfo': league_daily(st), 'PostSendFlag': False, 'presetCharacterReward': [],
                'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'arenaLeagueInfo':
        if int(st['Ticket']) < 10:   # local play: tickets refill whenever the League screen opens
            st['Ticket'] = 10; save(player)
        return {'InitSeason': False, 'RankingSeason': league_season(), 'ArenaLeagueDailyInfo': league_daily(st),
                'ArenaLeagueSeasonInfo': league_season_info(st), 'Ranking': league_rank(st),
                'PrevSeasonResult': {'Rating': 0, 'Tier': 0, 'RankingReward': False, 'Ranking': league_rank(st),
                                     'ArenaLeague': 0, 'LastSeason': 0},
                'ScheduleInfo': {'RankingGroup': 1, 'LeagueEntryIndex': 1, 'ImgSmall': '', 'ImgBig': '', 'RuleDesc': '', 'EntryDesc': ''},
                'MatchInfo': {'RefreshTime': 1600000000000, 'PaymentRefreshCount': 0}, 'ServerUtcTime': now_ms(),
                # the slot list indexes these targets; an empty list threw out-of-range in TierSlotList.SetUserList (seen live)
                'MatchTargetList': league_targets(player, st),
                'ArenaLeagueTierResult': {'Rating': int(st['Rating']), 'Tier': int(st['Tier']), 'Rank': 1, 'RankRate': 100},
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'matchingRefresh':
        st['Refresh'] += 1; save(player)
        return {'ServerUtcTime': now_ms(), 'AccountMoney': player['AccountMoney'], 'MyRanking': league_rank(st),
                'MatchInfo': {'RefreshTime': 1600000000000, 'PaymentRefreshCount': 0}, 'MatchTargetList': league_targets(player, st),
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'arenaLeagueStart':
        st['Ticket'] = max(0, int(st['Ticket']) - 1); st['Target'] = int(payload.get('TargetUsn') or 0); save(player)
        return {'ArenaLeaguePlayToken': now_ms(), 'PlayType': 1,   # SingleDuelPlayType.NormalMatch; 0 = no auto fight order on timeout (SettingTeams out-of-range, seen live)
                'ArenaLeagueDailyInfo': league_daily(st),
                'LeagueStageGroupIndex': 1, 'AccountMoney': player['AccountMoney'],
                'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'arenaLeagueEnd':
        won = int(payload.get('BattleResult') or 0) == 1; money = player['AccountMoney']; rewards = []
        if won:
            st['Rating'] += 20; st['Wins'] += 1; st['Streak'] += 1; money['Gold'] += 3000; rewards.append(goods(1, 1, 3000))
        else:
            st['Rating'] = max(0, int(st['Rating']) - 10); st['Streak'] = 0
        pay_coin(player, 35, 30 if won else 10, rewards)   # League Coin -> League Exchange
        # + Championship Coins (-> Championship Exchange): the Championship itself is live PvP (room server, frame input sync)
        # and cannot run locally, so the League - its single-player ranked counterpart - pays its coin (amounts mine)
        got = []; pay_item(player, CHAMP_COIN, 10 if won else 3, rewards, got)
        save(player); d = 20 if won else -10
        return {'AccountLevelUpFlag': 0, 'AccountMoney': money, 'PlayerAccount': player['PlayerAccount'],
                'CharacterList': [character_simple(c) for c in player['CharacterList']], 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'RewardItemList': got, 'PlayRewardList': rewards,
                'ArenaLeagueDailyInfo': league_daily(st), 'ArenaLeagueSeasonInfo': league_season_info(st), 'PostSendFlag': False,
                'AddScore': {'PlayBase': d, 'PlayBonus': 0, 'PlayScore': d, 'TimeScore': 0, 'AddScoreResult': d},
                'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'GuildBuffList': [], 'GlobalDropRewardList': [],
                'AccountLevelUpRewardList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'rankingList':
        return {'ServerUtcTime': now_ms(), 'RankingSeason': league_season(), 'MyRanking': league_rank(st), 'ArenaLeague': 1,
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'dailyWinningReward':
        return {'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [],
                'ArenaLeagueDailyInfo': league_daily(st), 'PostSendFlag': False, 'ResultCode': 0, 'ResultMessage': ''}
    return {}



# ---- Colosseum = solo duel (ModeType 201 Single_Duel; /api/colosseum/*; DTOs from the PC dump: ColosseumInfoResponse
#      {ColosseumDailyInfo, ColosseumSeasonInfo, MatchTargetList: ColosseumMatchingTarget, ...}, ColosseumStart/End,
#      RankingList, MatchingRefresh, DailyRankingReward). Like the Arena League: local bot teams (LEAGUE_BOTS, ids 920001+,
#      battle/matchUserInfo builds them), rating +20 / -10, tickets refill when the screen opens. State in player['Colosseum'].
#      Values are local.
def colo_state(player):
    st = player.setdefault('Colosseum', {})
    for k, v in (('Rating', 1000), ('Tier', 1), ('Ticket', 10), ('Played', 0), ('Streak', 0), ('Refresh', 0), ('Target', 0), ('Best', 0)):
        st.setdefault(k, v)
    if st.get('Day') != _today():
        st['Day'] = _today(); st['DailyRewarded'] = False
    return st


def colo_daily(st):
    return {'Ticket': int(st['Ticket']), 'PaymentPlayCount': 0, 'TicketRefreshTime': now_ms(), 'NextTicketRefreshTime': now_ms() + 3600000,
            'DailyBestRank': 1, 'DailyBestRankReward': bool(st.get('DailyRewarded')), 'TierCheckFlag': False}


def colo_season_info(st):
    return {'Rating': int(st['Rating']), 'Tier': int(st['Tier']), 'NormalPlayCount': int(st['Played']), 'WinningStreak': int(st['Streak'])}


def colo_tier(rating):   # the 25 bands of ColosseumTierTable (make_data: tier i from 900 + 100 * i, tier 1 below 1100)
    return max(1, min(25, (int(rating) - 900) // 100)) if int(rating) >= 1100 else 1


def colo_targets(st):
    n = len(LEAGUE_BOTS); k = int(st['Refresh']) % n; out = []
    for i in range(n):
        name, chars = LEAGUE_BOTS[(k + i) % n]
        out.append({'RevisionIndex': 0, 'TargetUsn': 920001 + (k + i) % n, 'GameDb': 1, 'Rank': 10 + i,
                    'Rating': int(st['Rating']) - 40 + 40 * i, 'UserType': 0, 'TeamPower': 30000 + 8000 * i,
                    'CharacterIndex1': chars[0], 'CharacterIndex2': chars[1], 'CharacterIndex3': chars[2],
                    'NickName': name, 'Tier': int(st['Tier']), 'GuildName': ''})
    return out


def colo_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; st = colo_state(player); money = player['AccountMoney']
    rank = {'Rank': 1, 'RankRate': 100, 'Score': float(st['Rating']), 'Time': 0}
    if op == 'colosseumInfo':
        if int(st['Ticket']) < 10:   # local play: tickets refill whenever the screen opens
            st['Ticket'] = 10; save(player)
        return {'InitSeason': False, 'RankingSeason': league_season(), 'ColosseumDailyInfo': colo_daily(st),
                'ColosseumSeasonInfo': colo_season_info(st), 'Ranking': rank,
                'PrevSeasonResult': {'Rating': 0, 'Tier': 0, 'RankingReward': False, 'Ranking': rank, 'LastSeason': 0},
                'ScheduleInfo': {'RankingGroup': 1, 'HandicapMax': 0}, 'MatchInfo': {'RefreshTime': 1600000000000, 'PaymentRefreshCount': 0},
                'MatchTargetList': colo_targets(st), 'ServerUtcTime': now_ms(),
                'ColosseumRatingDeduct': None,   # set = 'Arena Deduct: Abnormal Termination' popup (a quit match), seen live
                'ColosseumTierResult': {'Rating': int(st['Rating']), 'Tier': int(st['Tier']), 'Rank': 1, 'RankRate': 100},
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'matchingRefresh':
        st['Refresh'] += 1; save(player)
        return {'ServerUtcTime': now_ms(), 'AccountMoney': money, 'MyRanking': rank,
                'MatchInfo': {'RefreshTime': 1600000000000, 'PaymentRefreshCount': 0}, 'MatchTargetList': colo_targets(st),
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'colosseumStart':
        st['Ticket'] = max(0, int(st['Ticket']) - 1); st['Target'] = int(payload.get('TargetUsn') or 0); st['Token'] = now_ms(); save(player)
        return {'ColosseumPlayToken': st['Token'], 'PlayType': 1, 'OriginalBossGroupIndex': 0,   # 1 = normal match (as League)
                'ColosseumDailyInfo': colo_daily(st), 'HandicapList': [], 'AccountMoney': money,
                'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'colosseumEnd':
        won = int(payload.get('BattleResult') or 0) == 1; rewards = []
        st['Played'] += 1
        if won:
            st['Rating'] += 20; st['Streak'] += 1; money['Gold'] += 3000; rewards.append(goods(1, 1, 3000))
        else:
            st['Rating'] = max(0, int(st['Rating']) - 10); st['Streak'] = 0
        st['Tier'] = colo_tier(st['Rating']); st['Best'] = max(int(st['Best']), int(st['Rating']))
        pay_coin(player, 35, 30 if won else 10, rewards)   # League Coin -> League Exchange (as the Arena League)
        save(player); d = 20 if won else -10
        return {'AccountLevelUpFlag': 0, 'AccountMoney': money, 'PlayerAccount': player['PlayerAccount'],
                'CharacterList': [character_simple(c) for c in player['CharacterList']], 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'RewardItemList': [], 'PlayRewardList': rewards, 'OriginalBossRewardList': [],
                'ColosseumDailyInfo': colo_daily(st), 'ColosseumSeasonInfo': colo_season_info(st), 'PostSendFlag': False,
                'AddScore': {'PlayBase': d, 'PlayBonus': 0, 'PlayScore': d, 'TimeScore': 0, 'Character1Score': 0, 'Character2Score': 0,
                             'Character3Score': 0, 'HandicapRate': 0, 'HandicapBonus': 0, 'AddScoreResult': d},
                'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'GuildBuffList': [],
                'CharacterHp1': int(payload.get('CharacterHp1') or 0), 'CharacterHp2': int(payload.get('CharacterHp2') or 0),
                'CharacterHp3': int(payload.get('CharacterHp3') or 0), 'GlobalDropRewardList': [], 'AccountLevelUpRewardList': [],
                'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'rankingList':
        r = player['Route']; d = player['TeamDeckList'][0]; chars = {c['CharacterIndex']: c for c in player['CharacterList']}
        me = {'Usn': r['Usn'], 'Rating': int(st['Rating']), 'Tier': int(st['Tier'])}
        for n in (1, 2, 3):
            c = chars.get(int(d.get('CharacterIndex%d' % n) or 0), {})
            me.update({'CharacterIndex%d' % n: int(c.get('CharacterIndex', 0)), 'Grade%d' % n: int(c.get('Grade', 0)), 'Exp%d' % n: int(c.get('Exp', 0))})
        return {'ServerUtcTime': now_ms(), 'RankingSeason': league_season(), 'MyRanking': rank,
                'RankingList': [{'Usn': r['Usn'], 'Score': float(st['Rating']), 'GameDb': r.get('GameDb', 1), 'NickName': r.get('NickName', ''), 'Rank': 1}],
                'RankingUserList': [me], 'FriendGuildInfoList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'dailyRankingReward':
        rewards = []
        if not st.get('DailyRewarded'):
            st['DailyRewarded'] = True; money['Cash'] += 50; rewards.append(goods(1, 2, 50)); save(player)
        return {'AccountMoney': money, 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [], 'PostSendFlag': False,
                'ColosseumDailyInfo': colo_daily(st), 'RewardList': rewards, 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                'ResultCode': 0, 'ResultMessage': ''}
    return {}

HOF_PATH = Path(__file__).resolve().parent / 'halloffame.json'


def hof_halls():
    return json.loads(HOF_PATH.read_text())['halls'] if HOF_PATH.exists() else []


def hof_fame_list():
    """battle/battleLobby FameList: one finished season (1) per Hall of Fame row (popupSeason = season: no lobby alarm)."""
    return [{'hallOfFameIndex': int(h), 'season': 1, 'seasonOrder': 1, 'popupSeason': 1} for h, _m in hof_halls()]


def hof_top(player, hall):
    """Top 3 of the last season: the player (league rating) and two league rivals below them (local ranking)."""
    st = league_state(player); d = player['TeamDeckList'][0]
    me = {'hallOfFameIndex': hall, 'season': 1, 'usn': player['PlayerAccount']['Usn'], 'rank': 1, 'rating': int(st['Rating']),
          'characterIndex': int(d.get('CharacterIndex1') or 101), 'guildName': (player.get('Guild') or {}).get('GuildName', ''),
          'nickName': player['Route'].get('NickName', ''), 'gradeIndex': int(st['Tier']), 'gameDb': 0}
    out = [me]
    for n, (name, chars) in enumerate(LEAGUE_BOTS[:2], 2):
        out.append({'hallOfFameIndex': hall, 'season': 1, 'usn': 900000 + n, 'rank': n, 'rating': max(0, int(st['Rating']) - 50 * (n - 1)),
                    'characterIndex': chars[0], 'guildName': '', 'nickName': name, 'gradeIndex': max(1, int(st['Tier']) - 1), 'gameDb': 0})
    return out


MEMTRADE_PATH = Path(__file__).resolve().parent / 'memtrade.json'


def memtrade_cfg():
    return json.loads(MEMTRADE_PATH.read_text()) if MEMTRADE_PATH.exists() else {}


def memtrade_counts(player):
    """player['MemoryTrade']: trades per category this local week (tradeCountResetType 1 = weekly, mine)."""
    st = player.setdefault('MemoryTrade', {}); wk = int(team_week())
    if st.get('Week') != wk:
        st.clear(); st['Week'] = wk
    return [{'memoryCategoryIndex': int(k), 'tradeCount': int(st.get(k, 0))} for k in sorted(memtrade_cfg(), key=int)]


def memtrade_route(op, player, payload):
    cfg = memtrade_cfg()
    if op == 'memoryDimensionTradeInfo':
        return {'MemoryTradeList': memtrade_counts(player)}
    ci = str(int(payload.get('memoryCategoryIndex') or 0)); c = cfg.get(ci)
    memtrade_counts(player); st = player['MemoryTrade']
    # summed per index (item_need): a Memory listed twice was checked entry by entry and went negative (3 + 3 of 4 -> -1)
    need, err = item_need(payload.get('ItemList'))
    inv = {i['ItemIndex']: i for i in items(player)}
    ok = not err and bool(c) and int(st.get(ci, 0)) < int(c['max']) and sum(need.values()) == int(c['count']) and \
        all(ix in c['materials'] for ix in need) and item_short(player, need) is None
    if not ok:
        return {'ResultCode': 1, 'ResultMessage': 'cannot trade'}
    changed = []
    for ix, q in need.items():
        inv[ix]['Qty'] = int(inv[ix]['Qty']) - q; changed.append(inv[ix])
    tgt = inv.get(int(c['target']))
    if tgt is None:
        tgt = {'ItemIndex': int(c['target']), 'Qty': 0, 'Lock': False}; player.setdefault('ItemList', []).append(tgt)
    tgt['Qty'] = int(tgt['Qty']) + 1
    st[ci] = int(st.get(ci, 0)) + 1; save(player)
    # Parse_CharacterMemoryExchange: RewardItemList is ADDED (delta), ItemList is SET (absolute rows; the result showed 6 for +1)
    return {'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [], 'RewardBattleCardList': [],
            'RewardItemList': [{'ItemIndex': int(c['target']), 'Qty': 1, 'Lock': False}],
            'RewardImprintStoneList': [], 'ItemList': changed + [tgt], 'PostSendFlag': False, 'presetCharacterReward': [],
            'presetCharacterCoreReward': [], 'MemoryTradeList': memtrade_counts(player)}


PIECES_PATH = Path(__file__).resolve().parent / 'pieces.json'


def pieces_cfg():
    return json.loads(PIECES_PATH.read_text()) if PIECES_PATH.exists() else {'pieces': {}}


def piece_route(op, player, payload):
    """item/pieceCombine | pieceSell {itemIndex, itemQty} -> PieceRewardResponse (lowercase DTO names). Combining the needed
    pieces grants the fighter, or its Soul + Memory when already owned (like a duplicate summon)."""
    cfg = pieces_cfg()['pieces']; ix = int(payload.get('itemIndex') or 0); qty = int(payload.get('itemQty') or 0); c = cfg.get(str(ix))
    inv = {i['ItemIndex']: i for i in items(player)}; row = inv.get(ix)
    if not c or not row or qty < 1 or int(row['Qty']) < qty or (op == 'pieceCombine' and qty < int(c['need'])):
        return {'ResultCode': 1, 'ResultMessage': 'not enough pieces'}
    out = {'accountMoney': player['AccountMoney'], 'rewardCharacterList': [], 'rewardBattleCardList': [], 'rewardItemList': [],
           'rewardImprintStoneList': [], 'rewardList': [], 'postSendFlag': False}
    if op == 'pieceSell':
        row['Qty'] = int(row['Qty']) - qty; gold = int(c['sell']) * qty
        player['AccountMoney']['Gold'] += gold; out['rewardList'] = [goods(1, 1, gold)]
    else:
        n = qty // int(c['need']); row['Qty'] = int(row['Qty']) - n * int(c['need']); ci = int(c['char'])
        for _k in range(n):
            if any(int(x['CharacterIndex']) == ci for x in player['CharacterList']):
                got = []
                for gix, gq in ((SOUL_BASE + ci, 50), (MEM_BASE + ci, 1)):
                    g = inv.get(gix)
                    if g is None:
                        g = {'ItemIndex': gix, 'Qty': 0, 'Lock': False}; player.setdefault('ItemList', []).append(g); inv[gix] = g
                    g['Qty'] = int(g['Qty']) + gq; got.append({'ItemIndex': gix, 'Qty': gq, 'Lock': False})
                out['rewardItemList'] += got
                out['rewardCharacterList'].append({'CharacterIndex': ci, 'Grade': 3, 'Exp': 0, 'ExCharacterSoul': SOUL_BASE + ci,
                                                   'ExCharacterSoulQty': 50, 'fighterMemoryIndex': MEM_BASE + ci, 'fighterMemoryIndexQty': 1})
            else:
                player['CharacterList'].append(new_character(ci))
                out['rewardCharacterList'].append({'CharacterIndex': ci, 'Grade': 3, 'Exp': 0})
    out['remainItem'] = dict(row); save(player)
    return out


def piece_drop(player, rew):
    """Battlefield win: bfDrop pieces of a random fighter (added to RewardContentsList; returns the ADDED Item rows)."""
    cfg = pieces_cfg(); keys = list(cfg['pieces'])
    if not keys:
        return []
    ix = int(random.choice(keys)); q = int(cfg.get('bfDrop', 5))
    r, _got = pay_reward(player, {'items': [[ix, q]]})
    for x in r:
        x['No'] = len(rew) + 1; rew.append(x)
    return [{'ItemIndex': ix, 'Qty': q, 'Lock': False}]


SERMIS_PATH = Path(__file__).resolve().parent / 'seriesmission.json'


def sermis_cfg():
    return json.loads(SERMIS_PATH.read_text()) if SERMIS_PATH.exists() else {'rows': {}, 'total': {}}


def sermis_stars(player, ser, d):
    """Stars (filled star missions) of the series on a difficulty, from the saved story StageList."""
    return sum(1 for st in player.get('StageList', []) if (int(st.get('SeriesIndex', 0)), int(st.get('StageDifficulty', 0))) == (ser, d)
               for k in ('Mission1Index', 'Mission2Index', 'Mission3Index') if int(st.get(k) or 0))


def sermis_entry(player, ser, d):
    claimed = player.setdefault('SeriesMissions', {}).get('%d,%d' % (ser, d), [])
    return {'SeriesIndex': ser, 'StageDifficulty': d, 'ClearMissionCount': sermis_stars(player, ser, d),
            'RewardList': ','.join(str(x) for x in claimed)}


def sermis_list(player):
    """adventure/stageList StageSeriesMissionList: one row per story series and difficulty."""
    return [sermis_entry(player, *(int(x) for x in key.split(','))) for key in sermis_cfg()['total']]


def grant_fighter(player, ci, dup_souls=50):
    """A fighter reward: the fighter, or its Soul + Memory when already owned -> (CharacterReward row, changed Item rows)."""
    if any(int(c['CharacterIndex']) == ci for c in player['CharacterList']):
        inv = {i['ItemIndex']: i for i in items(player)}; got = []
        for ix, q in ((SOUL_BASE + ci, dup_souls), (MEM_BASE + ci, 1)):
            row = inv.get(ix)
            if row is None:
                row = {'ItemIndex': ix, 'Qty': 0, 'Lock': False}; player.setdefault('ItemList', []).append(row)
            row['Qty'] = int(row['Qty']) + q; got.append(row)
        return ({'CharacterIndex': ci, 'Grade': 3, 'Exp': 0, 'ExCharacterSoul': SOUL_BASE + ci, 'ExCharacterSoulQty': dup_souls,
                 'fighterMemoryIndex': MEM_BASE + ci, 'fighterMemoryIndexQty': 1}, got)
    player['CharacterList'].append(new_character(ci))
    return {'CharacterIndex': ci, 'Grade': 3, 'Exp': 0}, []


def sermis_claim(player, payload):
    cfg = sermis_cfg(); ser = int(payload.get('SeriesIndex') or 0); d = int(payload.get('StageDifficulty') or 0)
    row = cfg['rows'].get(str(int(payload.get('SeriesMissionCompleteIndex') or 0)))
    key = '%d,%d' % (ser, d); claimed = player.setdefault('SeriesMissions', {}).setdefault(key, [])
    if not row or (row[0], row[1]) != (ser, d) or row[2] in claimed or \
            sermis_stars(player, ser, d) < -(-int(row[2]) * int(cfg['total'].get(key, 0)) // 100):
        return {'ResultCode': 1, 'ResultMessage': 'series mission not complete'}
    claimed.append(int(row[2])); money = player['AccountMoney']; chars, got = [], []
    money['Gold'] += int(row[3]); money['Cash'] += int(row[4])
    if row[5]:
        rc, got = grant_fighter(player, int(row[5])); chars.append(rc)
    save(player)
    return {'StageSeriesMission': sermis_entry(player, ser, d), 'AccountMoney': money, 'RewardCharacterList': chars,
            'RewardBattleCardList': [], 'RewardItemList': got, 'PostSendFlag': False, 'RewardImprintStoneList': [],
            'presetCharacterReward': [], 'presetCharacterCoreReward': []}


EXPLORE_PATH = Path(__file__).resolve().parent / 'explore.json'


def explore_cfg():
    return json.loads(EXPLORE_PATH.read_text()) if EXPLORE_PATH.exists() else {'spots': {}, 'rewards': {}, 'periods': []}


def explore_state(player):
    """player['Explore'][spot] = {Open, Period, Fighters[5], Expire (ms, 0 = idle), Power}."""
    st = player.setdefault('Explore', {})
    for k, sp in explore_cfg()['spots'].items():
        st.setdefault(k, {'Open': bool(sp['open']), 'Period': 0, 'Fighters': [0] * 5, 'Expire': 0, 'Power': 0})
    return st


def explore_vo(k, s):
    now = now_ms()
    flag = 0 if not s['Open'] else (1 if not s['Expire'] else (2 if s['Expire'] > now else 3))
    f = (list(s['Fighters']) + [0] * 5)[:5]
    return {'ExploreSpotIndex': int(k), 'ExplorePeriodType': int(s['Period']), 'FighterIndex1': f[0], 'FighterIndex2': f[1],
            'FighterIndex3': f[2], 'FighterIndex4': f[3], 'FighterIndex5': f[4], 'FighterLevelSum': 0, 'ExpireTime': int(s['Expire']),
            'StateFlag': flag}


def explore_route(op, player, payload):
    cfg = explore_cfg(); st = explore_state(player); k = str(int(payload.get('ExploreSpotIndex') or 0)); s = st.get(k)
    lst = lambda: [explore_vo(x, st[x]) for x in sorted(st, key=int)]
    base = lambda **kw: dict({'ServerUtcTime': now_ms(), 'ExploreList': lst()}, **kw)
    if op == 'exploreList':
        save(player); return base()
    if s is None:
        return {'ResultCode': 1, 'ResultMessage': 'no such spot'}
    money = player['AccountMoney']
    if op == 'exploreOpen':
        price = int(cfg['spots'][k]['price'])
        if s['Open'] or money['Cash'] < price:
            return {'ResultCode': 1, 'ResultMessage': 'cannot open'}
        money['Cash'] -= price; s['Open'] = True; save(player)
        return base(AccountMoney=money, ExploreSpotInfo=explore_vo(k, s))
    if not s['Open']:
        return {'ResultCode': 1, 'ResultMessage': 'spot locked'}
    fighters = [int(payload.get('FighterIndex%d' % n) or 0) for n in range(1, 6)]
    if op in ('exploreDeckSetting', 'exploreStart'):
        if s['Expire']:
            return {'ResultCode': 1, 'ResultMessage': 'already exploring'}
        period = int(payload.get('ExplorePeriodType') or 0)
        if period:
            s['Period'] = period
        if any(fighters) or op == 'exploreDeckSetting':
            s['Fighters'] = fighters
        if op == 'exploreStart':
            if not any(s['Fighters']) or int(s['Period']) not in [int(x) for x in cfg['periods']]:
                return {'ResultCode': 1, 'ResultMessage': 'no fighters or time'}
            s['Power'] = sum(int(payload.get('Fighter%dPower' % n) or 0) for n in range(1, 6))
            s['Expire'] = now_ms() + int(s['Period']) * 3600000
        save(player)
        return base(ExploreSpotInfo=explore_vo(k, s)) if op == 'exploreStart' else base()
    if op == 'exploreCancel':
        s['Expire'] = 0; save(player)
        return base(ExploreSpotInfo=explore_vo(k, s))
    if op == 'exploreReward':
        if not s['Expire'] or s['Expire'] > now_ms():
            return {'ResultCode': 1, 'ResultMessage': 'not finished'}
        rows = cfg['rewards'][k].get(str(int(s['Period'])), [])
        row = max((r for r in rows if int(s['Power']) >= int(r[0])), key=lambda r: int(r[0]), default=None)
        rew = []
        if row:
            rew, _got = pay_reward(player, {'gold': row[1], 'items': row[2]})
            if random.randrange(10000) < int(row[4]):
                r2, _g2 = pay_reward(player, {'ruby': row[3]})
                for x in r2:
                    x['No'] = len(rew) + 1; rew.append(x)
        s['Expire'] = 0; save(player)
        return base(AccountMoney=money, ExploreSpotInfo=explore_vo(k, s), RewardList=rew)
    return {'ResultCode': 1, 'ResultMessage': 'unknown explore op'}


def utility_route(path, player, payload):
    """Small account actions (DTOs from the PC dump): nickname, profile message, AP refill for rubies, item use (AddPoint AP),
    imprint stone lock / vested reset. Returns None for other paths."""
    money = player['AccountMoney']
    if path == '/api/player/nickNameSet':   # AccountNickNameSetRequest {NickName}
        name = str(payload.get('NickName') or '').strip()[:16]
        if not name:
            return {'ResultCode': 1, 'ResultMessage': 'empty name'}
        player['Route']['NickName'] = name; save(player)
        return {'NickName': name, 'AccountMoney': money}
    if path == '/api/player/profileMessageUpdate':   # AccountProfileMessageUpdateRequest {Message}
        player.setdefault('ProfileCharacter', {})['Message'] = str(payload.get('Message') or '')[:60]; save(player)
        return {'Message': player['ProfileCharacter']['Message']}
    if path == '/api/player/buyActivePoint':   # BuyActivePointRequest {UseCash, BuyActivePointType} -> refill to the AP maximum
        cost = int(payload.get('UseCash') or 0)
        if cost < 0 or money['Cash'] < cost:
            return {'ResultCode': 1, 'ResultMessage': 'not enough rubies', 'AccountMoney': money}
        regen_active_point(player)
        money['Cash'] -= cost; money['ActivePoint'] = int(money['ActivePoint']) + int(money.get('ActivePointMax') or 100)
        save(player)
        return {'AccountMoney': money}
    if path == '/api/item/lockItem':
        # ItemLockRequest {LockItemIndexList, UnlockItemIndexList} -> ItemLockResponse {ItemList} (TakeAndSetItemList: the rows
        # are SET). Soul Lock (UIPage_SoulLock -> Send_ItemLock). Had no handler: the lock was never saved (item test round 4).
        rows = {i['ItemIndex']: i for i in items(player)}; changed = []
        for key, val in (('LockItemIndexList', True), ('UnlockItemIndexList', False)):
            for ix in payload.get(key) or []:
                r = rows.get(int(ix or 0))
                if r is not None and bool(r.get('Lock')) != val:
                    r['Lock'] = val; changed.append(dict(r))
        save(player)
        return {'ItemList': changed, 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/item/useItem':   # ItemUseRequest {AddPoint, Item{ItemIndex, Qty}} -> spend the item, add AP
        it = payload.get('Item') or {}; ix, q = int(it.get('ItemIndex') or 0), req_count(it, 'Qty')
        row = next((i for i in items(player) if i['ItemIndex'] == ix), None)
        add = int(payload.get('AddPoint') or 0)
        if q is None or not 0 <= add <= QTY_MAX or row is None or int(row['Qty']) < q:
            return {'ResultCode': 1, 'ResultMessage': 'no item', 'AccountMoney': money}
        row['Qty'] = int(row['Qty']) - q; money['ActivePoint'] = int(money['ActivePoint']) + add
        save(player)
        return {'AccountMoney': money, 'Item': dict(row), 'BuffList': [], 'HotTimeInfoList': [], 'rewardList': []}
    if path == '/api/item/openBox':
        # ItemOpenBoxRequest {ItemIndex, Item{ItemIndex, Qty}, SelectedIndex, ItemQty} -> ItemOpenBoxResponse (ItemList = the box's
        # new total, OpenBoxRewardList = the 'received' popup, RewardImprintStoneList = new stones). Guild Raid boxes: contents from
        # guildraid.json boxContents (make_data GRAID_BOXSETS; [gold, Guild Coins, imprint stones, [[item, count], ...]] per box,
        # mine). Parse_ItemOpenBox: ItemList -> TakeAndSetItemList (new totals: the box), RewardItemList -> TakeAndAddItemList
        # (ADDED counts, and its callback puts them in the 'received' popup), OpenBoxRewardList -> popup rows (GoodsType 13 rows
        # are not shown there: with the items only in ItemList the popup listed gold/coins/stones only, live 2026-10-25).
        # NetworkManagerWEB.Send_ItemOpenBox(boxIndex, boxQty, keyIndex, keyCount, selectedIndex): ItemIndex = the box, ItemQty =
        # how many to open, Item = the KEY item (only set when keyIndex > 0), SelectedIndex only when > 0. (The old fallback to
        # Item.ItemIndex / Item.Qty read the key; a 0 or negative count was forced to 1.)
        ix = int(payload.get('ItemIndex') or 0); q = req_count(payload, 'ItemQty')
        box = (graid_cfg().get('boxContents') or {}).get(str(ix))
        row = next((i for i in items(player) if i['ItemIndex'] == ix), None)
        if q is None or box is None or row is None or int(row['Qty']) < q:
            return {'ResultCode': 1, 'ResultMessage': 'cannot open', 'AccountMoney': money}
        row['Qty'] = int(row['Qty']) - q
        gold, coin, stones = (int(v) * q for v in box[:3])
        money['Gold'] = int(money.get('Gold', 0)) + gold; money['GuildCoin'] = int(money.get('GuildCoin', 0)) + coin
        lst = imprint_stones(player); new = []; shapes = {}
        for _ in range(stones):
            k = random.choice(IMPRINT_STONES); shapes[k] = shapes.get(k, 0) + 1
            new.append({'ImprintStoneNo': max([s['ImprintStoneNo'] for s in lst] + [0]) + 1, 'ImprintStoneIndex': k, 'CreateTime': now_ms(),
                        'Enchant': 0, 'Status': 0, 'VestedCharacterIndex': 0, 'LikeFlag': 0, 'BonusWeight': 0, 'Polishing': 0})
            lst.append(new[-1])
        rewards = [goods(1, 1, gold), goods(2, 30, coin)] + [dict(goods(3 + n, 14, c), ContentsIndex=k) for n, (k, c) in enumerate(shapes.items())]
        got = []
        for it, c in (box[3] if len(box) > 3 else []):
            pay_item(player, int(it), int(c) * q, None, got)
        save(player)
        return {'AccountMoney': money, 'ItemList': [dict(row)], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': got,
                'OpenBoxRewardList': rewards, 'PostSendFlag': False, 'RewardImprintStoneList': new, 'presetCharacterReward': [],
                'presetCharacterCoreReward': []}
    if path in ('/api/imprint/like', '/api/imprint/vestedReset'):
        no = int(payload.get('ImprintStoneNo') or 0)
        st = next((x for x in player.get('ImprintStoneList', []) if int(x['ImprintStoneNo']) == no), None)
        if st is None:
            return {'ResultCode': 1, 'ResultMessage': 'no stone'}
        if path.endswith('like'):   # ImprintLikeRequest {ImprintStoneNo, Like}: lock flag
            st['LikeFlag'] = 1 if payload.get('Like') else 0; save(player)
            return {'ImprintStoneNo': no, 'Like': bool(st['LikeFlag'])}
        # ImprintVestedResetRequest {PriceType, PriceIndex, PriceValue}: unbind the stone from its fighter for the price
        pt, pi, pv = int(payload.get('PriceType') or 0), int(payload.get('PriceIndex') or 0), int(payload.get('PriceValue') or 0)
        remain = {'ItemIndex': 0, 'Qty': 0, 'Lock': False}
        if pt == 13 and pv:
            row = next((i for i in items(player) if i['ItemIndex'] == pi), None)
            if row is None or int(row['Qty']) < pv:
                return {'ResultCode': 1, 'ResultMessage': 'no item', 'AccountMoney': money}
            row['Qty'] = int(row['Qty']) - pv; remain = dict(row)
        elif pv:
            key = PRICE_KEY.get(pt, 'Cash')
            if int(money.get(key, 0)) < pv:
                return {'ResultCode': 1, 'ResultMessage': 'not enough', 'AccountMoney': money}
            money[key] = int(money.get(key, 0)) - pv
        st['VestedCharacterIndex'] = 0; save(player)
        return {'AccountMoney': money, 'ImprintStone': dict(st), 'RemainItem': remain}
    return None


SOUL_PATH = Path(__file__).resolve().parent / 'soul.json'


def soul_cfg():
    return json.loads(SOUL_PATH.read_text()) if SOUL_PATH.exists() else {'stages': {}, 'costs': [], 'daily': 3}


def soul_state(player):
    """player['SoulEvent'] = {Day, Resets{stage: n}}; a soul stage's StageList row PlayCount = today's plays."""
    st = player.setdefault('SoulEvent', {})
    if st.get('Day') != _today():
        st.update({'Day': _today(), 'Resets': {}})
        stages = soul_cfg()['stages']
        for r in player.get('StageList', []):
            if str(r['StageIndex']) in stages:
                r['PlayCount'] = 0
    return st


def soul_row(player, idx):
    rows = player.setdefault('StageList', []); r = next((x for x in rows if x['StageIndex'] == idx), None)
    if r is None:
        r = {'SeriesIndex': stage_meta(idx)[0], 'Chapter': stage_meta(idx)[1], 'StageDifficulty': 1, 'StageIndex': idx, 'BattleResult': 0,
             'PlayCount': 0}
        rows.append(r)
    return r


def soul_entry(player, k):
    """SoulDropEventStage DTO of a soul stage (today's plays and recharges)."""
    c = soul_cfg()['stages'][k]; r = soul_row(player, int(k)); st = soul_state(player)
    return {'SeriesIndex': int(c['series']), 'StageIndex': int(k), 'StagePlayToken': 0, 'Chapter': int(c['chapter']), 'StageDifficulty': 1,
            'Mission1Index': 0, 'Mission2Index': 0, 'Mission3Index': 0, 'PlayCount': int(r['PlayCount']), 'BattleResult': int(r['BattleResult']),
            'TodayDate': now_ms(), 'ResetCount': int(st['Resets'].get(k, 0))}


def soul_route(op, player, payload):
    cfg = soul_cfg(); st = soul_state(player); money = player['AccountMoney']
    if op == 'adventureSoulDropEventStageList':
        out = [soul_entry(player, k) for k in cfg['stages']]
        save(player)
        return {'SoulDropEventStageList': out}
    k = str(int(payload.get('StageIndex') or 0)); n = int(st['Resets'].get(k, 0))
    if k not in cfg['stages'] or n >= len(cfg['costs']) or money['Cash'] < int(cfg['costs'][n]):
        return {'ResultCode': 1, 'ResultMessage': 'cannot recharge', 'AccountMoney': money}
    money['Cash'] -= int(cfg['costs'][n]); st['Resets'][k] = n + 1; soul_row(player, int(k))['PlayCount'] = 0; save(player)
    return {'AccountMoney': money, 'StageIndex': int(k), 'RechargeCount': n + 1, 'PlayCount': 0}


def league_match_user(player, payload):
    """battle/matchUserInfo for a League bot (MatchUserInfoResponse from the PC dump). The bot's fighters are copies of
    the player's own records for the same CharacterIndex (falls back to the first record), battle cards stripped."""
    st = league_state(player); usn = int(payload.get('TargetUsn') or st.get('Target') or 900001)
    # bot ids: League 900001+i, Infinite 910001+i (i = LEAGUE_BOTS index); the team must match the opponent list, or the
    # client maps only the shared fighters and leaves null slots (UIUnit_SingleDuelTurnSelector NRE, seen live)
    n = len(LEAGUE_BOTS); name, chars = LEAGUE_BOTS[((usn - 1) % 10000) % n]
    own = {c['CharacterIndex']: c for c in player['CharacterList']}
    out = []
    for ci in chars:
        c = dict(own.get(ci) or player['CharacterList'][0]); c['CharacterIndex'] = ci
        for k in list(c):
            if k.startswith('BattleCardNo') or k.startswith('ImprintStoneNo'):
                c[k] = 0
        out.append(c)
    deck = {'DeckNo': 1, 'CharacterIndex1': chars[0], 'CharacterIndex2': chars[1], 'CharacterIndex3': chars[2],
            'SupportCharacterIndex1': 0, 'SupportCharacterIndex2': 0, 'SupportCharacterIndex3': 0, 'DeckName': name,
            'TeamRelationIndex': 0, 'GroupGrowthIndex': 0, 'TeamPower': 30000, 'LeaderPower': 10000}
    return {'Request': payload, 'Player': {'NickName': name, 'GuildName': '', 'GuildNo': 0}, 'CharacterList': out,
            # the client looks the bot deck up by the mode's deck number (League = 21); a miss made an empty deck and
            # Controller_Single_DuelLeague.SettingTeams threw out-of-range (seen live) -> same team under every number.
            'TeamDeckList': [dict(deck, DeckNo=n) for n in list(range(1, 41)) + [55, 60, 61, 62, 63]], 'BattleCardList': [], 'PlayerAccount': {'Usn': usn, 'Exp': int(player['PlayerAccount'].get('Exp', 0))},
            'TeamPower': 30000, 'CharacterCoresList': [], 'ListBuff': [], 'TeamRelationList': [], 'ImprintStoneList': [],
            'CharacterAwakenCoreList': [], 'AccountGrowthStatList': [], 'AccountExtraList': [], 'ResultCode': 0, 'ResultMessage': ''}


# ---- Prove Dungeon (/api/proveDungeon/*; DTOs ProveDungeon*Request/Response from the PC dump, plain JSON classes).
#      State in player['Prove'] = {Deck, Support, Bosses, PlayCount}. Local balance.
PROVE_PATH = Path(__file__).resolve().parent / 'prove.json'


def prove_cfg():
    return json.loads(PROVE_PATH.read_text()) if PROVE_PATH.exists() else None


def prove_pick(cfg):
    by_tier = {}
    for b in cfg['bosses']:
        by_tier.setdefault(cfg['tiers'][str(b)], []).append(b)
    # the ready screen has 5 matchup rows (seen live): 2 low-tier, 2 mid, 1 high, all distinct
    out = []
    for t, n in ((1, 2), (2, 2), (3, 1)):
        out += random.sample(by_tier.get(t, []), min(n, len(by_tier.get(t, []))))
    return out


def prove_state(player):
    cfg = prove_cfg() or {}; st = player.setdefault('Prove', {})
    st.setdefault('Deck', []); st.setdefault('Support', []); st.setdefault('PlayCount', 0)
    if len(st.get('Bosses') or []) != 5:
        st['Bosses'] = prove_pick(cfg)
    return st


def prove_route(path, player, payload):
    cfg = prove_cfg()
    if not cfg:
        return {}
    op = path.rsplit('/', 1)[1]; st = prove_state(player)
    with open(Path(__file__).resolve().parent / 'prove_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
    if op == 'info':
        save(player)
        return {'ProveDungeonStageIndex': cfg['stage'], 'RematchProveDungeonStageIndex': cfg['stage'], 'SuraDungeonDifficultyIndex': 0,
                'BossRematchCost': cfg['rematchCost'], 'CharacterIndexList': st['Deck'], 'SupportCharacterIndexList': st['Support'],
                'RandomBossIndexList': st['Bosses'], 'PlayCount': st['PlayCount'], 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('teamDeckUpdate', 'deckUpdate'):   # client path is deckUpdate (seen live)
        st['Deck'] = [int(x) for x in payload.get('CharacterIndexList') or []]
        st['Support'] = [int(x) for x in payload.get('SupportCharacterIndexList') or []]
        save(player)
        return {'CharacterIndexList': st['Deck'], 'SupportCharacterIndexList': st['Support'], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'rematch':
        st['Bosses'] = prove_pick(cfg); save(player)
        return {'AccountMoney': player['AccountMoney'], 'ProveDungeonStageIndex': cfg['stage'], 'RandomBossIndexList': st['Bosses'],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'stageStart':
        return {'PlayToken': now_ms(), 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('stageEnd', 'stageMopUp', 'mopup'):   # client path is stageMopUp (StringLiteral_13419)
        wins = int(payload.get('WinRoundCount') or 0) if op == 'stageEnd' else 3
        money = player['AccountMoney']; gold = int(cfg['gold']) * wins // 3; rewards = []; got = []
        if gold:
            money['Gold'] += gold; rewards.append(goods(1, 1, gold))
        if wins:
            pay_coin(player, 31, 5 * wins, rewards)   # Soul Token -> Soul Exchange (15 per full clear)
            pay_item(player, PROVE_COIN, 5 * wins, rewards, got)   # Prove Coin -> Prove Exchange (15 per full clear; mine)
        st['PlayCount'] += 1
        if wins >= 3:
            st['Bosses'] = prove_pick(cfg)   # cleared: next boss team
        save(player)
        return {'PlayerAccount': player['PlayerAccount'], 'AccountMoney': money, 'PlayCount': st['PlayCount'], 'RewardItemList': got,
                'RewardBattleCardList': [], 'RewardCharacterList': [], 'RewardContentsList': rewards, 'HandicapRewardContentsList': [],
                'RewardImprintStoneList': [], 'PostSendFlag': False, 'GuildBuffList': [], 'presetCharacterReward': [],
                'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    return {}


# ---- Infinite Fight (/api/infiniteFight/*; DTOs InfiniteFight* from the PC dump). Bot targets reuse LEAGUE_BOTS; the
#      opponent's fighters are CharacterSimple9 copies of the player's own records. State in player['Infinite'].
INFINITE_PATH = Path(__file__).resolve().parent / 'infinite.json'


def infinite_cfg():
    return json.loads(INFINITE_PATH.read_text()) if INFINITE_PATH.exists() else None


def infinite_state(player):
    st = player.setdefault('Infinite', {})
    for k, v in (('Rating', 1000), ('Tier', 1), ('Ticket', 10), ('AtkPlay', 0), ('AtkWin', 0), ('Refresh', 0), ('Target', 0)):
        st.setdefault(k, v)
    return st


def infinite_info(cfg, st):
    return {'EventIndex': cfg['event'], 'Tier': int(st['Tier']), 'Rating': int(st['Rating']), 'Rank': 1, 'DailyBestRank': 1,
            'SeasonBestRating': int(st['Rating']), 'AttackPlayCount': int(st['AtkPlay']), 'AttackWinCount': int(st['AtkWin']),
            'DefencePlayCount': 0, 'DefenceWinCount': 0, 'RefreshDate': now_ms(), 'PaymentPlayCount': 0,
            'Ticket': int(st['Ticket']), 'TicketMax': 10}


def simple9(c, ci):
    return {'CharacterIndex': ci, 'Exp': int(c.get('Exp', 0)), 'Grade': int(c.get('Grade', 1)), 'EnchantHp': 0, 'EnchantAtk': 0,
            'EnchantDef': 0, 'LimitBreakGrade': int(c.get('LimitBreakGrade', 0)), 'LimitBreakProgressCount': 0,
            'Awaken': int(c.get('Awaken', 0)), 'AwakenExp': 0, 'ex': 0, 'IsEx': False, 'ImprintStoneNo1': 0, 'ImprintStoneNo2': 0,
            'ImprintStoneNo3': 0, 'ImprintStoneNo4': 0, 'ImprintStoneNo5': 0}


def infinite_targets(player, st):
    own = {c['CharacterIndex']: c for c in player['CharacterList']}; base = player['CharacterList'][0]
    n = len(LEAGUE_BOTS); k = int(st['Refresh']) % n; out = []
    for i in range(3):
        name, chars = LEAGUE_BOTS[(k + i) % n]
        out.append({'UserType': 0, 'TargetUsn': 910001 + (k + i) % n, 'GameDb': 1, 'Tier': int(st['Tier']), 'Rank': 10 + i,
                    'Rating': int(st['Rating']) - 40 + 40 * i, 'NickName': name, 'GuildNo': 0, 'GuildName': '',
                    'CharacterInfoList': [simple9(own.get(ci, base), ci) for ci in chars], 'TeamPower': 30000 + 8000 * i, 'AccountId': ''})
    return out


# ---- All Out Fight (/api/allOutFight/*; DTOs AllOutFight* + AllOutFightWebData.* from the PC dump). allout.json (make_data):
#      event, rule, win gold, daily free plays, grade rating floors. State in player['AllOut']: Rating, play/win counts, Used
#      (fighters that fought: the client locks them, PlayFighterList) cleared by usedCharacterRefresh, Free + FreeDay, Played
#      (opponents beaten/fought this list, MatchTargetInfo.AlreadyPlayed), Refresh. Opponents = 4 LEAGUE_BOTS rotating
#      (battle/matchUserInfo serves their decks by usn 920001+i). Season = local calendar month (local_poll Category 28).
ALLOUT_PATH = Path(__file__).resolve().parent / 'allout.json'


def allout_cfg():
    return json.loads(ALLOUT_PATH.read_text()) if ALLOUT_PATH.exists() else None


def allout_season():
    t = time.localtime()
    return max(1, (t.tm_year - 2026) * 12 + t.tm_mon - 9)   # October 2026 = season 1


def allout_state(player):
    cfg = allout_cfg(); st = player.setdefault('AllOut', {})
    for k, v in (('Rating', 1000), ('Best', 1000), ('AtkPlay', 0), ('AtkWin', 0), ('Used', []), ('Played', []), ('Refresh', 0),
                 ('Target', 0), ('UsedRefresh', 3)):
        st.setdefault(k, v)
    if st.get('FreeDay') != _today():
        st['FreeDay'] = _today(); st['Free'] = int(cfg['free']); st['UsedRefresh'] = 3
    if st.get('Season') != allout_season():   # new season: last season's best grade becomes the Tier Bonus tier
        if st.get('Season') is not None:
            st['PrevGrade'] = allout_grade(cfg, int(st['Best'])); st['Best'] = int(st['Rating'])
        st['Season'] = allout_season()
    return st


def fame_cfg():
    f = Path(__file__).with_name('fame.json')
    return json.loads(f.read_text()) if f.exists() else None


def fame_extras(player):
    """AccountExtraList for the Absolute War Tier Bonus (DBData.User.SetAccountStatData keys mode209Tier / mode209beforeTier =
    AllOutFightGradeIndex). Official: last season's tier; in the first season (no last season yet) the season best counts."""
    cfg = allout_cfg()
    if not cfg:
        return []
    st = allout_state(player)
    tier = int(st.get('PrevGrade') or allout_grade(cfg, int(st['Best'])))
    return [{'Key': 'mode209Tier', 'Value': str(tier)}, {'Key': 'mode209beforeTier', 'Value': str(tier)}]


def fame_stats(player):
    return [{'StatSpot': int(k), 'StatLevel': int(v)} for k, v in sorted(player.get('AccountGrowthStat', {}).items(), key=lambda x: int(x[0]))]


def allout_grade(cfg, rating):
    return max(i for i, floor in enumerate(cfg['grades'], 1) if rating >= floor)


def allout_info(cfg, st):
    g = allout_grade(cfg, int(st['Rating']))
    return {'AllOutFightEventIndex': cfg['event'], 'LastSeason': allout_season(), 'Rating': int(st['Rating']),
            'SeasonBestRating': int(st['Best']), 'SeasonBestGradeIndex': allout_grade(cfg, int(st['Best'])),
            'RemainFreePlayCount': int(st['Free']), 'AttackPlayCount': int(st['AtkPlay']), 'AttackWinCount': int(st['AtkWin']),
            'DefencePlayCount': 0, 'DefenceWinCount': 0, 'PaymentPlayCount': 0, 'SeasonChangeFlag': False, 'GradeChangeFlag': False,
            'RemainCharacterRefreshCount': int(st['UsedRefresh']), 'NextBattleResetTime': 0, 'NextMatchingResetTime': 0,
            'Rank': 1, 'Rate': 100, 'GradeIndex': g}


def allout_targets(player, cfg, st):
    own = {c['CharacterIndex']: c for c in player['CharacterList']}; base = player['CharacterList'][0]
    n = len(LEAGUE_BOTS); k = int(st['Refresh']) % n; out = []
    for i in range(4):
        b = (k + i) % n; name, chars = LEAGUE_BOTS[b]; usn = 920001 + b; r = int(st['Rating']) - 60 + 40 * i
        out.append({'UserType': 0, 'TargetUsn': usn, 'GameDb': 1, 'AccountId': '', 'Rating': r, 'NickName': name, 'GuildNo': 0,
                    'GuildName': '', 'TeamPower': 30000 + 8000 * i, 'CharacterInfoList': [simple9(own.get(ci, base), ci) for ci in chars],
                    'AlreadyPlayed': usn in st['Played'], 'GradeIndex': allout_grade(cfg, max(0, r)), 'Rank': 10 + i})
    return out


def allout_route(path, player, payload):
    cfg = allout_cfg()
    if not cfg:
        return {}
    op = path.rsplit('/', 1)[1]; st = allout_state(player); money = player['AccountMoney']
    with open(Path(__file__).resolve().parent / 'allout_debug.jsonl', 'a') as f:   # first runs: what the client sends
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    ok = {'ResultCode': 0, 'ResultMessage': ''}
    if op == 'lobby':
        t = time.localtime(); start = int(time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, -1))) * 1000
        return dict(ok, AllOutFightSeasonScheduleList=[{'AllOutFightEventIndex': cfg['event'], 'AllOutFightRuleIndex': cfg['rule'],
                    'Season': allout_season(), 'StartTime': start, 'EndTime': league_season()['SeasonEndDate']}],
                    AllOutFightSeasonResultList=[])
    if op == 'info':
        save(player)
        return dict(ok, AllOutFightInfo=allout_info(cfg, st), PlayFighterList=list(st['Used']),
                    MatchTargetList=allout_targets(player, cfg, st), FighterPresetList=[], PresetTeamPower=0,
                    AttackDeckNo=60, DefenceDeckNo=61)
    if op in ('matchingRefresh', 'matchingRefreshFree'):
        st['Refresh'] += 1; st['Played'] = []; save(player)
        return dict(ok, MatchTargetList=allout_targets(player, cfg, st), AccountMoney=money, AllOutFightInfo=allout_info(cfg, st))
    if op == 'presetUpdate':
        return dict(ok, FighterPresetList=[], PresetTeamPower=int(payload.get('PresetTeamPower') or 0))
    if op in ('usedCharacterRefresh', 'battleCoolTimeRefresh'):
        if op == 'usedCharacterRefresh':
            st['Used'] = []; st['UsedRefresh'] = max(0, int(st['UsedRefresh']) - 1)
            money['Gold'] = max(0, int(money['Gold']) - 1)   # the reset popup shows 1 gold (ConfigTable AllOutFightUsedCharacterRefreshGoods)
        save(player)
        return dict(ok, AccountMoney=money, AllOutFightInfo=allout_info(cfg, st))
    if op == 'start':
        st['Free'] = max(0, int(st['Free']) - 1); st['Target'] = int(payload.get('TargetUsn') or 0)
        st['TargetPower'] = next((t['TeamPower'] for t in allout_targets(player, cfg, st) if t['TargetUsn'] == st['Target']), 0); save(player)
        return dict(ok, PlayToken=now_ms(), AccountMoney=money, RemainItem={'ItemIndex': 0, 'Qty': 0, 'Lock': False})
    if op == 'end':
        # score rows of the duel result page (InfiniteFightAddScore): win 15 / loss -10, clear time (<=60 s +3, <=120 s +1),
        # remaining HP (CharacterHp1-3 are percents: up to +5), beating a stronger team +2 (my values)
        won = int(payload.get('BattleResult') or 0) == 1; rewards = []
        hp = sum(int(payload.get('CharacterHp%d' % i) or 0) for i in (1, 2, 3)); ct = int(payload.get('ClearTime') or 0)
        sc = {'PlayResultScore': 15 if won else -10, 'TimeScore': (3 if ct <= 60 else 1 if ct <= 120 else 0) if won else 0,
              'RemainScore': round(hp / 300 * 5) if won else 0,
              'TeamCpScore': 2 if won and int(st.get('TargetPower') or 0) > int(payload.get('TeamPower') or 0) else 0}
        d = sum(sc.values()); sc['TotalScore'] = d
        st['AtkPlay'] += 1; st['Rating'] = max(0, int(st['Rating']) + d); st['Best'] = max(int(st['Best']), int(st['Rating']))
        # the fighters that fought (the client sends them in CharacterInfoList; CharacterList came empty, seen live)
        used = [int(c.get('CharacterIndex') or 0) for c in payload.get('CharacterInfoList') or []] + \
               [int(c) for c in payload.get('CharacterList') or []]
        used = [c for c in used if c]
        st['Used'] = sorted(set(st['Used']) | set(used))
        if st['Target'] and st['Target'] not in st['Played']:
            st['Played'].append(st['Target'])
        medals = []
        if won:
            st['AtkWin'] += 1; money['Gold'] += int(cfg['gold']); rewards.append(goods(1, 1, int(cfg['gold'])))
            fc = fame_cfg()
            if fc:   # official: Bronze/Silver/Gold medals by rank on a win (make_data FAME_WIN, by gradeTier)
                tier = (allout_grade(cfg, int(st['Rating'])) - 1) // 5 + 1
                inv = {i['ItemIndex']: i for i in items(player)}
                for ix, q in fc['win'].get(str(tier), []):
                    if ix not in inv:
                        inv[ix] = {'ItemIndex': ix, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[ix])
                    inv[ix]['Qty'] += q; medals.append(inv[ix])
                    rewards.append(dict(goods(len(rewards) + 1, 13, q), ContentsIndex=ix, ContentsType=1, ContentsCount=q))
        pay_coin(player, 6, 20 if won else 5, rewards)   # Arena Coin -> Arena Exchange
        save(player)
        return dict(ok, AllOutFightInfo=allout_info(cfg, st), PlayRewardList=rewards, AccountMoney=money, RewardCharacterList=[],
                    RewardBattleCardList=[], RewardImprintStoneList=[], RewardItemList=medals, PostSendFlag=False, GlobalDropRewardList=[],
                    presetCharacterReward=[], presetCharacterCoreReward=[],
                    AddScore=sc)
    if op == 'rankingList':
        me = {'Usn': int(player['Route'].get('Usn') or 0), 'NickName': player['Route'].get('NickName', ''),
              'GuildName': '', 'AttackPlayCount': int(st['AtkPlay']), 'AttackWinCount': int(st['AtkWin']), 'DefencePlayCount': 0,
              'DefenceWinCount': 0, 'GradeIndex': allout_grade(cfg, int(st['Rating'])), 'Rating': int(st['Rating']), 'Rank': 1}
        return dict(ok, AllOutFightInfo=allout_info(cfg, st), AllOutFightRankingInfoList=[me])
    if op == 'history':
        return dict(ok, AllOutFightInfo=allout_info(cfg, st), AllOutFightHistoryList=[])
    if op == 'seasonChangeInfo':
        return dict(ok, AccountExtraList=fame_extras(player))
    return {}


def infinite_route(path, player, payload):
    cfg = infinite_cfg()
    if not cfg:
        return {}
    op = path.rsplit('/', 1)[1]; st = infinite_state(player)
    with open(Path(__file__).resolve().parent / 'infinite_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if op == 'lobby':
        return {'ServerUtcTime': now_ms(), 'InfiniteFightScheduleInfoList': [{'ModeId': cfg['mode'], 'SeasonStartTime': cfg['seasonStart'],
                'SeasonEndTime': league_season()['SeasonEndDate'], 'InfiniteFightRuleIndex': cfg['rule']}], 'InfiniteFightSeasonEndInfoList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'info':
        if int(st['Ticket']) < 10:
            st['Ticket'] = 10
        save(player)
        return {'ServerUtcTime': now_ms(), 'PlayFighterList': [], 'InfiniteFightInfo': infinite_info(cfg, st),
                'MatchTargetList': infinite_targets(player, st), 'DailyRewardFlag': False, 'InitSeasonFlag': False, 'TierUpFlag': False,
                'FighterPresetList': [], 'AttackDeckNo': 1, 'DefenceDeckNo': 1, 'PresetTeamPower': 0, 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'matchingRefresh':
        st['Refresh'] += 1; save(player)
        return {'MatchTargetList': infinite_targets(player, st), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'presetUpdate':
        return {'FighterPresetList': [], 'PresetTeamPower': int(payload.get('PresetTeamPower') or 0), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'start':
        st['Ticket'] = max(0, int(st['Ticket']) - 1); st['Target'] = int(payload.get('TargetUsn') or 0); save(player)
        return {'InfiniteFightPlayToken': now_ms(), 'AccountMoney': player['AccountMoney'],
                'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'end':
        won = int(payload.get('BattleResult') or 0) == 1; money = player['AccountMoney']; rewards = []; d = 20 if won else -10
        st['AtkPlay'] += 1; st['Rating'] = max(0, int(st['Rating']) + d)
        if won:
            st['AtkWin'] += 1; money['Gold'] += int(cfg['gold']); rewards.append(goods(1, 1, int(cfg['gold'])))
        # its own coin only: ParseInfiniteFightEnd removes every GoodsType 6 (Arena Coin) row from the result (original design),
        # so the Arena Coins paid here until 2026-10-24 were never shown (user: stop them)
        got = []; pay_item(player, INFINITE_COIN, 20 if won else 5, rewards, got)   # -> Infinite Fight Exchange (amounts mine)
        save(player)
        return {'AccountMoney': money, 'InfiniteFightInfo': infinite_info(cfg, st), 'PlayRewardList': rewards, 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'RewardItemList': got, 'PostSendFlag': False,
                'AddScore': {'PlayResultScore': d, 'TimeScore': 0, 'RemainScore': 0, 'TeamCpScore': 0, 'TotalScore': d},
                'GlobalDropRewardList': [], 'RewardImprintStoneList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'rankingList':
        return {'ServerUtcTime': now_ms(), 'SeasonEndTime': league_season()['SeasonEndDate'], 'InfiniteFightInfo': infinite_info(cfg, st),
                'InfiniteFightRankingInfoList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'history':
        return {'HistoryNo': 0, 'InfiniteFightInfo': infinite_info(cfg, st), 'InfiniteFightHistoryInfoList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'dailyReward':
        return {'AccountMoney': player['AccountMoney'], 'InfiniteFightInfo': infinite_info(cfg, st), 'PlayRewardList': [],
                'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [], 'PostSendFlag': False,
                'RewardImprintStoneList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    return {}


# ---- Shop (/api/shop/shopGoodsQtyList, /api/shop/shopGoodsBuy; DTOs ShopGoodsQtyListResponse, ShopGoodsBuyRequest/
#      Response, Shop from the PC dump). shop.json from make_data.py: goodsIndex -> item, count, priceType (GoodsType
#      1 Gold / 2 Cash), price. Bought counts kept in player['ShopBuy'].
SHOP_PATH = Path(__file__).resolve().parent / 'shop.json'
# GoodsType of a price -> AccountMoney field (client NetworkManagerWEB.TakeAccountMoney / DBData.Acount.GetCurrency)
PRICE_KEY = {1: 'Gold', 2: 'Cash', 6: 'ColosseumCoin', 26: 'Topaz', 30: 'GuildCoin', 31: 'SoulToken', 33: 'SoulDust', 35: 'ArenaLeagueCoin'}


def pay_coin(player, goods_type, n, rewards, no=2):
    """Add n of a coin currency (GoodsType 6 / 31 / 35) to AccountMoney and to a RewardContents list."""
    money = player['AccountMoney']; key = PRICE_KEY[goods_type]
    money[key] = int(money.get(key, 0)) + n
    if rewards is not None:
        rewards.append(goods(no, goods_type, n))


INFINITE_COIN, PROVE_COIN, CHAMP_COIN = 8049, 8058, 8048   # the original mode exchange tokens (make_data EXCHANGE_TOKENS / EXCHANGES 9906-9908)


def pay_item(player, idx, n, rewards, got, no=3):
    """Add n of an item to the inventory, to 'got' (a RewardItemList: the Infinite Fight / Prove end parsers ADD its rows,
    InnerAddCount / TakeAndAddItemList) and to a RewardContents list for the result screen."""
    inv = items(player); row = next((i for i in inv if i['ItemIndex'] == idx), None)
    if row is None:
        row = {'ItemIndex': idx, 'Qty': 0, 'Lock': False}; inv.append(row)
    n = max(0, min(n, QTY_MAX - int(row['Qty']))); row['Qty'] = int(row['Qty']) + n
    got.append({'ItemIndex': idx, 'Qty': n, 'Lock': False})
    if rewards is not None:
        rewards.append(dict(goods(no, 13, n), ContentsIndex=idx))


def shop_cfg():
    return json.loads(SHOP_PATH.read_text()) if SHOP_PATH.exists() else {}


def shop_refresh_key(cfg, payload):
    want = (int(payload.get('ShopType') or 0), int(payload.get('ShopSubType') or 0))
    return next((k for k, c in (cfg.get('refresh') or {}).items() if (int(c['type']), int(c['sub'])) == want), None)


def shop_refresh_state(player, cfg, payload):
    """player['ShopRefresh'][manage] = refreshes used today {Day, Free, Manual} (reset at local midnight with the daily restock)."""
    key = shop_refresh_key(cfg, payload)
    if not key:
        return {'Free': 0, 'Manual': 0}
    r = player.setdefault('ShopRefresh', {}).setdefault(key, {})
    if r.get('Day') != _today():
        r.update({'Day': _today(), 'Free': 0, 'Manual': 0})
    return r


def shop_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; bought = player.setdefault('ShopBuy', {})
    cfg = shop_cfg()
    if player.get('ShopBuyDay') != _today():   # daily goods (Secret Shop, make_data 'daily') restock at local midnight
        player['ShopBuyDay'] = _today()
        for k in [k for k in bought if cfg.get(k, {}).get('daily')]:
            del bought[k]
        save(player)
    with open(Path(__file__).resolve().parent / 'shop_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if op == 'shopGoodsQtyList':
        pv = cfg.get('private') or {}   # ShopGoodsTable.SetTableData lists ONLY these when non-empty -> just for that shop
        priv = list(pv.get('goods') or []) if (int(payload.get('ShopType') or 0), int(payload.get('ShopSubType') or 0)) ==             (int(pv.get('type', -1)), int(pv.get('sub', -1))) else []
        rf = shop_refresh_state(player, cfg, payload)
        return {'ServerUtcTime': now_ms(), 'ShopRefreshInfo': {'ManualRefreshCount': rf['Manual'], 'RefreshCount': rf['Manual'] + rf['Free'],
                'RefreshTime': 0, 'FreeRefreshCount': rf['Free'],
                'nextRefreshTime': int(time.mktime(time.strptime(_today(), '%Y-%m-%d'))) * 1000 + 86400000},
                'ShopGoodsQtyList': [{'GoodsIndex': int(k), 'BuyType': 0, 'BuyCount': int(v), 'UpdateTime': now_ms()} for k, v in bought.items()],
                'ShopGiveConditionList': [], 'ShopSellConditionList': [], 'ShopSmartPackageList': [], 'AdsViewCountList': [],
                'PrivateShopGoodsIndexList': priv, 'PrivateShopPackageIndexList': [],   # priv: only for the private shop's own request
                'shopEventProgressList': [], 'shopTotalBuyList': [],
                'tierList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'shopGoodsRefresh':   # Secret Shop refresh: restock that shop's goods (free first, then PriceValue rubies)
        key = shop_refresh_key(cfg, payload); rf = shop_refresh_state(player, cfg, payload); money = player['AccountMoney']
        conf = (cfg.get('refresh') or {}).get(key or '')
        if not conf:
            return {'ResultCode': 1, 'ResultMessage': 'no refresh', 'AccountMoney': money}
        price = int(payload.get('PriceValue') or 0)
        if rf['Free'] < int(conf['free']):
            rf['Free'] += 1
        elif rf['Manual'] < int(conf['max']) and money['Cash'] >= price:
            rf['Manual'] += 1; money['Cash'] -= price
        else:
            return {'ResultCode': 1, 'ResultMessage': 'no refresh left', 'AccountMoney': money}
        for k in [k for k, g in cfg.items() if k.isdigit() and (int(g.get('type', -1)), int(g.get('group', -1))) == (int(conf['type']), int(conf['sub']))]:
            bought.pop(k, None)
        save(player)
        return {'ServerUtcTime': now_ms(), 'AccountMoney': money}
    if op == 'shopGoodsBuy':
        gi = int(payload.get('GoodsIndex') or 0); n = req_count(payload, 'BuyCount'); g = cfg.get(str(gi))   # 0 / negative were forced to 1
        bt = int(payload.get('BuyType') or 0)
        money = player['AccountMoney']
        if not g or n is None:
            return {'ResultCode': 1, 'ResultMessage': 'unknown goods' if not g else 'bad count', 'AccountMoney': money}
        key = PRICE_KEY.get(int(g['priceType']), 'Cash'); cost = int(g['price']) * n
        if g.get('limit') and int(bought.get(str(gi), 0)) + n > int(g['limit']):
            return {'ResultCode': 1, 'ResultMessage': 'sold out', 'AccountMoney': money}
        price_row = None
        if int(g['priceType']) == 13:   # item-priced goods (shopPriceIndex): spend the item, RemainItem = its new total
            price_row = next((i for i in items(player) if i['ItemIndex'] == int(g['priceItem'])), None)
            if not price_row or int(price_row['Qty']) < cost:
                return {'ResultCode': 1, 'ResultMessage': 'not enough items', 'AccountMoney': money}
            price_row['Qty'] = int(price_row['Qty']) - cost
        elif int(money.get(key, 0)) < cost:
            return {'ResultCode': 1, 'ResultMessage': 'not enough ' + key, 'AccountMoney': money}
        else:
            money[key] = int(money.get(key, 0)) - cost
        if int(g.get('give', 13)) == 14:   # GoodsType.ImprintStone -> new stones in RewardImprintStoneList
            lst = imprint_stones(player); new = []
            for _ in range(int(g['count']) * n):
                new.append({'ImprintStoneNo': max([x['ImprintStoneNo'] for x in lst] + [0]) + 1, 'ImprintStoneIndex': int(g['item']),
                            'CreateTime': now_ms(), 'Enchant': 0, 'Status': 0, 'VestedCharacterIndex': 0, 'LikeFlag': 0,
                            'BonusWeight': 0, 'Polishing': 0})
                lst.append(new[-1])
            bought[str(gi)] = int(bought.get(str(gi), 0)) + n
            save(player)
            return {'ShopGoodsQty': {'GoodsIndex': gi, 'BuyType': bt, 'BuyCount': bought[str(gi)], 'UpdateTime': now_ms()},
                    'AccountMoney': money, 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [],
                    'RewardPostList': [], 'PostSendFlag': False, 'AdsList': [], 'RewardImprintStoneList': new,
                    'CompletedShopEventGroupIndexList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                    'ResultCode': 0, 'ResultMessage': ''}
        inv = {i['ItemIndex']: i for i in items(player)}
        if g.get('randomSoul'):   # Soul Dust Exchange pack (guide: souls "received randomly"): N souls of a random fighter
            roster = json.loads(ROSTER_PATH.read_text()) if ROSTER_PATH.exists() else [101]
            got = {}
            for _ in range(n):
                k = SOUL_BASE + random.choice(roster); got[k] = got.get(k, 0) + int(g['randomSoul'])
            for k, q in got.items():
                if k not in inv:
                    inv[k] = {'ItemIndex': k, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[k])
                inv[k]['Qty'] += q
            bought[str(gi)] = int(bought.get(str(gi), 0)) + n
            save(player)
            last = dict(price_row) if price_row else inv[list(got)[-1]]   # RemainItem = the spent price item's new total (Soul Dust)
            return {'ShopGoodsQty': {'GoodsIndex': gi, 'BuyType': bt, 'BuyCount': bought[str(gi)], 'UpdateTime': now_ms()},
                    'AccountMoney': money, 'RewardCharacterList': [], 'RewardBattleCardList': [],
                    'RewardItemList': [{'ItemIndex': k, 'Qty': q, 'Lock': False} for k, q in got.items()],
                    'RewardPostList': [], 'RemainItem': last, 'PostSendFlag': False, 'AdsList': [], 'RewardImprintStoneList': [],
                    'CompletedShopEventGroupIndexList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                    'ResultCode': 0, 'ResultMessage': ''}
        row = inv.get(int(g['item']))
        if row is None:
            row = {'ItemIndex': int(g['item']), 'Qty': 0, 'Lock': False}; player['ItemList'].append(row)
        row['Qty'] += int(g['count']) * n
        bought[str(gi)] = int(bought.get(str(gi), 0)) + n
        save(player)
        return {'ShopGoodsQty': {'GoodsIndex': gi, 'BuyType': bt, 'BuyCount': bought[str(gi)], 'UpdateTime': now_ms()},
                'AccountMoney': money, 'RewardCharacterList': [], 'RewardBattleCardList': [],
                'RewardItemList': [{'ItemIndex': row['ItemIndex'], 'Qty': int(g['count']) * n, 'Lock': False}],   # added
                'RewardPostList': [], 'RemainItem': price_row or row, 'PostSendFlag': False, 'AdsList': [],   # set (new total)
                'RewardImprintStoneList': [], 'CompletedShopEventGroupIndexList': [], 'presetCharacterReward': [],
                'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    return {}


# ---- Guild (solo, local). guild/create (GuildCreateRequest {CreateGoodsType/Value, GuildName, JoinType, Open,
#      JoinLevelLimit, DonationLimit}) -> GuildInfo + MemberInfo + AccountMoney; SceneLobby_GuildIntro.RecvGuildCreate then
#      opens the guild lobby (scene 0x67), which asks guild/guildInfo. AccountProfileResponse.GuildDetailInfo tells the lobby
#      the player is in a guild. DTOs from the PC dump; the player is the only member (GuildMemberType 203 Master).
GUILD_PATH = Path(__file__).resolve().parent / 'guild.json'


def guild_cfg():
    return json.loads(GUILD_PATH.read_text()) if GUILD_PATH.exists() else {'levels': [0], 'createType': 1, 'createCost': 0}


def guild_donated_today(g):
    return int(g.get('DonationToday', 0)) if g.get('DonationDay') == _today() else 0


def guild_level(exp):
    lv = 1
    for n, need in enumerate(guild_cfg()['levels'], 1):
        if exp >= need: lv = n
    return lv


def guild_info(player):
    g = player['Guild']; name = player['Route'].get('NickName', '')
    return {'GuildNo': g['GuildNo'], 'GuildName': g['GuildName'], 'MasterUsn': player['PlayerAccount']['Usn'], 'MasterNickName': name,
            'JoinType': g.get('JoinType', 0), 'JoinLevelLimit': g.get('JoinLevelLimit', 1), 'MemberCount': 1 + len(guild_mates(player)), 'MaxMemberCount': 30,
            'GuildExp': g.get('Exp', 0), 'GuildJoinReceiveCount': 0, 'BoardCount': 0, 'HistoryCount': 0, 'OpenFlag': bool(g.get('Open', True)),
            # DonationLimit = gold a member may donate per day (UIPopup_GuildDonationGoods 'Today Remain'); the create request
            # carried the old config default 999, so the server's cap (guild.json donationLimit) is reported instead
            'BestLevel': guild_level(g.get('Exp', 0)), 'DonationLimit': int(guild_cfg().get('donationLimit', 0)),
            'DonationAmount': guild_donated_today(g),
            'OperationAmount': g.get('Donation', 0) - g.get('FundSpent', 0)}


def guild_member(player):
    g = player['Guild']; pc = player['ProfileCharacter']; ch = character(player, int(pc.get('CharacterIndex') or 101)) or {}
    return {'GuildNo': g['GuildNo'], 'Usn': player['PlayerAccount']['Usn'], 'GameDb': player['Route'].get('GameDb', 1),
            'NickName': player['Route'].get('NickName', ''), 'AccountLevel': int(player.get('LastAccountLevel', 1)),
            'CharacterIndex': int(pc.get('CharacterIndex') or 101), 'Grade': int(ch.get('Grade', 3)), 'Exp': int(ch.get('Exp', 0)),
            'LastLoginTime': now_ms(), 'LeaderPower': 0, 'LimitBreakGrade': int(ch.get('LimitBreakGrade', 0)),
            'LimitBreakProgressCount': int(ch.get('LimitBreakProgressCount', 0)), 'JoinStatus': 1, 'GuildMemberLevel': 203,
            'DemandExpireTime': 0, 'RegTime': g.get('Created', 0), 'AccountId': player['Route'].get('AccountId', ''),
            'Pid': player['Route'].get('Pid', ''), 'MsgGuildChat': 0, 'DonationAmount': guild_donated_today(g), 'DonationDate': 0,
            'Donation': g.get('Donation', 0) + g.get('ItemContribution', 0), 'Greet': False}


def guild_buffs(player):
    """Active guild buffs as GuildBuffInfo [{GuildBuffIndex, ExpireTime}] (expired ones dropped)."""
    g = player.get('Guild') or {}; t = now_ms()
    return [{'GuildBuffIndex': int(k), 'ExpireTime': v} for k, v in sorted((g.get('Buffs') or {}).items()) if v > t]


def guild_detail(player):
    """AccountProfileResponse.GuildDetailInfo (GuildDetailInfo2); GuildNo 0 = no guild."""
    g = player.get('Guild')
    if not g:
        return {'GuildNo': 0, 'GuildName': '', 'PenaltyExpireTime': 0, 'GuildJoinRequestCount': 0, 'GuildBuffList': [], 'MasterUsn': 0}
    return {'GuildNo': g['GuildNo'], 'GuildName': g['GuildName'], 'PenaltyExpireTime': 0, 'GuildJoinRequestCount': 0,
            'GuildBuffList': guild_buffs(player), 'MasterUsn': player['PlayerAccount']['Usn']}


GRAID_PATH = Path(__file__).resolve().parent / 'guildraid.json'


def graid_cfg():
    return json.loads(GRAID_PATH.read_text()) if GRAID_PATH.exists() else {'groups': {}, 'brackets': [], 'clear': 0, 'tickets': 0}


GRAID_SEASON0 = 2961   # local week index before the first local raid season (graid_season()[0] - this = displayed season)


def graid_season():
    """(season number, start ms, end ms): one guild raid season per local week (Monday 00:00)."""
    import local_poll
    w = local_poll.week_start()
    return w // (7 * 86400), w * 1000, (w + 7 * 86400) * 1000


def graid_seasons():
    n, st, en = graid_season()
    return [{'bossGroup': int(g), 'season': n, 'seasonStartDate': st, 'seasonEndDate': en} for g in sorted(graid_cfg()['groups'], key=int)]


def graid_find(cfg, bi):
    """(group key, difficulty dict) of a GuildBossDifficultyTable index (unique across the raid bosses)."""
    for grp, gr in cfg['groups'].items():
        if str(bi) in gr.get('difficulties', {}):
            return grp, gr['difficulties'][str(bi)]
    return None, None


def graid_box(cfg, grp, total):
    """(box number, box item index) for a season's cumulative damage on one difficulty: the highest box whose damage minimum is
    reached (make_data GRAID_BOXSETS -> guildraid.json groups[g].boxes = [[minDamage, itemIndex], ...]); (0, 0) below box I."""
    n, ix = 0, 0
    for k, (lo, item) in enumerate((cfg['groups'].get(str(grp)) or {}).get('boxes', []), 1):
        if total >= lo:
            n, ix = k, item
    return n, ix


ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']


def graid_calculate(player, cfg, st):
    """Season calculation (the original 'Guild Raid calculation complete!' screen): for every difficulty with damage this season,
    the Raid Box of its cumulative damage, x2 when the boss was defeated (cumulative >= HP), mailed ('Rewards will be sent to your
    Mailbox'); the results wait in st['SeasonResults'] for the lobby's SeasonResultList (GuildSeasonResult per boss group)."""
    res = {}
    for bi, total in sorted(st.get('Total', {}).items(), key=lambda kv: int(kv[0])):
        grp, d = graid_find(cfg, bi)
        if not d or int(total) <= 0:
            continue
        clear = int(total) >= float(d.get('hp') or 0) > 0
        n, ix = graid_box(cfg, grp, int(total)); qty = (2 if clear else 1) * int(d.get('boxQty') or 1); rewards = []   # Ultra: boxQty 5
        if ix:
            msg = 'Guild Raid %s (%s), season %d: Raid Box %s%s' % (cfg['groups'][grp].get('name', 'boss'), d.get('name', ''),
                                                                  int(st['Season']), ROMAN[n - 1], ' x2 (boss defeated)' if clear else '')
            post_add(player, 13, ix, qty, msg)
            rewards.append(dict(goods(1, 13, qty), ContentsIndex=ix, ContentsType=1))
        res.setdefault(grp, []).append({'bossIndex': int(bi), 'score': int(total), 'clear': 1 if clear else 0, 'rewardList': rewards})
    st['SeasonResults'] = st.get('SeasonResults', []) + [{'season': int(st['Season']), 'bossGroup': int(g), 'bossList': bl}
                                                          for g, bl in res.items()]


def graid_state(player):
    """player['Guild']['Raid']: tickets (refill to max each local day), best score and cumulative damage ('Total', the shared boss
    HP, the ranking and the season's Raid Box: the original lobby says 'Cumulative DMG') per difficulty, cleared difficulties, and
    the calculated results of the last season still to be shown ('SeasonResults')."""
    g = player['Guild']; st = g.setdefault('Raid', {}); cfg = graid_cfg()
    if st.get('Day') != _today():
        st['Day'] = _today(); st['Tickets'] = int(cfg.get('tickets', 0))
    n = graid_season()[0]
    if st.get('Season') != n:   # weekly season: calculate the old one, then best scores and damage reset, clears stay
        if st.get('Season') is not None:
            graid_calculate(player, cfg, st)
        st['Season'] = n; st['Best'] = {}; st['Total'] = {}; st['Attacks'] = {}; st['BotRef'] = {}
    st.setdefault('Best', {}); st.setdefault('Cleared', []); st.setdefault('Total', dict(st['Best'])); st.setdefault('Attacks', {})
    st.pop('Tier', None); st.pop('Paid', None)   # the per-fight Box tiers of the first reward version (2026-10-24)
    return st


# Bot guildmates and bot guilds for the raid / co-op rankings: the local guild has one real member, so these local stand-ins fill
# the lists. Names, decks and numbers are mine. Each bot's numbers are seeded by season and boss (the same list on every reopen)
# and scaled around the player's own score. Display only: they never touch boss HP, steps or rewards.
GUILD_MATES = LEAGUE_BOTS + [('Leona Main', (162, 173, 101)), ('Orochi Hunter', (121, 118, 104)), ('Crimson Moon', (101, 123, 103))]
BOT_GUILDS = [('Southtown Wolves', 'Wolfpack'), ('Esaka Fighters', 'Esaka Kid'), ('Kyokugen Dojo', 'Tiger Fist'),
              ('Pao Pao Cafe', 'Cafe Regular'), ('Ikari Squad', 'Sergeant'), ('Orochi Seekers', 'Seal Keeper'),
              ('Hero Team', 'Fire Fist'), ('Art of Fighting', 'Dragon Kick'), ('Fatal Fury', 'Burn Knuckle')]


def bot_deck(player, chars, r):
    return {'DeckNo': 1, 'CharacterIndex1': chars[0], 'CharacterIndex2': chars[1], 'CharacterIndex3': chars[2],
            'SupportCharacterIndex1': 0, 'SupportCharacterIndex2': 0, 'SupportCharacterIndex3': 0, 'DeckName': '',
            'TeamRelationIndex': 0, 'GroupGrowthIndex': 0, 'LeaderPower': 0,
            'TeamPower': int(int(player['TeamDeckList'][0].get('TeamPower') or 30000) * r.uniform(0.5, 1.1))}


def deck_fighters(player, deck):
    """CharacterSimple9 of every fighter in a deck (UIPopup_GuildDungeonRankingDetail looks the cards up in fighterList by index);
    a fighter the player doesn't own copies the first owned record."""
    own = {c['CharacterIndex']: c for c in player['CharacterList']}; base = player['CharacterList'][0]
    keys = ('CharacterIndex1', 'CharacterIndex2', 'CharacterIndex3', 'SupportCharacterIndex1', 'SupportCharacterIndex2', 'SupportCharacterIndex3')
    return [simple9(own.get(int(deck[k]), base), int(deck[k])) for k in keys if int(deck.get(k) or 0)]


def bot_guilds(season, key, mine, ref):
    """Bot guilds around the player's guild score 'mine' (or 'ref' while it is 0) -> [(no, name, master, level, members, score)]."""
    out = []
    for i, (name, master) in enumerate(BOT_GUILDS):
        r = random.Random('%s:%d:%s' % (key, season, i))
        out.append((901 + i, name, master, r.randint(4, 10), r.randint(18, 30), int((mine or ref) * r.uniform(0.4, 1.6))))
    return out


def guild_mates(player):
    """The bot guildmates still in the guild -> [(index, usn, name, chars)]; kicked ones are in Guild['Kicked'] (guild/expulsion)."""
    kicked = set((player.get('Guild') or {}).get('Kicked', []))
    return [(i, 930001 + i, name, chars) for i, (name, chars) in enumerate(GUILD_MATES) if 930001 + i not in kicked]


GUILD_GREET_COIN = 10   # Guild Coins per greeting (mine); greetings a day = GuildTable.greetNumber (make_data: 5)
GUILD_GREETS, GUILD_SUBMASTERS = 5, 2   # GuildTable greetNumber / subMasterLimit (make_data)


def guild_greets(player):
    """Today's greetings [usn, ...] (Guild['Greet'] = {Day, Usns})."""
    gr = player['Guild'].setdefault('Greet', {})
    if gr.get('Day') != _today():
        gr['Day'] = _today(); gr['Usns'] = []
    return gr['Usns']


def guild_bot_member(player, i, usn, name, chars):
    """MemberInfo of a bot guildmate (same fields as guild_member); level / login offset / donation seeded per bot."""
    g = player['Guild']; r = random.Random('mate:%d' % i)
    return {'GuildNo': g['GuildNo'], 'Usn': usn, 'GameDb': 1, 'NickName': name, 'AccountLevel': r.randint(20, 60),
            'CharacterIndex': chars[0], 'Grade': 5, 'Exp': 0, 'LastLoginTime': now_ms() - r.randint(1, 30) * 3600000,
            'LeaderPower': 0, 'LimitBreakGrade': 0, 'LimitBreakProgressCount': 0, 'JoinStatus': 1,
            'GuildMemberLevel': int((g.get('MateLevels') or {}).get(str(usn), 201)), 'DemandExpireTime': 0,
            'RegTime': g.get('Created', 0), 'AccountId': 'localbot%d' % usn, 'Pid': '', 'MsgGuildChat': 0, 'DonationAmount': 0,
            'DonationDate': 0, 'Donation': r.randint(1, 50) * 1000, 'Greet': usn in guild_greets(player)}


def guild_members(player):
    return [guild_member(player)] + [guild_bot_member(player, *m) for m in guild_mates(player)]


def graid_mates(player, st, bi, hp):
    """Bot guildmates on raid difficulty bi this season -> [(usn, name, deck, best, total, attacks)]: best fight 0.3-1.15 x a
    reference, season damage = 1-3 such fights a day of the season so far (numbers mine). The reference is the player's best
    when first seen this season (st['BotRef'], kept for the season; 2% of the boss HP before the player's first fight), so the
    bots stay on the player's scale but no longer follow the player: until 2026-10-25 their best followed the player's best and
    their season damage the player's season damage, a bot seeded above the player stayed ahead whatever the player did and the
    rank never moved. A fixed share of the boss HP alone put them at 2.7B on a 1.7B boss (live 2026-10-25)."""
    n, s0, s1 = graid_season(); days = max(1, (now_ms() - s0) // 86400000 + 1)
    best0 = int(st['Best'].get(bi, 0)); refs = st.setdefault('BotRef', {})
    if best0 and bi not in refs:
        refs[bi] = best0
    ref = int(refs.get(bi) or hp * 0.02) or 100000; out = []
    for i, usn, name, chars in guild_mates(player):
        r = random.Random('graid:%d:%s:%d' % (n, bi, i)); deck = bot_deck(player, chars, r); best = int(ref * r.uniform(0.3, 1.15))
        total = best * (days + r.randint(0, 2 * days)) * 4 // 5
        out.append((usn, name, deck, best, total, max(1, round(total / (best * 0.8)))))
    return out


def graid_rank(player, st, bi, hp):
    """The player's place in the guild ranking of difficulty bi (the 'ranking' list: season damage, highest first, the player
    before bots on a tie). GuildDungeonPlayEnd/PlayMopup ResultRank: UIPopup_GuildDungeonMopupResult.OpenRankingChangePopup
    shows 'Ranking up!' when it differs from the cached list's rank, moving the player to ResultRank (always 1 before)."""
    mine = int(st['Total'].get(bi, 0))
    return 1 + sum(1 for m in graid_mates(player, st, bi, hp) if m[4] > mine)


def graid_info(st):
    nxt = int(time.mktime(time.strptime(_today(), '%Y-%m-%d'))) * 1000 + 86400000
    return {'ticket': int(st['Tickets']), 'paymentPlayCount': 0, 'ticketRefreshTime': nxt - 86400000, 'nextTicketRefreshTime': nxt}


def graid_route(path, player, payload):
    """guildDungeon/* (GuildDungeonLobby/PlayStart/PlayEnd/Ranking DTOs from the PC dump). BossIndex = GuildBossDifficultyTable
    index; score = damage. Rewards by damage bracket (guildraid.json = the GuildBossRewardTable rows make_data writes)."""
    op = path.rsplit('/', 1)[1]; money = player['AccountMoney']
    with open(Path(__file__).resolve().parent / 'guild_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if not player.get('Guild'):
        return {'ResultCode': 1, 'ResultMessage': 'no guild'}
    cfg = graid_cfg(); st = graid_state(player); n, s0, s1 = graid_season()
    grp = str(int(payload.get('BossGroup') or st.get('Group') or 1))
    diffs = (cfg['groups'].get(grp) or {}).get('difficulties', {})
    scores = [{'bossIndex': int(k), 'score': int(st['Total'].get(k, 0)), 'myScore': int(st['Total'].get(k, 0))} for k in sorted(diffs, key=int)]
    if op == 'lobby':
        st['Group'] = int(grp)
        # last season's calculation for this boss, shown once (Controller_GuildDungeonLobby.OpenSeasonResult)
        shown = [r for r in st.get('SeasonResults', []) if str(r['bossGroup']) == grp]
        st['SeasonResults'] = [r for r in st.get('SeasonResults', []) if str(r['bossGroup']) != grp]; save(player)
        # Model_GuildDungeonLobby.UpdateDifficultyState: unlocked = IsClearBoss(unlockDifficulty) (a list lookup), and the first
        # difficulty's unlockDifficulty is 0 -> 0 is always 'cleared' (without it every difficulty stayed locked, seen live)
        return {'ClearBossIndexList': [0] + [int(x) for x in st['Cleared']], 'DungeonScoreList': scores, 'DungeonInfo': graid_info(st),
                'SeasonInfo': {'bossGroup': int(grp), 'season': n, 'seasonStartDate': s0, 'seasonEndDate': s1}, 'SeasonResultList': shown,
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'playStart':
        bi = str(int(payload.get('BossIndex') or 0)); grp = str(int(payload.get('BossGroup') or grp))
        # an unreadable start (server.py passes {}; seen 2026-10-25 on the first BATTLE START after a team change, the retry
        # was fine) used to get 'unknown boss' -> the boss the player has open (the ranking request just before names it)
        if bi == '0' and (st.get('View') or {}).get('Boss'):
            bi, grp = str(st['View']['Boss']), str(st['View']['Group'])
            with open(Path(__file__).resolve().parent / 'guild_debug.jsonl', 'a') as f:
                f.write(json.dumps({'raid_start_fallback': {'boss': bi, 'group': grp}}) + chr(10))
        if bi not in (cfg['groups'].get(grp) or {}).get('difficulties', {}) or st['Tickets'] < 1:
            return {'ResultCode': 1, 'ResultMessage': 'no ticket' if st['Tickets'] < 1 else 'unknown boss'}
        st['Tickets'] -= 1; st['Play'] = {'Token': now_ms(), 'Group': grp, 'Boss': bi}; save(player)
        return {'PlayToken': st['Play']['Token'], 'DungeonInfo': graid_info(st),
                'DungeonScore': {'bossIndex': int(bi), 'score': int(st['Best'].get(bi, 0)), 'myScore': int(st['Best'].get(bi, 0))},
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'playEnd':
        play = st.get('Play') or {}; bi = play.get('Boss', '0'); grp = play.get('Group', grp)
        d = (cfg['groups'].get(grp) or {}).get('difficulties', {}).get(bi)
        score = max(0, int(payload.get('Score') or 0))
        if not d:
            return {'ResultCode': 1, 'ResultMessage': 'no play', 'AccountMoney': money}
        renew = score > int(st['Best'].get(bi, 0))
        if renew:
            st['Best'][bi] = score
        st['Total'][bi] = int(st['Total'].get(bi, 0)) + score   # shared boss HP = cumulative damage = the season's Raid Box
        st['Attacks'][bi] = int(st['Attacks'].get(bi, 0)) + 1   # fights + sweeps this season (the ranking's attack count)
        if score >= int(cfg['clear']) * int(d['difficulty']) and int(bi) not in st['Cleared']:
            st['Cleared'].append(int(bi))
        # farmable (user 2026-10-24: "every time I reach this damage I get the item, I can farm it as much as I want"): the Raid
        # Box of this fight's damage is mailed at once, x2 when this difficulty's boss is defeated; the season calculation stays
        n, ix = graid_box(cfg, grp, score)
        if ix:
            dead = int(st['Total'][bi]) >= float(d.get('hp') or 0) > 0
            post_add(player, 13, ix, (2 if dead else 1) * int(d.get('boxQty') or 1), 'Guild Raid %s (%s): %s damage - Raid Box %s%s' % (
                cfg['groups'][grp].get('name', 'boss'), d.get('name', ''), '{:,}'.format(score), ROMAN[n - 1], ' x2 (boss defeated)' if dead else ''))
        st.pop('Play', None); save(player)
        with open(Path(__file__).resolve().parent / 'guild_debug.jsonl', 'a') as f:
            f.write(json.dumps({'raid_end': {'boss': bi, 'score': score, 'total': st['Total'][bi], 'box': n}}) + chr(10))
        return {'AccountMoney': money, 'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'DungeonInfo': graid_info(st),
                'DungeonScore': {'bossIndex': int(bi), 'score': int(st['Total'].get(bi, 0)), 'myScore': score},
                'BestScoreRenew': renew, 'ResultRank': graid_rank(player, st, bi, float(d.get('hp') or 0)), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'playMopup':   # GuildDungeonPlayMopupRequest {BossGroup, BossIndex, MopupCount}: each key repeats the best fight
        # Skip Ticket (guildraid.json skipItem = config 90005 GuildDungeonMopupItem, make_data GRAID_SKIP_TICKET): one per skip;
        # RemainItemList = its new total (ParseGuildDungeonMopup -> TakeAndSetItemList).
        bi = str(int(payload.get('BossIndex') or 0)); grp = str(int(payload.get('BossGroup') or grp)); cnt = max(1, int(payload.get('MopupCount') or 1))
        d = (cfg['groups'].get(grp) or {}).get('difficulties', {}).get(bi); best = int(st['Best'].get(bi, 0))
        skip = int(cfg.get('skipItem') or 0); srow = next((i for i in items(player) if i['ItemIndex'] == skip), None) if skip else None
        have = int(srow['Qty']) if srow is not None else 0
        if skip and have < cnt:   # the client's slider only counts raid entries; its error popup shows this message
            return {'ResultCode': 1, 'ResultMessage': 'Not enough Skip Tickets: you have %d, this sweep needs %d.' % (have, cnt),
                    'AccountMoney': money}
        if not d or not best or int(st['Tickets']) < cnt:
            return {'ResultCode': 1, 'ResultMessage': 'cannot sweep', 'AccountMoney': money}
        st['Tickets'] = int(st['Tickets']) - cnt
        if srow is not None:
            srow['Qty'] = int(srow['Qty']) - cnt
        st['Total'][bi] = int(st['Total'].get(bi, 0)) + best * cnt   # cumulative damage (the Raid Box at season end)
        st['Attacks'][bi] = int(st['Attacks'].get(bi, 0)) + cnt
        n, ix = graid_box(cfg, grp, best)   # and one Raid Box per key at the best fight's tier, x2 when the boss is defeated
        if ix:
            dead = int(st['Total'][bi]) >= float(d.get('hp') or 0) > 0
            post_add(player, 13, ix, cnt * (2 if dead else 1) * int(d.get('boxQty') or 1), 'Guild Raid %s (%s): sweep x%d - Raid Box %s%s' % (
                cfg['groups'][grp].get('name', 'boss'), d.get('name', ''), cnt, ROMAN[n - 1], ' x2 (boss defeated)' if dead else ''))
        save(player)
        return {'AccountMoney': money, 'DungeonInfo': graid_info(st),
                'DungeonScore': {'bossIndex': int(bi), 'score': int(st['Total'][bi]), 'myScore': best},
                'ResultRank': graid_rank(player, st, bi, float(d.get('hp') or 0)),
                'RemainItemList': [dict(srow)] if srow is not None else [], 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('ranking', 'guildRanking'):
        bi = str(int(payload.get('BossIndex') or 0)); me = player['PlayerAccount']['Usn']; best = int(st['Best'].get(bi, 0))
        if op == 'ranking' and bi in diffs and st.get('View') != {'Group': grp, 'Boss': bi}:   # the difficulty on screen (playStart)
            st['View'] = {'Group': grp, 'Boss': bi}; save(player)
        total = int(st['Total'].get(bi, 0)); hp = float((graid_find(cfg, bi)[1] or {}).get('hp') or 0)
        mates = graid_mates(player, st, bi, hp); deck = player['TeamDeckList'][0]; nick = player['Route'].get('NickName', '')
        if op == 'guildRanking':   # GuildRanking {guildNo, guildName, masterName, ranking, score}: guild score = all members' damage
            g = player['Guild']; mine = total + sum(m[4] for m in mates)
            rows = [(g['GuildNo'], g['GuildName'], nick, mine)]
            rows += [(no, name, master, sc) for no, name, master, lv, cnt, sc in bot_guilds(n, 'graid:' + bi, mine, hp * 2)]
            rows.sort(key=lambda x: -x[3])
            # the popup's 'Season {0}' = GuildSeasonInfo.season (graid_seasons: n) - the selected ranking season, which starts at
            # maxSeason (UIPopup_GuildDungeonGuildRanking.RecvGuildDungeonGuildRanking + UIPage_GuildDungeonSeasonList; n / n showed
            # 'Season 0'): one ranking season GRAID_SEASON0 -> 'Season 1' = the week of 2026-10-12, when the local server started
            return {'minSeason': GRAID_SEASON0, 'maxSeason': GRAID_SEASON0, 'rankingList': [{'guildNo': no, 'guildName': name, 'masterName': master,
                    'ranking': k, 'score': sc} for k, (no, name, master, sc) in enumerate(rows, 1)], 'ResultCode': 0, 'ResultMessage': ''}
        # attack count: tracked since 2026-10-24; estimated from damage for the season that was already running
        att = int(st['Attacks'].get(bi, 0)) or (round(total / best) if best else 0)
        rows = [(me, nick, deck, best, total, att)] if best else []
        rows += [m for m in mates if m[5]]; rows.sort(key=lambda x: -x[4])
        return {'nameList': [{'usn': me, 'nickName': nick}] + [{'usn': m[0], 'nickName': m[1]} for m in mates],
                'playList': [{'usn': u, 'clearCount': 1 if (int(bi) in st['Cleared'] if u == me else 0 < hp <= tot) else 0,
                              'score': tot, 'bestScore': b, 'teamDeck': dk, 'fighterList': deck_fighters(player, dk),
                              'rankingTime': now_ms(), 'attackCount': att} for u, name, dk, b, tot, att in rows],
                'ResultCode': 0, 'ResultMessage': ''}
    return {'ResultCode': 0, 'ResultMessage': ''}


GCOOP_PATH = Path(__file__).resolve().parent / 'gcoop.json'


def gcoop_cfg():
    """gcoop.json; with 'groups' the boss in use is 'active' (one at a time: the client enters GuildCoopSeasonList[0]) ->
    its group and steps replace the top-level ones (Omega Rugal)."""
    if not GCOOP_PATH.exists():
        return None
    cfg = json.loads(GCOOP_PATH.read_text()); act = str(cfg.get('active', cfg.get('group')))
    if cfg.get('rotation'):   # weekly boss rotation like the original seasons: week rotationWeek0 = rotation[0]
        rot = cfg['rotation']; act = str(rot[(graid_season()[0] - int(cfg.get('rotationWeek0', 0))) % len(rot)])
    if act in (cfg.get('groups') or {}):
        cfg = dict(cfg, group=int(act), steps=cfg['groups'][act]['steps'])
    return cfg


def gcoop_seasons():
    """guild/guildInfo GuildCoopSeasonList: one weekly season (same week as the raid); bossGroup = GuildCoopTable index."""
    cfg = gcoop_cfg()
    if not cfg:
        return []
    n, s0, s1 = graid_season()
    return [{'bossGroup': int(cfg['group']), 'season': n, 'seasonStartDate': s0, 'seasonEndDate': s1}]


def gcoop_state(player):
    """player['Guild']['Coop']: plays used today, current step + damage on it, attack count, cleared steps (weekly season)."""
    st = player['Guild'].setdefault('Coop', {})
    if st.get('Day') != _today():
        st.update({'Day': _today(), 'Used': 0, 'Recharge': 0})
    n = graid_season()[0]; g = int((gcoop_cfg() or {}).get('group', 1))
    if st.get('Season') != n:   # new week: every boss starts over
        st.update({'Season': n, 'Step': 1, 'Score': 0, 'Attacks': 0, 'Steps': []}); st.pop('ByGroup', None)
    if int(st.get('Group', 1)) != g:   # another boss switched in: park this boss's steps, take the other's (or start fresh)
        by = st.setdefault('ByGroup', {})
        by[str(st.get('Group', 1))] = {k: st[k] for k in ('Step', 'Score', 'Attacks', 'Steps') if k in st}
        st.update(by.pop(str(g), {'Step': 1, 'Score': 0, 'Attacks': 0, 'Steps': []})); st['Group'] = g
    return st


def gcoop_route(path, player, payload):
    """guildCoop/* (GuildCoop* DTOs, PC dump). The local guild has one member, so the guild's step damage is the player's: a step
    clears when its damage reaches the step HP (= the lobby boss HP make_data sets), the next step opens, the last repeats."""
    op = path.rsplit('/', 1)[1]; money = player['AccountMoney']; cfg = gcoop_cfg()
    if not player.get('Guild') or not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no guild co-op'}
    st = gcoop_state(player); n, s0, s1 = graid_season(); steps = cfg['steps']
    score = lambda: {'step': int(st['Step']), 'score': int(st['Score']), 'attackCount': int(st['Attacks'])}
    info = lambda: {'useTicketCount': int(st['Used']), 'rechargeCount': int(st['Recharge'])}
    me = player['PlayerAccount']['Usn']; nick = player['Route'].get('NickName', '')
    if op == 'lobby':
        save(player)
        return {'DungeonScore': score(), 'DungeonInfo': info(), 'SeasonInfo': {'bossGroup': int(cfg['group']), 'season': n,
                'seasonStartDate': s0, 'seasonEndDate': s1}, 'SeasonResultList': [], 'StepClearRewardList': []}
    if op == 'playStart':
        if int(st['Used']) >= int(cfg['plays']):
            return {'ResultCode': 1, 'ResultMessage': 'no play left'}
        st['Used'] = int(st['Used']) + 1; st['Play'] = now_ms(); save(player)
        return {'PlayToken': st['Play'], 'DungeonScore': score()}
    if op == 'playEnd':
        dmg = max(0, int(payload.get('Score') or 0)); step = int(st['Step'])
        hp = int(steps[min(step, len(steps)) - 1]['hp'])
        st['Attacks'] = int(st['Attacks']) + 1; st['Score'] = int(st['Score']) + dmg
        gold, coin = int(cfg['gold']), int(cfg['coin'])
        if st['Score'] >= hp - max(10, hp // 100000):   # float32 balance rate: the client's HP can be a few points under the table value
            st['Steps'].append({'step': step, 'score': int(st['Score']), 'attackCount': int(st['Attacks']), 'clear': True,
                                'clearUsn': me, 'clearUserName': nick})
            coin += int(cfg['clearCoin'])
            if step < len(steps):
                st['Step'] = step + 1
            st['Score'] = 0; st['Attacks'] = 0
        money['Gold'] = int(money.get('Gold', 0)) + gold; money['GuildCoin'] = int(money.get('GuildCoin', 0)) + coin
        best = dmg > int(st.get('Best', 0)); st['Best'] = max(int(st.get('Best', 0)), dmg); st.pop('Play', None); save(player)
        nxt = int(time.mktime(time.strptime(_today(), '%Y-%m-%d'))) * 1000 + 86400000
        return {'AccountMoney': money, 'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False},
                'DungeonInfo': {'ticket': max(0, int(cfg['plays']) - int(st['Used'])), 'paymentPlayCount': 0,
                                'ticketRefreshTime': nxt - 86400000, 'nextTicketRefreshTime': nxt},
                'DungeonScore': {'bossIndex': step, 'score': int(st['Score']), 'myScore': dmg}, 'BestScoreRenew': best,
                'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [], 'RewardImprintStoneList': [],
                'presetCharacterList': [], 'presetCharacterCoreList': [], 'FirstClearRewardList': []}
    if op == 'recharge':
        st['Used'] = 0; st['Recharge'] = int(st['Recharge']) + 1; save(player)
        return {'AccountMoney': money, 'DungeonInfo': info()}
    if op == 'memberRanking':   # + the bot guildmates (best fight around the player's; step clears stay the player's)
        best = int(st.get('Best', 0)); deck = player['TeamDeckList'][0]; days = max(1, (now_ms() - s0) // 86400000 + 1)
        ref = best or int(steps[0]['hp']) // 20 or 100000
        rows = [(me, nick, deck, best, len(st['Steps']), int(st['Attacks']))] if best else []
        for i, usn, name, chars in guild_mates(player):
            r = random.Random('gcoop:%d:%d' % (n, i))
            att = sum(random.Random('gcoop:%d:%d:%d' % (n, i, d)).randint(1 if d == 0 else 0, 3) for d in range(days))
            rows.append((usn, name, bot_deck(player, chars, r), int(ref * r.uniform(0.3, 1.15)), 0, att))
        rows.sort(key=lambda x: -x[3])
        return {'NameList': [{'usn': me, 'nickName': nick}] + [{'usn': u, 'nickName': nm} for i, u, nm, c in guild_mates(player)],
                'PlayList': [{'usn': u, 'clearCount': cl, 'score': b, 'bestScore': b, 'teamDeck': dk, 'fighterList': deck_fighters(player, dk),
                              'rankingTime': now_ms(), 'attackCount': att} for u, name, dk, b, cl, att in rows]}
    if op == 'guildRanking':   # the player's guild (step damage) among the bot guilds
        g = player['Guild']; mine = sum(int(x['score']) for x in st['Steps']) + int(st['Score'])
        rows = [(g['GuildNo'], g['GuildName'], nick, guild_level(g.get('Exp', 0)), 1 + len(guild_mates(player)), mine)]
        rows += bot_guilds(n, 'gcoop', mine, int(steps[0]['hp'])); rows.sort(key=lambda x: -x[5])
        return {'Season': n, 'RankingList': [{'guildNo': no, 'guildName': name, 'masterName': master, 'ranking': k, 'guildLv': lv,
                'memberCount': cnt, 'score': sc} for k, (no, name, master, lv, cnt, sc) in enumerate(rows, 1)]}
    if op == 'seasonResultHistory':
        return {'StepList': list(st['Steps']) + [{'step': int(st['Step']), 'score': int(st['Score']), 'attackCount': int(st['Attacks']),
                'clear': False, 'clearUsn': 0, 'clearUserName': ''}]}
    return {}


def guild_items_today(g):
    d = g.get('ItemDonation') or {}
    return int(d.get('Count', 0)) if d.get('Day') == _today() else 0


GUILD_BOARD_SEED = [   # bot guildmate posts seeded on first view (mine): (GUILD_MATES index, hours ago, message)
    (8, 50, 'Welcome to the guild! Greet each other every day.'),
    (3, 30, 'Donated gold today. Let us get the ATK buff running for the raid.'),
    (4, 12, 'Who wants to clear Guild Co-op together tonight?'),
    (7, 3, 'Raid boss down! Thanks for the help, everyone.'),
]


def guild_board(player):
    """Guild['Board'] = {Seq, Posts, Liked}; the bot posts are added once."""
    g = player['Guild']; bd = g.get('Board')
    if bd is None:
        bd = g['Board'] = {'Seq': 0, 'Posts': [], 'Liked': []}
        for i, hours, msg in GUILD_BOARD_SEED:
            name, chars = GUILD_MATES[i]; bd['Seq'] += 1
            bd['Posts'].append({'Usn': 930001 + i, 'NickName': name, 'CharacterIndex': chars[0], 'BoardNo': bd['Seq'], 'Message': msg,
                                'LikeCount': (i * 7) % 5, 'RegTime': now_ms() - hours * 3600000})
    return bd


def guild_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; money = player['AccountMoney']
    if (payload.get('commonParam') or {}).get('accountLevel'):
        player['LastAccountLevel'] = int(payload['commonParam']['accountLevel'])
    with open(Path(__file__).resolve().parent / 'guild_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if op == 'create':
        cfg = guild_cfg(); key = PRICE_KEY.get(int(cfg['createType']), 'Gold'); cost = int(cfg['createCost'])
        name = str(payload.get('GuildName') or '').strip()[:16]
        if player.get('Guild') or not name or int(money.get(key, 0)) < cost:
            return {'ResultCode': 1, 'ResultMessage': 'cannot create guild', 'AccountMoney': money}
        money[key] = int(money.get(key, 0)) - cost
        player['Guild'] = {'GuildNo': 1, 'GuildName': name, 'JoinType': int(payload.get('JoinType') or 0),
                           'Open': bool(payload.get('Open', True)), 'JoinLevelLimit': int(payload.get('JoinLevelLimit') or 1),
                           'DonationLimit': int(payload.get('DonationLimit') or 0), 'Exp': 0, 'Donation': 0, 'Created': now_ms()}
        save(player)
        return {'GuildInfo': guild_info(player), 'MemberInfo': guild_members(player), 'AccountMoney': money,
                'ResultCode': 0, 'ResultMessage': ''}
    if not player.get('Guild'):
        return {'ResultCode': 0, 'ResultMessage': ''}
    g = player['Guild']
    if op == 'guildInfo':
        return {'GuildInfo': guild_info(player), 'MemberInfo': guild_members(player), 'GuildRoomNo': '', 'Message': g.get('Notice', ''),
                'GuildBuffList': guild_buffs(player), 'GuildRankInfo': {'RankingSeason': {}, 'RankList': []},
                'MyGuildInfo': {'DonationAmount': guild_donated_today(g), 'Donation': g.get('Donation', 0), 'GreetCount': 0,
                                'LevelUpEffect': False,
                                # AttendanceReward = today's attendance still claimable (SceneLobby_GuildLobbyMain msg 0x2fe)
                                'AttendanceReward': g.get('AttendDay') != _today(), 'RankingRewardDisplayList': [],
                                'MasterAuthorization': '',
                                'GuildExp': g.get('Exp', 0), 'DonationItem': guild_items_today(g), 'GuildName': g['GuildName'], 'GuildNo': g['GuildNo'],
                                'NoticeUpdateTime': 0},
                'AttendanceInfo': {'TodayAttendanceMemberCount': 0, 'AttendanceMemberCount': 0}, 'RedDotList': [],
                'GuildDungeonSeasonList': graid_seasons(), 'GuildCoopSeasonList': gcoop_seasons(), 'ResultCode': 0, 'ResultMessage': ''}
    cfg = guild_cfg()
    def level_info(before):
        return {'GuildExp': g.get('Exp', 0), 'LevelUpDown': guild_level(g.get('Exp', 0)) - before, 'RankPoint': 0}
    if op == 'attendanceReward':
        # GuildAttendanceRewardResponse {AttendanceRewardList [{AttendanceType 1 Daily, RewardType GoodsType, RewardValue}],
        # GuildLevelInfo}; the client shows the reward popup from it, the wallet syncs from the next AccountMoney reply
        if g.get('AttendDay') == _today():
            return {'ResultCode': 1, 'ResultMessage': 'already attended'}
        before = guild_level(g.get('Exp', 0)); coin = int(cfg.get('attendanceCoin', 0))
        g['AttendDay'] = _today(); g['Exp'] = g.get('Exp', 0) + int(cfg.get('attendanceExp', 0))
        money['GuildCoin'] = int(money.get('GuildCoin', 0)) + coin
        save(player)
        return {'AttendanceRewardList': [{'AttendanceType': 1, 'RewardType': 30, 'RewardValue': coin}],
                'GuildLevelInfo': level_info(before), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'buffList':
        return {'GuildBuffList': guild_buffs(player), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'buffOn':
        # GuildBuffOnRequest {GuildBuffIndex}; reply OperationAmount (fund left) + GuildBuffInfo. Fund = gold donated - spent.
        bi = str(int(payload.get('GuildBuffIndex') or 0)); b = (cfg.get('buffs') or {}).get(bi)
        fund = g.get('Donation', 0) - g.get('FundSpent', 0)
        if not b or fund < int(b['cost']):
            return {'ResultCode': 1, 'ResultMessage': 'not enough guild funds'}
        g['FundSpent'] = g.get('FundSpent', 0) + int(b['cost'])
        g.setdefault('Buffs', {})[bi] = now_ms() + int(b['minutes']) * 60000
        save(player)
        return {'OperationAmount': fund - int(b['cost']), 'GuildBuffInfo': {'GuildBuffIndex': int(bi), 'ExpireTime': g['Buffs'][bi]},
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'donationGoods':
        # GuildDonationGoodsRequest {DonationAmount = gold}; reply AccountMoney, MyGuildInfo (MemberInfo2), GuildLevelInfo.
        # Guild EXP += gold, Guild Coins += gold x coinPerGold; daily cap donationLimit.
        amt = int(payload.get('DonationAmount') or 0)
        if g.get('DonationDay') != _today():
            g['DonationDay'] = _today(); g['DonationToday'] = 0
        fund = g.get('Donation', 0) - g.get('FundSpent', 0)
        if amt <= 0 or money['Gold'] < amt or g['DonationToday'] + amt > int(cfg.get('donationLimit', 0)) \
                or fund + amt > int(cfg.get('fundCap', 10 ** 12)):   # GuildHaveCashLimitValue (config 20206)
            return {'ResultCode': 1, 'ResultMessage': 'cannot donate', 'AccountMoney': money}
        before = guild_level(g.get('Exp', 0))
        money['Gold'] -= amt; g['DonationToday'] += amt; g['Donation'] = g.get('Donation', 0) + amt
        g['Exp'] = g.get('Exp', 0) + amt
        money['GuildCoin'] = int(money.get('GuildCoin', 0)) + int(amt * float(cfg.get('coinPerGold', 0)))
        save(player)
        return {'AccountMoney': money, 'MyGuildInfo': {'Donation': g['Donation'], 'DonationAmount': g['DonationToday'],
                'OperationAmount': g['Donation'] - g.get('FundSpent', 0), 'DonationItem': guild_items_today(g)}, 'GuildLevelInfo': level_info(before),
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'donationItem':
        # GuildDonationItemRequest {DonationItemList: [DonationItem {ItemIndex, ItemCnt}]} -> GuildDonationItemResponse
        # {DonationItemList: the items' REMAINING counts (Parse_GuildDonationItem InnerSets them), GuildLevelInfo}. Guild EXP +=
        # donationExp, Guild Coins += getContributeValue per item (guild.json itemDonation, make_data GUILD_DONATE_ITEMS); at most
        # itemDonationDaily items a day (config GuildLimitValueDonateItem). All-or-nothing.
        table = cfg.get('itemDonation') or {}; want = {}
        for e in payload.get('DonationItemList') or []:
            ix, n = int(e.get('ItemIndex') or 0), int(e.get('ItemCnt') or 0)
            if n > 0: want[ix] = want.get(ix, 0) + n
        inv = {i['ItemIndex']: i for i in items(player)}
        if not want or any(str(ix) not in table or int(inv.get(ix, {}).get('Qty', 0)) < n for ix, n in want.items()) \
                or guild_items_today(g) + sum(want.values()) > int(cfg.get('itemDonationDaily', 0)):
            return {'ResultCode': 1, 'ResultMessage': 'cannot donate these items'}
        before = guild_level(g.get('Exp', 0)); exp = coin = 0
        for ix, n in want.items():
            inv[ix]['Qty'] = int(inv[ix]['Qty']) - n; exp += table[str(ix)][0] * n; coin += table[str(ix)][1] * n
        g['Exp'] = g.get('Exp', 0) + exp; g['ItemContribution'] = g.get('ItemContribution', 0) + coin
        money['GuildCoin'] = int(money.get('GuildCoin', 0)) + coin
        g['ItemDonation'] = {'Day': _today(), 'Count': guild_items_today(g) + sum(want.values())}; save(player)
        return {'DonationItemList': [{'ItemIndex': ix, 'ItemCnt': int(inv[ix]['Qty'])} for ix in want], 'GuildLevelInfo': level_info(before),
                'AccountMoney': money, 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('boardList', 'boardCreate', 'boardDelete', 'boardLike'):
        # GuildBoardRequest {BoardNo[], NoticeType, NickName, CharacterIndex, Message} / GuildBoardLikeRequest {BoardNo[], LikeFlag}
        # -> GuildBoardResponse {GuildBoardInfo: [{Usn, NickName, CharacterIndex, BoardNo, Message, LikeCount, RegTime}],
        # GuildBoardLikeInfo: [{BoardNo}] (posts the player liked)}. Posts in Guild['Board']; a few bot guildmate posts are seeded.
        bd = guild_board(player); me = player['PlayerAccount']['Usn']; nos = [int(x) for x in payload.get('BoardNo') or []]
        if op == 'boardCreate':
            msg = str(payload.get('Message') or '').strip()[:200]
            if not msg:
                return {'ResultCode': 1, 'ResultMessage': 'empty post'}
            bd['Seq'] += 1
            bd['Posts'].append({'Usn': me, 'NickName': player['Route'].get('NickName', ''), 'BoardNo': bd['Seq'], 'Message': msg,
                                'CharacterIndex': int(payload.get('CharacterIndex') or player['ProfileCharacter'].get('CharacterIndex') or 101),
                                'LikeCount': 0, 'RegTime': now_ms()})
            bd['Posts'] = bd['Posts'][-50:]   # GuildTable postBoardDisplayLimit 50
        elif op == 'boardDelete':   # the player is the master: any post may be deleted
            bd['Posts'] = [x for x in bd['Posts'] if x['BoardNo'] not in nos]; bd['Liked'] = [n for n in bd['Liked'] if n not in nos]
        elif op == 'boardLike':
            like = int(payload.get('LikeFlag') or 0) == 1
            for x in bd['Posts']:
                if x['BoardNo'] in nos and like != (x['BoardNo'] in bd['Liked']):
                    x['LikeCount'] = max(0, int(x['LikeCount']) + (1 if like else -1))
                    if like: bd['Liked'].append(x['BoardNo'])
                    else: bd['Liked'].remove(x['BoardNo'])
        if op != 'boardList':
            save(player)
        return {'GuildBoardInfo': sorted(bd['Posts'], key=lambda x: -x['RegTime']),
                'GuildBoardLikeInfo': [{'BoardNo': n} for n in bd['Liked']], 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('noticeList', 'notice'):
        # GuildBoardRequest {NoticeType (1 Guild, 2 Chatting, 3 Board, 4 Introduce), Message} -> GuildNoticeResponse {GuildNoticeInfo:
        # [{GuildNo, NoticeType, Message, RegTime, UpdateTime}]}: every stored notice (Parse_GuildNoticeList filters by type)
        nt = g.setdefault('Notices', {})
        if g.get('Notice') and '1' not in nt:   # the guild-lobby notice stored before notices existed
            nt['1'] = {'Message': g['Notice'], 'RegTime': now_ms(), 'UpdateTime': now_ms()}
        if op == 'notice':
            t = str(int(payload.get('NoticeType') or 1)); msg = str(payload.get('Message') or '').strip()[:200]
            old = nt.get(t) or {'RegTime': now_ms()}
            nt[t] = {'Message': msg, 'RegTime': old['RegTime'], 'UpdateTime': now_ms()}
            if t == '1':
                g['Notice'] = msg
            save(player)
        return {'GuildNoticeInfo': [{'GuildNo': g['GuildNo'], 'NoticeType': int(t), 'Message': v['Message'], 'RegTime': v['RegTime'],
                                     'UpdateTime': v['UpdateTime']} for t, v in sorted(nt.items()) if v.get('Message')],
                'ResultCode': 0, 'ResultMessage': ''}
    if op in ('close', 'withdrawal'):
        # disband / leave (the only member): the guild is deleted; no join penalty (GuildDetailInfo PenaltyExpireTime 0)
        player.pop('Guild', None); save(player)
        return {'GuildDetailInfo': {'GuildNo': 0, 'PenaltyExpireTime': 0, 'GuildJoinRequestCount': 0},
                'GuildLevelInfo': {'GuildExp': 0, 'LevelUpDown': 0, 'RankPoint': 0}, 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('memberList', 'joinList'):   # both parse GuildListResponse {List: [MemberInfo]} (joinList = pending applicants)
        return {'List': guild_members(player) if op == 'memberList' else [], 'GuildAllOutFightTierList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    # bot guildmates (GUILD_MATES): UIUnit_GuildMember greet / rank / kick send these with TargetUsn; replies per the PC dump
    mates = {u: (i, u, nm, c) for i, u, nm, c in guild_mates(player)}
    tgt = int(payload.get('TargetUsn') or 0)
    if op == 'greetList':   # GuildGreetListResponse {GreetInfoList: [GreetInfo {TargetUsn, RegTime, IsGreet}]}
        return {'GreetInfoList': [{'TargetUsn': u, 'RegTime': now_ms(), 'IsGreet': 1} for u in guild_greets(player)],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'greeting':    # GuildGreetingRequest {TargetUsn} -> GuildGreetingResponse {AccountMoney, GreetInfoList, GuildLevelInfo}
        done = guild_greets(player)
        if tgt not in mates or tgt in done or len(done) >= GUILD_GREETS:
            return {'ResultCode': 1, 'ResultMessage': 'cannot greet', 'AccountMoney': money}
        before = guild_level(g.get('Exp', 0)); done.append(tgt)
        money['GuildCoin'] = int(money.get('GuildCoin', 0)) + GUILD_GREET_COIN; save(player)
        return {'AccountMoney': money, 'GreetInfoList': [{'TargetUsn': u, 'RegTime': now_ms(), 'IsGreet': 1} for u in done],
                'GuildLevelInfo': level_info(before), 'ResultCode': 0, 'ResultMessage': ''}
    if op in ('expulsion', 'change'):   # both parse GuildListResponse {List} (Parse_GuildExpulsion / Parse_GuildChange)
        if tgt not in mates:
            return {'ResultCode': 1, 'ResultMessage': 'not a guildmate'}
        if op == 'expulsion':
            g.setdefault('Kicked', []).append(tgt); g.get('MateLevels', {}).pop(str(tgt), None)
        else:   # GuildChangeRequest {TargetUsn, TargetGuildMemberLevel}: 201 Member / 202 Sub Master; 203 (hand over master) refused
            lv = int(payload.get('TargetGuildMemberLevel') or 0); levels = g.setdefault('MateLevels', {})
            subs = sum(1 for k, v in levels.items() if int(v) == 202 and int(k) != tgt)
            if lv not in (201, 202) or (lv == 202 and subs >= GUILD_SUBMASTERS):
                return {'ResultCode': 1, 'ResultMessage': 'cannot change'}
            levels[str(tgt)] = lv
        save(player)
        return {'List': guild_members(player), 'GuildAllOutFightTierList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'masterAuth':   # take over an inactive master: the player is always the master here
        return {'ResultCode': 1, 'ResultMessage': 'you are the guild master'}
    return {'ResultCode': 0, 'ResultMessage': ''}


# ---- Post Box (post/postList, post/postRead; DTOs PostListResponse, Post, PostNoInfo, PostReadRequest/Response from the PC
#      dump). PostCategory 0 All, 1 Fighter, 2 BattleCard, 3 Item, 4 ETC. Mail text = PostTypeTable 1001 '{0}' + Post.Message
#      (make_data). Local mail: a one-time welcome gift and one supply mail per local day, 7 days to claim. Amounts are mine.
MAIL_WELCOME = [(2, 0, 300, 'Welcome to KOF ALLSTAR (local server)! A starter gift.'),
                (1, 0, 50000, 'Welcome gift: Gold.'), (13, 1002, 5, 'Welcome gift: EXP Capsules.'),
                (13, 4302, 3, 'Welcome gift: Enchant Kits.')]
MAIL_DAILY = [(1, 0, 10000, 'Daily supply: Gold.'), (13, 1001, 5, 'Daily supply: EXP Capsules.'),
              (13, 4304, 3, 'Daily supply: Polishing Cores.')]
MAIL_DAYS = 7


def post_category(goods_type):
    return {11: 1, 12: 2, 13: 3}.get(int(goods_type), 4)


def post_add(player, gt, idx, cnt, msg):
    posts = player.setdefault('Posts', []); t = now_ms()
    player['PostSeq'] = int(player.get('PostSeq', 0)) + 1
    posts.append({'PostNo': player['PostSeq'], 'PostType': 1001, 'PostCategory': post_category(gt), 'GoodsType': gt,
                  'ContentsIndex': idx, 'ContentsGrade': 0, 'ContentsCount': cnt, 'ContentsLevel': 0, 'ContentsType': 0,
                  'ContentsValue': '', 'SenderUsn': 0, 'SenderGameDb': 0, 'Message': msg, 'ReadTime': 0,
                  'CreateTime': t, 'ExpireTime': t + MAIL_DAYS * 86400000})


def post_reward(player, rw, msg):
    """Mail a make_data reward dict ({gold, ruby, items}) instead of paying it."""
    if rw.get('gold'): post_add(player, 1, 0, int(rw['gold']), msg)
    if rw.get('ruby'): post_add(player, 2, 0, int(rw['ruby']), msg)
    for it, q in rw.get('items', []): post_add(player, 13, int(it), int(q), msg)


def mailbox(player):
    """player['Posts'] after adding the welcome mail (once) and today's supply mail, minus expired mail."""
    posts = player.setdefault('Posts', []); t = now_ms(); changed = False
    def add(gt, idx, cnt, msg):
        post_add(player, gt, idx, cnt, msg)
    if not player.get('MailWelcome'):
        player['MailWelcome'] = True; changed = True
        for m in MAIL_WELCOME: add(*m)
    dc = dice_cfg()
    gc = gift_cfg()
    if gc and not player.get('GiftWelcome'):
        player['GiftWelcome'] = True; changed = True
        for ix, q in gc['welcome']: add(13, int(ix), int(q), "Gifts for Kula's Gift Event.")
    if dc and not player.get('DiceWelcome'):
        player['DiceWelcome'] = True; changed = True
        add(13, int(dc['item']), int(dc['welcomePoints']), 'Dice Points for the Dice Mini-game.')
    if player.get('MailDay') != _today():
        player['MailDay'] = _today(); changed = True
        for m in MAIL_DAILY: add(*m)
        if dc: add(13, int(dc['item']), int(dc['dailyPoints']), 'Daily Dice Points.')
        if gc:
            for ix, q in gc['daily']: add(13, int(ix), int(q), "Daily gifts for Kula's Gift Event.")
    keep = [x for x in posts if x['ExpireTime'] > t]
    if len(keep) != len(posts):
        posts[:] = keep; changed = True
    if changed:
        save(player)
    return posts


def red_dots(player):
    """LobbyResponse / RenewResponse.RedDotList [KeyValueObject {Key, Value}]: NetworkManagerWEB.TakeAndSetReddotList registers
    each known key with NewMarkManager (Value through Boolean.Parse). isNewPostGet = the lobby mail icon's red dot: unclaimed
    mail waiting (it never showed: both lists were empty, e.g. a Guild Raid box mailed after a fight, 2026-10-24)."""
    return [{'Key': 'isNewPostGet', 'Value': 'True' if mailbox(player) else 'False'}]


def post_route(path, player, payload):
    posts = mailbox(player); cat = int(payload.get('PostCategory') or 0)
    if path.endswith('postList'):
        # JSON key 'PostCount' (the proto field name; C# names it PostCount_ only because it clashes with the class). 'PostCount_' was
        # dropped by the client's JsonParser: every count read 0, the All tab total 0 -> RECEIVE ALL greyed (probe_postbox, 2026-10-24)
        counts = [{'PostCategory': c, 'PostCount': sum(1 for x in posts if x['PostCategory'] == c)} for c in (1, 2, 3, 4)]
        info = {}
        for c in (1, 2, 3, 4):
            top = max([x['PostNo'] for x in posts if x['PostCategory'] == c] + [0])
            info['Category%dCurrentPostNo' % c] = top; info['Category%dReadPostNo' % c] = 0
        return {'PostCategory': cat, 'PostCountList': counts,
                'PostList': [x for x in posts if cat in (0, x['PostCategory'])], 'SenderProfileList': [],
                'SenderCharacterList': [], 'PostNoInfo': info, 'ResultCode': 0, 'ResultMessage': ''}
    # postRead: claim the listed mail (all of the category when the list is empty)
    nos = {int(n) for n in payload.get('PostNoList') or []}
    take = [x for x in posts if x['PostNo'] in nos] if nos else [x for x in posts if cat in (0, x['PostCategory'])]
    money = player['AccountMoney']; inv = {i['ItemIndex']: i for i in items(player)}; got = {}; stones = []
    for x in take:
        gt, cnt = int(x['GoodsType']), int(x['ContentsCount'])
        if gt in PRICE_KEY:
            money[PRICE_KEY[gt]] = int(money.get(PRICE_KEY[gt], 0)) + cnt
        elif gt == 14:   # GoodsType.ImprintStone (Guild Raid Box): new stone rows, sent back in RewardImprintStoneList like the shop
            lst = imprint_stones(player)
            for _ in range(cnt):
                stones.append({'ImprintStoneNo': max([s['ImprintStoneNo'] for s in lst] + [0]) + 1, 'ImprintStoneIndex': int(x['ContentsIndex']),
                               'CreateTime': now_ms(), 'Enchant': 0, 'Status': 0, 'VestedCharacterIndex': 0, 'LikeFlag': 0,
                               'BonusWeight': 0, 'Polishing': 0})
                lst.append(stones[-1])
        elif gt == 13:
            it = int(x['ContentsIndex'])
            if it not in inv:
                inv[it] = {'ItemIndex': it, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[it])
            inv[it]['Qty'] += cnt; got[it] = got.get(it, 0) + cnt
        posts.remove(x)
    save(player)
    return {'PostNoList': [x['PostNo'] for x in take], 'ReadTime': now_ms(), 'PlayerAccount': player['PlayerAccount'],
            'AccountMoney': money, 'RewardCharacterList': [], 'RewardBattleCardList': [],
            'RewardItemList': [{'ItemIndex': it, 'Qty': n, 'Lock': False} for it, n in got.items()],   # added
            'RewardImprintStoneList': stones, 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
            'ResultCode': 0, 'ResultMessage': ''}


# ---- Craft (/api/craft/list, /api/craft/make; CraftListResponse {CraftList: [CraftInfo]}, CraftMakeRequest {CraftIndex,
#      CraftCount, ItemList, BattleCardList}, CraftMakeResponse). NetworkManagerWEB.Parse_CraftMake: RemainItemList is SET
#      (TakeAndSetItemList), RewardItemList is ADDED (InnerAddCount). Recipes from craft.json (make_data.py); counts made
#      kept in player['CraftMade'].
CRAFT_PATH = Path(__file__).resolve().parent / 'craft.json'


def craft_route(path, player, payload):
    op = path.rsplit('/', 1)[1]; made = player.setdefault('CraftMade', {})
    cfg = json.loads(CRAFT_PATH.read_text()) if CRAFT_PATH.exists() else {}
    def infos():
        return [{'CraftIndex': int(k), 'ProductType': 3, 'ProductIndex': int(cfg[k]['product']) if k in cfg else 0,
                 'CraftCount': int(v), 'CraftAbleResetTime': 0} for k, v in made.items()]
    money = player['AccountMoney']
    if op == 'list':
        return {'CraftList': infos(), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'make':
        ci = str(int(payload.get('CraftIndex') or 0)); n = req_count(payload, 'CraftCount'); rc = cfg.get(ci)   # 0 / negative were forced to 1
        with open(Path(__file__).resolve().parent / 'craft_debug.jsonl', 'a') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        if not rc or n is None:
            return {'ResultCode': 1, 'ResultMessage': 'unknown craft' if not rc else 'bad count', 'AccountMoney': money}
        inv = {i['ItemIndex']: i for i in items(player)}
        cost = int(rc['cost']) * n
        if money['Gold'] < cost or any(int(inv.get(m, {}).get('Qty', 0)) < q * n for m, q in rc['mats']):
            return {'ResultCode': 1, 'ResultMessage': 'not enough materials', 'AccountMoney': money}
        money['Gold'] -= cost
        remain = []
        for m, q in rc['mats']:
            inv[m]['Qty'] -= q * n; remain.append(inv[m])
        prod = inv.get(int(rc['product']))
        if prod is None:
            prod = {'ItemIndex': int(rc['product']), 'Qty': 0, 'Lock': False}; player['ItemList'].append(prod)
        got = int(rc['count']) * n
        prod['Qty'] += got
        made[ci] = int(made.get(ci, 0)) + n
        save(player)
        return {'AccountMoney': money, 'RemainItemList': remain,
                'RewardItemList': [{'ItemIndex': prod['ItemIndex'], 'Qty': got, 'Lock': False}],
                'RewardBattleCardList': [], 'RewardCharacterList': [], 'PostSendFlag': False, 'RewardImprintStoneList': [],
                'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'TagCode': [], 'ResultCode': 0, 'ResultMessage': ''}
    return {}


# ---- Group Growth (/api/character/groupGrowth{Info,Open,Equip,Remove}; GroupGrowthInfoResponse {GroupGrowthList:
#      [GroupGrowthInfo {GroupGrowthIndex, Status 0 lock/1 openable/2 open, UseBuff, Slot1-10}], TeamDeckList, RemainItem};
#      GroupGrowthEquipRequest {GroupGrowthIndex, CharacterIndex, SlotNo}). groupgrowth.json from make_data: allowed
#      fighters per slot. UseBuff = open and every slot filled. State in player['GroupGrowth'].
GG_PATH = Path(__file__).resolve().parent / 'groupgrowth.json'


def gg_route(path, player, payload):
    cfg = json.loads(GG_PATH.read_text()) if GG_PATH.exists() else {}
    st = player.setdefault('GroupGrowth', {})
    for gi in cfg:
        st.setdefault(gi, {'Status': 2, 'Slots': [0] * 10})   # open from the start: Status 1 needs a key item (unlock popup)
    for g in st.values():
        g['Status'] = 2
    op = path.rsplit('/', 1)[1]
    with open(Path(__file__).resolve().parent / 'gg_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    gi = str(int(payload.get('GroupGrowthIndex') or 0))
    if op in ('groupGrowthOpen', 'groupGrowthEquip', 'groupGrowthRemove') and gi in st:
        g = st[gi]
        if op == 'groupGrowthOpen':
            g['Status'] = 2
        else:
            ci = int(payload.get('CharacterIndex') or 0); no = int(payload.get('SlotNo') or 0)
            k = no - 1 if 1 <= no <= 10 else no   # SlotNo 1-based (0 treated as the first slot)
            if 0 <= k < 10:
                if op == 'groupGrowthEquip':
                    allowed = cfg[gi]['slots'][k] if k < len(cfg[gi]['slots']) else []
                    if ci in allowed:
                        for other in st.values():   # a fighter sits in one slot only
                            other['Slots'] = [0 if x == ci else x for x in other['Slots']]
                        g['Slots'][k] = ci
                else:
                    g['Slots'][k] = 0
        save(player)

    def info(gi_, g):
        n = len(cfg[gi_]['slots'])
        use = 1 if g['Status'] == 2 and all(g['Slots'][i] for i in range(n)) else 0
        return dict({'GroupGrowthIndex': int(gi_), 'Status': g['Status'], 'UseBuff': use},
                    **{'Slot%d' % (i + 1): int(g['Slots'][i]) for i in range(10)})
    return {'GroupGrowthList': [info(k, v) for k, v in sorted(st.items(), key=lambda kv: int(kv[0])) if k in cfg],
            'TeamDeckList': player.get('TeamDeckList', []), 'RemainItem': None, 'ResultCode': 0, 'ResultMessage': ''}


# ---- Challenge (Time Attack; /api/challenge/{eventInfo,eventStart,eventEnd,rankingList}; DTOs ChallengeInfo/Start/End
#      Response, ChallengePlayInfo, ChallengeTermInfo from the PC dump). challenge.json from make_data: schedule, stage,
#      gold per clear, score rows [index, grade, max seconds, first-time rubies]. ScoreRewardList = claimed score indices
#      (comma list, parsed by NetworkManagerWEB.ParseChallengeEventInfo). State in player['Challenge'].
CHALLENGE_PATH = Path(__file__).resolve().parent / 'challenge.json'


def challenge_route(path, player, payload):
    cfg = json.loads(CHALLENGE_PATH.read_text()) if CHALLENGE_PATH.exists() else None
    op = path.rsplit('/', 1)[1]
    with open(Path(__file__).resolve().parent / 'challenge_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if not cfg:
        return {}
    st = player.setdefault('Challenge', {'Team': [0, 0, 0], 'Best': 0, 'Total': 0, 'Day': '', 'DayCount': 0, 'Claimed': [], 'Result': 0})
    if st.get('Day') != _today():
        st['Day'] = _today(); st['DayCount'] = 0
    season = local_poll.week_start()   # weekly season (same window as the poll's category-12 schedule)
    if st.get('Season') != season:
        if st.get('Season') is not None:   # new week: best time, ranking and grade rewards start over
            if any(v.get('BestMs') or v.get('Best') for v in [st] + list((st.get('PerSched') or {}).values())):   # weekly rank reward for last season (alone = rank 1 = top tier)
                player['AccountMoney']['Cash'] += int(cfg.get('rankReward', 0))
                st['LastSeasonReward'] = {'Season': st['Season'], 'Cash': int(cfg.get('rankReward', 0))}
            st.update({'Best': 0, 'BestMs': 0, 'BestTeam': [], 'BestPower': 0, 'Claimed': [], 'Result': 0})
            for v in (st.get('PerSched') or {}).values():
                v.update({'Best': 0, 'BestMs': 0, 'BestTeam': [], 'BestPower': 0, 'Claimed': [], 'Result': 0})
        st['Season'] = season
        save(player)
    # one schedule card per Time Attack stage (challenge.json 'schedules', 2026-10-23). Best time, grades and result are per
    # schedule: the first keeps the top-level fields (older saves), the others live in st['PerSched']. eventEnd / rankingList
    # carry no schedule -> the one last opened (eventInfo / eventStart send ChallengeScheduleIndex).
    scheds = {int(x['schedule']): x for x in cfg.get('schedules') or [{'schedule': cfg['schedule'], 'stage': cfg['stage'], 'scores': cfg['scores']}]}
    if payload.get('ChallengeScheduleIndex'):
        st['Sched'] = int(payload['ChallengeScheduleIndex'])
    sc = scheds.get(int(st.get('Sched') or cfg['schedule'])) or scheds[int(cfg['schedule'])]
    ss = st if int(sc['schedule']) == int(cfg['schedule']) else st.setdefault('PerSched', {}).setdefault(
        str(sc['schedule']), {'Best': 0, 'BestMs': 0, 'BestTeam': [], 'BestPower': 0, 'Claimed': [], 'Result': 0})

    def term():
        return {'Term': 1, 'TermPlayCount': st['Total'], 'DayPlayCount': st['DayCount'], 'TotalPlayCount': st['Total']}

    def play_info():
        t = st['Team']
        return dict(term(), ChallengeScheduleIndex=sc['schedule'], ChallengeStageIndex=sc['stage'], BattleType=1,
                    CharacterIndex1=t[0], CharacterIndex2=t[1], CharacterIndex3=t[2], SupportCharacterIndex1=0,
                    SupportCharacterIndex2=0, SupportCharacterIndex3=0, BattleResult=ss['Result'], FirstPlayRewardTime=0,
                    ScoreRewardList=','.join(str(i) for i in ss['Claimed']))
    if op == 'eventInfo':
        # the selectable fighters come from ChallengeCharacterInfoList even in Normal formation (ChallengeModeData cached
        # character list; empty = Auto Team / team slots have no candidates) -> every owned fighter
        chars = [{'ChallengeScheduleIndex': sc['schedule'], 'ChallengeStageIndex': sc['stage'], 'OrderByNo': n, 'RandomFlag': 0,
                  'CharacterIndex': c['CharacterIndex']} for n, c in enumerate(player['CharacterList'], 1)]
        return {'ServerUtcTime': now_ms(), 'ChallengePlayInfo': play_info(), 'UserPlayList': [], 'ChallengeCharacterInfoList': chars,
                'ChallengeWeekRankingInfoList': [], 'ChallengeCharacterInfoStrikerList': [], 'blockUserInfoList': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op == 'eventStart':
        team = [int(c.get('CharacterIndex') or 0) for c in (payload.get('CharacterList') or [])][:3]
        st['Team'] = (team + [0, 0, 0])[:3]; save(player)
        return {'StrikerType': int(payload.get('StrikerType') or 0), 'StrikerUsn': 0, 'StrikerGameDb': 0, 'StrikerNickName': '',
                'StrikerCharacter': None, 'StrikerBattleCardList': [], 'CharacterCoresList': [], 'AccountMoney': player['AccountMoney'],
                'LuckySpawn': 0, 'DropGoldLucky': 0, 'DropGoldJaco': 0, 'DropGoldElite': 0, 'DropGoldBoss': 0, 'DropGoldGimmick1': 0,
                'DropGoldGimmick2': 0, 'DropGoldGimmick3': 0, 'DropLuckyList': [], 'DropJacoList': [], 'DropEliteList': [], 'DropBossList': [],
                'DropGimmickList': [], 'ChallengePlayToken': now_ms(), 'PlayStrikeTime': 0, 'RankingValue': 0, 'StrikerImprintStoneList': [],
                'StrikerAwakenCoreList': [], 'StrikerAccountGrowthStatList': [], 'StrikerAccountExtraList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'eventEnd':
        won = int(payload.get('BattleResult') or 0) == 1; secs = int(payload.get('ClearTime') or 0)
        money = player['AccountMoney']; first = 0
        st['Total'] += 1; st['DayCount'] += 1; ss['Result'] = 1 if won else ss['Result']
        if won:
            money['Gold'] += int(cfg['gold'])
            player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP; grant_char_exp(player, payload)
            if not ss['Best'] or (secs and secs < ss['Best']):
                first = 1 if not ss['Best'] else 0
                ss['Best'] = secs
            ms = int(payload.get('ClearRankTime') or secs * 1000)
            if ms and (not ss.get('BestMs') or ms < ss['BestMs']):   # ranking time (UIUnit_RankingTime.SetData(milliSeconds))
                ss['BestMs'] = ms; ss['BestTeam'] = list(st['Team']); ss['BestPower'] = int(payload.get('TeamPower') or 0)
            for idx, grade, limit, ruby in sc['scores']:
                if secs <= limit and idx not in ss['Claimed']:
                    ss['Claimed'].append(idx); money['Cash'] += int(ruby)
        save(player)
        return {'ChallengeStageIndex': sc['stage'], 'BattleResult': 1 if won else 0, 'RewardItemList': [], 'RewardCharacterList': [],
                'PlayerAccount': player['PlayerAccount'], 'AccountMoney': money,
                'CharacterList': [character_simple(c) for c in player['CharacterList'] if c['CharacterIndex'] in st['Team']],
                'RewardBattleCardList': [], 'ChallengeTermInfo': term(), 'PostSendFlag': False, 'FirstClearFlag': first,
                'ScoreRewardList': ','.join(str(i) for i in ss['Claimed']), 'RewardImprintStoneList': [], 'presetCharacterReward': [],
                'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'rankingList':
        # ChallengeRankingListResponse {MyRanking: RankingDataRank, RankingList: RankingDataScore[], RankingUserList:
        # ChallengeRankingUser[]}: ParseChallengeRankingList pairs each RankingList row with the RankingUserList entry of the
        # same Usn. Offline there is one player -> rank 1 with the best time once a run is cleared.
        best = int(ss.get('BestMs') or ss['Best'] * 1000)
        if not best:
            return {'ServerUtcTime': now_ms(), 'MyRanking': {'Rank': 0, 'RankRate': 0, 'Score': 0, 'Time': 0}, 'RankingList': [],
                    'RankingUserList': [], 'ResultCode': 0, 'ResultMessage': ''}
        r = player['Route']; team = (list(ss.get('BestTeam') or st['Team']) + [0, 0, 0])[:3]
        chars = {c['CharacterIndex']: c for c in player['CharacterList']}
        user = {'ChallengeScheduleIndex': sc['schedule'], 'ChallengeStageIndex': sc['stage'], 'Usn': r['Usn'], 'BattleType': 1,
                'RankingValue': best, 'TeamPower': int(ss.get('BestPower') or 0), 'CreateTime': now_ms(), 'UpdateTime': now_ms(),
                'guildNo': 0, 'guildName': ''}
        for n, ci in enumerate(team, 1):
            c = chars.get(ci, {})
            user.update({'CharacterIndex%d' % n: ci, 'Grade%d' % n: int(c.get('Grade', 0)), 'Exp%d' % n: int(c.get('Exp', 0))})
        return {'ServerUtcTime': now_ms(), 'MyRanking': {'Rank': 1, 'RankRate': 1, 'Score': best, 'Time': best},
                'RankingList': [{'Usn': r['Usn'], 'Score': best, 'GameDb': r.get('GameDb', 1), 'NickName': r.get('NickName', ''), 'Rank': 1}],
                'RankingUserList': [user], 'ResultCode': 0, 'ResultMessage': ''}
    return {}


# ---- Sura Dungeon (/api/suraDungeon/{info,stageStart,stageEnd,stageMopUp}; DTOs SuraDungeonResponse {SuraDungeon:
#      SuraDungeonWEBData, SuraDungeonStageList}, SuraDungeonStageStart/End/Mopup from the PC dump). sura.json from
#      make_data: difficulty -> stage indices in order. Clearing a difficulty's last stage opens the next difficulty.
#      State in player['Sura'] = {Diff, Cleared: {stage: plays}}.
SURA_PATH = Path(__file__).resolve().parent / 'sura.json'


def sura_route(path, player, payload):
    cfg = json.loads(SURA_PATH.read_text()) if SURA_PATH.exists() else None
    op = path.rsplit('/', 1)[1]
    with open(Path(__file__).resolve().parent / 'sura_debug.jsonl', 'a') as f:
        f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
    if not cfg:
        return {}
    st = player.setdefault('Sura', {'Diff': 1, 'Cleared': {}, 'Token': 0})
    diffs = {int(k): v for k, v in cfg['difficulties'].items()}
    if st.get('SweepDay') != time.strftime('%Y-%m-%d'):   # free sweeps reset at local midnight
        st['SweepDay'] = time.strftime('%Y-%m-%d'); st['Sweeps'] = 0

    def info():
        stages = diffs[st['Diff']]
        cleared = [i for i in stages if str(i) in st['Cleared']]
        # SuraDungeonData.SetPlayState: stage == ClearStageIndex + 1 is the playable one -> first - 1 when none cleared
        last = max(cleared) if cleared else stages[0] - 1
        allc = [int(i) for i in st['Cleared']]
        return {'SuraDungeon': {'SuraDungeonDifficultyIndex': st['Diff'], 'SuraDungeonClearStageIndex': last,
                                'SuraDungeonClearStageIndexMax': max(allc) if allc else 0, 'FreeMopUpPlayCount': int(st['Sweeps']),
                                'PayMopUpPlayCount': 0},
                # SuraStageListModel.SetData builds the stage slots ONLY from this list -> every stage of the difficulty
                'SuraDungeonStageList': [{'SuraDungeonStageIndex': i, 'BattleResult': 1 if str(i) in st['Cleared'] else 0,
                                          'PlayCount': int(st['Cleared'].get(str(i), 0))} for i in stages]}
    if op == 'info':
        return dict(info(), ServerUtcTime=now_ms(), ResultCode=0, ResultMessage='')
    if op == 'stageStart':
        st['Token'] = now_ms(); save(player)
        return {'PlayToken': st['Token'], 'ResultCode': 0, 'ResultMessage': ''}
    money = regen_active_point(player)
    if op == 'stageEnd':
        si = str(int(payload.get('SuraDungeonStageIndex') or 0)); won = int(payload.get('BattleResult') or 0) == 1
        first = 0; clear, firsts = [], []
        if won:
            first = 0 if si in st['Cleared'] else 1
            st['Cleared'][si] = int(st['Cleared'].get(si, 0)) + 1
            money['Gold'] += int(cfg['gold']); clear.append(goods(1, 1, int(cfg['gold'])))
            player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP   # rank EXP like the other stage modes
            grant_char_exp(player, payload)   # stored; the Sura end reply has no CharacterList (visible after re-entering)
            if first:
                money['Cash'] += int(cfg['firstCash']); firsts.append(goods(1, 2, int(cfg['firstCash'])))
            stages = diffs[st['Diff']]
            if all(str(i) in st['Cleared'] for i in stages) and st['Diff'] + 1 in diffs:
                st['Diff'] += 1   # whole difficulty cleared -> next one (client: CheckOpenDifficulty 'phase up')
        save(player)
        return {'BattleResult': 1 if won else 0, 'FirstClearFlag': first, 'PlayerAccount': player['PlayerAccount'], 'AccountMoney': money,
                'RewardItemList': [], 'RewardBattleCardList': [], 'RewardCharacterList': [], 'ClearRewardList': clear,
                'GlobalDropRewardList': [], 'RewardContentsList': clear, 'FirstClearRewardList': firsts, 'RewardImprintStoneList': [],
                'PostSendFlag': False, 'GuildBuffList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                'ResultCode': 0, 'ResultMessage': ''}
    if op in ('stageMopUp', 'mopup'):
        n = max(1, int(payload.get('MopUpCount') or 1)); gold = int(cfg['gold']) * n
        if int(st['Sweeps']) + n > int(cfg.get('sweepMax', 3)) or not st['Cleared']:
            return {'ResultCode': 1, 'ResultMessage': 'no free sweeps left today', 'AccountMoney': money}
        st['Sweeps'] = int(st['Sweeps']) + n
        money['Gold'] += gold; save(player)
        return {'PlayerAccount': player['PlayerAccount'], 'AccountMoney': money, 'RewardItemList': [], 'RewardBattleCardList': [],
                'RewardCharacterList': [], 'ClearRewardList': [goods(1, 1, gold)], 'GlobalDropRewardList': [],
                'RewardContentsList': [goods(1, 1, gold)], 'RewardImprintStoneList': [], 'PostSendFlag': False, 'GuildBuffList': [],
                'RemainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'AdsList': [], 'SuraDungeonDifficultyIndex': st['Diff'],
                'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    return {}


def route_overrides(path, player, payload=None):
    """Per-route content for otherwise default responses. payload = decoded request JSON (may be None)."""
    payload = payload or {}
    if path.startswith('/api/gacha2/'):   # the PC 1.11.2 summon screen calls gacha2/* (seen live 2026-10-15)
        path = '/api/gacha/' + path[len('/api/gacha2/'):]
    if path == '/api/personal/contentsList':
        # Private Shop (shop.json 'private', make_data): one PersonalInfo per day opens the isPersonalCustomShop until midnight
        pv = shop_cfg().get('private') or {}
        day = int(time.mktime(time.strptime(_today(), '%Y-%m-%d'))) * 1000
        info = [{'PersonalContentsIndex': int(pv['contents']), 'OpenTime': day, 'CloseTime': day + 86400000}] if pv.get('contents') else []
        return {'GachaScheduleList': gacha_schedules(), 'PersonalInfoList': info,
                'CustomShopManageIndexList': [int(pv['manage'])] if info else [], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/gacha/gachaInfo':
        # 'GachaType' = the proto name (C# GachaType_; the client's JsonParser drops 'GachaType_' and read 0 = None, see post_route);
        # 1 = GachaType.Default, as GachaTypeTable row 1
        return {'GachaScheduleList': gacha_schedules(),
                'GachaTypeList': [{'GachaTypeIndex': 1, 'GachaType': 1, 'GachaContentType': 1, 'GachaListSortOrder': 1,
                                   'AttributeType': '', 'GachaStart': 0, 'GachaEnd': 0, 'IsChanceGacha': 0}],
                'GachaStepUpList': [],
                'GachaDefaultList': [{'GachaTypeIndex': 1, 'GachaDefaultIndex': di, 'GachaDiscountBuyCount': 0,
                                      'GachaBuyCount': 0, 'GachaFreeTime': 0, 'GachaDiscountBuyTime': 0}
                                     for di in sorted(GACHA_DEFAULTS)],
                'GachaMileageList': [], 'gachaSelectPickUpList': [], 'gachaMileageSelectList': [],
                'gachaRateUpScheduleList': [], 'gachaChoiceList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if path in ('/api/gacha/gachaDefaultPlay', '/api/gacha/gachaTicketRandom'):
        # which pull (1x / 10x): the request carries the chosen gachaDefaultIndex; field name varies, so try the
        # known candidates and fall back to 1. The full payload is logged once so a real pull confirms the field.
        di = None
        for k in ('GachaDefaultIndex', 'gachaDefaultIndex', 'normalCategory', 'NormalCategory'):
            if payload.get(k):
                di = int(payload[k]); break
        if di not in GACHA_DEFAULTS:
            di = 1
        return gacha_play(player, di)
    if path == '/api/attendance/info':
        # the calendar is EventAttendanceTable row 1 (make_data); AttendanceReward = the player's progress in it.
        # Seen live: GiveTime counts today and RewardGetFlag 1 = today's reward is waiting -> the attendance page sends
        # attendance/give by itself (GiveTime 0 / flag 0 showed day 1 as "Next Bonus" and never claimed).
        return {'DailyAttendanceAccumulate': attendance_accumulate(player), 'EventAttendanceList': [attendance_accumulate(player)],
                'FailureRewardList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/attendance/give':
        with open(Path(__file__).resolve().parent / 'attendance_debug.jsonl', 'a') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        out = attendance_give(player)
        # never an error: a repeated claim on the same day just returns the current state (an error = NETWORK ERROR popup).
        # The old ms LastGiveTime overflowed int32, the parse threw inside CheckResultWithoutUI (traced live with Frida) and
        # silently aborted UIPage_Attendance.RecvAttendanceGive: no reward popup, the screen mask stayed on, X was dead.
        # EventAttendanceList updates the client's model (claimed -> no red dot); the wallet syncs from the next AccountMoney.
        return {'EventAttendanceList': [attendance_accumulate(player)], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/book/bookReward':   # BookRewardRequest {CollectionType, CollectionRewardIndex, CharacterIndex, CharacterGrade}
        ctype = int(payload.get('CollectionType') or 1); ri = int(payload.get('CollectionRewardIndex') or 0)
        r = book_claim(player, ctype, ri, int(payload.get('CharacterIndex') or 0))
        if r is None:   # already claimed / unknown: no error popup, the client just keeps its state
            return {'CollectionType': ctype, 'CollectionRewardIndex': ri, 'RewardType': 0, 'RewardList': [], 'ListBuff': [],
                    'TeamCollectionIndex': 0, 'ResultCode': 0, 'ResultMessage': ''}
        vo, rw = r; book_mail(player, [rw], 'fighter' if ctype == 1 else 'team' if ctype == 4 else 'collection'); save(player)
        return {'CollectionType': ctype, 'CollectionRewardIndex': ri, 'RewardType': vo['RewardType'], 'RewardList': vo['RewardList'],
                'ListBuff': [], 'TeamCollectionIndex': vo['TeamCollectionIndex'], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/book/bookRewardAll':   # BookRewardAllRequest {ListBookReward: [BookRewardRequestVO]}
        out, prizes = [], []
        for q in payload.get('ListBookReward') or []:
            r = book_claim(player, int(q.get('CollectionType') or 1), int(q.get('CollectionRewardIndex') or 0), int(q.get('CharacterIndex') or 0))
            if r is not None:
                r[0]['CharacterGrade'] = int(q.get('CharacterGrade') or 0); out.append(r[0]); prizes.append(r[1])
        if out:
            book_mail(player, prizes, '%d rewards' % len(out)); save(player)
        return {'ListBookReward': out, 'ListBuff': [], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/affection/giveGift':
        return affection_give_gift(player, payload)
    if path == '/api/character/characterEnchant':
        # CharacterEnchantRequest {Character: CharacterSimple7 {CharacterIndex, ...}, AddEnchantHp/Atk/Def, ItemList}
        # -> CharacterEnchantResponse {Character, ItemList}. The fighter is inside 'Character' (reading a top-level
        # CharacterIndex answered "no such character" to every Plus Capsule use, seen 2026-10-18). The client computes the
        # added plus levels from the boosters (1093 ATK, 1094 DEF, 1095 HP); the server checks and spends the items.
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        cpay = payload.get('Character') or {}
        ch = character(player, int(cpay.get('CharacterIndex') or payload.get('CharacterIndex') or 0))
        if not ch:
            return {'Character': cpay, 'ItemList': [], 'ResultCode': 1, 'ResultMessage': 'no such character'}
        inv = {i['ItemIndex']: i for i in items(player)}
        cap = int(awaken_cfg().get('plusMax', 99))   # +99 per stat (Character.EnchantMax; config 801 / maxPlusLevelUp)
        room = {k: max(0, cap - int(ch.get('Enchant' + k, 0))) for k in ('Hp', 'Atk', 'Def')}
        fail = lambda msg: {'Character': cpay, 'ItemList': [], 'ResultCode': 1, 'ResultMessage': msg}
        need, err = item_need(payload.get('ItemList'))
        if err or item_short(player, need) is not None:   # the listed boosters must exist, even the part the cap leaves unused
            return fail(err or 'not enough boosters')
        # 1 booster = +1 plus (make_data: +99 per stat = 99 boosters); a stat only rises by the boosters of that stat that are
        # spent, under the cap (the declared AddEnchant used to be trusted: +HP with an ATK booster, or with none at all).
        # Nothing to add (stat already at the cap) stays a success that changes nothing, as before.
        booster = {1093: 'Atk', 1094: 'Def', 1095: 'Hp'}
        add = {s: min(room[s], max(0, int(payload.get('AddEnchant' + s) or 0)), need.get(b, 0)) for b, s in booster.items()}
        spend = {b: add[s] for b, s in booster.items() if add[s]}
        used = []
        for k, q in spend.items():
            inv[k]['Qty'] = int(inv[k]['Qty']) - q; used.append(inv[k])
        for k in ('Hp', 'Atk', 'Def'):
            ch['Enchant' + k] = int(ch.get('Enchant' + k, 0)) + add[k]
        save(player)
        return {'Character': {'CharacterIndex': ch['CharacterIndex'], 'Grade': ch['Grade'], 'EnchantHp': ch.get('EnchantHp', 0),
                'EnchantAtk': ch.get('EnchantAtk', 0), 'EnchantDef': ch.get('EnchantDef', 0),
                'CharacterLevel': level_of(ch),
                'CharacterPower': int(cpay.get('CharacterPower') or 0), 'ex': int(cpay.get('ex') or 0)},
                'ItemList': used, 'ResultCode': 0, 'ResultMessage': ''}
    if path in ('/api/character/awaken', '/api/character/awakenLevelUp', '/api/character/awakenEnchant'):
        # AwakenRequest {CharacterIndex, Phase, slot1-4ItemList, UsedGold}; LevelUp {CharacterIndex, AddExp, ItemList};
        # Enchant {CharacterIndex, AddEnchantHp/Atk/Def, ItemList}. All answer AwakenResponse {AccountMoney, ItemList, Character}.
        # Official guide checks: awaken at Lv90 (1 own Memory), next tier only from the max level of the current one
        # (10 levels per tier), max tier from awaken.json (3 for bronze/silver), EXP capped at the tier's max level.
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        ch = character(player, int(payload.get('CharacterIndex') or 0))
        fail = lambda msg: {'AccountMoney': player['AccountMoney'], 'ItemList': [], 'Character': character_simple6(ch) if ch else {},
                            'ResultCode': 1, 'ResultMessage': msg}
        if not ch:
            return fail('no such character')
        cfg = awaken_cfg(); money = player['AccountMoney']
        if path.endswith(('/awaken', '/awakenLevelUp')) and level_of(ch) < 90:
            return fail('normal fighter level 90 is required; review normal EXP and limit breaks')
        phase = int(ch.get('Awaken') or 0)
        maxp = int(cfg['fighters'][str(ch['CharacterIndex'])]['maxPhase'])
        if not 0 <= phase <= maxp:
            return fail('invalid awakening phase; review saved progression')
        if path.endswith('/awakenLevelUp'):
            if phase == 0:
                return fail('not awakened')
            add_exp = payload.get('AddExp')
            if type(add_exp) is not int or not 1 <= add_exp <= QTY_MAX:
                return fail('AddExp must be a positive integer')
            cap = cfg['levelExp'][10 * phase - 2]
            if int(ch.get('AwakenExp', 0)) >= cap:
                return fail('awakening level already at the phase limit')
        lists = [payload.get(k) or [] for k in ('ItemList', 'slot1ItemList', 'slot2ItemList', 'slot3ItemList', 'slot4ItemList')]
        want = [u for l in lists for u in l]
        err = item_error(player, want)   # summed + no negative entries (a negative Qty used to pass and ADD items)
        if err:
            return fail('not enough materials' if err == 'not enough items' else err)
        if not 0 <= int(payload.get('UsedGold') or 0) <= int(money['Gold']):
            return fail('not enough gold')
        if path.endswith('/awaken'):
            target = int(payload.get('Phase') or phase + 1); maxp = int(cfg.get('fighters', {}).get(str(ch['CharacterIndex']), {}).get('maxPhase', 5))
            if target != phase + 1 or target > maxp:
                return fail('cannot awaken further')
            if phase == 0 and (int(ch.get('Grade', 0)) < 6 or int(ch.get('LimitBreakProgressCount', 0)) < 30):
                # guide: awaken at Lv90 = grade 6 with all 30 limit breaks (the client offered it at a grade-6 fighter's
                # current max level: Lady Maxima awakened at Lv61 with no limit breaks, 2026-10-18)
                return fail('the fighter must reach Lv90 (grade 6, all 30 limit breaks)')
            if phase > 0 and awaken_level(ch) < 10 * phase:
                return fail('reach the max level of this tier first')
            if money['Gold'] < int(payload.get('UsedGold') or 0):
                return fail('not enough gold')
            money['Gold'] -= int(payload.get('UsedGold') or 0)
            ch['Awaken'] = target
            if target == 1:
                ch['AwakenExp'] = 0   # awakening starts the fighter at awaken Lv1
        elif path.endswith('/awakenLevelUp'):
            if phase == 0:
                return fail('not awakened')
            # AwakenLevelTable.GetCharacterLevel: level L+1 once exp reaches row L; beyond the last row it returns 1, so
            # stop exactly at the requirement of row (tier max - 1) = the tier's max level
            ch['AwakenExp'] = min(cap, int(ch.get('AwakenExp', 0)) + add_exp)
        else:
            for k in ('Hp', 'Atk', 'Def'):
                ch['Enchant' + k] = int(ch.get('Enchant' + k, 0)) + int(payload.get('AddEnchant' + k) or 0)
        used = take_items(player, want)
        awaken_core_points(player, ch); save(player)
        return {'AccountMoney': money, 'ItemList': used, 'Character': character_simple6(ch), 'ResultCode': 0, 'ResultMessage': ''}
    _u = utility_route(path, player, payload or {})
    if _u is not None:
        return _u
    if path in ('/api/adventure/adventureSoulDropEventStageList', '/api/adventure/adventureSoulDropEventTicketRecharge'):
        return soul_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/questEvent/explore'):
        return explore_route(path.rsplit('/', 1)[1], player, payload or {})
    if path in ('/api/item/pieceCombine', '/api/item/pieceSell'):
        return piece_route(path.rsplit('/', 1)[1], player, payload or {})
    if path in ('/api/character/memoryDimensionTradeInfo', '/api/character/memoryDimensionTrade'):
        return memtrade_route(path.rsplit('/', 1)[1], player, payload or {})
    if path == '/api/character/memoryCombine':
        # MemoryCombineRequest {memoryCombineList: [{baseGrade, baseSynastry, combineQty, ItemList}]} -> MemoryCombineResponse
        # {AccountMoney, RewardItemList, ItemList, ...}. Official guide: 5 Memories of one element/grade -> 1 of the next grade
        # (Bronze 3 > Silver 4 > Gold 5 > Fest 9); 95% the Element Memory, 5% a fighter Memory of that grade and element.
        with GROWTH_LOG.open('a', encoding='utf-8') as f:   # never seen live before 2026-10-24: keep the real request shape
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        cfg = awaken_cfg(); fighters = cfg.get('fighters', {}); inv = {i['ItemIndex']: i for i in items(player)}
        nxt = {3: 4, 4: 5, 5: 9}; got = {}; changed = {}
        for job in payload.get('memoryCombineList') or []:
            g = int(job.get('baseGrade') or 0); g = 9 if g >= 90 else g; s = int(job.get('baseSynastry') or 0); n = int(job.get('combineQty') or 0)
            need, err = item_need(job.get('ItemList'))   # summed: a memory listed twice was checked per entry and went negative
            # materials must be Memories of that grade and element: the Element Memory (memElem + grade*10 + element) or a fighter
            # Memory (MEM_BASE + index) of a non-collab fighter with that grade and element (any item was accepted before)
            elem = int(cfg.get('memElem', 61000)) + g * 10 + s
            ok_mat = lambda k: k == elem or (MEM_BASE < k < MEM_BASE + 1000 and fighters.get(str(k - MEM_BASE), {}).get('grade') == g
                                             and fighters.get(str(k - MEM_BASE), {}).get('element') == s
                                             and not fighters.get(str(k - MEM_BASE), {}).get('collab'))
            if err or g not in nxt or not 1 <= s <= 5 or not 0 < n <= QTY_MAX // 5 or sum(need.values()) < 5 * n or \
                    not all(ok_mat(k) for k in need) or item_short(player, need) is not None:
                continue
            for k, q in need.items():
                inv[k]['Qty'] = int(inv[k]['Qty']) - q; changed[k] = inv[k]
            pool = [int(c) for c, f in fighters.items() if f.get('grade') == nxt[g] and f.get('element') == s and not f.get('collab')]
            for _ in range(n):
                k = (MEM_BASE + random.choice(pool)) if pool and random.random() < 0.05 else int(cfg.get('memElem', 61000)) + nxt[g] * 10 + s
                got[k] = got.get(k, 0) + 1
        for k, q in got.items():
            if k not in inv:
                inv[k] = {'ItemIndex': k, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[k])
            inv[k]['Qty'] += q; changed[k] = inv[k]
        save(player)
        return {'ResultCode': 0 if got else 1, 'ResultMessage': '' if got else 'nothing to combine', 'AccountMoney': player['AccountMoney'],
                'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [{'ItemIndex': k, 'Qty': q, 'Lock': False} for k, q in got.items()],
                'RewardImprintStoneList': [], 'ItemList': list(changed.values()), 'PostSendFlag': False,
                'presetCharacterReward': [], 'presetCharacterCoreReward': []}
    if path == '/api/imprint/polishing':
        # ImprintPolishingRequest {ImprintStoneNo, ImprintStoneIndex, PolishingLevel = target}; reply AccountMoney,
        # PolishingResult, ImprintStone, RemainItemList (set). Charges the target row's material + gold (as the popup shows).
        cfg = json.loads((Path(__file__).resolve().parent / 'imprint.json').read_text())
        no = int(payload.get('ImprintStoneNo') or 0); stone = next((x for x in imprint_stones(player) if x['ImprintStoneNo'] == no), None)
        target = int(payload.get('PolishingLevel') or 0); money = player['AccountMoney']
        cost = cfg.get('polishCost', {}).get(str(target)); core = int(cfg.get('polishCore', 0))
        inv = {i['ItemIndex']: i for i in items(player)}
        if not stone or not cost or target <= int(stone.get('Polishing', 0)) or inv.get(core, {}).get('Qty', 0) < cost[0] or money['Gold'] < cost[1]:
            return {'ResultCode': 1, 'ResultMessage': 'cannot polish', 'AccountMoney': money}
        inv[core]['Qty'] -= cost[0]; money['Gold'] -= cost[1]; stone['Polishing'] = target; save(player)
        return {'AccountMoney': money, 'PolishingResult': 1, 'ImprintStone': stone, 'RemainItemList': [inv[core]],
                'ResultCode': 0, 'ResultMessage': ''}
    if path in ('/api/imprint/sell', '/api/imprint/disassemble'):
        # sell: ImprintSellRequest {ImprintStoneNo, imprintStoneNoList} -> {AccountMoney}; disassemble: ImprintDisassembleRequest
        # {imprintList: [{ImprintStoneNo, ImprintStoneIndex, CostType, CostIndex, CostValue}]} -> AccountMoney, ItemList (set),
        # RewardContentsList (result popup). The client removes the stones itself. Amounts from imprint.json (make_data).
        cfg = json.loads((Path(__file__).resolve().parent / 'imprint.json').read_text())
        money = player['AccountMoney']; lst = imprint_stones(player)
        if path.endswith('sell'):
            nos = [int(n) for n in payload.get('imprintStoneNoList') or []] or [int(payload.get('ImprintStoneNo') or 0)]
        else:
            nos = [int(x.get('ImprintStoneNo') or 0) for x in payload.get('imprintList') or []]
        gone = [x for x in lst if x['ImprintStoneNo'] in set(nos)]
        if not gone:
            return {'ResultCode': 1, 'ResultMessage': 'no such stone', 'AccountMoney': money}
        if path.endswith('sell'):
            money['Gold'] += int(cfg.get('sellGold', 0)) * len(gone)
            reward = None
        else:
            plans = [cfg['disassemble'][str(min(int(x.get('Enchant', 0)), int(cfg['max'])))] for x in gone]
            cost = sum(c for c, _ in plans)
            if money['Gold'] < cost:
                return {'ResultCode': 1, 'ResultMessage': 'not enough gold', 'AccountMoney': money}
            money['Gold'] -= cost; inv = {i['ItemIndex']: i for i in items(player)}; got = {}
            for _, mats in plans:
                for it, n in mats:
                    got[it] = got.get(it, 0) + n
            for it, n in got.items():
                if it not in inv:
                    inv[it] = {'ItemIndex': it, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[it])
                inv[it]['Qty'] += n
            reward = [dict(goods(no, 13, n), ContentsIndex=it, ContentsCount=n) for no, (it, n) in enumerate(sorted(got.items()), 1)]
        for x in gone:   # off any fighter that wore it, then out of the inventory
            for ch in player['CharacterList']:
                for i in range(1, 6):
                    if ch.get('ImprintStoneNo%d' % i) == x['ImprintStoneNo']:
                        ch['ImprintStoneNo%d' % i] = 0
            lst.remove(x)
        save(player)
        if reward is None:
            return {'AccountMoney': money, 'ResultCode': 0, 'ResultMessage': ''}
        return {'AccountMoney': money, 'ItemList': [inv[it] for it in sorted(got)], 'RewardContentsList': reward,
                'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [], 'RewardImprintStoneList': [],
                'PostSendFlag': False, 'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/imprint/enchant':
        # ImprintEnchantRequest {ImprintStoneNo, ImprintStoneIndex, MaterialItem}; reply EnchantResult (>0 success),
        # AccountMoney, ImprintStone, RemainItemList (set). Rates/costs from imprint.json (make_data).
        cfg = json.loads((Path(__file__).resolve().parent / 'imprint.json').read_text())
        no = int(payload.get('ImprintStoneNo') or 0); stone = next((x for x in imprint_stones(player) if x['ImprintStoneNo'] == no), None)
        mat = payload.get('MaterialItem') or {}; kit = str(int(mat.get('ItemIndex') or 0)); money = player['AccountMoney']
        inv = {i['ItemIndex']: i for i in items(player)}
        if not stone or kit not in cfg['kits'] or int(stone['Enchant']) >= int(cfg['max']) or inv.get(int(kit), {}).get('Qty', 0) < 1:
            return {'ResultCode': 1, 'ResultMessage': 'cannot enchant', 'AccountMoney': money}
        lv = int(stone['Enchant']); cost = int(cfg['cost'][lv])
        if money['Gold'] < cost:
            return {'ResultCode': 1, 'ResultMessage': 'not enough gold', 'AccountMoney': money}
        money['Gold'] -= cost; inv[int(kit)]['Qty'] -= 1
        ok = random.randrange(100) < int(cfg['kits'][kit][lv])
        if ok:
            stone['Enchant'] = lv + 1
        save(player)
        return {'EnchantResult': 1 if ok else 0, 'AccountMoney': money, 'ImprintStone': stone, 'RemainItemList': [inv[int(kit)]],
                'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/character/imprintEquip':
        # ImprintEquipRequest.Character = {CharacterIndex, ImprintStoneNo1-5, ...}; echo the equipped slots back.
        c = payload.get('Character') or {}
        ch = character(player, int(c.get('CharacterIndex') or 0))
        if ch:
            for i in range(1, 6):
                ch['ImprintStoneNo%d' % i] = int(c.get('ImprintStoneNo%d' % i) or 0)
            save(player)
        return {'Character': dict(character_simple6(ch), **{'ImprintStoneNo%d' % i: ch.get('ImprintStoneNo%d' % i, 0) for i in range(1, 6)}) if ch else {},
                'ResultCode': 0 if ch else 1, 'ResultMessage': '' if ch else 'no such character'}
    if path == '/api/character/characterLike':
        ci = int(payload.get('CharacterIndex') or 0); like = bool(payload.get('Like'))
        ch = character(player, ci)
        if ch:
            ch['LikeFlag'] = like; save(player)
        return {'CharacterIndex': ci, 'Like': like, 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/player/cdnVersion':
        # DownloadManager.OnCheckTableVersion reads versions[<table key>] and versions[GetLanguagePackName()] with
        # get_Item (no ContainsKey) -> an empty VersionList threw KeyNotFoundException and silently aborted every
        # scene change that checks versions first (Summon, Shop, Craft, Exchange, Secret Shop). Return the published
        # pack versions (same numbers as /tables/common/table/version.kof) so nothing is re-downloaded.
        vf = Path(__file__).resolve().parent / 'table-versions.json'
        v = json.loads(vf.read_text()) if vf.exists() else {}
        v.setdefault('lang_en', v.get('lang_global', 0))
        return {'VersionList': [{'Key': k, 'Value': str(n)} for k, n in v.items()], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/player/activePointGive':
        # AccountActivePointGiveResponse {ActivePoint, ActivePointGiveClientTime, ActivePointUpdateTime, ServerTime}:
        # Parse_PlayerActivePointGive sets AP, the regen anchor and the server clock from it. The untyped default stub
        # returned none of them -> AP shown as 0 and the clock reset (seen live after a Sura clear).
        money = regen_active_point(player); save(player)
        return {'ActivePoint': money['ActivePoint'], 'ActivePointGiveClientTime': 0,
                'ActivePointUpdateTime': money['ActivePointUpdateTime'], 'ServerTime': now_ms(), 'ResultCode': 0, 'ResultMessage': ''}
    if path.startswith('/api/suraDungeon/'):
        return sura_route(path, player, payload or {})
    if path.startswith('/api/challenge/') and not path.endswith('rankingCharacterInfo'):
        return challenge_route(path, player, payload or {})
    if path.startswith('/api/character/groupGrowth'):
        return gg_route(path, player, payload or {})
    if path in ('/api/craft/list', '/api/craft/make'):
        return craft_route(path, player, payload or {})
    if path.startswith('/api/guild/'):
        return guild_route(path, player, payload or {})
    if path.startswith('/api/guildCoop/'):
        return gcoop_route(path, player, payload or {})
    if path.startswith('/api/guildDungeon/'):
        return graid_route(path, player, payload or {})
    if path in ('/api/post/postList', '/api/post/postRead'):
        return post_route(path, player, payload or {})
    if path in ('/api/shop/shopGoodsQtyList', '/api/shop/shopGoodsBuy', '/api/shop/shopGoodsRefresh'):
        return shop_route(path, player, payload or {})
    if path.startswith('/api/allOutFight/') and allout_cfg():
        return allout_route(path, player, payload or {})
    if path.startswith('/api/infiniteFight/'):
        return infinite_route(path, player, payload or {})
    if path.startswith('/api/proveDungeon/'):
        return prove_route(path, player, payload or {})
    if path == '/api/battle/matchUserInfo':
        return league_match_user(player, payload or {})
    if path.startswith('/api/arenaLeague/'):
        return league_route(path, player, payload or {})
    if path.startswith('/api/colosseum/'):
        return colo_route(path, player, payload or {})
    if path == '/api/battle/hallOfFame':
        hall = int((payload or {}).get('hallOfFameIndex') or 1)
        return {'TopInfo': {'hallOfFameIndex': hall, 'season': 1, 'topUserList': hof_top(player, hall)}}
    if path == '/api/battle/hallOfFameRanking':   # Top 50 popup: no stored past-season rankings -> empty lists ('no record')
        return {'ChampionShipRankingList': [], 'ChampionShipRankingUserList': [], 'ArenaLeagueRankingList': [],
                'ArenaLeagueRankingUserList': [], 'FriendGuildInfoList': [], 'InfiniteFightRankingInfoList': [], 'AllOutFightRankingInfoList': []}
    if path == '/api/battle/battleLobby':
        # RankingSeason dates are Unix ms (DateTimeExts.ToDateTime). SingleDuelLeagueData.IsOpen = start <= now < end;
        # IsMidProcessTime = MidProcessStart expired and MidProcessEnd not -> keep both in the future (Ghidra).
        season = league_season()
        return {'ServerUtcTime': now_ms(), 'ColosseumSeason': dict(season), 'ArenaLeagueSeason': dict(season),
                'ChampionshipSeason': dict(season), 'ChampionshipOperateSchedule': [], 'ChampionshipSeasonScheduleList': [],
                'FameList': hof_fame_list(), 'ResultCode': 0, 'ResultMessage': ''}
    if path.startswith('/api/relayDungeon/') and teamrelay_cfg():
        op = path.rsplit('/', 1)[1]
        payload = payload or {}
        rc = relay_row(payload.get('TeamRelayIndex') or payload.get('teamRelayIndex'))
        if op == 'dungeonInfoList':   # RelayDungeonInfoListRequest.ModeIndex: 501 Team Relay, 502 Meta Team Relay, 503 High Score
            mode = int(payload.get('ModeIndex') or 501)
            return {'ServerUtcTime': now_ms(), 'TeamRelayDungeonInfoList': [teamrelay_dungeon(player, r) for r in relay_rows() if int(r['mode']) == mode],
                    'RankingRewardList': [], 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'dungeonInfo':
            return {'ServerUtcTime': now_ms(), 'DungeonInfo': teamrelay_dungeon(player, rc),
                    'TeamRelayTeamList': teamrelay_state(player, rc)['Decks'], 'myRanking': teamrelay_rank(player, rc),
                    'ResultCode': 0, 'ResultMessage': ''}
        if op == 'teamDeckUpdate':
            st = teamrelay_state(player, rc)
            st['Decks'] = [d for d in (payload.get('TeamRelayTeamList') or []) if isinstance(d, dict)]
            save(player)
            return {'ResultCode': 0, 'ResultMessage': ''}
        if op == 'dungeonStart':
            money = regen_active_point(player); save(player)
            return {'AccountMoney': money, 'PlayToken': now_ms(), 'BossHP': int(teamrelay_state(player, rc)['BossHP']),
                    'ResultCode': 0, 'ResultMessage': ''}
        if op in ('dungeonEnd', 'dungeonMopup'):
            return teamrelay_end(player, payload)
        if op == 'dungeonRecharge':
            return {'Recharge': 0, 'AccountMoney': player['AccountMoney'], 'Point': 99, 'ResultCode': 0, 'ResultMessage': ''}
        if op in ('rankingInfoList', 'rankingInfoDetail'):
            return {'myRanking': teamrelay_rank(player, rc), 'RankingList': [], 'ResultCode': 0, 'ResultMessage': ''}
    if path.startswith('/api/smash/') and smash_cfg():
        return smash_route(path, player, payload or {})
    if path.startswith('/api/questEvent/buffDungeon') and bsd_event():
        r = bsd_route(path, player, payload or {})
        if r is not None:
            return r
    if path.startswith('/api/questEvent/crucibleTower') and ct_event():
        r = ct_route(path, player, payload or {})
        if r is not None:
            return r
    if path.startswith('/api/questEvent/eventTower') and tower_cfg():
        return tower_route(path, player, payload or {})
    if path.startswith('/api/questEvent/marathon') and marathon_cfg():
        return marathon_route(path, player, payload or {})
    if path.startswith('/api/epicQuest/') and epic_cfg():
        op = path.rsplit('/', 1)[1]; cfg = epic_cfg()
        epic = next((e for e in cfg['epics'] if e['index'] == int(payload.get('EpicQuestIndex') or 0)), None)
        if op == 'epicList':
            return {'ServerUtcTime': now_ms(), 'EpicList': [{'EpicQuestIndex': e['index'], 'State': 1} for e in cfg['epics']],
                    'ResultCode': 0, 'ResultMessage': ''}
        if op == 'chapterList':
            rows = [c for e in ([epic] if epic else cfg['epics']) for c in epic_chapters(player, e)]
            return {'ServerUtcTime': now_ms(), 'ChapterList': rows, 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'stageList':
            ci = int(payload.get('EpicQuestChapterIndex') or 0)
            rows = [r for e in ([epic] if epic else cfg['epics']) for c in e['chapters'] if not ci or c['index'] == ci
                    for r in epic_stage_rows(player, e, c)]
            return {'ServerUtcTime': now_ms(), 'StageList': rows, 'RedDotList': [], 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'playStart':
            money = regen_active_point(player)
            money['ActivePoint'] = max(0, money['ActivePoint'] - int(payload.get('UsedActivePoint') or 0)); save(player)
            return {'EpicQuestPlayToken': now_ms(), 'PlayStrikeTime': now_ms(), 'AccountMoney': money, 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'playEnd':
            return epic_end(player, payload)
        if op == 'mopUp':
            return epic_end(player, payload, mopup=True)
    if path.startswith('/api/fighterQuest/') and fq_cfg():
        with open(Path(__file__).resolve().parent / 'fq_debug.jsonl', 'a') as f: f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
        op = path.rsplit('/', 1)[1]; st = fq_state(player)
        if op == 'playList':
            return {'ServerUtcTime': now_ms(), 'PlayList': fq_rows(player), 'PickupPlayList': [], 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'pickupPlayList':
            return {'PickupPlayList': [], 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'playInfo':
            return {'ServerUtcTime': now_ms(), 'PlayInfo': fq_playinfo(player), 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'randomPick':
            # The opponent is another FighterQuestTable row: Scene_Single_FighterQuest.AddLoadMonsterCharacter loads
            # CharacterTable.Find(monsterRow.playerFighterIndex) (Ghidra). Rows are 90000000 + difficulty*1000000 + fighter.
            qi = int(payload.get('FighterQuestIndex') or 0) or (fq_cfg()['quests'][0])
            d, me = (qi - 90000000) // 1000000, qi % 1000000
            opp = [c for c in fq_cfg().get('opponents', []) if c != me] or [me]
            mq = 90000000 + d * 1000000 + random.choice(opp)
            st['Current'] = qi; st['Monster'] = mq; save(player)
            return {'AccountMoney': player['AccountMoney'], 'MonsterFighterQuestIndex': mq, 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'playStart':
            qi = int(payload.get('FighterQuestIndex') or 0); st['Current'] = qi
            save(player)   # guide: Soul Tokens are spent only on a win (fq_end)
            return {'QuestPlayToken': now_ms(), 'DropBossList': [], 'BonusMap': 0, 'Point': int(st['Point']), 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'playEnd':
            return fq_end(player, payload)
        if op == 'fighterQuestMopUp':
            return fq_end(player, payload, mopup=True)
        if op == 'giveUp':
            st['Current'] = 0; save(player)
            return {'Point': int(st['Point']), 'ResultCode': 0, 'ResultMessage': ''}
        if op == 'charge':
            st['Point'] = int((fq_cfg() or {}).get('maxPoint', 10)); save(player)
            return {'ChargeCount': 0, 'AccountMoney': player['AccountMoney'], 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/questEvent/questEventList':
        return questevent_list_response(player)
    if path == '/api/questEvent/questEventOpen':
        return {'Item': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'QuestEventStageList': questevent_stage_rows(player),
                'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/questEvent/questEventStart':
        money = regen_active_point(player)
        money['ActivePoint'] = max(0, money['ActivePoint'] - int(payload.get('UsedActivePoint') or 0))
        save(player)
        out = {'QuestEventPlayToken': now_ms(), 'PlayStrikeTime': now_ms(), 'AccountMoney': money, 'ResultCode': 0, 'ResultMessage': ''}
        si = int(payload.get('QuestEventStageIndex') or payload.get('StageIndex') or 0); ev = questevent_event(si)
        pats = ((ev or {}).get('patterns') or {}).get(str(si))
        if pats:   # random stage (Battle Card Descended): the zone maps/triggers of this run (RandomStagePatternGroupTable row)
            out['RandomStagePatternGroupIndex'] = random.choice(pats)
            fp = Path(__file__).resolve().parent / 'force_pattern.json'   # debugging aid: {"<stage>": <pattern>}
            if fp.exists():
                out['RandomStagePatternGroupIndex'] = int(json.loads(fp.read_text()).get(str(si), out['RandomStagePatternGroupIndex']))
            with open(Path(__file__).resolve().parent / 'questevent_debug.jsonl', 'a') as f:   # which zones a run used
                f.write(json.dumps({'time': now_ms(), 'stage': si, 'pattern': out['RandomStagePatternGroupIndex']}) + chr(10))
        return out
    if path == '/api/questEvent/questEventEnd':
        return questevent_end(player, payload)
    if path == '/api/questEvent/questEventMopUp':
        return questevent_end(player, payload, mopup=True)
    if path == '/api/questEvent/questEventRecharge':
        return {'AccountMoney': player['AccountMoney'], 'QuestEventIndex': int(payload.get('QuestEventIndex') or 0),
                'QuestEventStageIndex': int(payload.get('QuestEventStageIndex') or 0), 'RechargeCount': 0, 'PlayCount': 0,
                'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/character/teamDeckSizeUp':
        # Team slot expansion (UIPopup_ExtraTeamDeck, TeamDeckSizeUpRequest {SizeUpCount}). As an untyped stub the reply had no
        # AccountMoney and RecvTeamDeckSizeUp -> TakeAccountMoney showed AP 0/0, rubies 0, gold 0 (seen live 2026-10-19).
        # Cost per added slot = TEAM_SLOT_COSTS by the current extra size, the same list as ConfigTable 229 value2 that the popup
        # shows (UIPopup_ExtraTeamDeck.GetSizeUpCost; make_data TEAM_SLOT_COSTS), paid in rubies.
        n = max(0, int(payload.get('SizeUpCount') or 0)); extra = int(player.get('TeamDeckExtraSize') or 0)
        n = min(n, max(0, TEAM_SLOT_MAX - extra))
        costs = TEAM_SLOT_COSTS
        cost = sum(costs[min(i, len(costs) - 1)] for i in range(extra, extra + n))
        money = player['AccountMoney']
        if n and int(money['Cash']) >= cost:
            money['Cash'] = int(money['Cash']) - cost; extra += n; player['TeamDeckExtraSize'] = extra; save(player)
        return {'AccountMoney': money, 'TeamDeckExtraSize': {'extraSize': extra}, 'ResultCode': 0, 'ResultMessage': ''}
    if path == '/api/character/teamDeckUpdate':
        # the client sends the whole TeamDeckList (CharacterTeamDeckUpdateRequest); store each deck by DeckNo and echo
        # it back so the team the user built survives a relaunch (was a default reply that discarded it).
        decks = player.setdefault('TeamDeckList', [])
        by_no = {d['DeckNo']: d for d in decks}
        for vo in payload.get('TeamDeckList') or []:
            no = int(vo.get('DeckNo') or 0)
            if not no:
                continue
            row = by_no.get(no)
            if row is None:
                row = {'DeckNo': no}
                decks.append(row); by_no[no] = row
            for f in TEAMDECK_FIELDS:
                if f in vo:
                    row[f] = vo[f]
        decks.sort(key=lambda d: d['DeckNo'])
        save(player)
        return {'TeamDeckList': decks}
    if path == '/api/player/detail':
        # UIView_UserProfile.SendMyProfile -> RecvPlayerDetail reads AccountDetailResponse.FriendCount (FriendCount2 {FriendCount,
        # FriendMaxCount}) without a null check; the default reply left it null (Ghidra 0x181303CC0)
        return {'FriendCount': {'FriendCount': 0, 'FriendMaxCount': 50}}
    if path == '/api/player/detailArenaLeagueInfo':
        # profile LEAGUE tab (UIPage_UserBattleInfo.SetData NREd on the default reply's null sub-messages, probe_throw 0x7ac56a):
        # DetailArenaLeagueInfoResponse {ArenaLeagueTier {Tier, Rating, ArenaLeague}, ArenaLeagueRanking / PowerRanking /
        # PastArenaLeagueRanking (RankingDataRank), ArenaLeagueTeamInfo {TeamPower, CharacterIndex1-3, Grade1-3, Exp1-3, awaken1-3,
        # awakenExp1-3, ex1-3}, ArenaLeagueBestRank}; the league team = team deck 1 (the deck the League uses here)
        st = league_state(player); d = (player.get('TeamDeckList') or [{}])[0]; team = {'TeamPower': int(d.get('TeamPower') or 0)}
        for n in (1, 2, 3):
            c = character(player, int(d.get('CharacterIndex%d' % n) or 0)) or {}
            team.update({'CharacterIndex%d' % n: int(c.get('CharacterIndex') or 0), 'Grade%d' % n: int(c.get('Grade') or 0),
                         'Exp%d' % n: int(c.get('Exp') or 0), 'awaken%d' % n: int(c.get('Awaken') or 0),
                         'awakenExp%d' % n: int(c.get('AwakenExp') or 0), 'ex%d' % n: int(c.get('ex') or 0)})
        return {'ArenaLeagueTier': {'Tier': int(st['Tier']), 'Rating': int(st['Rating']), 'ArenaLeague': 1},
                'ArenaLeagueRanking': league_rank(st), 'PowerRanking': league_rank(st), 'PastArenaLeagueRanking': league_rank(st),
                'ArenaLeagueTeamInfo': team, 'ArenaLeagueBestRank': 1}
    if path == '/api/player/detailAchieveRate':
        # profile RECORDS tab: AchieveRate {StageClearCount, StageMissionCount, CharacterCount, BattleCardCount, TotalGrowPoint}
        # (the client shows each against its own table total). No story stage has missions here and growth points are not
        # tracked, so those two stay 0.
        return {'DetailAchieveRate': {
            'StageClearCount': sum(1 for x in player.get('StageList', []) if int(x.get('BattleResult') or 0) == 1),
            'StageMissionCount': 0, 'CharacterCount': len(player.get('CharacterList', [])),
            'BattleCardCount': len({c.get('BattleCardIndex') for c in player.get('BattleCardList', []) if c.get('BattleCardIndex')}),
            'TotalGrowPoint': 0}}
    if path == '/api/player/profileCharacterSet':
        # 'representative team' (profile team): NetworkManagerWEB.Send_RepresentativeTeamDeckSet sends RepresentativeTeamDeckSetRequest
        # {characterIndex, leaderPower, characterIndex2, characterIndex3, teamDeck (TeamDeckType 55)}; Parse_CharacterTeamDeckUpdate
        # stores the echoed three fighters as team deck <teamDeck> (MyInfo.AddOrUpdateTeamDeck). The default reply echoed zeros.
        g = {k.lower(): v for k, v in payload.items()}
        c = [int(g.get(k) or 0) for k in ('characterindex', 'characterindex2', 'characterindex3')]
        td = int(g.get('teamdeck') or 55); lpow = int(g.get('leaderpower') or 0)
        if c[0]:
            pc = player.setdefault('ProfileCharacter', {})
            pc.update({'CharacterIndex': c[0], 'CharacterIndex2': c[1], 'CharacterIndex3': c[2], 'TeamDeck': td})
            decks = player.setdefault('TeamDeckList', [])
            row = next((d for d in decks if int(d.get('DeckNo') or 0) == td), None)
            if row is None:
                row = {f: (0 if not isinstance(v, str) else '') for f, v in (decks[0] if decks else {}).items()}; row['DeckNo'] = td
                decks.append(row); decks.sort(key=lambda d: d['DeckNo'])
            row.update({'CharacterIndex1': c[0], 'CharacterIndex2': c[1], 'CharacterIndex3': c[2], 'LeaderPower': lpow})
            save(player)
        return {'characterIndex': c[0], 'leaderPower': lpow, 'characterIndex2': c[1], 'characterIndex3': c[2], 'teamDeck': td}
    if path == '/api/player/optionUpdate':
        # OptionUpdateRequest {BattlePoint, OptionInfoList [KeyValueObject {Key, Value}]} -> OptionUpdateResponse {OptionInfoList};
        # kept by Key in player['OptionInfoList'] (sent back at login) - the default reply returned an empty list
        opts = player.setdefault('OptionInfoList', []); by_key = {o.get('Key'): o for o in opts}
        for vo in payload.get('OptionInfoList') or []:
            k = vo.get('Key')
            if not k:
                continue
            if k in by_key: by_key[k]['Value'] = vo.get('Value') or ''
            else:
                by_key[k] = {'Key': k, 'Value': vo.get('Value') or ''}; opts.append(by_key[k])
        save(player)
        return {'OptionInfoList': opts}
    if path == '/api/character/getTeamDeck':
        return {'TeamDeckList': player.get('TeamDeckList', [])}
    if path.startswith('/api/card2/card') and path.rsplit('/', 1)[1] in (
            'cardLevelUp', 'cardSkillUp', 'cardGradeUp', 'cardSell', 'cardLock'):
        return card_route(path, player, payload)
    if path == '/api/player/accountGrowthStatLevelUp':
        # AccountStatLevelUpRequest {StatSpot, AddLevel, ItemList (medals the client priced from AccountStatTable + config 231)}
        # -> {RemainItemList, AccountGrowthStat {StatSpot, StatLevel}}. Checks: known spot, max level, the medals are there.
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        fc = fame_cfg() or {}; spot = int(payload.get('StatSpot') or 0); add = int(payload.get('AddLevel') or 0)
        stats = player.setdefault('AccountGrowthStat', {}); cur = int(stats.get(str(spot), 0))
        want = [(int(u.get('ItemIndex') or 0), int(u.get('Qty') or 0)) for u in payload.get('ItemList') or []]
        inv = {i['ItemIndex']: i for i in items(player)}
        fail = lambda msg: {'RemainItemList': [], 'AccountGrowthStat': {'StatSpot': spot, 'StatLevel': cur}, 'ResultCode': 1, 'ResultMessage': msg}
        if spot not in fc.get('spots', []) or add < 1 or cur + add > int(fc.get('max', 30)):
            return fail('cannot raise this stat further')
        need, err = item_need(payload.get('ItemList'))   # summed, no negative entries (they used to ADD medals)
        if err or not need or item_short(player, need) is not None:
            return fail(err or 'not enough medals')
        changed = take_items(player, payload.get('ItemList'))
        stats[str(spot)] = cur + add
        save(player)
        return {'RemainItemList': changed, 'AccountGrowthStat': {'StatSpot': spot, 'StatLevel': cur + add}}
    if path == '/api/character/stageEntryList':
        # StageEntryListRequest {groupIndex} -> fighters allowed in that mode's Fighter Select (FighterEntryManager.RecvStageEntry).
        # Only Dispatch has a StageEntryListGroupTable row (level-only rule), so: every owned fighter, no strikers.
        return {'CharacterIndexList': [c['CharacterIndex'] for c in player['CharacterList']], 'StrikerIndexList': []}
    if path.startswith('/api/dispatch/'):
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        return dispatch_route(path.rsplit('/', 1)[1], player, payload or {})
    if path in ('/api/card2/cardAwaken', '/api/card2/cardAwakenSkill'):
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        return card_awaken_skill(player, payload) if path.endswith('Skill') else card_awaken(player, payload)
    if path == '/api/card2/cardCombine':
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        return card_combine(player, payload)
    if path == '/api/core/coreInfo':
        ci = int(payload.get('CharacterIndex') or 0)
        return {'CharacterIndex': ci, 'CoreList': unlocked_cores(player).get(str(ci), [])}
    if path in ('/api/core/awakenCoreLevelUp', '/api/core/awakenCoreReset'):
        # AwakenCoreLevelUpRequest {characterIndex, coreIndex, addLevel} -> {awakenCore {coreIndex, coreLevel}, corePoint
        # {characterIndex, corePoint}}; ResetAwakenCoreLevelRequest {characterIndex} -> {accountMoney, corePoint, remainItem}.
        # Points: awaken_core_points (awaken.json corePoint per awaken level); levels capped by coreMax. Reset is free.
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
        g = lambda *ks: next((payload.get(k) for k in ks if payload.get(k) is not None), 0)
        ci = int(g('characterIndex', 'CharacterIndex') or 0); ch = character(player, ci)
        if not ch:
            return {'ResultCode': 1, 'ResultMessage': 'no such character'}
        cores = awaken_cores(player, ci)
        if path.endswith('Reset'):
            cores.clear(); pts = awaken_core_points(player, ch); save(player)
            return {'accountMoney': player['AccountMoney'], 'corePoint': {'characterIndex': ci, 'corePoint': pts},
                    'remainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}, 'ResultCode': 0, 'ResultMessage': ''}
        core = str(int(g('coreIndex', 'awakenCoreIndex', 'CoreIndex') or 0)); add = max(1, int(g('addLevel', 'AddLevel') or 1))
        cap = int(awaken_cfg().get('coreMax', {}).get(core, 0)); cur = int(cores.get(core, 0))
        add = min(add, cap - cur, awaken_core_points(player, ch))
        if cap and add > 0:
            cores[core] = cur + add
        pts = awaken_core_points(player, ch); save(player)
        return {'awakenCore': {'coreIndex': int(core), 'coreLevel': int(cores.get(core, 0))},
                'corePoint': {'characterIndex': ci, 'corePoint': pts}, 'ResultCode': 0 if add > 0 else 1,
                'ResultMessage': '' if add > 0 else 'not enough core points'}
    if path == '/api/core/coreAcquire':
        # request: CharacterIndex, CoreTreeIndex, PreCoreTreeIndex, UsedCost (gold), ItemList (core items used).
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
        ci, tree = int(payload.get('CharacterIndex') or 0), int(payload.get('CoreTreeIndex') or 0)
        ch = character(player, ci)
        nodes = {n[0]: n for n in core_defs().get(str(ci), [])}
        if ch is None or tree not in nodes:
            return {'CharacterIndex': ci, 'AccountMoney': player['AccountMoney'], 'ItemList': [],
                    'CoreList': player.get('Cores', {}).get(str(ci), []),
                    'ResultCode': 1, 'ResultMessage': 'unknown fighter or core'}
        cores = unlocked_cores(player)
        lst = cores.get(str(ci), [])
        # path unlock: the client sends the picked node + CoreTreeCount (nodes on the path) and the summed cost; walk back
        # through the prerequisite links to the first unlocked node (or the root) and open them all
        path_, cur = [], tree
        while cur and cur in nodes and cur not in lst and len(path_) < max(1, int(payload.get('CoreTreeCount') or 1)):
            path_.append(cur); cur = nodes[cur][2]
        lv = level_of(ch) if ch else 0
        ok_path = bool(path_) and (cur == 0 or cur in lst) and ch is not None and all(lv >= nodes[t][1] for t in path_)
        if ch is None or tree not in nodes:
            return {'CharacterIndex': ci, 'AccountMoney': player['AccountMoney'], 'ItemList': [], 'CoreList': lst,
                    'ResultCode': 1, 'ResultMessage': 'unknown fighter or core'}
        if tree in lst:
            return {'CharacterIndex': ci, 'AccountMoney': player['AccountMoney'], 'ItemList': [], 'CoreList': lst}
        if not ok_path:
            return {'CharacterIndex': ci, 'AccountMoney': player['AccountMoney'], 'ItemList': [], 'CoreList': lst,
                    'ResultCode': 1, 'ResultMessage': 'normal level or prerequisite core requirement not met'}
        money = player['AccountMoney']; cost = int(payload.get('UsedCost') or 0)
        err = (item_error(player, payload.get('ItemList')) or ('not enough gold' if not 0 <= cost <= int(money['Gold']) else None)) \
            if ok_path else None   # was: gold clamped at 0, items clamped at 0 (unlock without paying)
        if err:
            return {'CharacterIndex': ci, 'AccountMoney': money, 'ItemList': [], 'CoreList': lst, 'ResultCode': 1, 'ResultMessage': err}
        if ok_path:
            cores[str(ci)] = lst
            lst.extend(reversed(path_))
            money['Gold'] = int(money['Gold']) - cost
            changed = take_items(player, payload.get('ItemList'))
            save(player)
        else:
            changed = []
        return {'CharacterIndex': ci, 'AccountMoney': player['AccountMoney'], 'ItemList': changed, 'CoreList': lst}
    if path == '/api/adventure/seriesList':
        series = json.loads(SERIES_PATH.read_text()) if SERIES_PATH.exists() else [1]
        return {'SeriesList': [{'SeriesIndex': i, 'ProductionFlag': True, 'OpenFlag': True} for i in series]}
    if path == '/api/adventure/sagaList':   # make_data sagas.json: every saga open + intro seen (series unlocks gate progress)
        sp = Path(__file__).resolve().parent / 'sagas.json'
        sagas = json.loads(sp.read_text())['sagas'] if sp.exists() else []
        return {'SagasList': [{'SagaIndex': int(i), 'OpenFlag': True, 'ProductionFlag': True, 'LastPlayStageIndex': 0} for i in sagas]}
    if path == '/api/adventure/sagaProduction':
        return {}
    if path == '/api/adventure/chapterMissionComplete':
        # claim the chapter reward (rubies) once per chapter, when its star missions are done
        ch = int(payload.get('Chapter') or payload.get('ChapterIndex') or 0)
        claimed = player.setdefault('ChapterRewardsClaimed', [])
        money = player['AccountMoney']
        reward = []
        if ch and ch not in claimed:
            claimed.append(ch)
            money['Cash'] += CHAPTER_REWARD_CASH
            reward.append(dict(goods(1, 2, CHAPTER_REWARD_CASH), ContentsIndex=2, ContentsCount=CHAPTER_REWARD_CASH))
            save(player)
        return {'AccountMoney': money, 'RewardItemList': [], 'RewardCharacterList': [], 'RewardBattleCardList': [],
                'ClearRewardList': reward, 'PostSendFlag': False}
    if path == '/api/adventure/stageList':
        fixed = False   # repair rows saved before stage_meta (Hard+ clears were stored as difficulty 1 / series 1)
        for st in player.setdefault('StageList', []):
            ser, ch, d = stage_meta(st['StageIndex'])
            if (st.get('SeriesIndex'), st.get('Chapter'), st.get('StageDifficulty')) != (ser, ch, d):
                st.update({'SeriesIndex': ser, 'Chapter': ch, 'StageDifficulty': d}); fixed = True
        if fixed:
            save(player)
        # STORY rows (original dialogue, added after some battles were already cleared): count a row as read when the
        # stage after it is cleared, so existing progress stays unlocked.
        if STORY_ROWS_PATH.exists():
            stages = player.setdefault('StageList', [])
            index = json.loads(STORY_ROWS_PATH.read_text())
            rows = {r for r, _ in index}
            # STORY rows are numbered YYCC51.. per build; drop records of rows that no longer exist (unknown stage
            # indices in StageList are looked up by the client)
            soul = soul_cfg()['stages']   # Soul Stage rows (index ..90) are kept too
            keep = [s for s in stages if s['StageIndex'] % 100 <= 50 or s['StageIndex'] in rows or str(s['StageIndex']) in soul]
            added = len(keep) != len(stages)
            stages[:] = keep
            done = {s['StageIndex'] for s in stages if s['BattleResult'] == 1}
            for row, nxt in index:
                if row not in done and nxt and nxt in done:
                    stages.append({'SeriesIndex': stage_meta(row)[0], 'Chapter': stage_meta(row)[1], 'StageDifficulty': stage_meta(row)[2],
                                   'StageIndex': row, 'BattleResult': 1, 'PlayCount': 1})
                    done.add(row); added = True
            if added:
                save(player)
        soul_state(player)   # Soul Stage rows: PlayCount = today's plays
        return {'StageList': player.get('StageList', []), 'StageSeriesMissionList': sermis_list(player)}
    if path == '/api/adventure/seriesMissionComplete':
        return sermis_claim(player, payload)
    if path == '/api/adventure/stageStory':
        # a STORY row was read (AdventureStageStoryRequest StageIndex/FirstClearFlag): store it as cleared
        idx = int(payload.get('StageIndex') or 0)
        stages = player.setdefault('StageList', [])
        row = next((s for s in stages if s['StageIndex'] == idx), None)
        first = row is None or row['BattleResult'] != 1
        if idx:
            if row is None:
                row = {'SeriesIndex': stage_meta(idx)[0], 'Chapter': stage_meta(idx)[1], 'StageDifficulty': stage_meta(idx)[2],
                       'StageIndex': idx, 'BattleResult': 0, 'PlayCount': 0}
                stages.append(row)
            row['PlayCount'] += 1
            row['BattleResult'] = 1
        # a first clear always opens the reward popup (Scene_Single_Story.RecvAdventureStageStory_FirstClear 0x18063E640) with the
        # reply's reward lists; empty lists -> UIUnit_CommonReward.SetGoodsData NullReferenceException (player.log 2026-10-23).
        # Same first-clear rubies as a story battle.
        firsts = []
        if idx and first:
            player['AccountMoney']['Cash'] += FIRST_CLEAR_CASH; firsts.append(goods(1, 2, FIRST_CLEAR_CASH))
        if idx:
            save(player)
        return {'StageIndex': idx, 'FirstClearFlag': 1 if first else 0, 'AccountMoney': player['AccountMoney'],
                'FirstClearRewardList': firsts, 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': [],
                'PostSendFlag': False, 'GlobalDropRewardList': [], 'RewardImprintStoneList': []}
    if path == '/api/adventure/stageStart':
        money = regen_active_point(player)
        money['ActivePoint'] = max(0, money['ActivePoint'] - int(payload.get('UsedActivePoint') or 0))
        save(player)
        return {'StagePlayToken': now_ms(), 'PlayStrikeTime': now_ms(), 'AccountMoney': money}
    if path == '/api/adventure/stageEnd':
        # The client looks the stage up again by StageIndex (MyInfo.GetStageData) and throws on 0.
        soul_state(player)   # daily reset of Soul Stage play counts
        idx = int(payload.get('StageIndex') or 0)
        won = int(payload.get('BattleResult') or 0) == 1
        stages = player.setdefault('StageList', [])
        row = next((s for s in stages if s['StageIndex'] == idx), None)
        first = won and (row is None or row['BattleResult'] != 1)
        if idx:
            if row is None:
                row = {'SeriesIndex': stage_meta(idx)[0], 'Chapter': stage_meta(idx)[1], 'StageDifficulty': stage_meta(idx)[2], 'StageIndex': idx,
                       'BattleResult': 0, 'PlayCount': 0}
                stages.append(row)
            row['PlayCount'] += 1
            if won:
                row['BattleResult'] = 1
                # star missions: the client sends the indices it completed this run; keep the best (merge, never unset)
                for k in ('Mission1Index', 'Mission2Index', 'Mission3Index'):
                    v = int(payload.get(k) or 0)
                    if v:
                        row[k] = v
        clear, first_rewards, reward_idx = [], [], set()
        if won:
            # Placeholder reward amounts (originals unknown): gold + account/character exp per win, cash on first clear.
            money = player['AccountMoney']
            gold = STORY_GOLD.get(idx, STAGE_GOLD)
            money['Gold'] += gold
            clear.append(goods(1, 1, gold))
            # account EXP grows with the stage number; Soul Stages (index ..90) count as stage 1 (a win gave 3 ranks, seen live)
            player['PlayerAccount']['Exp'] += STAGE_ACCOUNT_EXP * (1 if str(idx) in soul_cfg()['stages'] else max(1, idx % 100))
            # only the fighters who played (request CharacterList; fall back to team 1)
            played = {int(c.get('CharacterIndex') or 0) for c in payload.get('CharacterList') or []} - {0}
            if not played:
                d = player['TeamDeckList'][0]
                played = {d['CharacterIndex1'], d['CharacterIndex2'], d['CharacterIndex3']} - {0}
            for ch in player['CharacterList']:
                if ch['CharacterIndex'] in played:
                    ch['Exp'] += STAGE_CHARACTER_EXP
            # materials per win (my amounts): 2x EXP Capsule M, 2 evolution materials (random kind; tier by chapter:
            # 1-3 lower, 4-6 middle, 7+ upper) and 5 souls for each fighter who played (limit break).
            inv = {i['ItemIndex']: i for i in items(player)}
            chapter = (idx // 100) % 100
            evo = random.choice(EVO_BASE) + (0 if chapter <= 3 else 1 if chapter <= 6 else 2)
            core = random.choice(CORE_ITEM_BASE) + (0 if chapter <= 3 else 1 if chapter <= 6 else 2)
            gains = [(1001, 2), (evo, 2), (core, 2)] + [(SOUL_BASE + c, 5) for c in sorted(played) if SOUL_BASE + c in inv]
            for no, (iidx, qty) in enumerate(gains, 2):
                inv[iidx]['Qty'] += qty
                clear.append(dict(goods(no, 13, qty), ContentsIndex=iidx, ContentsCount=qty))
            reward_idx = {i for i, _ in gains}
            sc = soul_cfg()['stages'].get(str(idx))
            if sc:   # Soul Event stage: Souls of its fighter (make_data SOUL_DROP)
                si = SOUL_BASE + int(sc['fighter'])
                if si not in inv:
                    inv[si] = {'ItemIndex': si, 'Qty': 0, 'Lock': False}; player['ItemList'].append(inv[si])
                inv[si]['Qty'] += 20; reward_idx.add(si)
                clear.append(dict(goods(len(clear) + 1, 13, 20), ContentsIndex=si, ContentsCount=20))
            if first:
                money['Cash'] += FIRST_CLEAR_CASH
                first_rewards.append(goods(1, 2, FIRST_CLEAR_CASH))
        save(player)
        out = {'StageIndex': idx, 'BattleResult': 1 if won else 0, 'FirstClearFlag': 1 if first else 0,
               'AccountMoney': player['AccountMoney'], 'PlayerAccount': player['PlayerAccount'],
               'CharacterList': [character_simple(c) for c in player['CharacterList']],
               'ClearRewardList': clear, 'FirstClearRewardList': first_rewards,
               'RewardItemList': [i for i in items(player) if i['ItemIndex'] in reward_idx]}
        if str(idx) in soul_cfg()['stages']:   # the client only refreshes its Soul Stage play count from this (seen live: stayed 3/3)
            out['SoulDropEventStage'] = soul_entry(player, str(idx))
        return out
    if path == '/api/character/battleCardEquipUpdate':
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
        req = payload.get('Character') or {}
        ch = character(player, int(req.get('CharacterIndex') or 0))
        if ch is None:
            return {'ResultCode': 1}
        for n in range(1, 9):
            no = int(req.get('BattleCardNo%d' % n) or 0)
            if no:   # a card can sit on one fighter only: take it off anyone else
                for other in player['CharacterList']:
                    for m in range(1, 9):
                        if other is not ch and other.get('BattleCardNo%d' % m) == no:
                            other['BattleCardNo%d' % m] = 0
            ch['BattleCardNo%d' % n] = no
        save(player)
        return {'Character': dict({'CharacterIndex': ch['CharacterIndex']},
                                  **{'BattleCardNo%d' % n: ch['BattleCardNo%d' % n] for n in range(1, 9)})}
    if path == '/api/character/characterLimitBreak':
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
        req = payload.get('Character') or {}
        ch = character(player, int(req.get('CharacterIndex') or 0))
        if ch is None:
            return {'ResultCode': 1}
        # checks (official guide: 30 limit breaks, +1 max level each; fighter / Element / Rainbow / Tier Souls): the step count
        # moves forward and stays <= 30 (6 phases x 5), the souls/items and gold are there
        money = player['AccountMoney']
        # LimitBreakProgressCount = total breaks so far (0..30); LimitBreakGrade = the phase (0..5) (requests: full = 5 / 30)
        cur = int(ch.get('LimitBreakProgressCount', 0))
        ng = int(payload.get('NextLimitBreakGrade') or ch.get('LimitBreakGrade', 0)); npc = int(payload.get('NextLimitBreakProgressCount') or 0)
        nxt = npc
        mats = list(payload.get('SoulItemList') or []) + list(payload.get('LimitBreakItemList') or [])
        fail = lambda msg: {'Character': character_simple6(ch), 'ItemList': [], 'AccountMoney': money, 'ResultCode': 1, 'ResultMessage': msg}
        if not cur < nxt <= 30:
            return fail('cannot limit break further')
        err = item_error(player, mats)   # both lists summed; a negative entry used to lower the need and then ADD items
        if err:
            return fail('not enough souls' if err == 'not enough items' else err)
        if not 0 <= int(payload.get('UsedGold') or 0) <= int(money['Gold']):
            return fail('not enough gold')
        changed = take_items(player, payload.get('SoulItemList')) + take_items(player, payload.get('LimitBreakItemList'))
        money['Gold'] -= int(payload.get('UsedGold') or 0)
        ch['LimitBreakGrade'] = ng
        ch['LimitBreakProgressCount'] = npc
        save(player)
        return {'Character': character_simple6(ch), 'ItemList': changed, 'AccountMoney': money}
    if path == '/api/character/soulDecomposition':
        # CharacterSoulDecompositionRequest {ItemList} -> {AccountMoney, ItemList, Reward*}. Guide: salvaging souls gives Soul
        # Dust (traded at the Soul Dust Exchange). Dust per soul by the fighter's base stars: 1 / 2 / 5 (3/4/5-star; my rate).
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + chr(10))
        stars = {int(k): int(v) for k, v in json.loads(BASE_STARS_PATH.read_text()).items()} if BASE_STARS_PATH.exists() else {}
        inv = {i['ItemIndex']: i for i in items(player)}; money = player['AccountMoney']; changed = []; dust = 0
        # all or nothing, summed per soul (a soul listed twice paid the first entry and silently skipped the rest). The client
        # always sends a fighter's whole stack (Send_CharacterSoulDecomposition: Qty = owned); Soul Lock is what protects souls.
        need, err = item_need(payload.get('ItemList'))
        if err or not need or not all(SOUL_BASE < k < SOUL_BASE + 900 and not inv.get(k, {}).get('Lock') for k in need) or \
                item_short(player, need) is not None:   # Soul Lock (item/lockItem) protects a stack here too
            need = {}
        for k, q in need.items():
            inv[k]['Qty'] = int(inv[k]['Qty']) - q; changed.append(inv[k])
            dust += q * {3: 1, 4: 2}.get(stars.get(k - SOUL_BASE, 5), 5)
        got = []
        if dust:   # paid as the Soul Dust item (the client lists ItemType 18 rewards; GoodsType 33 is never read)
            row = inv.get(SOUL_DUST_ITEM)
            if row is None:
                row = {'ItemIndex': SOUL_DUST_ITEM, 'Qty': 0, 'Lock': False}; player['ItemList'].append(row)
            row['Qty'] = int(row['Qty']) + dust; changed.append(row)
            got = [{'ItemIndex': SOUL_DUST_ITEM, 'Qty': dust, 'Lock': False}]
        save(player)
        return {'AccountMoney': money, 'ItemList': changed, 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': got,
                'RewardImprintStoneList': [], 'PostSendFlag': False, 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                'ResultCode': 0 if changed else 1, 'ResultMessage': '' if changed else 'nothing to salvage'}
    if path in ('/api/character/characterLevelUp', '/api/character/characterGradeUp'):
        with GROWTH_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'path': path, 'payload': payload}) + '\n')
        req = payload.get('Character') or {}
        ch = character(player, int(req.get('CharacterIndex') or 0))
        if ch is None:
            return {'ResultCode': 1}
        money = player['AccountMoney']; gold = int(payload.get('UsedGold') or 0) if path.endswith('characterGradeUp') else 0
        if path.endswith('characterLevelUp'):
            add_exp = payload.get('AddExp')
            cap_exp = exp_for_level(local_progression.normal_level_cap(ch), ch['CharacterIndex'])
            if type(add_exp) is not int or not 1 <= add_exp <= QTY_MAX or ch['Exp'] >= cap_exp:
                return {'ResultCode': 1, 'ResultMessage': 'invalid EXP gain or normal level already at limit',
                        'ItemList': [], 'Character': character_simple(ch), 'AccountMoney': money}
        err = item_error(player, payload.get('ItemList')) or \
            ('not enough gold' if not 0 <= gold <= int(money['Gold']) else None)   # was clamped at 0: evolving with too little gold
        if err:
            return {'ResultCode': 1, 'ResultMessage': err, 'ItemList': [], 'Character': character_simple(ch), 'AccountMoney': money}
        changed = take_items(player, payload.get('ItemList'))
        if path.endswith('characterLevelUp'):
            # request Character.Exp is the exp BEFORE the level-up; AddExp is what the used items give.
            # LevelUpSuccessType 1 Success / 2 BigSuccess (x1.5) / 3 ChoSuccess (x2): multipliers from 2018 guides,
            # rates (10% / 3%) are my assumption. The client plays the matching result + voice.
            roll = random.random()
            kind, mult = (3, 2.0) if roll < 0.03 else (2, 1.5) if roll < 0.13 else (1, 1.0)
            ch['Exp'] = min(ch['Exp'] + int(add_exp * mult), cap_exp)
            save(player)
            return {'LevelUpSuccess': kind, 'ItemList': changed, 'Character': character_simple(ch)}
        money['Gold'] = int(money['Gold']) - gold
        # request Character has the grade BEFORE evolving (its Exp field is always 0). The evolve page previews the SAME
        # level with the higher cap (e.g. 11/30 -> 11/40), so the level is kept: grade +1 only.
        ch['Grade'] = min(6, ch['Grade'] + 1)
        save(player)
        return {'AccountMoney': money, 'ItemList': changed, 'Character': character_simple(ch)}
    return {}


# ---- Missions (/api/quest/{list,reward,rewardAll}; DTOs Quest / QuestRewardResponse / QuestRewardAllResponse from the PC
#      dump). missions.json comes from make_data.py. Progress counters live in player['Missions'] and are bumped by
#      mission_track() after the routes that finish a fight (wrapped around route_overrides below). Daily counters and
#      daily claims reset when the local date changes.
MISSIONS_PATH = Path(__file__).resolve().parent / 'missions.json'
MISSION_WIN_PATHS = {'/api/adventure/stageEnd': 'story_clear', '/api/questEvent/questEventEnd': 'event_clear',
                     '/api/questEvent/crucibleTowerEnd': 'event_clear',
                     '/api/questEvent/buffDungeonEnd': 'event_clear',
                     '/api/epicQuest/playEnd': 'event_clear', '/api/fighterQuest/playEnd': 'duel_win',
                     '/api/arenaLeague/arenaLeagueEnd': 'league_win', '/api/infiniteFight/end': 'infinite_win',
                     '/api/allOutFight/end': 'infinite_win'}
MISSION_PLAY_PATHS = {'/api/relayDungeon/dungeonEnd': 'relay_play', '/api/proveDungeon/stageEnd': 'prove_play'}


DAILY_QUEST_TYPES = (1, 12, 2002)   # QuestType Daily, EventPageMissionDaily, EpicMissionDaily (reset at local midnight)
WEEKLY_QUEST_TYPES, MONTHLY_QUEST_TYPES = (101,), (102,)   # QuestType Weekly / Monthly (own counters '<stat>_week' / '_month')


def mission_key(m):
    t = int(m['type'])
    return m['stat'] + ('_week' if t in WEEKLY_QUEST_TYPES else '_month' if t in MONTHLY_QUEST_TYPES else '')


def missions_cfg():
    return json.loads(MISSIONS_PATH.read_text()) if MISSIONS_PATH.exists() else []


def missions_state(player):
    st = player.setdefault('Missions', {})
    st.setdefault('Counts', {}); st.setdefault('Claimed', {})
    today = time.strftime('%Y-%m-%d')
    if st.get('Day') != today:   # daily reset
        st['Day'] = today
        st['Counts'] = {k: v for k, v in st['Counts'].items() if k.endswith('_total')}
        daily = {str(m['index']) for m in missions_cfg() if m['type'] in DAILY_QUEST_TYPES}
        st['Claimed'] = {k: v for k, v in st['Claimed'].items() if k not in daily}
    for key, period, types, suffix in (('Week', str(team_week()), WEEKLY_QUEST_TYPES, '_week'),
                                       ('Month', time.strftime('%Y-%m'), MONTHLY_QUEST_TYPES, '_month')):
        if st.get(key) != period:   # weekly / monthly reset of their counters and claims
            st[key] = period
            st['Counts'] = {k: v for k, v in st['Counts'].items() if not k.endswith(suffix)}
            ids = {str(m['index']) for m in missions_cfg() if m['type'] in types}
            st['Claimed'] = {k: v for k, v in st['Claimed'].items() if k not in ids}
    return st


def mission_bump(player, stat, n=1):
    team_add(player, stat, n)   # Team Event activity points
    carnival_add(player, stat, n)   # Carnival points
    st = missions_state(player)
    for k in (stat, stat + '_total', stat + '_week', stat + '_month'):
        st['Counts'][k] = int(st['Counts'].get(k, 0)) + n


def quest_row(m, st):
    t = now_ms(); claimed = st['Claimed'].get(str(m['index']), 0)
    key = mission_key(m)
    done = min(int(st['Counts'].get(key, 0)), int(m['target']))
    # dailies expire at the next local midnight (the row shows "<n>h <m>m left"); achievements never expire
    # (ExpireTime 0 = no "<n>d left" line: a far date showed "26737d left", seen live 2026-10-18)
    tm = time.localtime(); end = (time.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday + 1, 0, 0, 0, 0, 0, -1)) * 1000
                                  if m['type'] in DAILY_QUEST_TYPES else (int(team_week()) + 7 * 86400) * 1000
                                  if m['type'] in WEEKLY_QUEST_TYPES else month_end_ms() if m['type'] in MONTHLY_QUEST_TYPES else 0)
    return {'QuestIndex': m['index'], 'QuestType': m['type'], 'CompleteCount': int(m['target']), 'ProcessCount': done,
            'AccumulateCount': done, 'UpdateTime': t, 'CreateTime': t, 'RewardGiveTime': int(claimed), 'ExpireTime': int(end),
            'RepeatCycle': 0, 'RepeatCount': 0, 'FestivalEventIndex': 0, 'EpicOpenTermStageIndex': 0, 'EpicEpisodeIndex': int(m.get('episode', 0)),
            'EpicChapterIndex': int(m.get('chapter', 0)), 'QuestCountType': 0, 'RandomTermsType': 0, 'RandomTermsValue': 0}


# ---- Growth Mission (QuestType 3000; make_data growth.json). Levels open in order (a level opens when the previous level's
#      all-clear quest is claimed), pages open in order (page k+1 when page k's all-clear is claimed). Only opened pages get
#      quest rows: the client reads a quest without a row as NotStarted (locked). Mission progress = Missions counters
#      (*_total, mission_track) or a save check (state:...). Claims share Missions['Claimed'] (never reset: not daily).
GROWTH_PATH = Path(__file__).resolve().parent / 'growth.json'
GROWTH_TRACK = {'/api/character/characterLevelUp': 'fighter_levelup', '/api/character/characterGradeUp': 'fighter_evolve',
                '/api/character/characterLimitBreak': 'fighter_limitbreak', '/api/core/coreAcquire': 'core_acquire',
                '/api/character/awaken': 'fighter_awaken', '/api/character/imprintEquip': 'imprint_equip',
                '/api/imprint/enchant': 'imprint_enchant', '/api/character/battleCardEquipUpdate': 'card_equip',
                '/api/card2/cardLevelUp': 'card_levelup', '/api/card2/cardSkillUp': 'card_skillup',
                '/api/card2/cardGradeUp': 'card_evolve', '/api/card2/cardAwaken': 'card_awaken'}


def growth_cfg():
    return json.loads(GROWTH_PATH.read_text()) if GROWTH_PATH.exists() else {'questType': 3000, 'levels': []}


def growth_stat(player, st, stat):
    if stat == 'state:account_level':
        return int(player.get('LastAccountLevel') or 1)
    if stat == 'state:fighter_level':
        return max((level_of(c) for c in player['CharacterList']), default=1)
    if stat == 'state:card_level':
        path = Path(__file__).with_name('cardlevel.json')
        rows = json.loads(path.read_text())['rowExp'] if path.exists() else []
        return max((1 + sum(1 for e in rows if int(e) <= int(c.get('Exp', 0))) for c in player.get('BattleCardList', [])), default=1)
    return int(st['Counts'].get(stat, 0))


def growth_quests(player):
    """{questIndex: (done, need, reward)} for every opened growth quest, in level/page order."""
    st = missions_state(player); claimed = st['Claimed']; out = {}
    for lv in growth_cfg()['levels']:
        if lv['open'] and not claimed.get(str(lv['open'])):
            break
        for n, pg in enumerate(lv['pages']):   # the last page's all-clear is the level all-clear (lv['final'])
            if n and not claimed.get(str(lv['pages'][n - 1]['clear'])):
                break
            got = 0
            for ms in pg['missions']:
                out[ms['index']] = (min(growth_stat(player, st, ms['stat']), int(ms['target'])), int(ms['target']), ms['reward'])
                got += 1 if claimed.get(str(ms['index'])) else 0
            out[pg['clear']] = (got, len(pg['missions']), pg['reward'])
    return out


def growth_rows(player):
    st = missions_state(player); t = now_ms(); qt = int(growth_cfg().get('questType', 3000))
    return [{'QuestIndex': qi, 'QuestType': qt, 'CompleteCount': need, 'ProcessCount': done, 'AccumulateCount': done, 'UpdateTime': t,
             'CreateTime': t, 'RewardGiveTime': int(st['Claimed'].get(str(qi), 0)), 'ExpireTime': 0, 'RepeatCycle': 0,
             'RepeatCount': 0, 'FestivalEventIndex': 0, 'EpicOpenTermStageIndex': 0, 'EpicEpisodeIndex': 0, 'EpicChapterIndex': 0,
             'QuestCountType': 0, 'RandomTermsType': 0, 'RandomTermsValue': 0} for qi, (done, need, _rw) in growth_quests(player).items()]


def growth_claim(player, idx):
    """Claim one opened, finished growth quest -> (rewards RewardContents, item rows) or None."""
    q = growth_quests(player).get(idx)
    st = missions_state(player)
    if not q or st['Claimed'].get(str(idx)) or q[0] < q[1]:
        return None
    st['Claimed'][str(idx)] = now_ms(); rw = q[2]; money = player['AccountMoney']; rew, got = [], []
    if rw.get('gold'):
        money['Gold'] += int(rw['gold']); rew.append(goods(len(rew) + 1, 1, int(rw['gold'])))
    if rw.get('ruby'):
        money['Cash'] += int(rw['ruby']); rew.append(goods(len(rew) + 1, 2, int(rw['ruby'])))
    inv = {i['ItemIndex']: i for i in items(player)}
    for ix, qty in rw.get('items', []):
        ix, qty = int(ix), int(qty)
        if ix not in inv:
            inv[ix] = {'ItemIndex': ix, 'Qty': 0, 'Lock': False}; player.setdefault('ItemList', []).append(inv[ix])
        inv[ix]['Qty'] += qty; got.append(inv[ix])
        rew.append(dict(goods(len(rew) + 1, 13, qty), ContentsIndex=ix, ContentsType=1, ContentsCount=qty))
    return rew, got


def pay_reward(player, rw):
    """Pay {'gold', 'ruby', 'items': [[index, qty]]} -> (RewardContents list, changed Item rows)."""
    money = player['AccountMoney']; rew, got = [], []
    if rw.get('gold'):
        money['Gold'] += int(rw['gold']); rew.append(goods(len(rew) + 1, 1, int(rw['gold'])))
    if rw.get('ruby'):
        money['Cash'] += int(rw['ruby']); rew.append(goods(len(rew) + 1, 2, int(rw['ruby'])))
    inv = {i['ItemIndex']: i for i in items(player)}
    for ix, qty in rw.get('items', []):
        ix, qty = int(ix), int(qty)
        if ix not in inv:
            inv[ix] = {'ItemIndex': ix, 'Qty': 0, 'Lock': False}; player.setdefault('ItemList', []).append(inv[ix])
        inv[ix]['Qty'] += qty
        if inv[ix] not in got:
            got.append(inv[ix])
        rew.append(dict(goods(len(rew) + 1, 13, qty), ContentsIndex=ix, ContentsType=1, ContentsCount=qty))
    return rew, got


# ---- Super Mission (make_data supermission.json): courses start in order (course 1 on first sight, course n when course
#      n-1's All Clear quest is claimed) and stay open activeDays; day d's missions open at start + (d-1) days.
SUPER_PATH = Path(__file__).resolve().parent / 'supermission.json'
DAY_MS = 86400000


def super_cfg():
    return json.loads(SUPER_PATH.read_text()) if SUPER_PATH.exists() else {'activeDays': 60, 'courses': []}


def super_state(player):
    st = player.setdefault('SuperMission', {}); st.setdefault('Start', {}); st.setdefault('Claimed', {})
    prev_final = None
    for c in super_cfg()['courses']:
        k = str(c['index'])
        if k not in st['Start']:
            if prev_final and not st['Claimed'].get(str(prev_final)):
                break
            st['Start'][k] = now_ms()
        prev_final = c['final']
    return st


def super_open_data(player):
    st = super_state(player); cfg = super_cfg(); now = now_ms(); out = []
    for c in cfg['courses']:
        start = st['Start'].get(str(c['index']))
        end = (start or 0) + int(cfg['activeDays']) * DAY_MS
        if start and now < end and not st['Claimed'].get(str(c['final'])):
            out.append({'superMissionIndex': c['index'], 'createTime': start, 'expireTime': end})
    return out


def super_quests(player, idx):
    """{questIndex: (done, need, reward, opens_at)} for one course."""
    st = super_state(player); mst = missions_state(player); cl = st['Claimed']
    c = next((x for x in super_cfg()['courses'] if x['index'] == idx), None); out = {}
    start = st['Start'].get(str(idx)) if c else None
    if not start:
        return out
    days_done = 0
    for d in c['days']:
        opens = start + (int(d['day']) - 1) * DAY_MS; got = 0
        for ms in d['missions']:
            out[ms['index']] = (min(growth_stat(player, mst, ms['stat']), int(ms['target'])), int(ms['target']), ms['reward'], opens)
            got += 1 if cl.get(str(ms['index'])) else 0
        out[d['clear']] = (got, len(d['missions']), d['reward'], opens)
        days_done += 1 if cl.get(str(d['clear'])) else 0
    out[c['final']] = (days_done, len(c['days']), c['reward'], start)
    return out


def super_route(op, player, payload):
    idx = int(payload.get('superMissionIndex') or 0); st = super_state(player); now = now_ms()
    start = st['Start'].get(str(idx), 0); end = start + int(super_cfg()['activeDays']) * DAY_MS
    if op == 'questList':
        save(player)
        return {'superMissionQuestList': [
            {'superMissionIndex': idx, 'superMissionQuestIndex': qi, 'processCount': done, 'completeCount': need, 'updateTime': now,
             'createTime': start, 'rewardGiveTime': int(st['Claimed'].get(str(qi), 0)), 'expireTime': end}
            for qi, (done, need, _rw, _op) in super_quests(player, idx).items()]}
    if op == 'reward':
        before = {d['superMissionIndex'] for d in super_open_data(player)}
        rew, got = [], []
        for qi in payload.get('superMissionQuestIndexList') or []:
            q = super_quests(player, idx).get(int(qi))
            if not q or st['Claimed'].get(str(qi)) or q[0] < q[1] or now < q[3]:
                continue
            st['Claimed'][str(qi)] = now
            r, g = pay_reward(player, q[2]); rew += r; got += [i for i in g if i not in got]
        opened = [d for d in super_open_data(player) if d['superMissionIndex'] not in before]   # next course
        save(player)
        return {'PlayerAccount': player['PlayerAccount'], 'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'RewardItemList': got, 'RewardImprintStoneList': [], 'PostSendFlag': False,
                'AccountLevelUpRewardList': [], 'RewardList': rew, 'SuperMissionList': opened, 'presetCharacterReward': [],
                'presetCharacterCoreReward': [], 'ResultCode': 0 if rew else 1, 'ResultMessage': '' if rew else 'nothing to claim'}
    return {}


# ---- Battle Pass (make_data pass.json): rolling seasons of `days` from the first visit (continueNextSeason); pass EXP from
#      claimed daily missions; both special tracks unlocked (their real-money packages cannot be bought offline).
PASS_PATH = Path(__file__).resolve().parent / 'pass.json'


def pass_cfg():
    return json.loads(PASS_PATH.read_text()) if PASS_PATH.exists() else None


def pass_state(player):
    cfg = pass_cfg(); st = player.setdefault('BattlePass', {}); now = now_ms()
    if not cfg:
        return st
    per = int(cfg['days']) * DAY_MS
    if not st.get('Start'):
        st.update({'Start': now, 'Exp': 0, 'Normal': 0, 'Special1': 0, 'Special2': 0, 'Period': 1})
    while now >= int(st['Start']) + per:   # new season: progress resets
        st.update({'Start': int(st['Start']) + per, 'Exp': 0, 'Normal': 0, 'Special1': 0, 'Special2': 0,
                   'Period': int(st.get('Period', 1)) + 1})
    return st


def pass_info(player):
    cfg = pass_cfg(); st = pass_state(player)
    return {'passIndex': int(cfg['index']), 'startTime': int(st['Start']), 'endTime': int(st['Start']) + int(cfg['days']) * DAY_MS,
            'rewardPassExp': int(st['Normal']), 'specialRewardExp': int(st['Special1']), 'specialRewardExp02': int(st['Special2']),
            'periodCount': int(st['Period']), 'passExp': int(st['Exp']), 'passAuthority': 1, 'passAuthority02': 1, 'status': 1}


def pass_web_list(player):
    if not pass_cfg():
        return []
    i = pass_info(player)
    return [{'passIndex': i['passIndex'], 'startTime': i['startTime'], 'endTime': i['endTime'], 'periodCount': i['periodCount'], 'status': 1}]


def pass_add_exp(player, n):
    if pass_cfg():
        st = pass_state(player); st['Exp'] = int(st['Exp']) + int(n)


def pass_route(op, player, payload):
    cfg = pass_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no pass'}
    if op == 'info':
        save(player)
        return {'passInfo': pass_info(player), 'ShopGoodsQtyList': []}
    if op == 'reward':
        st = pass_state(player); exp = int(st['Exp']); rew, got = [], []
        for key, track in (('Normal', 'normal'), ('Special1', 'special1'), ('Special2', 'special2')):
            for tier in cfg['tiers']:
                if int(st[key]) < int(tier['exp']) <= exp:
                    r, g = pay_reward(player, tier[track]); rew += r; got += [i for i in g if i not in got]
            st[key] = max([int(st[key])] + [int(tr['exp']) for tr in cfg['tiers'] if int(tr['exp']) <= exp])
        save(player)
        return {'passInfo': pass_info(player), 'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [],
                'RewardBattleCardList': [], 'RewardItemList': got, 'RewardImprintStoneList': [], 'RewardCurrencyList': rew,
                'PostSendFlag': False, 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
                'ResultCode': 0 if rew else 1, 'ResultMessage': '' if rew else 'nothing to claim'}
    return {}


# ---- Lucky Roulette (make_data roulette.json): event/rouletteInfo / roulettePlay / rouletteRewardSlot / rouletteRewardBonus.
#      State player['Roulette'] = {Slots: [[type, index, qty] x3], Day, Plays}. Prizes rolled by weight (/10000).
ROULETTE_PATH = Path(__file__).resolve().parent / 'roulette.json'


def roulette_cfg():
    return json.loads(ROULETTE_PATH.read_text()) if ROULETTE_PATH.exists() else None


def roulette_state(player):
    st = player.setdefault('Roulette', {}); st.setdefault('Slots', [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
    if st.get('Day') != _today():
        st['Day'] = _today(); st['Plays'] = 0
    return st


def roulette_slot(cfg, st):
    s = st['Slots']; out = {'RouletteIndex': int(cfg['index']), 'PlayCount': int(st.get('Plays', 0))}
    for n in range(3):
        out['ItemType%d' % (n + 1)], out['ItemIndex%d' % (n + 1)], out['ItemQty%d' % (n + 1)] = s[n]
    return out


def roulette_pay(player, items_):
    rw = {'gold': 0, 'ruby': 0, 'items': []}
    for ty, ix, q in items_:
        if ty == 1: rw['gold'] += q
        elif ty == 2: rw['ruby'] += q
        elif ty == 13: rw['items'].append([ix, q])
    return pay_reward(player, rw)


def roulette_route(op, player, payload):
    cfg = roulette_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no roulette'}
    st = roulette_state(player)
    if op == 'rouletteInfo':
        # the client takes price / daily limit / bonuses from this message, not from RouletteScheduleTable (TakeRouletteData)
        ev = dict(roulette_slot(cfg, st), EventStartTime=1600000000000, EventEndTime=4102444800000, EventRewardEndTime=4102444800000, EventUrl=0,
                  RouletteDoubleBonus=int(cfg['double']), RouletteTripleBonus=int(cfg['triple']), RouletteNeedItemType=2, RouletteNeedItemIndex=0,
                  RouletteNeedItemValue=int(cfg['price']), LimitDailyPlayRoulette=int(cfg['daily']), RouletteNeedItemType2=0,
                  RouletteNeedItemIndex2=0, RouletteNeedItemValue2=0, RouletteBingoType=0, ShopMoveTargetList='', CraftMoveTargetList='',
                  RewardPreset1=0, RewardPreset2=0, RewardPreset3=0)
        return {'RouletteInfo': ev, 'TicketDropInfoList': [], 'ShortCutButtonOnOff': 0,
                'RouletteRewardList': [{'RouletteRewardIndex': n, 'RouletteRewardItemType': ty, 'RouletteRewardItemIndex': ix,
                                        'RouletteRewardItemValue': v, 'rewardPreset': 0} for n, (ty, ix, _w, v) in enumerate(cfg['prizes'], 1)]}
    if op == 'roulettePlay':
        # Classic wheel (RouletteBingoType 0): Parse_EventRoulettePlay finds the RewardList prize among the wheel items, the
        # wheel stops there (UIUnit_Roulette.GoRoulette(lastPickSlot)) and the prize is paid now; the 3-slot board is type 1.
        money = player['AccountMoney']; st['Slots'] = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        if int(st['Plays']) >= int(cfg['daily']) or int(money.get('Cash', 0)) < int(cfg['price']):
            return {'ResultCode': 1, 'ResultMessage': 'cannot spin', 'RouletteIndex': cfg['index'], 'RouletteSlot': roulette_slot(cfg, st)}
        money['Cash'] = int(money['Cash']) - int(cfg['price'])
        ty, ix, _w, v = random.choices(cfg['prizes'], weights=[p[2] for p in cfg['prizes']])[0]
        rew, got = roulette_pay(player, [[ty, ix, v]]); st['Plays'] = int(st['Plays']) + 1
        save(player)
        return {'RouletteIndex': cfg['index'], 'RouletteSlot': roulette_slot(cfg, st), 'ItemList': got, 'AccountMoney': money,
                'PlayCount': st['Plays'], 'RewardList': rew, 'AdsList': []}
    if op == 'rouletteRewardSlot':
        n = int(payload.get('SlotNo') or 0) - 1
        if 0 <= n < 3 and st['Slots'][n][0]:
            roulette_pay(player, [st['Slots'][n]]); st['Slots'][n] = [0, 0, 0]; save(player)
        return {'RouletteSlot': roulette_slot(cfg, st)}
    if op == 'rouletteRewardBonus':
        s = st['Slots']
        if all(x[0] for x in s):
            keys = [(x[0], x[1], x[2]) for x in s]; pay = []
            for k in keys:
                same = keys.count(k)
                mult = int(cfg['triple']) if same == 3 else int(cfg['double']) if same == 2 else 1
                pay.append([k[0], k[1], k[2] * mult])
            roulette_pay(player, pay); st['Slots'] = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]; save(player)
        return {'RouletteSlot': roulette_slot(cfg, st)}
    return {}


def roulette_schedules():
    cfg = roulette_cfg()
    return [{'RouletteIndex': cfg['index'], 'EventStartTime': 1600000000000, 'EventEndTime': 4102444800000,
             'EventRewardEndTime': 4102444800000}] if cfg else []


# ---- Lucky Chance (make_data luckychance.json): luckyChance/info / play / boardRefresh. State player['LuckyChance'] =
#      {Page, Won: [[page, slotIndex, repeat, type, time]], Repeat}. A play opens one remaining slot of the page by weight;
#      the special slot (type 1) clears the page -> next page (the last page repeats: its wins are cleared, Repeat + 1).
LUCKY_PATH = Path(__file__).resolve().parent / 'luckychance.json'


def month_end_ms():
    """Start of next local calendar month in ms (rolling monthly 'season' for events whose end shows as a countdown)."""
    tm = time.localtime()
    return int(time.mktime((tm.tm_year + (tm.tm_mon == 12), tm.tm_mon % 12 + 1, 1, 0, 0, 0, 0, 0, -1)) * 1000)


def lucky_cfg():
    return json.loads(LUCKY_PATH.read_text()) if LUCKY_PATH.exists() else None


def lucky_state(player):
    st = player.setdefault('LuckyChance', {}); st.setdefault('Page', 1); st.setdefault('Won', []); st.setdefault('Repeat', 0)
    return st


def lucky_info(cfg, st):
    last = len(cfg['pages'])
    return {'luckyChanceIndex': int(cfg['index']), 'luckyChancePage': int(st['Page']), 'completeFlag': False, 'boardResetFlag': False,
            'expireTime': month_end_ms(), 'reddot': False, 'boardType': 0, 'boardCount': 0}


def lucky_rewards(cfg, st):
    return [{'luckyChanceIndex': int(cfg['index']), 'luckyChancePage': w[0], 'luckyChancePageRewardGroupIndex': w[1], 'repeatCount': w[2],
             'rewardType': w[3], 'rewardGiveTime': w[4]} for w in st['Won']]


def lucky_route(op, player, payload):
    cfg = lucky_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no lucky chance'}
    st = lucky_state(player)
    if op in ('info', 'boardRefresh'):
        return {'LuckyChanceInfo': lucky_info(cfg, st), 'LuckyChanceRewardList': lucky_rewards(cfg, st)}
    if op == 'play':
        money = player['AccountMoney']; page = next(p for p in cfg['pages'] if p['page'] == int(st['Page']))
        won = {w[1] for w in st['Won'] if w[0] == page['page']}
        left = [s for s in page['slots'] if s['index'] not in won]
        if not left or int(money.get('Cash', 0)) < int(cfg['price']):
            return {'ResultCode': 1, 'ResultMessage': 'cannot play', 'LuckyChanceInfo': lucky_info(cfg, st)}
        money['Cash'] = int(money['Cash']) - int(cfg['price'])
        pick = random.choices(left, weights=[s['weight'] for s in left])[0]
        row = [page['page'], pick['index'], int(st['Repeat']), pick['type'], now_ms()]
        st['Won'].append(row); rew, got = pay_reward(player, pick['reward'])
        if pick['type'] == 1:   # special prize: page cleared
            if page.get('repeat'):
                st['Won'] = [w for w in st['Won'] if w[0] != page['page']]; st['Repeat'] = int(st['Repeat']) + 1
            else:
                st['Page'] = int(st['Page']) + 1
        save(player)
        sel = {'luckyChanceIndex': int(cfg['index']), 'luckyChancePage': row[0], 'luckyChancePageRewardGroupIndex': row[1],
               'repeatCount': row[2], 'rewardType': row[3], 'rewardGiveTime': row[4]}
        return {'LuckyChanceInfo': lucky_info(cfg, st), 'LuckyChanceRewardList': lucky_rewards(cfg, st), 'SelectLuckyChanceReward': sel,
                'AccountMoney': money, 'ItemList': [], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': got,
                'RewardImprintStoneList': [], 'PostSendFlag': False, 'presetCharacterList': [], 'presetCharacterCoreList': []}
    return {}


# ---- Bingo (make_data bingo.json): squares are QuestType 6 missions (claimed through quest/reward: pays the square's small
#      reward and marks the square); lines / counts / final are claimed with bingo/reward and go to the mailbox, as the
#      client's popup says (System.V_Roulette.RewardSendPost). Claimed lines in player['Bingo']['Lines'].
BINGO_PATH = Path(__file__).resolve().parent / 'bingo.json'


def bingo_cfg():
    return json.loads(BINGO_PATH.read_text()) if BINGO_PATH.exists() else None


def bingo_quests(player):
    cfg = bingo_cfg()
    if not cfg:
        return {}
    mst = missions_state(player)
    return {q['index']: (min(growth_stat(player, mst, q['stat']), int(q['target'])), int(q['target']), q.get('reward') or {})
            for q in cfg['squares']}


def bingo_rows(player):
    st = missions_state(player); t = now_ms()
    return [{'QuestIndex': qi, 'QuestType': 6, 'CompleteCount': need, 'ProcessCount': done, 'AccumulateCount': done, 'UpdateTime': t,
             'CreateTime': t, 'RewardGiveTime': int(st['Claimed'].get(str(qi), 0)), 'ExpireTime': 0, 'RepeatCycle': 0, 'RepeatCount': 0,
             'FestivalEventIndex': 0, 'EpicOpenTermStageIndex': 0, 'EpicEpisodeIndex': 0, 'EpicChapterIndex': 0, 'QuestCountType': 0,
             'RandomTermsType': 0, 'RandomTermsValue': 0} for qi, (done, need, _r) in bingo_quests(player).items()]


def bingo_info(player):
    cfg = bingo_cfg(); st = player.setdefault('Bingo', {}); st.setdefault('Lines', [])
    done = len(st['Lines']) >= len(cfg['rewards'])
    return {'bingoIndex': int(cfg['index']), 'expireTime': month_end_ms(), 'bingoStatus': 1 if done else 0, 'reddot': 0}


def bingo_route(op, player, payload):
    cfg = bingo_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no bingo'}
    st = player.setdefault('Bingo', {}); st.setdefault('Lines', [])
    lines = lambda: [{'bingoIndex': int(cfg['index']), 'bingoRewardIndex': k} for k in st['Lines']]
    if op in ('info', 'rewardHistory', 'nextBingo'):
        return {'BingoInfo': bingo_info(player), 'QuestList': bingo_rows(player), 'BingoRewardList': lines()}
    if op == 'reward':
        k = int(payload.get('bingoRewardIndex') or 0); rw = next((r for r in cfg['rewards'] if r['index'] == k), None)
        claimed = missions_state(player)['Claimed']
        cleared = {q['slot'] for q in cfg['squares'] if claimed.get(str(q['index']))}
        ok = rw and k not in st['Lines'] and (
            (rw['type'] in (1, 2, 3) and set(rw['values']) <= cleared) or
            (rw['type'] == 4 and len(st['Lines']) >= int(rw['values'][0])) or
            (rw['type'] == 5 and len(st['Lines']) >= len(cfg['rewards']) - 1))
        if not ok:
            return {'ResultCode': 1, 'ResultMessage': 'line not complete', 'BingoInfo': bingo_info(player), 'BingoRewardList': lines()}
        st['Lines'].append(k); post_reward(player, rw['reward'], 'Bingo reward.'); save(player)   # client: 'Reward Send Post'
        return {'BingoInfo': bingo_info(player), 'BingoRewardList': lines(), 'AccountMoney': player['AccountMoney'],
                'RewardItemList': [], 'RewardList': []}
    return {}


def bingo_lobby(player):
    return [bingo_info(player)] if bingo_cfg() else []


# ---- Dice Mini-game (make_data dice.json): diceMiniGame/info + play. State player['Dice'] = {Pos 1..size, Laps, Charge,
#      ChargeDay, Stacks {slot: n}}. TicketType 2 = Dice Points (item), 3 = rubies (limit per day). Passing START = lap + 1
#      (lap reward, every stack square +1 up to its max); a Double square moves again by the same roll (DiceResult No 2).
#      Rewards go to the mailbox (the client's reward popup says 'Reward Send Post'); RewardContentsList only feeds the
#      popups: Reason = DiceResult No (1, 2) for square rewards, 0 for the lap reward (Model_DiceGame.GetRewardList).
#      Laps past the last DiceCompleteRewardTable row repeat the last lap reward (client text CompletRewardRepeat).
#      Dice Points arrive by mail (welcome + daily, see mailbox).
DICE_PATH = Path(__file__).resolve().parent / 'dice.json'


def dice_cfg():
    return json.loads(DICE_PATH.read_text()) if DICE_PATH.exists() else None


def dice_state(player, cfg):
    st = player.setdefault('Dice', {}); st.setdefault('Pos', 1); st.setdefault('Laps', 0); st.setdefault('Stacks', {})
    if st.get('ChargeDay') != _today():
        st['ChargeDay'] = _today(); st['Charge'] = 0
    for s in cfg['slots']:
        if s['type'] == 3: st['Stacks'].setdefault(str(s['slot']), 1)
    return st


def dice_info(cfg, st):
    return ({'DiceIndex': int(cfg['index']), 'UserSlotNumber': int(st['Pos']), 'FreeTicket': 0, 'ChargeCount': int(st['Charge']),
             'ContinueCount': int(st['Laps'])},
            [{'DiceIndex': int(cfg['index']), 'SlotType': 3, 'SlotNumber': int(k), 'EffectCount': int(v)} for k, v in st['Stacks'].items()])


def dice_route(op, player, payload):
    cfg = dice_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no dice game'}
    st = dice_state(player, cfg); t = now_ms()
    if op == 'info':
        info, slots = dice_info(cfg, st); save(player)
        return {'ServerUtcTime': t, 'DiceInfo': info, 'DiceSlotInfoList': slots}
    if op != 'play':
        return {}
    money = player['AccountMoney']; inv = {i['ItemIndex']: i for i in items(player)}; it = inv.get(int(cfg['item']))
    if int(payload.get('TicketType') or 2) == 3:
        if int(st['Charge']) >= int(cfg['rubyLimit']) or int(money.get('Cash', 0)) < int(cfg['ruby']):
            return {'ResultCode': 1, 'ResultMessage': 'cannot roll'}
        money['Cash'] = int(money['Cash']) - int(cfg['ruby']); st['Charge'] = int(st['Charge']) + 1
    else:
        if not it or int(it['Qty']) < int(cfg['points']):
            return {'ResultCode': 1, 'ResultMessage': 'not enough dice points'}
        it['Qty'] = int(it['Qty']) - int(cfg['points'])
    roll = random.randint(1, 6); size = int(cfg['size']); slots = {s['slot']: s for s in cfg['slots']}
    results, rewards = [], []
    def pay(rw, reason, mult=1):
        rw = {k: (v * mult if k in ('gold', 'ruby') else [[i, q * mult] for i, q in v]) for k, v in rw.items()}
        post_reward(player, rw, 'Dice Mini-game reward.')
        if rw.get('gold'): rewards.append(dict(goods(0, 1, int(rw['gold'])), Reason=reason))
        if rw.get('ruby'): rewards.append(dict(goods(0, 2, int(rw['ruby'])), Reason=reason))
        for ix, q in rw.get('items', []):
            rewards.append(dict(goods(0, 13, int(q)), Reason=reason, ContentsIndex=int(ix), ContentsType=1))
    for no in (1, 2):
        pos = int(st['Pos']) + roll
        if pos > size:
            pos -= size; st['Laps'] = int(st['Laps']) + 1
            laps = sorted(cfg['laps'], key=lambda l: l['lap'])
            lap = next((l for l in laps if l['lap'] == st['Laps']), laps[-1] if laps else None)
            if lap: pay(lap['reward'], 0)
            for s in cfg['slots']:
                if s['type'] == 3: st['Stacks'][str(s['slot'])] = min(int(s['max']), int(st['Stacks'][str(s['slot'])]) + 1)
        st['Pos'] = pos; sl = slots[pos]; eff = 1
        if sl['type'] == 3:
            eff = int(st['Stacks'][str(pos)]); st['Stacks'][str(pos)] = 1
        if sl['reward']: pay(sl['reward'], no, eff)
        results.append({'No': no, 'SlotType': int(sl['type']), 'SlotNumber': pos, 'EffectCount': eff})
        if sl['type'] != 2:
            break
    for i, r in enumerate(rewards, 1): r['No'] = i
    info, sinfo = dice_info(cfg, st); save(player)
    return {'ServerUtcTime': t, 'AccountMoney': money, 'DiceInfo': info, 'DiceSlotInfoList': sinfo, 'DiceResultList': results,
            'RewardContentsList': rewards, 'RemainItem': {'ItemIndex': int(cfg['item']), 'Qty': int(it['Qty']) if it else 0}}


# ---- Event Book (make_data eventbook.json): QuestType 6000 quests per featured fighter, progress read from the save
#      (level / grade / limit break / a battle card equipped); the fighter's all-clear quest counts its claimed missions.
#      Claims share Missions['Claimed'] (not daily).
EVENTBOOK_PATH = Path(__file__).resolve().parent / 'eventbook.json'


def eventbook_cfg():
    return json.loads(EVENTBOOK_PATH.read_text()) if EVENTBOOK_PATH.exists() else None


def eventbook_value(player, ci, kind):
    c = next((x for x in player['CharacterList'] if int(x['CharacterIndex']) == int(ci)), None)
    if not c:
        return 0
    if kind == 'level':
        return level_of(c)
    if kind == 'grade':
        return int(c.get('Grade', 0))
    if kind == 'limit':
        return int(c.get('LimitBreakGrade', 0))
    if kind == 'card':
        return 1 if any(int(c.get('BattleCardNo%d' % n, 0) or 0) for n in range(1, 9)) else 0
    return 0


def eventbook_quests(player):
    """{questIndex: (done, need, reward)} for every Event Book quest."""
    cfg = eventbook_cfg(); out = {}
    if not cfg:
        return out
    claimed = missions_state(player)['Claimed']
    for f in cfg['fighters']:
        got = 0
        for q in f['quests']:
            out[q['index']] = (min(eventbook_value(player, f['char'], q['kind']), int(q['target'])), int(q['target']), q['reward'])
            got += 1 if claimed.get(str(q['index'])) else 0
        out[f['final']['index']] = (got, len(f['quests']), f['final']['reward'])
    return out


def eventbook_rows(player):
    st = missions_state(player); t = now_ms()
    return [{'QuestIndex': qi, 'QuestType': 6000, 'CompleteCount': need, 'ProcessCount': done, 'AccumulateCount': done, 'UpdateTime': t,
             'CreateTime': t, 'RewardGiveTime': int(st['Claimed'].get(str(qi), 0)), 'ExpireTime': 0, 'RepeatCycle': 0, 'RepeatCount': 0,
             'FestivalEventIndex': 0, 'EpicOpenTermStageIndex': 0, 'EpicEpisodeIndex': 0, 'EpicChapterIndex': 0, 'QuestCountType': 0,
             'RandomTermsType': 0, 'RandomTermsValue': 0} for qi, (done, need, _r) in eventbook_quests(player).items()]


def eventbook_claim(player, idx):
    q = eventbook_quests(player).get(idx); st = missions_state(player)
    if not q or st['Claimed'].get(str(idx)) or q[0] < q[1]:
        return None
    st['Claimed'][str(idx)] = now_ms()
    return pay_reward(player, q[2])


# ---- Gift Event (make_data giftevent.json): giftevent/info + reward. player['GiftEvent'] = {'Favor': n}. Each gift item
#      adds its points x count (capped at the last level's threshold); every level threshold crossed mails its reward
#      (rewardPostList + PostSendFlag, as the client expects). Gift items arrive by mail (welcome + daily, see mailbox).
GIFT_PATH = Path(__file__).resolve().parent / 'giftevent.json'


def gift_cfg():
    return json.loads(GIFT_PATH.read_text()) if GIFT_PATH.exists() else None


def gift_route(op, player, payload):
    cfg = gift_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no gift event'}
    st = player.setdefault('GiftEvent', {}); st.setdefault('Favor', 0)
    info = lambda: {'giftEventIndex': int(cfg['index']), 'favorabilityValue': int(st['Favor'])}
    if op == 'info':
        return {'giftInfo': info()}
    if op != 'reward':
        return {}
    ix, n = int(payload.get('useItemIndex') or 0), int(payload.get('useItemValue') or 0)
    inv = {i['ItemIndex']: i for i in items(player)}; it = inv.get(ix); pts = int(cfg['items'].get(str(ix), 0))
    top = max(int(l['need']) for l in cfg['levels'])
    if not pts or n <= 0 or not it or int(it['Qty']) < n or int(st['Favor']) >= top:
        return {'ResultCode': 1, 'ResultMessage': 'cannot give', 'giftInfo': info()}
    it['Qty'] = int(it['Qty']) - n; old = int(st['Favor']); st['Favor'] = min(top, old + pts * n); rew = []
    for lv in cfg['levels']:
        if old < int(lv['need']) <= int(st['Favor']) and lv['reward']:
            post_reward(player, lv['reward'], "Kula's Gift Event reward.")
            r = lv['reward']
            if r.get('gold'): rew.append(goods(len(rew) + 1, 1, int(r['gold'])))
            if r.get('ruby'): rew.append(goods(len(rew) + 1, 2, int(r['ruby'])))
            for i, q in r.get('items', []): rew.append(dict(goods(len(rew) + 1, 13, int(q)), ContentsIndex=int(i), ContentsType=1))
    save(player)
    return {'giftInfo': info(), 'rewardPostList': rew, 'materialItem': {'ItemIndex': ix, 'Qty': int(it['Qty'])}, 'PostSendFlag': bool(rew)}


# ---- Team Event (make_data teamevent.json): weekly seasons (Monday 00:00), the player is on team 1. Personal points come
#      from activities (mission_bump stats x points); team totals = the player's points + simulated other players
#      (hours into the week x a fixed rate per team, mine); rank / rank rate from a simulated 5000-player field.
#      teamevent/reward rewardType 1 / 2 pays every personal / team threshold up to the current points.
#      When a new week starts, a participant's win/lose and rank rewards for the old week are mailed (mine).
TEAM_PATH = Path(__file__).resolve().parent / 'teamevent.json'
TEAM_RATE = (900, 950)   # simulated points per hour for team 1 / team 2 (mine)


def team_cfg():
    return json.loads(TEAM_PATH.read_text()) if TEAM_PATH.exists() else None


def team_week():
    tm = time.localtime()
    return int(time.mktime((tm.tm_year, tm.tm_mon, tm.tm_mday - tm.tm_wday, 0, 0, 0, 0, 0, -1)))


def team_result(cfg, week, mine, hours=168):
    """(won, rank, rankRate, my total, other total) for a week with `mine` personal points after `hours`."""
    my_total = hours * TEAM_RATE[0] + mine * 10; other = hours * TEAM_RATE[1]
    rank = max(1, int(5000 * math.exp(-mine / 300.0))); rate = round(rank * 100.0 / 5000, 2)
    return my_total > other, rank, rate, my_total, other


def team_state(player):
    st = player.setdefault('TeamEvent', {})
    if st.get('Week') != team_week():
        cfg = team_cfg()
        if cfg and st.get('Week') and int(st.get('Point', 0)) > 0:   # season over: mail win/lose + rank rewards (participants)
            won, rank, rate, _m, _o = team_result(cfg, st['Week'], int(st['Point']))
            post_reward(player, cfg['winlose']['1' if won else '2'], 'Team Battle result reward.')
            for r in cfg['rank']:   # first matching rank tier (rows ordered best first)
                if (r['value'] == 4 and rank == r['value2']) or (r['value'] == 3 and rank <= r['value2']) or                         (r['value'] == 2 and rate <= r['value2']):
                    post_reward(player, r['reward'], 'Team Battle ranking reward.'); break
        st.update({'Week': team_week(), 'Point': 0, 'UserReward': 0, 'TeamReward': 0})
    return st


def team_add(player, stat, n=1):
    cfg = team_cfg()
    if cfg and stat in cfg['acts']:
        st = team_state(player); st['Point'] = int(st['Point']) + int(cfg['acts'][stat]) * int(n)


def team_info(player):
    cfg = team_cfg(); st = team_state(player); hours = max(0, int(time.time()) - int(st['Week'])) // 3600
    mine = int(st['Point']); _w, rank, rate, my_total, other = team_result(cfg, st['Week'], mine, hours)
    return {'teamEventIndex': int(cfg['index']), 'teamNo': 1, 'status': 1, 'point': mine, 'userRewardPoint': int(st['UserReward']),
            'teamRewardPoint': int(st['TeamReward']), 'myTeamTotalPoint': my_total, 'otherTeamTotalPoint': other, 'rank': rank, 'rankRate': rate}


def team_lobby(player):
    cfg = team_cfg()
    if not cfg:
        return []
    i = team_info(player)
    can = any(i['userRewardPoint'] < r['value'] <= i['point'] for r in cfg['personal']) or \
        any(i['teamRewardPoint'] < r['value'] <= i['myTeamTotalPoint'] for r in cfg['team'])
    return [{'teamEventIndex': i['teamEventIndex'], 'status': 1, 'reddot': 1 if can else 0, 'teamNo': 1}]


def team_route(op, player, payload):
    cfg = team_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no team event'}
    if op == 'info':
        save(player)
        return {'teamEventInfo': team_info(player)}
    if op != 'reward':
        return {}
    st = team_state(player); i = team_info(player); kind = int(payload.get('rewardType') or 1); rew, got = [], []
    key, have, rows = (('UserReward', i['point'], cfg['personal']) if kind == 1 else ('TeamReward', i['myTeamTotalPoint'], cfg['team']))
    for r in rows:
        if int(st[key]) < int(r['value']) <= int(have):
            a, b = pay_reward(player, r['reward']); rew += a; got += [x for x in b if x not in got]
    if not rew:
        return {'ResultCode': 1, 'ResultMessage': 'nothing to claim', 'teamEventInfo': i}
    st[key] = int(have); save(player)
    return {'teamEventInfo': team_info(player), 'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [], 'RewardBattleCardList': [],
            'RewardItemList': got, 'RewardImprintStoneList': [], 'RewardCurrencyList': rew, 'PostSendFlag': False,
            'presetCharacterReward': [], 'presetCharacterCoreReward': []}


# ---- Carnival (make_data carnival.json): monthly season (matches the poll schedule end). Points from growth actions
#      (mission_bump stats x points); carnival/reward pays every threshold between the claimed-up-to mark and the points.
CARNIVAL_PATH = Path(__file__).resolve().parent / 'carnival.json'


def carnival_cfg():
    return json.loads(CARNIVAL_PATH.read_text()) if CARNIVAL_PATH.exists() else None


def carnival_state(player):
    st = player.setdefault('Carnival', {}); month = time.strftime('%Y-%m')
    if st.get('Month') != month:
        st.update({'Month': month, 'Point': 0, 'RewardPoint': 0})
    return st


def carnival_add(player, stat, n=1):
    cfg = carnival_cfg()
    if cfg and stat in cfg['acts']:
        st = carnival_state(player); st['Point'] = int(st['Point']) + int(cfg['acts'][stat]) * int(n)


def carnival_info(player):
    cfg = carnival_cfg(); st = carnival_state(player)
    return {'carnivalGroup': 0, 'carnivalIndex': int(cfg['index']), 'point': int(st['Point']), 'rewardPoint': int(st['RewardPoint']),
            'status': 1, 'repeatRemainPoint': 0, 'repeatCount': 0}


def carnival_route(op, player, payload):
    cfg = carnival_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no carnival'}
    if op == 'info':
        save(player)
        return {'serverUtcTime': now_ms(), 'carnivalInfo': carnival_info(player), 'groupRankingList': []}
    if op == 'rankingList':
        pt = int(carnival_state(player)['Point']); rank = max(1, int(5000 * math.exp(-pt / 500.0)))
        return {'myRanking': {'rank': rank, 'rankRate': max(1, rank * 100 // 5000), 'score': float(pt)}, 'rankingList': []}
    if op != 'reward':
        return {}
    st = carnival_state(player); rew, got = [], []
    for r in cfg['rewards']:
        if int(st['RewardPoint']) < int(r['need']) <= int(st['Point']):
            a, b = pay_reward(player, r['reward']); rew += a; got += [x for x in b if x not in got]
    if not rew:
        return {'ResultCode': 1, 'ResultMessage': 'nothing to claim', 'carnivalInfo': carnival_info(player)}
    st['RewardPoint'] = int(st['Point']); save(player)
    return {'AccountMoney': player['AccountMoney'], 'RewardCharacterList': [], 'RewardBattleCardList': [], 'RewardItemList': got,
            'RewardImprintStoneList': [], 'rewardCurrencyList': rew, 'PostSendFlag': False, 'presetCharacterReward': [],
            'presetCharacterCoreReward': [], 'carnivalInfo': carnival_info(player)}


# ---- Select Fighter (make_data selectfighter.json): lobby characterSelectionList offers the group once a month; picking
#      a fighter grants it (or, if already owned, its Soul + Memory like a duplicate summon) and closes the offer.
SELECT_PATH = Path(__file__).resolve().parent / 'selectfighter.json'


def select_cfg():
    return json.loads(SELECT_PATH.read_text()) if SELECT_PATH.exists() else None


def select_lobby(player):
    cfg = select_cfg()
    if not cfg or player.setdefault('SelectFighter', {}).get('Done') == time.strftime('%Y-%m'):
        return []
    end = month_end_ms()
    return [{'selectCharacterGroupIndex': int(cfg['group']), 'createTime': now_ms() - DAY_MS, 'endTime': end, 'expireTime': end}]


def select_route(op, player, payload):
    cfg = select_cfg()
    ci = int(payload.get('characterIndex') or 0)
    if not cfg or op != 'selectCharacter' or ci not in cfg['fighters'] or not select_lobby(player):
        return {'ResultCode': 1, 'ResultMessage': 'cannot select'}
    player['SelectFighter']['Done'] = time.strftime('%Y-%m')
    if any(int(c['CharacterIndex']) == ci for c in player['CharacterList']):
        inv = {i['ItemIndex']: i for i in items(player)}; got = []
        for ix, q in ((SOUL_BASE + ci, int(cfg['dupSouls'])), (MEM_BASE + ci, 1)):
            row = inv.get(ix)
            if row is None:
                row = {'ItemIndex': ix, 'Qty': 0, 'Lock': False}; player.setdefault('ItemList', []).append(row)
            row['Qty'] = int(row['Qty']) + q; got.append(row)
        reward = {'CharacterIndex': ci, 'Grade': 3, 'Exp': 0, 'ExCharacterSoul': SOUL_BASE + ci, 'ExCharacterSoulQty': int(cfg['dupSouls']),
                  'fighterMemoryIndex': MEM_BASE + ci, 'fighterMemoryIndexQty': 1}
    else:
        player['CharacterList'].append(new_character(ci)); got = []
        reward = {'CharacterIndex': ci, 'Grade': 3, 'Exp': 0}
    save(player)
    return {'RewardCharacterList': [reward], 'RewardItemList': got, 'presetCharacterReward': [], 'presetCharacterCoreReward': []}


# ---- Battlefield Dungeon (make_data battlefield.json): battledungeon/{info, deckUpdate, stageStart, stageEnd, stageMopUp,
#      charge}; DTOs BattleFieldDungeon* (lowercase JSON names). Weekly season; a win clears the stage and opens the next
#      (the last stage repeats); bosses are drawn from the Prove pool, harder tiers on later stages. Rewards mine.
#      battleDungeon.playCount / battleCount are REMAINING plays (Model_BattleFieldDungeon.get_RemainPlayCount; < 1 opens
#      the recharge popup; the ready view shows remaining/ConfigTable 97001 and 97002).
BF_PATH = Path(__file__).resolve().parent / 'battlefield.json'


def bf_cfg():
    return json.loads(BF_PATH.read_text()) if BF_PATH.exists() else None


def bf_bosses(cfg, stage):
    n = cfg['stages'].index(stage) if stage in cfg['stages'] else 0
    tier = 1 if n < 4 else (2 if n < 8 else 3)
    pool = [int(b) for b, t in cfg['bosses'].items() if t <= tier] or [int(b) for b in cfg['bosses']]
    return random.sample(pool, min(5, len(pool)))


def bf_state(player):
    cfg = bf_cfg(); st = player.setdefault('BattleField', {}); week = int(team_week())
    if st.get('Week') != week:
        st.update({'Week': week, 'PlayCount': 0})
    st.setdefault('Stage', cfg['stages'][0]); st.setdefault('LastClear', 0); st.setdefault('Deck', [0, 0, 0, 0, 0])
    if len(st.get('Bosses') or []) != 5:
        st['Bosses'] = bf_bosses(cfg, st['Stage'])
    return st


def bf_dungeon(st, cfg):
    end = (int(st['Week']) + 7 * 86400) * 1000; d = st['Deck'] + [0] * 5
    return {'season': 1, 'battleDungeonPlayToken': 0, 'playStageIndex': int(st['Stage']), 'lastClearStageIndex': int(st['LastClear']),
            'playCount': max(0, int(cfg['limit']) - int(st['PlayCount'])), 'battleCount': int(cfg['battles']), 'RechargePlay': 0, 'RechargeBattle': 0, 'countUpdateTime': now_ms(),
            'characterIndex1': d[0], 'characterIndex2': d[1], 'characterIndex3': d[2], 'characterIndex4': d[3], 'characterIndex5': d[4],
            'groupGrowthIndex': 0, 'endTime': end}


def bf_route(op, player, payload):
    cfg = bf_cfg()
    if not cfg:
        return {'ResultCode': 1, 'ResultMessage': 'no battlefield'}
    st = bf_state(player)
    stage_info = lambda: {'proveDungeonStageIndex': int(st['Stage']), 'battleResult': 0, **{'randomBossIndex%d' % (i + 1): int(b) for i, b in enumerate(st['Bosses'])},
                          'refreshBoss': 0, 'mopup': 1 if int(st['LastClear']) >= int(st['Stage']) else 0}
    if op == 'info':
        save(player)
        return {'seasonInfo': {'season': 1, 'startData': int(st['Week']) * 1000, 'endDate': (int(st['Week']) + 7 * 86400) * 1000},
                'battleDungeon': bf_dungeon(st, cfg), 'battleDungeonUserStage': stage_info()}
    if op == 'deckUpdate':
        st['Deck'] = [int(payload.get('characterIndex%d' % i) or 0) for i in range(1, 6)]; save(player)
        return dict({'characterIndex%d' % i: st['Deck'][i - 1] for i in range(1, 6)}, groupGrowthIndex=0)
    if op == 'stageStart':
        deck = [int(payload.get('characterIndex%d' % i) or 0) for i in range(1, 6)]
        if any(deck): st['Deck'] = deck
        save(player)
        return {'playToken': now_ms()}
    if op in ('stageEnd', 'stageMopUp'):
        win = op == 'stageMopUp' or int(payload.get('battleResult') or 0) == 1
        times = max(1, int(payload.get('mopUpCount') or 1)) if op == 'stageMopUp' else 1
        rew = []
        drop = []
        if win:
            r, _g = pay_reward(player, {'gold': int(cfg['gold']) * times, 'ruby': int(cfg['ruby']) * times}); rew += r
            drop = piece_drop(player, rew)   # fighter pieces (make_data pieces.json)
        st['PlayCount'] = int(st['PlayCount']) + times
        if win and op == 'stageEnd':
            stg = int(st['Stage']); st['LastClear'] = max(int(st['LastClear']), stg)
            nxt = [x for x in cfg['stages'] if x > stg]
            st['Stage'] = nxt[0] if nxt else stg; st['Bosses'] = bf_bosses(cfg, st['Stage'])
        save(player)
        base = {'PlayerAccount': player['PlayerAccount'], 'AccountMoney': player['AccountMoney'], 'RewardItemList': drop, 'RewardBattleCardList': [],
                'RewardCharacterList': [], 'RewardContentsList': rew, 'RewardImprintStoneList': [], 'PostSendFlag': False, 'GuildBuffList': [],
                'presetCharacterList': [], 'presetCharacterCoreList': [], 'battleDungeon': bf_dungeon(st, cfg)}
        if op == 'stageEnd':
            base.update({'PlayCount': max(0, int(cfg['limit']) - int(st['PlayCount'])), 'HandicapRewardContentsList': []})
        else:
            base['remainItem'] = {'ItemIndex': 0, 'Qty': 0, 'Lock': False}
        return base
    if op == 'charge':
        st['PlayCount'] = 0; save(player)
        return {'AccountMoney': player['AccountMoney'], 'battleDungeon': bf_dungeon(st, cfg), 'remainItem': {'ItemIndex': 0, 'Qty': 0, 'Lock': False}}
    return {}


def quest_rows(player):
    st = missions_state(player)
    return [quest_row(m, st) for m in missions_cfg()] + growth_rows(player) + bingo_rows(player) + eventbook_rows(player)


def mission_claim(player, idx):
    st = missions_state(player); m = next((x for x in missions_cfg() if x['index'] == idx), None)
    if not m or st['Claimed'].get(str(idx)):
        return None
    if int(st['Counts'].get(mission_key(m), 0)) < int(m['target']):
        return None
    st['Claimed'][str(idx)] = now_ms(); money = player['AccountMoney']; rew = []
    qpoint_add(player, idx)   # Mission Points (QuestProto.pointValue)
    if m['type'] == 1 and pass_cfg():
        pass_add_exp(player, int(pass_cfg().get('dailyExp', 0)))   # QuestTable passEXP
    if m['gold']:
        money['Gold'] += int(m['gold']); rew.append(goods(1, 1, int(m['gold'])))
    if m['ruby']:
        money['Cash'] += int(m['ruby']); rew.append(goods(1, 2, int(m['ruby'])))
    return m, rew


QPOINT_PATH = Path(__file__).resolve().parent / 'questpoints.json'


def qpoint_cfg():
    return json.loads(QPOINT_PATH.read_text()) if QPOINT_PATH.exists() else {'quests': {}, 'rewards': {}}


def qpoint_state(player):
    """player['QuestPoints'][pointIndex]: points and claimed milestones of today (pointResetType 1 = daily)."""
    st = player.setdefault('QuestPoints', {}); today = _today()
    for k in qpoint_cfg()['rewards']:
        s = st.setdefault(k, {})
        if s.get('Day') != today:
            s.update({'Day': today, 'Point': 0, 'Claimed': []})
    return st


def qpoint_list(player):
    st = qpoint_state(player)
    nxt = int(time.mktime(time.strptime(_today(), '%Y-%m-%d'))) * 1000 + 86400000
    return [{'questPointIndex': int(k), 'questPoint': int(v['Point']), 'questPointRewardIndexList': ','.join(str(x) for x in v['Claimed']),
             'expireTime': nxt} for k, v in sorted(st.items(), key=lambda kv: int(kv[0])) if k in qpoint_cfg()['rewards']]


def qpoint_add(player, quest_index):
    q = qpoint_cfg()['quests'].get(str(quest_index))
    if q:
        s = qpoint_state(player)[str(q[0])]; s['Point'] = int(s['Point']) + int(q[1])


def qpoint_reward(player, payload):
    k = str(int(payload.get('questPointIndex') or 0)); st = qpoint_state(player).get(k)
    want = [int(x) for x in (payload.get('questPointRewardIndexList') or [])]
    rows = {r[0]: r for r in qpoint_cfg()['rewards'].get(k, [])}
    if st is None:
        return {'ResultCode': 1, 'ResultMessage': 'no such point'}
    money = player['AccountMoney']; rew = []
    for ri in want or sorted(rows):
        r = rows.get(ri)
        if not r or ri in st['Claimed'] or int(st['Point']) < int(r[1]):
            continue
        st['Claimed'].append(ri)
        if r[2]:
            money['Gold'] += int(r[2]); rew.append(goods(len(rew) + 1, 1, int(r[2])))
        if r[3]:
            money['Cash'] += int(r[3]); rew.append(goods(len(rew) + 1, 2, int(r[3])))
    save(player)
    return {'PlayerAccount': player['PlayerAccount'], 'AccountMoney': money, 'RewardCharacterList': [], 'RewardBattleCardList': [],
            'RewardItemList': [], 'RewardImprintStoneList': [], 'PostSendFlag': False, 'AccountLevelUpRewardList': [], 'RewardList': rew,
            'SuperMissionList': [], 'presetCharacterReward': [], 'presetCharacterCoreReward': [],
            'questPoint': next((x for x in qpoint_list(player) if str(x['questPointIndex']) == k), None)}


def quest_route(path, player, payload):
    op = path.rsplit('/', 1)[1]
    if op == 'list':
        player['QuestList'] = quest_rows(player); save(player)
        return {'RewardQuestCountList': [], 'QuestList': player['QuestList'], 'ClearQuestFlag': 0, 'EventEpicQuestEndTime': 0,
                'questPointList': qpoint_list(player), 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'pointReward':
        return qpoint_reward(player, payload)
    base = {'ServerUtcTime': now_ms(), 'PlayerAccount': player['PlayerAccount'], 'RewardCharacterList': [], 'RewardBattleCardList': [],
            'RewardItemList': [], 'PostSendFlag': False, 'GuildRankPoint': 0, 'AccountLevelUpRewardList': [], 'RewardImprintStoneList': [],
            'presetCharacterReward': [], 'presetCharacterCoreReward': [], 'ResultCode': 0, 'ResultMessage': ''}
    if op == 'reward':
        idx = int(payload.get('QuestIndex') or 0)
        bq = bingo_quests(player).get(idx)
        if bq and not missions_state(player)['Claimed'].get(str(idx)) and bq[0] >= bq[1]:   # bingo square: reward + mark
            missions_state(player)['Claimed'][str(idx)] = now_ms(); rew, got = pay_reward(player, bq[2])
            player['QuestList'] = quest_rows(player); save(player)
            row = next((q for q in player['QuestList'] if q['QuestIndex'] == idx), None)
            return dict(base, Quest=row, NextQuest=None, AccountMoney=player['AccountMoney'], QuestRewardList=rew, RewardItemList=got)
        gq = growth_claim(player, idx) if idx in growth_quests(player) else (
            eventbook_claim(player, idx) if idx in eventbook_quests(player) else None)
        if gq:
            player['QuestList'] = quest_rows(player); save(player)
            row = next((q for q in player['QuestList'] if q['QuestIndex'] == idx), None)
            return dict(base, Quest=row, NextQuest=None, AccountMoney=player['AccountMoney'], QuestRewardList=gq[0], RewardItemList=gq[1])
        got = mission_claim(player, idx)
        player['QuestList'] = quest_rows(player); save(player)
        row = next((q for q in player['QuestList'] if q['QuestIndex'] == idx), None)
        # NextQuest must be null: the typed default is an empty Quest (index 0) and Parse_QuestReward then looks up
        # QuestTable row 0 -> NullReference before the row refresh (probe_exc.py, Parse_QuestReward+0xa11)
        return dict(base, Quest=row, NextQuest=None, AccountMoney=player['AccountMoney'], QuestRewardList=got[1] if got else [],
                    ResultCode=0 if got else 1, ResultMessage='' if got else 'not claimable')
    if op == 'rewardAll':
        rew, rows, its = [], [], []
        for idx in payload.get('QuestIndexList') or [m['index'] for m in missions_cfg()]:
            if int(idx) in growth_quests(player) or int(idx) in eventbook_quests(player):
                gq = growth_claim(player, int(idx)) if int(idx) in growth_quests(player) else eventbook_claim(player, int(idx))
                if gq:
                    rew += gq[0]; its += [i for i in gq[1] if i not in its]; rows.append(int(idx))
                continue
            got = mission_claim(player, int(idx))
            if got:
                rew += got[1]; rows.append(int(idx))
        player['QuestList'] = quest_rows(player); save(player)
        return dict(base, QuestList=[q for q in player['QuestList'] if q['QuestIndex'] in rows], NextQuestList=[], InvenFull=0,
                    AccountMoney=player['AccountMoney'], QuestRewardList=rew, RewardItemList=its)
    return {}


def mission_track(path, player, payload, resp):
    if path.startswith('/api/gacha2/'):
        path = '/api/gacha/' + path[len('/api/gacha2/'):]
    stat = None
    if path in MISSION_WIN_PATHS and int(payload.get('BattleResult') or 0) == 1:
        stat = MISSION_WIN_PATHS[path]
    elif path in MISSION_PLAY_PATHS:
        stat = MISSION_PLAY_PATHS[path]
    if not stat and path in GROWTH_TRACK and isinstance(resp, dict) and not resp.get('ResultCode'):
        stat = GROWTH_TRACK[path]
    if path == '/api/epicQuest/playEnd' and int(payload.get('BattleResult') or 0) == 1:   # Epic Missions: per-chapter clears
        sc = ((epic_cfg() or {}).get('stages') or {}).get(str(int(payload.get('EpicQuestStageIndex') or 0)))
        if sc and sc.get('chapter'):
            mission_bump(player, 'epic_ch_%d' % int(sc['chapter']))
    if stat:
        mission_bump(player, stat); save(player)
    elif path in ('/api/gacha/gachaDefaultPlay', '/api/gacha/gachaTicketRandom') and isinstance(resp, dict) and not resp.get('ResultCode'):
        n = len(resp.get('RewardCharacterList') or []) or 1
        mission_bump(player, 'gacha_pull', n); save(player)


# ---- Battle gold drops: start replies carry the per-type gold totals the client turns into coins (DropItemManager.MakeGoldData,
#      make_data StageDropTable/DropSettingGroupTable); the end request reports the gold picked up (DropGold). Totals are mine.
DROP_GOLD = {'DropGoldJaco': 400, 'DropGoldElite': 300, 'DropGoldBoss': 600, 'DropGoldGimmick1': 200, 'DropGoldGimmick2': 200,
             'DropGoldGimmick3': 200}
DROP_START_PATHS = {'/api/adventure/stageStart', '/api/questEvent/questEventStart', '/api/questEvent/crucibleTowerStart',
                    '/api/questEvent/marathonStart', '/api/smash/start', '/api/epicQuest/playStart', '/api/epicQuest/start'}


def drop_gold_hook(path, player, payload, resp):
    """Fill the drop totals on start replies; pay the collected DropGold on the next end (capped at the totals)."""
    if not isinstance(resp, dict) or resp.get('ResultCode'):
        return
    if path in DROP_START_PATHS:
        # story stages: coins worth about the stage's win gold (the original '96 HUD counted ~120 coins mid-fight next to a 270 win
        # reward), split like DROP_GOLD; other modes keep DROP_GOLD
        g = STORY_GOLD.get(int(payload.get('StageIndex') or 0)) if path == '/api/adventure/stageStart' else None
        drop = {k: max(1, round(v * g / sum(DROP_GOLD.values()))) for k, v in DROP_GOLD.items()} if g else DROP_GOLD
        resp.update(drop); player['DropAllot'] = sum(drop.values()); save(player)
    elif payload.get('DropGold') and player.get('DropAllot') and path.rsplit('/', 1)[1].lower().endswith('end'):
        gain = max(0, min(int(payload.get('DropGold') or 0), int(player['DropAllot'])))
        player['AccountMoney']['Gold'] = int(player['AccountMoney']['Gold']) + gain; player['DropAllot'] = 0; save(player)
        if 'AccountMoney' in resp:
            resp['AccountMoney'] = player['AccountMoney']


# ---- Star mission rewards: the result page fills a mission row only when MissionNRewardList has an entry
#      (NetworkManagerWEB.TakeMissionRewardList -> StarMissionReward.m_normal[n]; UIUnit_MissionReward.SetResultData returns on a
#      null Goods), so empty lists left three blank rows on every win. Each mission shows STAR_CASH rubies and pays them the first
#      time it is completed (repeat type Once, make_data); paid missions in player['StarPaid'] (mode:stage:n). 3 rubies per mission
#      as on the original QUEST INFO screens (ruby x3 next to each mission in the playthrough videos).
STAR_CASH = 3
STAR_STAGE_KEYS = ('StageIndex', 'QuestEventStageIndex', 'EpicQuestStageIndex', 'MarathonStageIndex', 'FighterQuestIndex',
                   'SmashModeStageIndex')


def star_reward_hook(path, player, payload, resp):
    if not isinstance(resp, dict) or resp.get('ResultCode') or not path.rsplit('/', 1)[1].lower().endswith('end'):
        return
    if not any(k in payload for k in ('Mission1Index', 'Mission2Index', 'Mission3Index')):
        return
    stage = next((int(payload[k]) for k in STAR_STAGE_KEYS if int(payload.get(k) or 0)), 0)
    won = int(payload.get('BattleResult') or resp.get('BattleResult') or 0) == 1
    paid = player.setdefault('StarPaid', []); gain = 0
    for n in (1, 2, 3):
        resp['Mission%dRewardList' % n] = [goods(n, 2, STAR_CASH)]
        key = '%s:%d:%d' % (path.rsplit('/', 2)[1], stage, n)
        if won and stage and int(payload.get('Mission%dIndex' % n) or 0) and key not in paid:
            paid.append(key); gain += STAR_CASH
    resp.setdefault('MissionAllRewardList', [])
    if gain:
        player['AccountMoney']['Cash'] = int(player['AccountMoney']['Cash']) + gain; save(player)
        if 'AccountMoney' in resp:
            resp['AccountMoney'] = player['AccountMoney']


_route_overrides_inner = route_overrides


def route_overrides(path, player, payload=None):
    if isinstance(player.get('AccountMoney'), dict):   # every reply that carries AccountMoney shows regenerated AP
        regen_active_point(player)                       # (shop buys showed the stale stored value: 89 -> 82, seen live)
    if path.startswith('/api/quest/'):
        return quest_route(path, player, payload or {})
    if path.startswith('/api/bingo/'):
        return bingo_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/battledungeon/'):
        return bf_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/characterSelection/'):
        return select_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/carnival/'):
        return carnival_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/teamevent/'):
        return team_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/giftevent/'):
        return gift_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/diceMiniGame/'):
        return dice_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/luckyChance/'):
        return lucky_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/event/roulette'):
        return roulette_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/pass/'):
        return pass_route(path.rsplit('/', 1)[1], player, payload or {})
    if path.startswith('/api/superMission/'):
        return super_route(path.rsplit('/', 1)[1], player, payload or {})
    if path == '/api/player/renew':   # the lobby's periodic renew: refreshes the red dots (mail mailed after a fight)
        return {'RedDotList': red_dots(player)}
    resp = _route_overrides_inner(path, player, payload)
    try:
        drop_gold_hook(path, player, payload or {}, resp)
        star_reward_hook(path, player, payload or {}, resp)
    except Exception as e:   # never break a battle reply over drop gold
        print('drop_gold_hook', e)
    try:
        mission_track(path, player, payload or {}, resp)
    except Exception:   # mission counting must never break a game route
        pass
    return resp


# ---- Retry guard for fight ends. The client sends no request id, so a retried fight end (timeout, lost reply) would be paid
#      twice by end routes that keep no per-play state (story stageEnd paid its win gold twice, test_items.py). An end whose body
#      is byte-identical to one that succeeded in the last REPLAY_SECS is answered with the stored reply instead of being applied
#      again (ends carry score and play time, so an identical body is a retry, not a new fight). Reward claims are not covered:
#      their routes keep claimed flags and must answer a second claim with their own refusal (pass / team / carnival / series
#      scenarios); purchases, crafting and box opening repeat legitimately. In memory only (a server restart forgets it).
import copy as _copy, hashlib as _hashlib, re as _re
REPLAY_SECS = 120
REPLAY_OPS = _re.compile(r'(End|end)$')
_REPLAYED = {}
_route_overrides_guarded = route_overrides


def route_overrides(path, player, payload=None):
    op = path.rsplit('/', 1)[-1]
    key = None
    if REPLAY_OPS.search(op):
        key = (path, _hashlib.sha1(json.dumps(payload or {}, sort_keys=True, default=str).encode()).hexdigest())
        hit = _REPLAYED.get(key)
        if hit and time.time() - hit[0] < REPLAY_SECS:
            return _copy.deepcopy(hit[1])
    resp = _route_overrides_guarded(path, player, payload)
    if key and isinstance(resp, dict) and not int(resp.get('ResultCode') or 0):
        now = time.time()
        for k in [k for k, (t, _) in _REPLAYED.items() if now - t >= REPLAY_SECS]:
            del _REPLAYED[k]
        _REPLAYED[key] = (now, _copy.deepcopy(resp))
    return resp
