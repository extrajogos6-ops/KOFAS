from bisect import bisect_right
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

ROOT = Path(__file__).resolve().parent
BASE_MAX_LEVEL = {3: 30, 4: 40, 5: 50, 6: 60}


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ValueError('truncated progression table')
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError('invalid progression varint')


def _fields(data: bytes):
    offset = 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        field, wire = tag >> 3, tag & 7
        if field == 0:
            raise ValueError('invalid progression field')
        if wire == 0:
            value, offset = _varint(data, offset)
        else:
            if wire == 2:
                size, offset = _varint(data, offset)
            elif wire in (1, 5):
                size = 8 if wire == 1 else 4
            else:
                raise ValueError('unsupported progression wire type')
            if offset + size > len(data):
                raise ValueError('truncated progression value')
            value = data[offset:offset + size]
            offset += size
        yield field, value


def _table_rows(name: str) -> list[dict[int, int | bytes]]:
    security = json.loads((ROOT / 'packs-claude' / 'security.json').read_text())['SecurityDataTable']
    with ZipFile(ROOT / 'packs-claude' / 'table.dat') as archive:
        encrypted = archive.read(name)
    payload = unpad(AES.new(bytes.fromhex(security['EncryptionKey']), AES.MODE_CBC,
                           bytes.fromhex(security['Iv'])).decrypt(encrypted), 16)
    with ZipFile(BytesIO(payload)) as archive:
        data = archive.read(name)
    rows = []
    for field, value in _fields(data):
        if field == 1:
            if not isinstance(value, bytes):
                raise ValueError('invalid progression row')
            rows.append(dict(_fields(value)))
    if not rows:
        raise ValueError('empty progression table')
    return rows


@lru_cache(maxsize=1)
def _curves() -> tuple[tuple[int, ...], ...]:
    rows = _table_rows('characterlevelingtable.bin')
    if [row.get(2) for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError('nonsequential progression levels')
    curves = []
    for field in range(3, 7):
        values = [row.get(field) for row in rows]
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError('invalid progression thresholds')
        if values != sorted(values) or len(set(values)) != len(values):
            raise ValueError('nonincreasing progression thresholds')
        curves.append(tuple(values))
    return tuple(curves)


@lru_cache(maxsize=1)
def _leveling_types() -> dict[int, int]:
    result = {}
    for row in _table_rows('charactertable.bin'):
        index, kind = row.get(2), row.get(12, 0)
        if type(index) is not int or type(kind) is not int or not 0 <= kind < 4:
            raise ValueError('invalid character leveling type')
        result[index] = kind
    return result


def _curve(character_index: int | None) -> tuple[int, ...]:
    kind = 0 if character_index is None else _leveling_types()[character_index]
    return _curves()[kind]


def level_from_exp(exp: int, character_index: int | None = None) -> int:
    if type(exp) is not int or exp < 0:
        raise ValueError('normal EXP must be a nonnegative integer')
    curve = _curve(character_index)
    position = bisect_right(curve, exp)
    return 1 if position == len(curve) else position + 1


def exp_for_level(level: int, character_index: int | None = None) -> int:
    curve = _curve(character_index)
    if type(level) is not int or not 1 <= level <= len(curve):
        raise ValueError('normal level outside progression table')
    return 0 if level == 1 else curve[level - 2]


def normal_level_cap(character: dict) -> int:
    grade = character['Grade']
    breaks = character.get('LimitBreakProgressCount', 0)
    if type(grade) is not int or grade not in BASE_MAX_LEVEL:
        raise ValueError('invalid character grade')
    if type(breaks) is not int or not 0 <= breaks <= 30:
        raise ValueError('invalid character limit breaks')
    return BASE_MAX_LEVEL[grade] + breaks


def normal_level(character: dict) -> int:
    return min(normal_level_cap(character),
               level_from_exp(character['Exp'], character['CharacterIndex']))
