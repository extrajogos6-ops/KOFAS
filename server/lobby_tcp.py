"""Local FreeNet lobby server (127.0.0.1:18776) for the KOFAS 1.11.2 client.

Frame: int32 LE body length (low 2 bytes = length, high 2 = checksum, client does not check it) + protobuf body.
Bodies are NEO.C2S.Protocol.Request (client->server) / Response (server->client), schema recovered from the
client's embedded descriptor (work/kofas/claude/c2s.proto). Encryption mode is never enabled, so bodies are plain.
"""
import socket
import struct
import threading
import time
from pathlib import Path

ADDRESS, PORT = '127.0.0.1', 18776
LOG = (Path(__file__).resolve().parent / 'lobby-tcp.log').open('a', encoding='utf-8', buffering=1)

# MessageType values (c2s.proto)
KEEP_ALIVE, PING, PING_CHECK, SERVER_USER_CONNECTION, LOGIN = 1, 2, 3, 990, 1000
CHAT_MESSAGE, CHAT_HISTORY = 1300, 1301

# Lobby chat (solo, local). The chat popup (UIPopup_Chatting) only fills in - text list AND the sticker page
# (ChattingBase.Init -> UIUnit_StampPage.SetData) - after ChatManager.RecvChattingHistory, which the client calls when
# the lobby server answers CN_Chat_History (Request field 252 -> Response field 251 SN_Chat_History{result, list, end}).
# Unanswered, the stamp page stayed an empty placeholder (traced live 2026-10-19). Messages the player sends
# (CN_Chat_Message, field 251 {Chat_Info}) get a seq + time and come back as SN_Chat_Message (field 250); chat_type 1 =
# text, 2 = sticker (msg = StampTable index). Kept in chat_history.json (last CHAT_KEEP).
import json
CHAT_PATH = Path(__file__).resolve().parent / 'chat_history.json'
CHAT_KEEP = 100
CHAT_LOCK = threading.Lock()


def chat_load():
    try:
        return json.loads(CHAT_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def chat_info(m):
    return (fv(1, m['seq']) + fv(2, m['time']) + fv(3, m['type']) + fv(4, m['usn']) + fb(5, m['account'].encode())
            + fb(6, m['nick'].encode()) + fb(7, m['msg'].encode()))


def log(*a):
    LOG.write(time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a) + '\n')


def varint(n):
    n &= (1 << 64) - 1
    out = bytearray()
    while n > 127:
        out.append((n & 127) | 128)
        n >>= 7
    out.append(n)
    return bytes(out)


def fv(num, val):          # varint field
    return varint(num << 3) + varint(val)


def fb(num, data):         # length-delimited field
    return varint(num << 3 | 2) + varint(len(data)) + data


def parse(b):
    """Flat protobuf parse: {field: [values]} (bytes for length-delimited)."""
    out, i = {}, 0
    while i < len(b):
        key, i = _rv(b, i)
        f, w = key >> 3, key & 7
        if w == 0:
            v, i = _rv(b, i)
        elif w == 2:
            ln, i = _rv(b, i)
            v = b[i:i + ln]
            i += ln
        elif w == 1:
            v = b[i:i + 8]; i += 8
        elif w == 5:
            v = b[i:i + 4]; i += 4
        else:
            raise ValueError('wire type %d' % w)
        out.setdefault(f, []).append(v)
    return out


def _rv(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 127) << s; s += 7
        if c < 128:
            return r, i


HEADER = 4
LEN_INCLUDES_HEADER = False   # verified against the client's parser by trial (see lobby-tcp.log)


PRE_KEY = b'preencryptedkeyy'   # CUserToken ctor: initial XOR key for both directions


def xor(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)) if key else data


def frame(body):
    n = len(body) + (HEADER if LEN_INCLUDES_HEADER else 0)
    return struct.pack('<HH', n, 0) + body


def response(seq, mtype, *fields):
    return fv(1, seq) + fv(2, mtype) + b''.join(fields)


