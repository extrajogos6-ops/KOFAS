"""Prepare rank 500 and a correctly framed original lobby for the local 1.11 client."""
from pathlib import Path
import argparse
import json
from local_awaken_balance import _unpack, _update_pack, _rows, _parts, _field, _edit

FILES = ('packs-claude/table.dat', 'packs-claude/table.kof', 'table-versions.json')
BACKGROUND = 'Prefabs/UI_Data/UI_Texture/BackgroundStage/Texture_Lobby_SS_Terry'


def build_patch(root, usn=1000001):
    root = Path(root)
    files = {name: (root / name).read_bytes() for name in FILES}
    key = json.loads((root / 'packs-claude/security.json').read_text())['SecurityDataTable']
    archive = files['packs-claude/table.dat']
    leveling = _unpack(archive, 'accountlevelingtable.bin', key)
    levels = _rows(leveling)
    if len(levels) not in (100, 500) or [r[2] for _, r in levels] != list(range(1, len(levels) + 1)):
        raise ValueError('unsupported account level table; expected the local 100 or 500-level curve')
    replacements = {}
    if len(levels) == 100:
        template, last = levels[-1]
        if last[3] != 10000 or last[4] != 505000:
            raise ValueError('not the reconstructed local account EXP curve')
        accumulated = last[4]
        extra = []
        for level in range(101, 501):
            accumulated += level * 100
            row = _edit(template, {2: (0, level), 3: (0, level * 100),
                                   4: (0, accumulated), 5: (0, last[5] + level - 100)})
            extra.append(_field(1, 2, row))
        leveling += b''.join(extra)
        replacements['accountlevelingtable.bin'] = leveling
        levels = _rows(leveling)
    background = _unpack(archive, 'lobbybgsettingtable.bin', key)
    updated = []
    for number, wire, value, raw in _parts(background):
        if number == 1 and wire == 2:
            # UV rectangle (0, .5, 1, .5): the landscape half of the original texture.
            value = _edit(value, {3: (2, BACKGROUND.encode()), 6: (0, 1),
                                   7: (2, BACKGROUND.encode()), 8: (0, 1)})
            raw = _field(number, wire, value)
        updated.append(raw)
    updated = b''.join(updated)
    if updated != background:
        replacements['lobbybgsettingtable.bin'] = updated
    if replacements:
        files['packs-claude/table.dat'], files['packs-claude/table.kof'] = _update_pack(
            archive, files['packs-claude/table.kof'], key, replacements)
        versions = json.loads(files['table-versions.json'])
        versions['table'] += 1
        files['table-versions.json'] = (json.dumps(versions, indent=2) + '\n').encode()
    config = {'usn': usn, 'rank': 500, 'exp_min': levels[-2][1][4],
              'exp_max': levels[-1][1][4] - 1, 'tier': 25, 'rating': 3400,
              'revision': 'rank500-diamond1-v1'}
    if config['exp_min'] != 12475000 or config['exp_max'] != 12524999:
        raise ValueError('unexpected maximum rank EXP interval')
    files['account-preset.json'] = (json.dumps(config, indent=2) + '\n').encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-data', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New review directory; never the active runtime')
    parser.add_argument('--usn', type=int, default=1000001)
    args = parser.parse_args()
    source, output = args.server_data.resolve(), args.output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('review output must be separate from the runtime')
    replacement = build_patch(source, args.usn)
    output.mkdir(parents=True, exist_ok=False)
    for name, content in replacement.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(f'Prepared {len(replacement)} files in {output}. No runtime or profile was modified.')


if __name__ == '__main__':
    main()
