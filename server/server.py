"""Local bootstrap experiment for the archived KOFAS 1.11.2 PC client.

Bootstrap routes and an experimental local PC account are implemented.
Unknown routes fail explicitly; a successful fixture is not proof of gameplay.
"""
from pathlib import Path
import base64,json,re,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from local_auth import decode_request,authenticate,start_session
from local_poll import poll,poll_safe
import local_player
ADDRESS='127.0.0.1'
PORT=18775
# the untouched original client's cache; a portable copy ships only the test client, whose cache holds the same bundles
PC_CACHE=ROOT.parent/('KOFAS-PC' if (ROOT.parent/'KOFAS-PC').is_dir() else 'KOFAS-PC-Test')/'storage'/'cache'
ASSET_ROOT=PC_CACHE/'assetbundles'
API_DEFAULTS=json.loads((ROOT/'api-defaults.json').read_text()) if (ROOT/'api-defaults.json').exists() else {'responses':{},'paths':{}}
# Billing replies carry AccountMoney; as untyped stubs ({ResultCode} only) the client read a missing wallet and showed AP 0/0,
# rubies 0 and gold 0 after a shop purchase tap (seen live 2026-10-19). Typed defaults get the real wallet below; nothing is sold.
for _p,_c in (('/api/billing/nmbillVerify','BillingVerifyNmbillResponse'),('/api/billing/billrewardVerify','BillingVerifyBillrewardResponse'),
              ('/api/billing/nmbillInitialize','BillingInitializeResponse')):
    if _c in API_DEFAULTS['responses']: API_DEFAULTS['paths'].setdefault(_p,_c)
ASSET_INDEX=json.loads((ROOT/'asset-index.json').read_text()) if (ROOT/'asset-index.json').exists() else {}
# Recoloured bundle copies (claude/recolor_unleashed.py): served instead of the originals, with their md5/size patched into
# bundle.manifest (the client checks each cached bundle against that md5 and downloads a changed one).
MOD_DIR=ROOT/'mod-bundles'
MOD_BUNDLES=json.loads((MOD_DIR/'mod-manifest.json').read_text()) if (MOD_DIR/'mod-manifest.json').exists() else {}
def bundle_manifest():
    lines=(ROOT/'bundle.manifest').read_bytes().decode('utf-8').split('\r\n')
    for i,l in enumerate(lines):
        name=l.split(':',1)[0]
        if name in MOD_BUNDLES: lines[i]='%s:%s:%d'%(name,MOD_BUNDLES[name]['md5'],MOD_BUNDLES[name]['size'])
    return '\r\n'.join(lines).encode('utf-8')
STATE={'client_version':'1.17.0','stage':'experimental-117-bootstrap','configuration_requests':0,'table_version_requests':0,'table_pack_requests':0,'local_auth_successes':0,'local_auth_rejections':0,'unimplemented_requests':0}
LOCK=threading.Lock()
def configuration():
    return json.loads((ROOT/'configuration.json').read_text(encoding='utf-8-sig'))
def encrypted_configuration():
    payload=json.dumps(configuration(),ensure_ascii=False,separators=(',',':')).encode('utf-8')
    # Client-shipped constants used by ServerSelect.RecvDownloadSecuredConfig.
    cipher=AES.new(b'neo4567neo123456',AES.MODE_CBC,iv=b'neo4567890neo456')
    return base64.b64encode(cipher.encrypt(pad(payload,16)))
