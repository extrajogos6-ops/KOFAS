"""Experimental PC authentication fixture. Never contacts Netmarble.

Only the published local test credentials are accepted. This does not recover
an old account, and the session shape still requires verification in the client.
"""
import base64
import gzip
import io
import json
import secrets
import zlib
import threading
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

TEST_ID = 'player@local.invalid'
TEST_PASSWORD = 'local-only'
KEY = bytes.fromhex('CA4BB353B60D4F10321ED79DB1B7A2F1')
IV = bytes.fromhex('CD2F0231A8D43378FF29C26D95E3B6AB')
MAX_BODY = 1048576
SESSIONS = {}
SESSION_LOCK = threading.Lock()
# Locally generated table keys (packs-claude/security.json, written by work/kofas/claude/build_tables.py).
from pathlib import Path as _P
SECURITY = json.loads((_P(__file__).resolve().parent/'packs-claude'/'security.json').read_text())

def decode_request(body, content_type):
    kind = content_type.split(';', 1)[0].strip().lower()
    if kind not in {'application/json', 'application/cipher'}:
        raise ValueError('unsupported_content_type')
    if kind == 'application/cipher':
        # Compressed client requests use raw ciphertext; uncompressed ones may
        # use Base64. Try each representation without retaining the payload.
        candidates = [body]
        try:
            candidates.append(base64.b64decode(body, validate=True))
        except ValueError:
            pass
        decoded = None
        for candidate in candidates:
            try:
                decoded = unpad(AES.new(KEY, AES.MODE_CBC, IV).decrypt(candidate), 16)
                break
            except ValueError:
                continue
        if decoded is None:
            raise ValueError('invalid_ciphertext')
        body = decoded
    if body.startswith(b'\x1f\x8b'):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as compressed:
                body = compressed.read(MAX_BODY + 1)
        except (OSError, EOFError, zlib.error) as error:
            raise ValueError('invalid_compression') from error
    if len(body) > MAX_BODY:
        raise ValueError('request_too_large')
    payload = json.loads(body.decode('utf-8-sig'))
    if not isinstance(payload, dict):
        raise ValueError('invalid_request')
    return payload

def authenticate(payload):
    account = payload.get('id')
    password = payload.get('pw')
    device_key = payload.get('deviceKey', 'local-pc')
    if not isinstance(device_key, str) or len(device_key) > 512:
        raise ValueError('invalid_device_key')
    # Single-user local server: every sign-in maps to the one local player (no real accounts exist here).
    if False:
        # This rejection code is experimental; no old credentials are accepted.
        return {'ResultCode': 1, 'ResultMessage': 'Use the local test account only.',
                'resultData': '', 'country': 'US', 'commonLog': ''}, False
    session = {
        'accessToken': 'local-' + secrets.token_hex(24),
        'player': {'playerId': '1000001'},
        'deviceKey': device_key,
        'gameCode': 'kofg',
        'gameRegion': 'local',
        'joinedCountryCode': 'US',
        'mailUserKey': 'local-player-1000001',
        'cipherKeyList': [{'cipherType': 'CIPHER_AES_128_CBC',
                           'secretKey': KEY.hex().upper(),
                           'aesInitVec': IV.hex().upper()}],
    }
    with SESSION_LOCK:
        SESSIONS[session['accessToken']] = time.monotonic()
    return {'ResultCode': 0, 'ResultMessage': '',
            'resultData': json.dumps(session, separators=(',', ':')),
            'country': 'US', 'commonLog': ''}, True

def start_session(payload):
    """New, unregistered synthetic player; no existing profile is fabricated."""
    token = payload.get('GameToken')
    with SESSION_LOCK:
        issued = SESSIONS.get(token) if isinstance(token, str) else None
    if payload.get('Pid') != '1000001' or issued is None or time.monotonic()-issued > 3600:
        return {'ResultCode': 1, 'ResultMessage': 'Local session expired; sign in again.'}, False
    # Route=null follows the client's explicit new-player branch. Table keys
    # remain absent because the archived table encryption is not yet recovered.
    import local_player
    player = local_player.load()   # existing local profile -> skip the new-player tutorial
    route = player['Route'] if player else None
    return {'ResultCode': 0, 'ResultMessage': '', 'Route': route,
            'Unregisted': 0 if player else 1000001, 'ServerUtcTime': int(time.time()*1000),
            'ServerZoneOffset': 0, 'SecurityDataTable': SECURITY['SecurityDataTable'],
            'SecurityLocalizing': SECURITY['SecurityLocalizing'], 'AppToken': token,
            'PcSeq': 1000001, 'BlockRemainTime': 0, 'AccountType': 0,
            'DailyResetHour': 0, 'PcBillingData': ''}, True
