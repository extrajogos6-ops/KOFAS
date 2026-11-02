"""Isolated KOFAS 1.17.0 bootstrap. Requires the exact validated client build.

Owns only the game and local services it starts. It never writes to the original
installation or the reference save. Runtime changes disappear with the process.
"""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
GAME = ROOT / 'outputs' / 'KOFAS-PC-Test'
SERVER = ROOT / 'outputs' / 'KOFAS-Local-Server'
DIAGNOSTICS = ROOT / 'diagnostics'
EXPECTED = {
    'GameAssembly.dll': '07beb870deee2a580d140041ad629e7149ed5a887d76323c36e63c9b532c03e2',
    'UnityPlayer.dll': '8a5753e1b38f73a4c05a3dba053f8863db53d717798067f18e49cc8efe4b7cf1',
    'KOF ALLSTAR_Data/il2cpp_data/Metadata/global-metadata.dat':
        'c059c55362e9ad7a013be02baeb5abbfce2273eb3fb236a58fb7a9e818888813',
}
HTTP_PORT, TCP_PORT = 18775, 18776


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate_client():
    for name, expected in EXPECTED.items():
        path = GAME / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f'Cliente incompatível: {name}. Os hooks não foram carregados.')


def health():
    try:
        with urlopen(f'http://127.0.0.1:{HTTP_PORT}/health', timeout=1) as response:
            result = json.load(response)
    except OSError:
        return False
    if result.get('project') != 'kofas-local-bootstrap' or result.get('client_version') != '1.17.0':
        raise RuntimeError(f'A porta {HTTP_PORT} pertence a outro serviço.')
    return True


def port_open(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.3):
            return True
    except OSError:
        return False


def running_experimental_game():
    marker = DIAGNOSTICS / 'active-probe.json'
    if not marker.exists():
        return False
    try:
        pid = int(json.loads(marker.read_text(encoding='utf-8'))['pid'])
    except (OSError, ValueError, KeyError):
        return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        count = ctypes.c_uint32(len(buffer))
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(count)):
            raise RuntimeError('Não foi possível verificar a identidade do processo experimental.')
        return Path(buffer.value).resolve() == (GAME / 'KOF ALLSTAR.exe').resolve()
    finally:
        kernel.CloseHandle(handle)


def main():
    import frida
    device = frida.get_local_device()
    validate_client()
    DIAGNOSTICS.mkdir(exist_ok=True)
    if running_experimental_game():
        raise RuntimeError('A instalação experimental já está em execução.')
    stop = DIAGNOSTICS / 'stop-probe'
    stop.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment['__COMPAT_LAYER'] = 'RunAsInvoker'
    environment['OPENSSL_ia32cap'] = ':~0x20000000'
    environment['KOFAS_PLAYER'] = str(SERVER / 'player.experimental.json')
    if not (SERVER / 'player.experimental.json').exists():
        (SERVER / 'player.experimental.json').write_bytes((SERVER / 'player.reference-1.11.2.json').read_bytes())
    owned = []
    logs = []
    game = None
    session = None
    finished = threading.Event()
    tag = time.strftime('run-%Y%m%d-%H%M%S')
    events = (DIAGNOSTICS / (tag + '-events.jsonl')).open('w', encoding='utf-8', buffering=1)
    prefs_path = ROOT / 'preferences.json'
    preferences = json.loads(prefs_path.read_text(encoding='utf-8')) if prefs_path.exists() else {}
    def message_received(message, data):
        event = message.get('payload', {}) if message.get('type') == 'send' else {}
        if event.get('event') == 'portable-pref':
            if event['op'] == 'set':
                preferences[event['key']] = event['value']
            elif event['op'] == 'delete':
                preferences.pop(event['key'], None)
            elif event['op'] == 'clear':
                preferences.clear()
            temporary = prefs_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(preferences, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(prefs_path)
            return
        events.write(json.dumps(message, ensure_ascii=False) + '\n')
    try:
        if not health():
            log = (SERVER / 'server-output.log').open('w', encoding='utf-8')
            logs.append(log)
            owned.append(subprocess.Popen([sys.executable, '-B', str(SERVER / 'server.py')],
                                          cwd=SERVER, env=environment, stdout=log, stderr=log,
                                          creationflags=0x08000000))
            for _ in range(80):
                if health():
                    break
                if owned[-1].poll() is not None:
                    raise RuntimeError('O servidor HTTP não iniciou; consulte server-output.log.')
                time.sleep(.1)
            else:
                raise RuntimeError('Timeout na inicialização do servidor HTTP.')
        if port_open(TCP_PORT):
            # A running service must not be mistaken for an owned experimental lobby.
            raise RuntimeError(f'A porta {TCP_PORT} já está ocupada; encerre a outra sessão de teste.')
        log = (SERVER / 'lobby-output.log').open('w', encoding='utf-8')
        logs.append(log)
        lobby = subprocess.Popen([sys.executable, '-B', str(SERVER / 'lobby_tcp.py')], cwd=SERVER,
                                 env=environment, stdout=log, stderr=log, creationflags=0x08000000)
        owned.append(lobby)
        for _ in range(50):
            if port_open(TCP_PORT):
                break
            if lobby.poll() is not None:
                raise RuntimeError('O lobby TCP não iniciou; consulte lobby-output.log.')
            time.sleep(.1)
        else:
            raise RuntimeError('Timeout na inicialização do lobby TCP.')
        game = subprocess.Popen([str(GAME / 'KOF ALLSTAR.exe'), '-screen-fullscreen', '0',
                                 '-screen-width', '1280', '-screen-height', '720', '-logFile',
                                 str(DIAGNOSTICS / (tag + '-unity.log'))], cwd=GAME,
                                env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # The native SDK closes foreign handles to its game process. Frida owns
        # lifecycle observation; release Popen's handle before SDK initialization.
        game._handle.Close()
        game.returncode = 0
        (SERVER / 'game.pid').write_text(str(game.pid), encoding='ascii')
        (DIAGNOSTICS / 'active-probe.json').write_text(json.dumps({
            'pid': game.pid, 'executable': str(GAME / 'KOF ALLSTAR.exe'), 'tag': tag}, indent=2), encoding='utf-8')
        session = device.attach(game.pid)
        session.on('detached', lambda *args: finished.set())
        script_text = (TOOLS / 'runtime_117.js').read_text(encoding='utf-8')
        cache = DIAGNOSTICS / 'crash-reporter-cache'
        cache.mkdir(exist_ok=True)
        script_text = script_text.replace('__HOOKS__', (TOOLS / 'hooks-1.17.json').read_text(encoding='utf-8'))
        script_text = script_text.replace('__CACHE__', json.dumps(str(cache)))
        script_text = script_text.replace('__PREFS__', json.dumps(preferences))
        script_text = script_text.replace('__MUTE__', 'true' if os.environ.get('KOFAS_TEST_MUTE') == '1' else 'false')
        script = session.create_script(script_text)
        script.on('message', message_received)
        script.load()
        while not finished.wait(.25):
            if stop.exists():
                device.kill(game.pid)
                finished.wait(5)
                break
    finally:
        if game is not None and not finished.is_set():
            try:
                device.kill(game.pid)
            except Exception:
                pass
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
        for process in reversed(owned):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        events.close()
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
