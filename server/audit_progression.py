import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
import local_progression


def audit(player: dict) -> dict:
    config = json.loads((ROOT / 'awaken.json').read_text())
    problems = []
    awakened = 0
    for character in player['CharacterList']:
        index = character['CharacterIndex']
        phase = character.get('Awaken', 0)
        exp = character.get('AwakenExp', 0)
        reasons = []
        row = {'CharacterIndex': index, 'Awaken': phase, 'AwakenExp': exp}
        try:
            level = local_progression.normal_level(character)
            row.update(NormalLevel=level, NormalMaxLevel=local_progression.normal_level_cap(character))
            if type(phase) is not int or not 0 <= phase <= config['fighters'][str(index)]['maxPhase']:
                reasons.append('invalid awakening phase')
            elif phase > 0:
                awakened += 1
                if level < 90:
                    reasons.append('awakened fighter has normal level below 90')
                if type(exp) is not int or exp < 0:
                    reasons.append('invalid awakening EXP')
                elif exp > config['levelExp'][10 * phase - 2]:
                    reasons.append('awakening EXP exceeds current phase limit')
            elif exp != 0:
                reasons.append('awakening EXP without an awakening phase')
        except (ValueError, KeyError, TypeError) as error:
            reasons.append('invalid saved progression: ' + str(error))
        if reasons:
            row['Issues'] = reasons
            problems.append(row)
    return {'CharactersChecked': len(player['CharacterList']), 'AwakenedCharacters': awakened,
            'CharactersWithIssues': len(problems), 'Issues': problems, 'Modified': False}


def main():
    parser = argparse.ArgumentParser(description='Read-only audit of saved fighter progression')
    parser.add_argument('--player', type=Path, default=ROOT / 'player.json')
    args = parser.parse_args()
    player = json.loads(args.player.read_text(encoding='utf-8-sig'))
    print(json.dumps(audit(player), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
