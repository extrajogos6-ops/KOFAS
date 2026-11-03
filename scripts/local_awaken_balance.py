"""Rebalance only the reconstructed local 1.11 awakening effects; never open a game."""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import struct
import sys
from zipfile import ZipFile

SERVER = Path(__file__).resolve().parents[1] / 'server'
sys.path.insert(0, str(SERVER / 'vendor'))
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

FILES = ('packs-claude/table.dat', 'packs-claude/table.kof',
         'packs-claude/lang_global.dat', 'packs-claude/lang_en.kof', 'table-versions.json')
OPTIONS = {group * 10 + n for group in (932, 933, 934) for n in range(3)}
EFFECT_BASE = 9900000


def _varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise ValueError('truncated protobuf varint')
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ValueError('invalid protobuf varint')


def _parts(data):
    pos = 0
    while pos < len(data):
        start = pos
        tag, pos = _varint(data, pos)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError('invalid field zero')
        if wire == 0:
            value, pos = _varint(data, pos)
        else:
            if wire == 2:
                size, pos = _varint(data, pos)
            elif wire in (1, 5):
                size = 8 if wire == 1 else 4
            else:
                raise ValueError('unsupported wire type')
            if pos + size > len(data):
                raise ValueError('truncated protobuf field')
            value = data[pos:pos + size]
            pos += size
        yield number, wire, value, data[start:pos]


def _v(value):
    if value < 0:
        raise ValueError('negative varint')
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    return bytes(out) + bytes([value])


def _field(number, wire, value):
    return _v(number * 8 + wire) + (_v(value) if wire == 0 else
                                   _v(len(value)) + value if wire == 2 else value)


def _edit(data, updates):
    remaining = dict(updates)
    out = []
    for n, w, value, raw in _parts(data):
        if n in remaining:
            wire, value = remaining.pop(n)
            out.append(_field(n, wire, value))
        else:
            out.append(raw)
    out.extend(_field(n, w, value) for n, (w, value) in remaining.items())
    return b''.join(out)


def _rows(data):
    return [(value, {n: v for n, _, v, _ in _parts(value)})
            for number, wire, value, _ in _parts(data) if number == 1 and wire == 2]


def _crypt(data, security, encrypt=False):
    cipher = AES.new(bytes.fromhex(security['EncryptionKey']), AES.MODE_CBC,
                     bytes.fromhex(security['Iv']))
    return cipher.encrypt(pad(data, 16)) if encrypt else unpad(cipher.decrypt(data), 16)


def _unpack(archive, name, security):
    with ZipFile(BytesIO(archive)) as outer:
        with ZipFile(BytesIO(_crypt(outer.read(name), security))) as inner:
            if inner.testzip() is not None or inner.namelist() != [name]:
                raise ValueError('invalid encrypted table ZIP')
            return inner.read(name)


def _replace_zip(archive, replacements):
    target = BytesIO()
    with ZipFile(BytesIO(archive)) as old, ZipFile(target, 'w') as new:
        if not set(replacements) <= set(old.namelist()):
            raise ValueError('missing archive entries')
        for info in old.infolist():
            new.writestr(info, replacements.get(info.filename, old.read(info)))
    return target.getvalue()


def _update_pack(archive, manifest, security, replacements):
    encrypted = {}
    for name, plain in replacements.items():
        inner = BytesIO()
        with ZipFile(inner, 'w') as z:
            z.writestr(name, plain)
        encrypted[name] = _crypt(inner.getvalue(), security, True)
    meta = json.loads(_crypt(manifest, security))
    updated = set()
    for row in meta:
        name = row['name'].lower() + '.bin'
        if name in replacements:
            row['hash'] = hashlib.md5(replacements[name]).hexdigest()
            updated.add(name)
    if updated != set(replacements):
        raise ValueError('missing table manifest entries')
    return _replace_zip(archive, encrypted), _crypt(
        json.dumps(meta, separators=(',', ':')).encode(), security, True)


