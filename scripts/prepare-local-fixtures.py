"""Import only the table fixtures required by existing server tests; never start a game."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-data', type=Path, required=True,
                        help='Existing local KOFAS-Local-Server directory (read only)')
    args = parser.parse_args()
    source = args.server_data.resolve()
    security = Path('packs-claude/security.json')
    if (source / security).read_bytes() != (ROOT / 'server' / security).read_bytes():
        raise SystemExit('Table-key fixture differs from this snapshot; refusing mixed data.')
    files = [Path('packs-claude') / name for name in (
        'table.dat', 'table.kof', 'lang_global.dat', 'lang_en.kof',
        'prohibited_en_text_words.dat', 'prohibited_en_text_words.kof')]
    banner = Path('packs-claude/banner_en.dat')
    if not (source / banner).is_file():
        banner = Path('packs/banner_en.dat')
    files.append(banner)
    for relative in files:
        if not (source / relative).is_file():
            raise SystemExit(f'Missing fixture: {relative}')
    manifest = []
    for relative in files:
        src = source / relative
        target = ROOT / 'server' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != src.read_bytes():
            raise SystemExit(f'Existing fixture differs; preserve/review it before replacing: {relative}')
        shutil.copy2(src, target)
        manifest.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    output = ROOT / '.local'
    output.mkdir(exist_ok=True)
    (output / 'fixture-import.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {len(files)} ignored local fixtures. No profile, client or game process touched.')


if __name__ == '__main__':
    main()