class Client(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__(daemon=True)
        self.c, self.addr, self.buf = conn, addr, b''
        self.key = PRE_KEY

    def send(self, body):
        self.c.sendall(frame(xor(body, self.key)))

    def run(self):
        log('connect', self.addr)
        # Server speaks first: SA_Server_User_Connection{result_type=SUCCESS} -> client sends CQ_Login
        self.send(response(0, SERVER_USER_CONNECTION, fb(105, b'')))
        try:
            while True:
                d = self.c.recv(65536)
                if not d:
                    break
                self.buf += d
                while len(self.buf) >= 4:
                    ln = struct.unpack_from('<H', self.buf, 0)[0] - (HEADER if LEN_INCLUDES_HEADER else 0)
                    if ln < 0 or len(self.buf) < 4 + ln:
                        if ln < 0: log('bad length', self.buf[:16].hex()); self.buf = b''
                        break
                    body, self.buf = self.buf[4:4 + ln], self.buf[4 + ln:]
                    self.handle(xor(body, self.key))
        except OSError as e:
            log('error', repr(e))
        log('closed', self.addr)
        self.c.close()

    def handle(self, body):
        try:
            p = parse(body)
        except Exception as e:
            log('unparsed', len(body), body[:80].hex(), repr(e)); return
        seq = p.get(1, [0])[0]; mtype = p.get(2, [0])[0]
        log('recv type', mtype, 'seq', seq, 'fields', sorted(p), body[:120].hex())
        if mtype == LOGIN:
            login = parse(p.get(100, [b''])[0])
            account = login.get(1, [b''])[0]
            client_key = login.get(3, [b'0' * 16])[0]
            # CUserToken.SetDecryptedKey: key[i] = client_key[i] ^ server_key[i]. Echoing the client key gives
            # 16 zero bytes, i.e. XOR becomes a no-op for everything after this reply.
            self.send(response(seq, LOGIN, fb(3, account), fb(110, fv(1, 0) + fb(2, client_key) + fv(3, 1))))
            self.key = bytes(16)
            log('login ok', account, 'client key', client_key)
        elif mtype in (KEEP_ALIVE,):
            ka = parse(p.get(11, [b''])[0])
            self.send(response(seq, KEEP_ALIVE, fb(21, fv(1, ka.get(1, [int(time.time() * 1000)])[0]))))
        elif mtype in (PING, PING_CHECK):
            self.send(response(seq, mtype, fb(20, fv(1, 1))))
        elif mtype == CHAT_HISTORY:
            with CHAT_LOCK:
                hist = chat_load()
            body = b''.join(fb(2, chat_info(m)) for m in hist[-CHAT_KEEP:]) + fv(3, 1)   # result SUCCESS (0) omitted
            self.send(response(seq, CHAT_HISTORY, fb(251, body)))
            log('chat history sent', len(hist))
        elif mtype == CHAT_MESSAGE:
            ci = parse(parse(p.get(251, [b''])[0]).get(1, [b''])[0])
            g = lambda f, d: ci.get(f, [d])[0]
            with CHAT_LOCK:
                hist = chat_load()
                m = {'seq': (hist[-1]['seq'] + 1) if hist else 1, 'time': int(time.time() * 1000), 'type': int(g(3, 1)),
                     'usn': int(g(4, 0)), 'account': g(5, b'').decode('utf-8', 'replace'), 'nick': g(6, b'').decode('utf-8', 'replace'),
                     'msg': g(7, b'').decode('utf-8', 'replace')}
                hist = (hist + [m])[-CHAT_KEEP:]
                CHAT_PATH.write_text(json.dumps(hist, ensure_ascii=False), encoding='utf-8')
            self.send(response(seq, CHAT_MESSAGE, fb(250, fb(2, chat_info(m)))))
            log('chat message', m['type'], m['msg'][:40])


def main():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ADDRESS, PORT)); s.listen(8)
    log('listening', PORT)
    while True:
        Client(*s.accept()).start()


if __name__ == '__main__':
    main()