def build_patch(root):
    """Build five replacement files in memory. No writes, process or network access."""
    root = Path(root)
    files = {name: (root / name).read_bytes() for name in FILES}
    security = json.loads((root / 'packs-claude/security.json').read_text())
    table_key, lang_key = security['SecurityDataTable'], security['SecurityLocalizing']
    archive = files['packs-claude/table.dat']
    buffs = _unpack(archive, 'bufftable.bin', table_key)
    awake = _unpack(archive, 'battlecardawakebufftable.bin', table_key)
    options = _rows(awake)
    if {r[2] for _, r in options} != OPTIONS:
        raise ValueError('not the supported reconstructed local 1.11 awakening table')
    by_id = {r[2]: (raw, r) for raw, r in _rows(buffs)}
    references = [int(r[5]) == EFFECT_BASE + r[2] for _, r in options]
    if all(references):
        for _, option in options:
            row = by_id[int(option[5])][1]
            base, step, cap = [struct.unpack('<f', row[n])[0] for n in (29, 30, 31)]
            if not (math.isclose(base, step) and math.isclose(cap, base * 6, rel_tol=1e-6)):
                raise ValueError('inconsistent existing awakening patch')
        return files
    if any(references):
        raise ValueError('partial awakening patch; restore a coherent backup before retrying')
    added, new_options, texts = [], [], []
    labels = {b'11': 'ATK', b'21': 'HP', b'31': 'DEF', b'41': 'Penetration', b'51': 'Critical Rate'}
    for raw, option in options:
        source, row = by_id[int(option[5])]
        effect = EFFECT_BASE + option[2]
        if effect in by_id:
            raise ValueError('effect ID collision')
        base = struct.unpack('<f', row[29])[0]
        if not math.isfinite(base) or base <= 0 or row[24] not in labels:
            raise ValueError('unsupported awakening status')
        name_tag, desc_tag = f'Buff.{effect}.Name', f'Buff.{effect}.Desc'
        added.append(_field(1, 2, _edit(source, {
            2: (0, effect), 3: (2, f'AwakenLinear_{option[2]}'.encode()),
            4: (2, name_tag.encode()), 30: (5, row[29]),
            31: (5, struct.pack('<f', base * 6)), 76: (2, desc_tag.encode())})))
        new_options.append(_field(1, 2, _edit(raw, {5: (2, str(effect).encode())})))
        label = labels[row[24]]
        desc = label + (' +{buffPower*100}%' if base < 1 else ' +{buffPower}')
        for tag, value in [(name_tag, 'Awaken ' + label), (desc_tag, desc)]:
            texts.append(_field(1, 2, _field(2, 2, tag.encode()) + _field(4, 2, value.encode())))
    # Existing buffs, card definitions and ordinary localization rows remain byte-for-byte intact.
    language = _unpack(files['packs-claude/lang_global.dat'], 'bufftable.bin', lang_key)
    updated_awake = b''.join(new_options)
    files['packs-claude/table.dat'], files['packs-claude/table.kof'] = _update_pack(
        archive, files['packs-claude/table.kof'], table_key,
        {'bufftable.bin': buffs + b''.join(added), 'battlecardawakebufftable.bin': updated_awake})
    files['packs-claude/lang_global.dat'], files['packs-claude/lang_en.kof'] = _update_pack(
        files['packs-claude/lang_global.dat'], files['packs-claude/lang_en.kof'], lang_key,
        {'bufftable.bin': language + b''.join(texts)})
    versions = json.loads(files['table-versions.json'])
    for key in ('table', 'lang_global'):
        versions[key] += 1
    files['table-versions.json'] = (json.dumps(versions, indent=2) + '\n').encode()
    return files


def install(root, backup):
    """Back up exact inputs, recheck them, replace packs and publish versions last."""
    root, backup = Path(root).resolve(), Path(backup).resolve()
    if backup.is_relative_to(root) or root.is_relative_to(backup):
        raise ValueError('backup and runtime must be separate directories')
    before = {name: (root / name).read_bytes() for name in FILES}
    replacement = build_patch(root)
    if replacement == before:
        return {'changed': False}
    backup.mkdir(parents=True, exist_ok=False)
    records = []
    for name in (*FILES, 'player.json'):
        path = root / name
        if not path.exists():
            continue
        content = before[name] if name in before else path.read_bytes()
        if name == 'player.json':
            json.loads(content)
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise OSError('backup verification failed')
        records.append({'path': name, 'sha256': digest})
    (backup / 'manifest.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    for name in FILES:
        if (root / name).read_bytes() != before[name]:
            raise RuntimeError('input changed since planning; no installation performed')
    for name in FILES:  # table-versions.json is deliberately last
        target = root / name
        temporary = target.with_name(target.name + '.awaken-patch-tmp')
        with temporary.open('xb') as stream:
            stream.write(replacement[name])
        temporary.replace(target)
        if target.read_bytes() != replacement[name]:
            raise OSError('installed file differs from validated patch')
    report = {'changed': True, 'backup': str(backup), 'versions': json.loads(replacement['table-versions.json']),
              'sha256': {name: hashlib.sha256(data).hexdigest() for name, data in replacement.items()},
              'profile_edited': False}
    (backup / 'installed.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-data', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.server_data, args.backup), indent=2))


if __name__ == '__main__':
    main()