def record(method,path,status):
    # No query strings, request bodies, passwords, or account tokens are retained.
    item={'time':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'method':method,'path':path,'status':status}
    with LOCK:
        with (ROOT/'requests.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(item)+'\n')
    print(json.dumps(item),flush=True)
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,data,content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        path=urlsplit(self.path).path
        language_fallbacks={
            '/tables/common/table/lang_pt.dat':'/tables/common/table/lang_en.dat',
            '/tables/common/table/lang_pt.kof':'/tables/common/table/lang_en.kof',
            '/tables/common/table/prohibited_pt_text_words.dat':'/tables/common/table/prohibited_en_text_words.dat',
            '/tables/common/table/prohibited_pt_text_words.kof':'/tables/common/table/prohibited_en_text_words.kof',
            '/tables/common/banner/pt.dat':'/tables/common/banner/en.dat',
        }
        resource_path=language_fallbacks.get(path,path)
        if path=='/health':
            self.reply(200,json.dumps({'project':'kofas-local-bootstrap',**STATE}).encode())
            return
        if path.rsplit('/',1)[-1].startswith('config_') and path.endswith('_win.json'):
            STATE['configuration_requests']+=1
            data=encrypted_configuration()
            record('GET',path,200)
            self.reply(200,data,'text/plain; charset=utf-8')
            return
        if path=='/tables/common/table/version.kof':
            STATE['table_version_requests']+=1
            data=(ROOT/'table-versions.json').read_bytes()
            record('GET',path,200)
            self.reply(200,data)
            return
        if path=='/tables/common/banner/version.kof':
            record('GET',path,200)
            self.reply(200,json.dumps({'banner_en':22042801}).encode())
            return
        table_packs={
            '/tables/common/table/table.dat':'table.dat',
            '/tables/common/table/lang_global.dat':'lang_global.dat',
            '/tables/common/table/lang_en.dat':'lang_global.dat',
            '/tables/common/table/prohibited_en_text_words.dat':'prohibited_en_text_words.dat',
            '/tables/common/banner/en.dat':'banner_en.dat',
        }
        if resource_path in table_packs:
            STATE['table_pack_requests']+=1
            name=table_packs[resource_path]
            data=((ROOT/'packs-claude'/name) if (ROOT/'packs-claude'/name).exists() else (ROOT/'packs'/name)).read_bytes()
            record('GET',path,200)
            self.reply(200,data,'application/zip')
            return
        # Encrypted {name,hash} manifests for the locally built tables.
        manifests={'/tables/common/table/table.kof':'table.kof','/tables/common/table/lang_en.kof':'lang_en.kof','/tables/common/table/prohibited_en_text_words.kof':'prohibited_en_text_words.kof'}
        if resource_path in manifests:
            data=(ROOT/'packs-claude'/manifests[resource_path]).read_bytes()
            record('GET',path,200)
            self.reply(200,data,'application/octet-stream')
            return
        # BannerManager 'CDN;<name>' banners (gacha button/background art): the client GETs /cdn/<name>; serve the
        # shipped copy from the PC cache (storage/cache/banner/<name>.png). Names are plain file stems only.
        if path.startswith('/cdn/') and path.count('/')==2 and re.fullmatch(r'[A-Za-z0-9_\-]+',path[5:]):
            f=ROOT/'banners'/(path[5:].lower()+'.png')   # composed banners (work/kofas/claude/smash_banners.py) first
            if not f.exists(): f=PC_CACHE/'banner'/(path[5:].lower()+'.png')
            if f.exists():
                record('GET',path,200)
                self.reply(200,f.read_bytes(),'image/png')
                return
        asset_prefix='/cdn/assets/win/r0/dxt/'
        if path.startswith(asset_prefix):
            name=path[len(asset_prefix):]
            if name in {'snapshot_gtuto.lst','snapshot_btuto.lst','snapshot_gtuto_only.lst'}:
                # Every bundle is already in the local cache; an empty tutorial list stops the client from
                # loading all 7,102 bundles at tutorial start.
                record('GET',path,200)
                self.reply(200,b'','text/plain; charset=utf-8')
                return
            if name in {'bundle.manifest','fullbundles.snapshot'}:
                data=bundle_manifest()
                record('GET',path,200)
                self.reply(200,data,'text/plain; charset=utf-8')
                return
            if name in MOD_BUNDLES and (MOD_DIR/name).exists():
                data=(MOD_DIR/name).read_bytes()
                record('GET',path,200)
                self.reply(200,data,'application/octet-stream')
                return
            if name in ASSET_INDEX:
                data=(ASSET_ROOT/ASSET_INDEX[name]['file']).read_bytes()
                record('GET',path,200)
                self.reply(200,data,'application/octet-stream')
                return
        STATE['unimplemented_requests']+=1
        record('GET',path,501)
        self.reply(501,json.dumps({'error':'not_implemented','route':path,'stage':STATE['stage']}).encode())
    def do_POST(self):
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:
            self.reply(400,b'{"error":"invalid_length"}')
            return
        if size<0 or size>1048576:
            self.reply(413,b'{"error":"request_too_large"}')
            return
        body=self.rfile.read(size)
        path=urlsplit(self.path).path
        if path=='/api/session/poll':
            # A refused poll used to get a 400: when that was the first poll after sign-in (it carries the schedule list)
            # the client had no schedules all session (raid boss selector: only Omega; sporadic, 5 times 2026-10-12..25).
            # Now an unreadable or unusual request still gets the schedules (poll_safe), and what it was is logged.
            payload=None; why=''
            try:
                payload=decode_request(body,self.headers.get('Content-Type',''))
            except (ValueError,OSError,EOFError,UnicodeError) as error:
                why='decode: %s'%error
            try:
                if why: raise ValueError(why)
                response=poll(payload)
            except ValueError as error:
                why=why or 'poll: %s'%error
                response=poll_safe(payload)
                try:
                    with open(ROOT/'poll_errors.jsonl','a',encoding='utf-8') as f:
                        f.write(json.dumps({'time':time.strftime('%Y-%m-%dT%H:%M:%S'),'why':why,
                            'contentType':self.headers.get('Content-Type',''),'bodyBytes':len(body),'bodyHead':body[:48].hex(),
                            'payload':payload if isinstance(payload,dict) else None},default=str)+chr(10))
                except OSError:
                    pass
            record('POST',path,200)
            self.reply(200,json.dumps(response,separators=(',',':')).encode())
            return
        if path in ('/api/player/lobby','/api/player/profile'):
            player=local_player.load()
            if player:
                record('POST',path,200)
                self.reply(200,json.dumps(local_player.account_profile_response(player),separators=(',',':')).encode())
                return
        if path=='/api/player/poll':
            path='/api/session/poll'
        if path=='/api/session/create':
            try:
                payload=decode_request(body,self.headers.get('Content-Type',''))
            except (ValueError,OSError,EOFError,UnicodeError):
                record('POST',path,400); self.reply(400,b'{"error":"invalid_request"}'); return
            nick=str(payload.get('NickName') or 'Player')[:24]
            try: cidx=int(payload.get('CharacterIndex') or 101)
            except (TypeError,ValueError): cidx=101
            player=local_player.create(nick,cidx)
            record('POST',path,200)
            self.reply(200,json.dumps(local_player.session_create_response(player),separators=(',',':')).encode())
            return
        if path in {'/api/session/pcAuth','/api/session/start'}:
            try:
                payload=decode_request(body,self.headers.get('Content-Type',''))
                response,accepted=(authenticate if path.endswith('/pcAuth') else start_session)(payload)
            except (ValueError,OSError,EOFError,UnicodeError):
                record('POST',path,400)
                self.reply(400,b'{"error":"invalid_local_auth_request"}')
                return
            with LOCK:
                STATE['local_auth_successes' if accepted else 'local_auth_rejections']+=1
            record('POST',path,200)
            self.reply(200,json.dumps(response,separators=(',',':')).encode())
            return
        if path.startswith('/api/'):
            # Generic success for game APIs we have not modelled yet: protobuf-from-JSON leaves every field at
            # its default. Logged as status 299 so stubbed routes are easy to find in requests.jsonl.
            STATE['unimplemented_requests']+=1
            cls=API_DEFAULTS['paths'].get(path)
            body_out=dict(API_DEFAULTS['responses'].get(cls,{'ResultCode':0,'ResultMessage':''}))
            player=local_player.load()
            if player:
                # never let a default reply zero the player's wallet/level on the client
                for k in ('AccountMoney','PlayerAccount'):
                    if k in body_out: body_out[k]=player[k]
                try: payload=decode_request(body,self.headers.get('Content-Type',''))
                except (ValueError,OSError,EOFError,UnicodeError) as error:
                    # still answered with {} (as before), but what could not be read is kept: request_errors.jsonl
                    # (a raid BATTLE START arrived like this once, 2026-10-25; its cause is unknown)
                    payload={}
                    try:
                        with open(ROOT/'request_errors.jsonl','a',encoding='utf-8') as f:
                            f.write(json.dumps({'time':time.strftime('%Y-%m-%dT%H:%M:%S'),'path':path,'why':str(error),
                                'contentType':self.headers.get('Content-Type',''),'bodyBytes':len(body),'bodyHead':body[:48].hex(),
                                'bodyTail':body[-16:].hex()})+chr(10))
                    except OSError:
                        pass
                body_out.update(local_player.route_overrides(path,player,payload if isinstance(payload,dict) else {}))
            # Many parsers call GameDefine.UpdateServerTime(resp.ServerUtcTime) (Ghidra xrefs: shopGoodsQtyList, renew,
            # questEventList, ...); a default 0 reset the client clock to year 1 and closed every time window (seen live:
            # dtServerTimeNow ~0 -> League IsOpen false). Always send the current time.
            for k in ('ServerUtcTime','ServerTime'):
                if k in body_out and not body_out.get(k): body_out[k]=int(time.time()*1000)
            record('POST',path,299 if cls else 298)   # 299 = typed default, 298 = untyped stub
            self.reply(200,json.dumps(body_out,separators=(',',':')).encode())
            return
        STATE['unimplemented_requests']+=1
        record('POST',path,501)
        self.reply(501,json.dumps({'error':'not_implemented','stage':STATE['stage']}).encode())
if __name__=='__main__':
    server=ThreadingHTTPServer((ADDRESS,PORT),Handler)
    print(f'Local configuration experiment: http://{ADDRESS}:{PORT}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
