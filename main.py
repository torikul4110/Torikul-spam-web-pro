import os, sys, time, json, ssl, socket, threading, asyncio, base64, binascii, re, jwt, pickle, random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, Response, stream_with_context, send_file
from functools import wraps
import requests
import urllib3
from Pb2 import MajoRLoGinrEq_pb2, xKEys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from google.protobuf.timestamp_pb2 import Timestamp
from google_play_scraper import app as play_store_info 
import aiohttp

from xC4 import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== LOGIN CONFIG ====================
ADMIN_PASSWORD = "TORIKULJOD"
SECRET_KEY = "mahir_system_secret_key_2024"

# ==================== ফ্লাস্ক অ্যাপ ====================
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ==================== LOGIN REQUIRED DECORATOR ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== গ্লোবাল ভেরিয়েবল ====================
connected_clients = {}
connected_clients_lock = threading.Lock()
active_spam_targets = {}
active_spam_lock = threading.Lock()
spam_threads = {}
spam_threads_lock = threading.Lock()
target_status_cache = {}
squad_targets = {}
SQUAD_JOIN_DURATION = 2 * 60 * 60
STATUS_CHECK_INTERVAL = 1
ACCOUNT_REFRESH_INTERVAL = 10 * 60

ACCOUNTS_FILE = "accs.txt"
SQUAD_DATA_FILE = "squad_data.json"
TARGETS_PASSWORD = "HUNTERTORIKUL"
TORIKUL_BANNERS = [
    "https://mahir-photo-url.vercel.app/image/Picsart_26-07-17_09-51-40-755.jpg",
    "https://mahir-photo-url.vercel.app/image/Picsart_26-07-17_09-50-50-396.jpg",
    "https://mahir-photo-url.vercel.app/image/Picsart_26-07-17_09-49-58-880.jpg"
]
# ডিফল্ট হিসেবে তালিকার প্রথমটি থাকবে
DEFAULT_BANNER = TORIKUL_BANNERS[0]
is_resetting = False  # রিসেট চলছে কিনা ট্র্যাক করার জন্য

C = "\033[96m"
G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
RS = "\033[0m"
BOLD = "\033[1m"

BADGES = {
    "V_BADGE": 32768,
    "PRO_BADGE": 262144,
    "CRAFTLAND": 1048576,
    "MODERATOR": 2048,
    "SMALL_V": 64,
}

# ================================================================
# 🔄 LIVE UPDATE SYSTEM
# ================================================================

def AuToUpDaTE():
    try:
        print("\033[96m🌐 Fetching live version from Play Store...\033[0m")
        data = play_store_info('com.dts.freefireth', lang="fr", country='CA')
        store_version = data.get("version")

        if not store_version:
            print("\033[91m❌ Critical Error: Could not detect Play Store version!\033[0m")
            sys.exit(1)

        api_url = f"https://version.ggwhitehawk.com/live/ver.php?version={store_version}&lang=fr&device=android&channel=android"
        r = requests.get(api_url, timeout=15)
        
        if r.status_code != 200:
            print(f"\033[91m❌ Server Error: API returned status {r.status_code}\033[0m")
            sys.exit(1)

        json_data = r.json()
        login_url = json_data.get('server_url')
        ob_version = json_data.get('latest_release_version')
        remote_patch_ver = json_data.get('remote_version')

        if not all([login_url, ob_version, remote_patch_ver]):
            print("\033[91m❌ Error: API response is missing critical data!\033[0m")
            sys.exit(1)

        return login_url, ob_version, remote_patch_ver, store_version

    except Exception as e:
        print(f"\033[91m❌ Update System Failure: {e}\033[0m")
        sys.exit(1)

try:
    temp_url, temp_ob, temp_remote, temp_store = AuToUpDaTE()
    
    DYNAMIC_SERVER_URL = temp_url.rstrip('/')
    CURRENT_OB = temp_ob
    FREEFIRE_VERSION_NAME = temp_remote  
    STORE_VERSION = temp_store           

    print(f"""
\033[1;92m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 LIVE DATA LOADED (STRICT MODE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Current OB         : \033[1;97m{CURRENT_OB}\033[1;92m
🛒 Play Store Version : \033[1;97m{STORE_VERSION}\033[1;92m
🎮 Remote Version     : \033[1;97m{FREEFIRE_VERSION_NAME}\033[1;92m
🌐 Dynamic Server     : \033[1;97m{DYNAMIC_SERVER_URL}\033[1;92m

✅ System is ready with latest patch info.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
\033[0m""")

except Exception as e:
    print(f"\033[91m❌ Execution Error: {e}\033[0m")
    sys.exit(1)

# ==================== FILE LOADERS ====================
def load_unified_accounts(filename="accs.txt"):
    all_accounts = []
    processed_list = []
    
    try:
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                f.write("# Format: UID:PASSWORD\n")
            return []

        with open(filename, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    if ":" in line:
                        parts = line.split(":")
                        uid, pwd = parts[0].strip(), parts[1].strip()
                    else:
                        uid, pwd = line.strip(), ""
                    
                    if uid.isdigit():
                        processed_list.append({'id': uid, 'password': pwd})
        
        for i, acc in enumerate(processed_list):
            acc_type = 'group'  # সব অ্যাকাউন্ট গ্রুপ হিসেবে চিহ্নিত
            acc['type'] = acc_type
            all_accounts.append(acc)
            
        group_count = len([a for a in all_accounts if a['type'] == 'group'])
        room_count = 0  # রুম অ্যাকাউন্ট নেই
        
        print(f"{G}📦 Total Loaded: {len(all_accounts)} (All Group){RS}")
    except Exception as e:
        print(f"{R}❌ Error loading accounts: {e}{RS}")
    
    return all_accounts

ACCOUNTS = load_unified_accounts("accs.txt")

def save_target_to_file(uid):
    try:
        uids = []
        if os.path.exists("target.txt"):
            with open("target.txt", "r") as f:
                uids = [line.strip() for line in f.readlines()]
        
        if uid not in uids:
            with open("target.txt", "a") as f:
                f.write(f"{uid}\n")
    except Exception as e:
        print(f"{R}❌ Error saving target to file: {e}{RS}")

def remove_target_from_file(uid):
    try:
        if not os.path.exists("target.txt"):
            return
        with open("target.txt", "r") as f:
            lines = f.readlines()
        with open("target.txt", "w") as f:
            for line in lines:
                if line.strip() != str(uid):
                    f.write(line)
    except Exception as e:
        print(f"{R}❌ Error removing target from file: {e}{RS}")

def load_saved_targets():
    if os.path.exists("target.txt"):
        with open("target.txt", "r") as f:
            for line in f:
                uid = line.strip()
                if uid.isdigit():
                    start_spam(uid, 'full')

# ==================== STATUS CHECKER ====================
_ID = '6720928059'
_PW = '196138DE75B7BE7CD3D7EB7636C022EE83704A0B6C22779D5B498E1A7F90D6EF'
_TTL = 6 * 60 * 60
_cx = {}
_lk = threading.Lock()

_Hr = {
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Expect': '100-continue',
    'X-Unity-Version': '2018.4.11f1',
    'X-GA': 'v1 1',
    'ReleaseVersion': CURRENT_OB,
}

async def encrypted_proto(data_bytes):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data_bytes, 16))

async def EncRypTMajoRLoGin(open_id, access_token, version):
    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire"
    major_login.platform_id = 2
    major_login.client_version = FREEFIRE_VERSION_NAME
    major_login.system_software = "Android OS 15 / API-35 (AP3A.240617.008/T.R4T2.230617d-33f5e)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Robi"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1666
    major_login.screen_height = 750
    major_login.screen_dpi = "314"
    major_login.processor_details = "ARM64 FP ASIMD AES | 2000 | 8"
    major_login.memory = 7723
    major_login.gpu_renderer = "Mali-G52 MC2"
    major_login.gpu_version = "OpenGL ES 3.2 v1.r49p1-03bet0.19498e0ae1d5dac223383c39a2e58f04"
    major_login.unique_device_id = "Google|9683cec2-b6fc-424c-aa18-d32bc0e0af87"
    
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.login_open_id_type = 4
    major_login.access_token = access_token
    major_login.login_by = 3
    major_login.device_type = "Handheld"
    
    major_login.platform_sdk_id = 2
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    
    major_login.network_operator_a = "Robi"
    major_login.network_type_a = "WIFI"

    major_login.memory_available.version = 55
    major_login.memory_available.hidden_value = 81
    
    major_login.external_storage_total = 225554
    major_login.external_storage_available = 77192
    major_login.internal_storage_total = 225554
    major_login.internal_storage_available = 77716
    major_login.game_disk_storage_total = 225554
    major_login.game_disk_storage_available = 77716
    
    major_login.library_path = "/data/app/~~eI6I6W4wOsVjxgnf1TGOiw==/com.dts.freefireth-E-hRAzA1WRAwmVJah_awUQ==/lib/arm64"
    major_login.library_token = "4c322aeb56444feaa151d1ea91a8f7f2|/data/app/~~eI6I6W4wOsVjxgnf1TGOiw==/com.dts.freefireth-E-hRAzA1WRAwmVJah_awUQ==/base.apk"
    
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.supported_astc_bitset = 8191
    
    major_login.analytics_detail = b"KqsHT20lrgH2VZSZVBrjiMQlH1D4ByEnCuAp9O88Z77L10j7f3Nyn/PzA3fYYKorO4qAlimdHPTie8ttBgw98SG36+U=" 
    
    major_login.loading_time = 111207
    major_login.release_channel = "android"
    major_login.if_push = 1
    major_login.is_vpn = 0
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019120828"
    major_login.graphics_api = "OpenGLES2"
    major_login.android_engine_init_flag = 1003114253

    serialized_data = major_login.SerializeToString()
    return await encrypted_proto(serialized_data)

def _rdVr(data, pos):
    n = 0; sh = 0
    while True:
        b = data[pos]; pos += 1
        n |= (b & 0x7F) << sh; sh += 7
        if not b & 0x80: break
    return n, pos

def _pbF(data):
    out = {}; pos = 0
    while pos < len(data):
        try:
            tag, pos = _rdVr(data, pos)
            fn = tag >> 3; wt = tag & 0x7
            if wt == 0:
                v, pos = _rdVr(data, pos); out[fn] = v
            elif wt == 2:
                ln, pos = _rdVr(data, pos); out[fn] = data[pos:pos+ln]; pos += ln
            elif wt == 1:
                out[fn] = data[pos:pos+8]; pos += 8
            elif wt == 5:
                out[fn] = data[pos:pos+4]; pos += 4
            else: break
        except: break
    return out

async def _vr(n):
    h = []
    while True:
        b = n & 0x7F; n >>= 7
        if n: b |= 0x80
        h.append(b)
        if not n: break
    return bytes(h)

async def _enc(hx, k, v):
    return AES.new(k, AES.MODE_CBC, v).encrypt(pad(bytes.fromhex(hx), 16)).hex()

async def _hx(n):
    f = hex(n)[2:]
    return ('0' + f) if len(f) == 1 else f

async def _pb(flds):
    async def _var(fn, val): return await _vr((fn << 3) | 0) + await _vr(val)
    async def _len(fn, val):
        e = val.encode() if isinstance(val, str) else val
        return await _vr((fn << 3) | 2) + await _vr(len(e)) + e
    
    p = bytearray()
    for f, v in flds.items():
        if isinstance(v, dict): p.extend(await _len(f, await _pb(v)))
        elif isinstance(v, int): p.extend(await _var(f, v))
        elif isinstance(v, (str, bytes)): p.extend(await _len(f, v))
    return p

async def _pk(px, n, k, v):
    e = await _enc(px, k, v)
    _ = await _hx(len(e) // 2)
    m = {2:'000000', 3:'00000', 4:'0000', 5:'000'}
    return bytes.fromhex(n + m.get(len(_), '000000') + _ + e)

async def _fix(rs):
    d = {}
    for r in rs:
        fd = {'wire_type': r.wire_type}
        if r.wire_type in ('varint', 'string', 'bytes'): fd['data'] = r.data
        elif r.wire_type == 'length_delimited': fd['data'] = await _fix(r.data.results)
        d[r.field] = fd
    return d

async def _parse(hx):
    try: 
        from protobuf_decoder.protobuf_decoder import Parser
        return json.dumps(await _fix(Parser().parse(hx)))
    except: return None

async def _stPkt(uid, k, v):
    ue = (await _pb({1: int(uid)})).hex()[2:]
    return await _pk(f"080112090A05{ue}1005", '0F15', k, v)

async def _rmPkt(ruid, k, v):
    return await _pk((await _pb({1: 1, 2: {1: ruid, 3: {}, 4: 1, 6: 'en'}})).hex(), '0E15', k, v)

def _tdiff(ts):
    d = int((datetime.now() - datetime.fromtimestamp(ts)).total_seconds())
    return f"{(abs(d) % 3600) // 60:02}:{abs(d) % 60:02}"

def _pStatus(pkt):
    data = json.loads(pkt)
    if '5' not in data or 'data' not in data['5']: return {'status': 'OFFLINE'}
    jd = data['5']['data']
    if '1' not in jd or 'data' not in jd['1']: return {'status': 'OFFLINE'}
    d = jd['1']['data']
    if '3' not in d or 'data' not in d['3']: return {'status': 'OFFLINE'}
    st = d['3']['data']
    gc = d.get('9', {}).get('data', 0)
    cm = d.get('10', {}).get('data', 0) + 1 if '10' in d else 0
    go = d.get('8', {}).get('data', 0)
    tg = d.get('4', {}).get('data', 0)
    m5 = d.get('5', {}).get('data')
    m6 = d.get('6', {}).get('data')
    mn = sc = 0
    if tg:
        a, b = _tdiff(tg).split(':'); mn = int(a); sc = int(b)
    if st == 4:
        return {'status': 'IN_ROOM', 'room_uid': d.get('15', {}).get('data'),
                'players': f"{d.get('17',{}).get('data',0)}/{d.get('18',{}).get('data',0)}",
                'room_owner': d.get('1', {}).get('data')}
    base = {1:'SOLO', 2:'INSQUAD', 3:'INGAME', 5:'INGAME', 7:'MATCHMAKING', 6:'SOCIAL_ISLAND'}.get(st, 'OFFLINE')
    mode = None
    f14 = d.get('14', {}).get('data')
    if f14 == 1: mode = 'TRAINING'
    elif f14 == 2: mode = 'SOCIAL_ISLAND'
    mm = {(2,1):'BR_RANK',(5,23):'TRAINING',(6,15):'CS_RANK',(1,43):'LONE_WOLF',
          (1,1):'BERMUDA',(1,15):'CLASH_SQUAD',(1,29):'CONVOY_CRUNCH',(1,61):'FREE_FOR_ALL'}
    if (m5, m6) in mm: mode = mm[(m5, m6)]
    res = {'status': base, 'mode': mode}
    if base == 'INSQUAD':
        res['squad_owner'] = str(go)
        res['squad_size'] = f"{gc}/{cm}" if gc else None
    if base in ('INGAME', 'INSQUAD') and tg:
        res['time_playing'] = f"{mn}m {sc}s"
    return res

def _pRoom(pkt):
    data = json.loads(pkt)
    rd = data['5']['data']['1']['data']
    mm = {1:'BERMUDA',201:'BATTLE_CAGE',15:'CLASH_SQUAD',43:'LONE_WOLF',3:'RUSH_HOUR',27:'BOMB_SQUAD_5V5',24:'DEATH_MATCH'}
    return {
        'room_id': int(rd['1']['data']),
        'room_name': rd['2']['data'],
        'owner_uid': int(rd['37']['data']['1']['data']),
        'mode': mm.get(rd.get('4', {}).get('data'), 'UNKNOWN'),
        'players': f"{rd.get('6',{}).get('data',0)}/{rd.get('7',{}).get('data',0)}",
        'spectators': rd.get('9', {}).get('data', 0),
        'emulator': bool(rd.get('17', {}).get('data', 1)),
    }

async def _rAll(reader, timeout=0.1):
    buf = b''
    while True:
        try: chunk = await asyncio.wait_for(reader.read(65536), timeout=timeout)
        except asyncio.TimeoutError: break
        if not chunk: break
        buf += chunk
    return buf

async def _scan(buf, k, v):
    h = buf.hex()
    for mk, pt in [('0f00','0f'),('0e00','0e')]:
        i = h.find(mk)
        if i != -1 and i % 2 == 0: return pt, h[i + 10:]
    if len(buf) > 5:
        pl = buf[5:]; pl = pl[:len(pl) - (len(pl) % 16)]
        if len(pl) >= 16:
            try:
                dc = unpad(AES.new(k, AES.MODE_CBC, v).decrypt(pl), 16).hex()
                for mk, pt in [('0f00','0f'),('0e00','0e')]:
                    i = dc.find(mk)
                    if i != -1 and i % 2 == 0: return pt, dc[i + 10:]
            except: pass
    return None, None

async def _auth(uid, tok, ts, k, v):
    uh = hex(uid)[2:]
    hd = {9:'0000000',8:'00000000',10:'000000',7:'000000000'}.get(len(uh),'0000000')
    e = await _enc(tok.encode().hex(), k, v)
    el = await _hx(len(e) // 2)
    return f"0115{hd}{uh}{await _hx(ts)}00000{el}{e}"

def get_session_sync():
    result = None
    def _run():
        nonlocal result
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_login())
        except Exception as e:
            print(f"{R}❌ Login error: {e}{RS}")
        finally:
            loop.close()
    
    thread = Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=20)
    return result

def _sess():
    with _lk:
        s = _cx.get('s')
        if s and time.time() < s['exp']:
            return s
    
    ns = get_session_sync()
    if ns:
        with _lk:
            _cx['s'] = ns
        return ns
    return None

async def _login():
    sx = ssl.create_default_context()
    sx.check_hostname = False
    sx.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as s:
        async with s.post('https://100067.connect.garena.com/oauth/guest/token/grant', headers=_Hr,
            data={'uid':_ID,'password':_PW,'response_type':'token','client_type':'2',
                  'client_secret':'2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3',
                  'client_id':'100067'}, ssl=sx) as r:
            if r.status != 200:
                raise Exception(f"OAuth {r.status}")
            d = await r.json()
            oid = d['open_id']
            atk = d['access_token']

    ep = await EncRypTMajoRLoGin(oid, atk, _Hr['ReleaseVersion'])

    async with aiohttp.ClientSession() as s:
        async with s.post('https://loginbp.ggpolarbear.com/MajorLogin', data=ep, headers=_Hr, ssl=sx) as r:
            if r.status != 200:
                raise Exception(f"MajorLogin {r.status}")
            mr = await r.read()

    mlr = _pbF(mr)
    tok = mlr[8].decode()
    tgt = mlr[1]
    k = mlr[22]
    v = mlr[23]
    ts = mlr[21]
    url = mlr[10].decode()

    h2 = {**_Hr, 'Authorization': f'Bearer {tok}'}
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{url}/GetLoginData", data=ep, headers=h2, ssl=sx) as r:
            if r.status != 200:
                raise Exception(f"GetLoginData {r.status}")
            lr = await r.read()

    ld = _pbF(lr)
    ip, port = ld[14].decode().split(':')
    at = await _auth(int(tgt), tok, int(ts), k, v)
    return {'account_id': tgt, 'token': tok, 'key': k, 'iv': v, 'ip': ip, 'port': int(port), 'auth': at, 'exp': time.time()+_TTL}

async def check_target_status_async(uid):
    try:
        sx = _sess()
        if not sx:
            return {'status': 'ERROR', 'error': 'No session'}
        
        rd, wr = await asyncio.open_connection(sx['ip'], sx['port'])
        try:
            wr.write(bytes.fromhex(sx['auth']))
            await wr.drain()
            await _rAll(rd, timeout=0.2)
            pkt = await _stPkt(uid, sx['key'], sx['iv'])
            wr.write(pkt)
            await wr.drain()
            buf = await _rAll(rd, timeout=0.6)
            if not buf:
                return {'status': 'OFFLINE'}
            pt, pl = await _scan(buf, sx['key'], sx['iv'])
            if pt == '0f':
                raw = await _parse(pl)
                if not raw:
                    return {'status': 'PARSE_ERROR'}
                info = _pStatus(raw)
                if info.get('status') == 'IN_ROOM':
                    wr.write(await _rmPkt(int(info['room_uid']), sx['key'], sx['iv']))
                    await wr.drain()
                    rb = await _rAll(rd, timeout=0.5)
                    if rb:
                        rt, rp = await _scan(rb, sx['key'], sx['iv'])
                        if rt == '0e':
                            rr = await _parse(rp)
                            if rr:
                                info['room_info'] = _pRoom(rr)
                return info
            elif pt == '0e':
                raw = await _parse(pl)
                return _pRoom(raw) if raw else {'status': 'PARSE_ERROR'}
            return {'status': 'UNKNOWN'}
        finally:
            wr.close()
            try:
                await wr.wait_closed()
            except:
                pass
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e)}

def check_target_status_sync(uid):
    result = {'status': 'ERROR'}
    
    def _run():
        nonlocal result
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(check_target_status_async(uid))
        except Exception as e:
            result = {'status': 'ERROR', 'error': str(e)}
        finally:
            loop.close()
    
    thread = Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=3.0)
    return result

# ==================== PACKET CREATION FUNCTIONS ====================
def create_badge_join_packet(key, iv, target_uid, badge_value, region="BD"):
    try:
        avatar_ids = [
            902000011, 902000013, 902047016, 902049015,
            902000154, 902000127, 902000207, 902000305,        
            902037031, 902042011, 902053016, 902053018
        ]
        selected_avatar = random.choice(avatar_ids)

        proto_fields = {
            1: 33,
            2: {
                1: int(target_uid),
                2: region.upper(),
                3: 1,
                4: 1,
                5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]),
                6: "[C][B][FF0000] TORIKUL BADGE",
                7: 330,
                8: 1000,
                10: region.upper(),
                11: bytes.fromhex("61" * 32),
                12: 1,
                13: int(target_uid),
                14: {
                    1: random.randint(1000000000, 9999999999),
                    2: 8,
                    3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
                },
                16: 1,
                17: 1,
                18: 312,
                19: 46,
                23: bytes([16, 1, 24, 1]),
                24: selected_avatar,
                26: "",
                28: "",
                31: {1: 1, 2: badge_value},
                32: badge_value,
                34: {
                    1: int(target_uid),
                    2: 8,
                    3: bytes([15, 6, 21, 8, 10, 11, 19, 12, 17, 4, 14, 20, 7, 2, 1, 5, 16, 3, 13, 18])
                }
            },
            10: "en",
            13: {2: 1, 3: 1}
        }
        
        packet = create_proto_sync(proto_fields).hex()
        
        if region.lower() == "ind":
            packet_type = "0514"
        elif region.lower() == "bd":
            packet_type = "0519"
        else:
            packet_type = "0515"
        
        encrypted = EnC_PacKeT(packet, key, iv)
        length = len(encrypted) // 2
        len_hex = DecodE_HeX(length)
        padding_map = {2: "000000", 3: "00000", 4: "0000", 5: "000"}
        padding = padding_map.get(len(len_hex), "000")
        
        return bytes.fromhex(packet_type + padding + len_hex + encrypted)
    except Exception as e:
        print(f"{R}❌ Badge join packet error: {e}{RS}")
        return None

def encode_varint_sync(value: int) -> bytes:
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        result.append(byte)
        if not value:
            break
    return bytes(result)

def create_proto_sync(fields):
    packet = bytearray()
    
    for field, value in fields.items():
        field_num = int(field)
        
        if isinstance(value, dict):
            nested = create_proto_sync(value)
            packet.extend(encode_varint_sync((field_num << 3) | 2))
            packet.extend(encode_varint_sync(len(nested)))
            packet.extend(nested)
        elif isinstance(value, int):
            packet.extend(encode_varint_sync((field_num << 3) | 0))
            packet.extend(encode_varint_sync(value))
        elif isinstance(value, str):
            data = value.encode('utf-8')
            packet.extend(encode_varint_sync((field_num << 3) | 2))
            packet.extend(encode_varint_sync(len(data)))
            packet.extend(data)
        elif isinstance(value, bytes):
            packet.extend(encode_varint_sync((field_num << 3) | 2))
            packet.extend(encode_varint_sync(len(value)))
            packet.extend(value)
            
    return bytes(packet)

def create_squad_invite_packet(key, iv, target_uid, region="BD"):
    try:
        fields = {1: 2, 2: {1: int(target_uid), 2: region.upper(), 4: 5}}
        packet = create_proto_sync(fields).hex()
        encrypted = EnC_PacKeT(packet, key, iv)
        length = len(encrypted) // 2
        len_hex = DecodE_HeX(length)
        padding_map = {2: "000000", 3: "00000", 4: "0000", 5: "000"}
        padding = padding_map.get(len(len_hex), "000")
        
        if region.lower() == "ind":
            packet_type = "0514"
        elif region.lower() == "bd":
            packet_type = "0519"
        else:
            packet_type = "0515"
        
        return bytes.fromhex(packet_type + padding + len_hex + encrypted)
    except Exception as e:
        print(f"{R}❌ Squad invite packet error: {e}{RS}")
        return None

def create_open_squad_packet(key, iv, region="BD"):
    try:
        fields = {
            1: 1,
            2: {
                2: "\u0001",
                3: 2,
                4: 1,
                5: "en",
                9: 1,
                11: 1,
                13: 1,
                14: {
                    1: 1,
                    2: 1393,
                    6: 11,
                    8: FREEFIRE_VERSION_NAME,
                    9: 2,
                    10: 4
                }
            }
        }
        packet = create_proto_sync(fields).hex()
        encrypted = EnC_PacKeT(packet, key, iv)
        length = len(encrypted) // 2
        len_hex = DecodE_HeX(length)
        padding_map = {2: "000000", 3: "00000", 4: "0000", 5: "000"}
        padding = padding_map.get(len(len_hex), "000")
        
        if region.lower() == "ind":
            packet_type = "0514"
        elif region.lower() == "bd":
            packet_type = "0519"
        else:
            packet_type = "0515"
        
        return bytes.fromhex(packet_type + padding + len_hex + encrypted)
    except Exception as e:
        print(f"\033[91m❌ Open squad packet error: {e}\033[0m")
        return None

def create_change_squad_size_packet(key, iv, target_uid, region="BD"):
    try:
        fields = {
            1: 17,
            2: {
                1: int(target_uid),
                2: 1,
                3: 4,
                4: 1,
                5: "\x1a",
                8: 12,
                13: 330
            }
        }
        packet = create_proto_sync(fields).hex()
        encrypted = EnC_PacKeT(packet, key, iv)
        length = len(encrypted) // 2
        len_hex = DecodE_HeX(length)
        padding_map = {2: "000000", 3: "00000", 4: "0000", 5: "000"}
        padding = padding_map.get(len(len_hex), "000")
        
        if region.lower() == "ind":
            packet_type = "0514"
        elif region.lower() == "bd":
            packet_type = "0519"
        else:
            packet_type = "0515"
        
        return bytes.fromhex(packet_type + padding + len_hex + encrypted)
    except Exception as e:
        print(f"{R}❌ Change squad size packet error: {e}{RS}")
        return None

# ==================== SPAM WORKER FUNCTIONS - শুধু গ্রুপ স্প্যাম ====================
def send_group_badge_spam(client, target_uid, badge_value):
    total_sent = 0
    
    try:
        if not hasattr(client, 'CliEnts2') or not client.key:
            return 0
        
        # ১. স্কোয়াড ওপেন করা
        open_pkt = create_open_squad_packet(client.key, client.iv)
        if open_pkt:
            try:
                client.CliEnts2.send(open_pkt)
                total_sent += 1
                time.sleep(0.08)
            except:
                pass
        
        # ২. স্কোয়াড সাইজ পরিবর্তন
        size_pkt = create_change_squad_size_packet(client.key, client.iv, int(client.id))
        if size_pkt:
            try:
                client.CliEnts2.send(size_pkt)
                total_sent += 1
                time.sleep(0.08)
            except:
                pass
        
        # ৩. স্কোয়াড ইনভাইট পাঠানো
        invite_pkt = create_squad_invite_packet(client.key, client.iv, target_uid)
        if invite_pkt:
            try:
                client.CliEnts2.send(invite_pkt)
                total_sent += 1
                time.sleep(0.05)
            except:
                pass
        
        # ৪. ব্যাজ জয়েন প্যাকেট
        try:
            badge_pkt = create_badge_join_packet(client.key, client.iv, target_uid, badge_value)
            if badge_pkt:
                try:
                    client.CliEnts2.send(badge_pkt)
                    total_sent += 1
                except:
                    pass
        except:
            pass
                
    except Exception as e:
        pass
    
    return total_sent

def send_room_badge_spam(client, target_uid, badge_value):
    # রুম স্প্যাম সরানো হয়েছে - শুধু গ্রুপ স্প্যাম কাজ করবে
    return 0

def send_squad_join_packet(client, target_uid, squad_uid):
    try:
        proto_fields = {
            1: 2,
            2: {
                1: int(squad_uid),
                2: int(target_uid)
            }
        }
        packet = create_proto_sync(proto_fields).hex()
        encrypted = EnC_PacKeT(packet, client.key, client.iv)
        length = len(encrypted) // 2
        len_hex = DecodE_HeX(length)
        padding_map = {2: "000000", 3: "00000", 4: "0000", 5: "000"}
        padding = padding_map.get(len(len_hex), "000")
        pkt = bytes.fromhex("0615" + padding + len_hex + encrypted)
        client.CliEnts2.send(pkt)
        return True
    except Exception as e:
        return False

def load_squad_json():
    if os.path.exists(SQUAD_DATA_FILE):
        try:
            with open(SQUAD_DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_squad_json(data):
    try:
        with open(SQUAD_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")

def clean_and_load_squad_targets():
    data = load_squad_json()
    current_time = datetime.now()
    updated_data = {}
    
    print(f"{C}🔄 Checking persistent squad targets...{RS}")
    
    for uid, info in data.items():
        start_time = datetime.fromisoformat(info['start_time'])
        if (current_time - start_time).total_seconds() < SQUAD_JOIN_DURATION:
            updated_data[uid] = info
            start_spam(uid, 'squad')
            print(f"{G}✅ Restored Squad Target: {uid} (Remaining: {int(120 - (current_time - start_time).total_seconds()/60)} min){RS}")
        else:
            print(f"{R}⏰ Expired: {uid} (Still kept in file){RS}")
            
    save_squad_json(updated_data)

# ==================== স্প্যাম ওয়ার্কার - স্কোয়াড লিডার অ্যাড করার সময় ====================
def add_squad_leader_as_target(squad_leader_uid, original_target_uid):
    squad_uid_str = str(squad_leader_uid).strip()
    if not (squad_uid_str.isdigit() and 8 <= len(squad_uid_str) <= 12):
        return False

    with active_spam_lock:
        if squad_uid_str in active_spam_targets:
            return False
        
        start_time = datetime.now()
        selected_banner = random.choice(TORIKUL_BANNERS)

        active_spam_targets[squad_uid_str] = {
            'type': 'squad',
            'start_time': start_time,
            'status': 'CHECKING',
            'banner_url': selected_banner,
            'squad_leader': '',
            'last_check': datetime.now(),
            'is_spamming': True,
            'is_online': False,
            'is_squad_leader': True,
            'original_target': original_target_uid,
            'added_by_squad': True,
            'added_by': 'SYSTEM',
            'reason': f'Auto-detected as squad leader of {original_target_uid}'
        }
        
        current_squad_data = load_squad_json()
        current_squad_data[str(squad_leader_uid)] = {
            'start_time': start_time.isoformat(),
            'original_target': original_target_uid
        }
        save_squad_json(current_squad_data)
        
        if squad_leader_uid not in squad_targets:
            squad_targets[squad_leader_uid] = {
                'target_uids': [],
                'start_time': start_time
            }
        squad_targets[squad_leader_uid]['target_uids'].append(original_target_uid)
        
        thread = Thread(target=spam_worker, args=(squad_leader_uid, 'squad'), daemon=True)
        with spam_threads_lock:
            spam_threads[squad_leader_uid] = thread
        thread.start()
        
        print(f"{G}✅ Squad leader {squad_leader_uid} auto-added (Reason: In squad of {original_target_uid}){RS}")
        return True

def update_target_status(target_uid):
    try:
        status_info = check_target_status_sync(target_uid)
        status = status_info.get('status', 'OFFLINE')
        
        is_online = status not in ['OFFLINE', 'NO_RESPONSE', 'ERROR', 'TIMEOUT']
        
        with active_spam_lock:
            if target_uid in active_spam_targets:
                active_spam_targets[target_uid]['status'] = status
                active_spam_targets[target_uid]['last_check'] = datetime.now()
                active_spam_targets[target_uid]['is_online'] = is_online
                if status == 'INSQUAD':
                    active_spam_targets[target_uid]['squad_leader'] = status_info.get('squad_owner', '')
                else:
                    active_spam_targets[target_uid]['squad_leader'] = ''
        
        target_status_cache[target_uid] = {
            'status': status,
            'last_check': time.time(),
            'squad_leader': status_info.get('squad_owner', ''),
            'squad_owner': status_info.get('squad_owner', ''),
            'mode': status_info.get('mode', ''),
            'time_playing': status_info.get('time_playing', ''),
            'is_online': is_online
        }
        
        if status == 'INSQUAD':
            squad_leader = status_info.get('squad_owner', '')
            if squad_leader and squad_leader != target_uid:
                if target_uid not in squad_targets or squad_targets[target_uid].get('squad_leader') != squad_leader:
                    add_squad_leader_as_target(squad_leader, target_uid)
        
        return status
    except Exception as e:
        print(f"{R}❌ Status update error: {e}{RS}")
        return 'ERROR'

def status_checker_thread():
    while True:
        try:
            with active_spam_lock:
                targets = list(active_spam_targets.keys())
            
            current_time = datetime.now()
            for squad_leader, data in list(squad_targets.items()):
                if (current_time - data['start_time']).total_seconds() > SQUAD_JOIN_DURATION:
                    print(f"{Y}⏰ Squad leader {squad_leader} duration expired (2 hours){RS}")
                    with active_spam_lock:
                        if squad_leader in active_spam_targets:
                            del active_spam_targets[squad_leader]
                    del squad_targets[squad_leader]
            
            for target_uid in targets:
                update_target_status(target_uid)
                time.sleep(0.3)
            
            time.sleep(STATUS_CHECK_INTERVAL)
        except Exception as e:
            print(f"{R}❌ Status checker error: {e}{RS}")
            time.sleep(5)

def spam_worker(target_uid, spam_type='full'):
    print(f"\n{G}{'='*60}{RS}")
    print(f"{G}🎯 SPAM STARTED ON {target_uid} (Type: {spam_type}){RS}")
    print(f"{C}{'='*60}{RS}\n")

    total_requests = 0
    round_number = 0
    is_spamming = True
    
    badge_vals = list(BADGES.values())

    while True:
        with active_spam_lock:
            if target_uid not in active_spam_targets:
                break
            
            is_online = active_spam_targets[target_uid].get('is_online', False)
            
            if not is_online:
                if is_spamming:
                    is_spamming = False
                    print(f"{Y}⚠️ Target {target_uid} is OFFLINE - Pausing spam{RS}")
            else:
                if not is_spamming:
                    is_spamming = True
                    print(f"{G}✅ Target {target_uid} is ONLINE - Resuming spam{RS}")

        with connected_clients_lock:
            clients_list = list(connected_clients.values())

        if not clients_list:
            time.sleep(2)
            continue

        if not is_spamming:
            time.sleep(2)
            continue

        round_number += 1

        for i, client in enumerate(clients_list):
            with active_spam_lock:
                if target_uid not in active_spam_targets:
                    break

            try:
                assigned_badge = badge_vals[i % len(badge_vals)]
                total_requests += send_group_badge_spam(client, target_uid, assigned_badge)
            except Exception as e:
                pass

            time.sleep(0.05)

        if round_number % 10 == 0:
            status = target_status_cache.get(target_uid, {}).get('status', 'UNKNOWN')
            print(f"{C}{'='*50}{RS}")
            print(f"{G}📊 Round {round_number} Complete{RS}")
            print(f"{G}📊 Total Requests: {total_requests}{RS}")
            print(f"{G}🎯 Target: {target_uid}{RS}")
            print(f"{G}📊 Status: {status}{RS}")
            print(f"{G}📊 Online: {is_spamming}{RS}")
            print(f"{G}🤖 Bots: {len(clients_list)}{RS}")
            print(f"{C}{'='*50}{RS}\n")
        
        time.sleep(0.5)

    with spam_threads_lock:
        if target_uid in spam_threads:
            del spam_threads[target_uid]

    print(f"\n{R}🛑 SPAM STOPPED ON {target_uid}{RS}\n")

# ==================== স্প্যাম শুরু করার ফাংশন ====================
def start_spam(target_uid, spam_type='full', added_by='TORIKUL', reason='Manual Start'):
    target_uid_str = str(target_uid).strip()
    if not (target_uid_str.isdigit() and 8 <= len(target_uid_str) <= 12):
        return False, "Invalid UID! Length must be 8-12 digits."

    with active_spam_lock:
        if target_uid_str in active_spam_targets:
            return False, f"Already spamming {target_uid_str}"
        
        selected_banner = random.choice(TORIKUL_BANNERS)

        active_spam_targets[target_uid_str] = {
            'type': spam_type,
            'start_time': datetime.now(),
            'status': 'CHECKING',
            'banner_url': selected_banner,
            'squad_leader': '',
            'last_check': datetime.now(),
            'is_spamming': True,
            'is_online': False,
            'is_squad_leader': True if spam_type == 'squad' else False,
            'original_target': '',
            'added_by_squad': True if spam_type == 'squad' else False,
            'added_by': added_by,
            'reason': reason
        }
    
    if spam_type == 'full':
        save_target_to_file(target_uid_str) 
    
    thread = Thread(target=spam_worker, args=(target_uid_str, spam_type), daemon=True)
    with spam_threads_lock:
        spam_threads[target_uid_str] = thread
    thread.start()
    
    Thread(target=update_target_status, args=(target_uid_str,), daemon=True).start()
    return True, f"Started spam on {target_uid_str}"

def stop_spam(target_uid):
    with active_spam_lock:
        if target_uid in active_spam_targets:
            remove_target_from_file(target_uid) 
            
            if active_spam_targets[target_uid].get('added_by_squad', False):
                if target_uid in squad_targets:
                    del squad_targets[target_uid]
            
            del active_spam_targets[target_uid]
            if target_uid in target_status_cache:
                del target_status_cache[target_uid]
            return True, f"Stopped spam on {target_uid}"
    return False, f"No spam found for {target_uid}"

def stop_all_spam():
    with active_spam_lock:
        targets = list(active_spam_targets.keys())
        for target in targets:
            remove_target_from_file(target)
            del active_spam_targets[target]
        squad_targets.clear()
        target_status_cache.clear()
    return True, f"Stopped all spam ({len(targets)} targets)"

def get_spam_status():
    with active_spam_lock:
        active_targets = []
        for target, info in active_spam_targets.items():
            start_time = info.get('start_time')
            elapsed = (datetime.now() - start_time).total_seconds() if start_time else 0
            status = info.get('status', 'UNKNOWN')
            squad_leader = info.get('squad_leader', '')
            is_online = info.get('is_online', False)
            is_squad_leader = info.get('is_squad_leader', False)
            original_target = info.get('original_target', '')
            
            status_display = status
            if status == 'SOLO': status_display = '🟢 Solo'
            elif status == 'INSQUAD': status_display = '🔵 In Squad'
            elif status == 'INGAME': status_display = '🟡 In Game'
            elif status == 'IN_ROOM': status_display = '🟠 In Room'
            elif status == 'OFFLINE': status_display = '⚪ Offline'
            elif status == 'SOCIAL_ISLAND': status_display = '🟣 Social Island'
            elif status == 'MATCHMAKING': status_display = '🟣 Matchmaking'
            elif status == 'CHECKING': status_display = '⏳ Checking...'
            else: status_display = '⚪ Unknown'
            
            banner_url = info.get('banner_url', f"https://mahir-banner-api.vercel.app/fiuid={target}")
            
            active_targets.append({
                'uid': target,
                'type': 'SQUAD' if is_squad_leader else info.get('type', 'full'),
                'elapsed_minutes': int(elapsed / 60),
                'banner_url': banner_url,
                'status': status,
                'status_display': status_display,
                'squad_leader': squad_leader,
                'squad_owner': info.get('squad_leader', ''),
                'mode': target_status_cache.get(target, {}).get('mode', ''),
                'time_playing': target_status_cache.get(target, {}).get('time_playing', ''),
                'last_check': info.get('last_check', datetime.now()).strftime('%H:%M:%S'),
                'is_online': is_online,
                'is_squad_leader': is_squad_leader,
                'original_target': original_target,
                'added_by': info.get('added_by', 'TORIKUL'),
                'reason': info.get('reason', 'Manual Start'),
                'added_time': info.get('start_time', datetime.now()).isoformat() if info.get('start_time') else None
            })
    
    with connected_clients_lock:
        accounts_count = len(connected_clients)
        accounts_list = list(connected_clients.keys())
    
    return {
        'active_targets': active_targets,
        'active_count': len(active_targets),
        'accounts_count': accounts_count,
        'accounts_list': accounts_list[:50]
    }


# ==================== FF CLIENT ====================
class FF_CLient():
    def __init__(self, uid, password, is_group_account=True):
        self.id = uid
        self.password = password
        self.is_group_account = True  # সব অ্যাকাউন্ট গ্রুপ
        self.key = None
        self.iv = None
        self.running = True
        self.Get_FiNal_ToKen_0115()

    def Connect_SerVer_OnLine(self, Token, tok, host, port, key, iv, host2, port2):
        try:
            self.AutH_ToKen_0115 = tok
            self.CliEnts2 = socket.create_connection((host2, int(port2)), timeout=10)
            self.CliEnts2.send(bytes.fromhex(self.AutH_ToKen_0115))
            with connected_clients_lock:
                if self.id not in connected_clients:
                    connected_clients[self.id] = self
                    print(f"{G}✅ Online: {self.id} (Type: GROUP) (Total: {len(connected_clients)}){RS}")
        except Exception as e:
            print(f"{R}❌ Online error {self.id}: {e}{RS}")
            return
        while self.running:
            try:
                self.CliEnts2.settimeout(30)
                self.DaTa2 = self.CliEnts2.recv(99999)
                if not self.DaTa2:
                    break
                if '0500' in self.DaTa2.hex()[0:4] and len(self.DaTa2.hex()) > 30:
                    self.packet = json.loads(DeCode_PackEt(f'08{self.DaTa2.hex().split("08",1)[1]}'))
                    self.AutH = self.packet['5']['data']['7']['data']
            except socket.timeout:
                continue
            except Exception as e:
                break

    def Connect_SerVer(self, Token, tok, host, port, key, iv, host2, port2):
        self.AutH_ToKen_0115 = tok
        try:
            self.CliEnts = socket.create_connection((host, int(port)), timeout=10)
            self.CliEnts.send(bytes.fromhex(self.AutH_ToKen_0115))
            self.DaTa = self.CliEnts.recv(1024)
            threading.Thread(target=self.Connect_SerVer_OnLine, args=(Token, tok, host, port, key, iv, host2, port2), daemon=True).start()
        except Exception as e:
            print(f"{R}❌ Connection error {self.id}: {e}{RS}")
            return
        
        self.key = key
        self.iv = iv
        with connected_clients_lock:
            if self.id not in connected_clients:
                connected_clients[self.id] = self
                print(f"{G}✅ Registered: {self.id} (Type: GROUP){RS}")
        
        while self.running:
            try:
                self.CliEnts.settimeout(30)
                self.DaTa = self.CliEnts.recv(1024)
                if not self.DaTa:
                    break
            except socket.timeout:
                continue
            except Exception as e:
                break
        
        if self.running:
            time.sleep(2)
            self.Connect_SerVer(Token, tok, host, port, key, iv, host2, port2)

    def GeT_Key_Iv(self, serialized_data):
        my_message = xKEys.MyMessage()
        my_message.ParseFromString(serialized_data)
        timestamp, key, iv = my_message.field21, my_message.field22, my_message.field23
        timestamp_obj = Timestamp()
        timestamp_obj.FromNanoseconds(timestamp)
        combined = timestamp_obj.seconds * 1_000_000_000 + timestamp_obj.nanos
        return combined, key, iv

    def Guest_GeneRaTe(self, uid, password):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
        }
        data = {
            "uid": uid,
            "password": password,
            "response_type": "token",
            "client_type": "2",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_id": "100067",
        }
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=10).json()
            access_token, open_id = resp['access_token'], resp['open_id']
            time.sleep(0.2)
            print(f'{C}🔐 Login: {self.id} (GROUP){RS}')
            return self.ToKen_GeneRaTe(access_token, open_id)
        except:
            time.sleep(10)
            return self.Guest_GeneRaTe(uid, password)

    def GeT_LoGin_PorTs(self, jwt_token, payload, dynamic_url="https://clientbp.ggpolarbear.com"):
        url = f'{dynamic_url}/GetLoginData'
        headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {jwt_token}',
            'X-Unity-Version': '2022.3.47f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Connection': 'close',
            'Accept-Encoding': 'deflate, gzip',
        }
        try:
            resp = requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
            data = json.loads(DeCode_PackEt(resp.content.hex()))
            addr1, addr2 = data['32']['data'], data['14']['data']
            ip, ip2 = addr1[:-6], addr2[:-6]
            port, port2 = addr1[-5:], addr2[-5:]
            return ip, port, ip2, port2
        except:
            return None, None, None, None

    def ToKen_GeneRaTe(self, access_token, open_id):
        url = f"{DYNAMIC_SERVER_URL}/MajorLogin"
        
        dynamic_host = DYNAMIC_SERVER_URL.split("//")[-1].split("/")[0]

        headers = {
            'X-Unity-Version': '2022.3.47f1',
            'ReleaseVersion': CURRENT_OB, 
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': dynamic_host, 
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        try:
            major_login = MajoRLoGinrEq_pb2.MajorLogin()
    
            major_login.event_time = str(datetime.now())[:-7]
            major_login.game_name = "free fire"
            major_login.platform_id = 2
            major_login.client_version = FREEFIRE_VERSION_NAME
            major_login.system_software = "Android OS 15 / API-35 (AP3A.240617.008/T.R4T2.230617d-33f5e)"
            major_login.system_hardware = "Handheld"
            major_login.telecom_operator = "Robi"
            major_login.network_type = "WIFI"
            major_login.screen_width = 1666
            major_login.screen_height = 750
            major_login.screen_dpi = "314"
            major_login.processor_details = "ARM64 FP ASIMD AES | 2000 | 8"
            major_login.memory = 7723
            major_login.gpu_renderer = "Mali-G52 MC2"
            major_login.gpu_version = "OpenGL ES 3.2 v1.r49p1-03bet0.19498e0ae1d5dac223383c39a2e58f04"
            major_login.unique_device_id = "Google|9683cec2-b6fc-424c-aa18-d32bc0e0af87"
    
            major_login.language = "en"
            major_login.open_id = open_id
            major_login.open_id_type = "4"
            major_login.login_open_id_type = 4
            major_login.access_token = access_token
            major_login.login_by = 3
            major_login.device_type = "Handheld"
    
            major_login.platform_sdk_id = 2
            major_login.origin_platform_type = "4"
            major_login.primary_platform_type = "4"
    
            major_login.network_operator_a = "Robi"
            major_login.network_type_a = "WIFI"

            major_login.memory_available.version = 55
            major_login.memory_available.hidden_value = 81
    
            major_login.external_storage_total = 225554
            major_login.external_storage_available = 77192
            major_login.internal_storage_total = 225554
            major_login.internal_storage_available = 77716
            major_login.game_disk_storage_total = 225554
            major_login.game_disk_storage_available = 77716
    
            major_login.library_path = "/data/app/~~eI6I6W4wOsVjxgnf1TGOiw==/com.dts.freefireth-E-hRAzA1WRAwmVJah_awUQ==/lib/arm64"
            major_login.library_token = "4c322aeb56444feaa151d1ea91a8f7f2|/data/app/~~eI6I6W4wOsVjxgnf1TGOiw==/com.dts.freefireth-E-hRAzA1WRAwmVJah_awUQ==/base.apk"
    
            major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
            major_login.supported_astc_bitset = 8191
    
            major_login.analytics_detail = b"KqsHT20lrgH2VZSZVBrjiMQlH1D4ByEnCuAp9O88Z77L10j7f3Nyn/PzA3fYYKorO4qAlimdHPTie8ttBgw98SG36+U=" 
    
            major_login.loading_time = 111207
            major_login.release_channel = "android"
            major_login.if_push = 1
            major_login.is_vpn = 0
            major_login.cpu_type = 2
            major_login.cpu_architecture = "64"
            major_login.client_version_code = "2019120828"
            major_login.graphics_api = "OpenGLES2"
            major_login.android_engine_init_flag = 1003114253

            raw_data = major_login.SerializeToString()
            key = b'Yg&tc%DEuh6%Zc^8'
            iv = b'6oyZDr22E3ychjM%'
            cipher = AES.new(key, AES.MODE_CBC, iv)
            payload = cipher.encrypt(pad(raw_data, 16))
        except Exception as e:
            print(f"Error packing proto: {e}")
            time.sleep(5)
            return self.ToKen_GeneRaTe(access_token, open_id)

        resp = requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
        if resp.status_code == 200:
            try:
                data = json.loads(DeCode_PackEt(resp.content.hex()))
                jwt_token = data['8']['data']
                combined, key, iv = self.GeT_Key_Iv(resp.content)
                ip, port, ip2, port2 = self.GeT_LoGin_PorTs(jwt_token, payload)
                return jwt_token, key, iv, combined, ip, port, ip2, port2
            except:
                time.sleep(5)
                return self.ToKen_GeneRaTe(access_token, open_id)
        else:
            time.sleep(5)
            return self.ToKen_GeneRaTe(access_token, open_id)

    def Get_FiNal_ToKen_0115(self):
        try:
            result = self.Guest_GeneRaTe(self.id, self.password)
            if not result:
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
            token, key, iv, ts, ip, port, ip2, port2 = result
            if not all([ip, port, ip2, port2]):
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
            self.JwT_ToKen = token
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                account_id = decoded.get('account_id')
                enc_acc = hex(account_id)[2:]
                hex_ts = DecodE_HeX(ts)
                self.JwT_ToKen_ = token.encode().hex()
                print(f'{C}🆔 Account UID: {account_id} (GROUP){RS}')
            except:
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
            try:
                enc_len = len(EnC_PacKeT(self.JwT_ToKen_, key, iv)) // 2
                header = hex(enc_len)[2:]
                length = len(enc_acc)
                pad = '00000000'
                if length == 9:
                    pad = '0000000'
                elif length == 8:
                    pad = '00000000'
                elif length == 10:
                    pad = '000000'
                elif length == 7:
                    pad = '000000000'
                self.Header = f'0115{pad}{enc_acc}{hex_ts}00000{header}'
                self.FiNal_ToKen_0115 = self.Header + EnC_PacKeT(self.JwT_ToKen_, key, iv)
            except:
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
            self.AutH_ToKen = self.FiNal_ToKen_0115
            self.Connect_SerVer(self.JwT_ToKen, self.AutH_ToKen, ip, port, key, iv, ip2, port2)
            return self.AutH_ToKen, key, iv
        except:
            time.sleep(5)
            return self.Get_FiNal_ToKen_0115()
    
    def stop(self):
        self.running = False
        try:
            if hasattr(self, 'CliEnts'):
                self.CliEnts.close()
        except:
            pass
        try:
            if hasattr(self, 'CliEnts2'):
                self.CliEnts2.close()
        except:
            pass

# ==================== ACCOUNT RUNNER ====================
def start_account(account):
    try:
        FF_CLient(account['id'], account['password'], is_group_account=True)
    except Exception as e:
        print(f"{R}❌ [ERROR] Login failed for {account['id']}: {e}. Retrying in 3s...{RS}")
        time.sleep(3)
        start_account(account)

def run_accounts():
    global ACCOUNTS
    print(f"{Y}⚙️ [SYSTEM] Triggering login sequence for {len(ACCOUNTS)} accounts...{RS}")
    for acc in ACCOUNTS:
        t = threading.Thread(target=start_account, args=(acc,), daemon=True)
        t.start()
        time.sleep(0.5)

def reset_accounts():
    global is_resetting, ACCOUNTS
    
    if is_resetting:
        return False, "Reset is already in progress..."
    
    is_resetting = True
    print(f"\n{Y}🔄 [SYSTEM] RESET INITIATED: Cleaning up connections...{RS}")
    
    try:
        with connected_clients_lock:
            uids = list(connected_clients.keys())
            print(f"{R}🧹 Closing {len(uids)} active connections...{RS}")
            for uid in uids:
                try:
                    client = connected_clients[uid]
                    client.stop()
                except:
                    pass
            connected_clients.clear()
        
        time.sleep(1)
        ACCOUNTS = load_unified_accounts(ACCOUNTS_FILE)
        is_resetting = False
        
        if len(ACCOUNTS) > 0:
            run_accounts()
            print(f"{G}✅ [SYSTEM] RESET SUCCESSFUL: Connecting {len(ACCOUNTS)} accounts...{RS}\n")
            return True, f"Reset complete. {len(ACCOUNTS)} accounts are logging in."
        else:
            print(f"{R}⚠️ [SYSTEM] RESET COMPLETED: But no accounts found in {ACCOUNTS_FILE}!{RS}\n")
            return False, "Reset done, but accs.txt is empty."

    except Exception as e:
        is_resetting = False
        print(f"{R}❌ [FATAL ERROR] Reset failed: {e}{RS}")
        return False, f"System error during reset: {str(e)}"

# ==================== FLASK ROUTES ====================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template_string(LOGIN_TEMPLATE, error='Invalid Password!')
    return render_template_string(LOGIN_TEMPLATE, error=None)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/targets', methods=['GET', 'POST'])
def targets_page():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == TARGETS_PASSWORD:
            session['targets_view'] = True
            return redirect(url_for('targets_page'))
        return render_template_string(TARGETS_LOGIN_TEMPLATE, error='Invalid Password!')
    
    if not session.get('targets_view'):
        return render_template_string(TARGETS_LOGIN_TEMPLATE, error=None)
    
    return render_template_string(TARGETS_TEMPLATE)

@app.route('/targets/logout')
def targets_logout():
    session.pop('targets_view', None)
    return redirect(url_for('targets_page'))

@app.route('/stream/targets')
def stream_targets():
    def generate():
        while True:
            with active_spam_lock:
                targets = []
                for uid, info in active_spam_targets.items():
                    elapsed = (datetime.now() - info['start_time']).total_seconds() if info.get('start_time') else 0
                    status = info.get('status', 'UNKNOWN')
                    squad_leader = info.get('squad_leader', '')
                    is_online = info.get('is_online', False)
                    is_squad_leader = info.get('is_squad_leader', False)
                    original_target = info.get('original_target', '')
                    
                    status_display = status
                    if status == 'SOLO': status_display = '🟢 Solo'
                    elif status == 'INSQUAD': status_display = '🔵 In Squad'
                    elif status == 'INGAME': status_display = '🟡 In Game'
                    elif status == 'IN_ROOM': status_display = '🟠 In Room'
                    elif status == 'OFFLINE': status_display = '⚪ Offline'
                    elif status == 'SOCIAL_ISLAND': status_display = '🟣 Social Island'
                    elif status == 'MATCHMAKING': status_display = '🟣 Matchmaking'
                    else: status_display = '⚪ Unknown'
                    
                    banner_url = info.get('banner_url', f"https://mahir-banner-api.vercel.app/uid={uid}")
                    cache_info = target_status_cache.get(uid, {})
                    targets.append({
                        'uid': uid,
                        'type': 'SQUAD' if is_squad_leader else info.get('type', 'full'),
                        'elapsed_minutes': int(elapsed / 60),
                        'banner_url': banner_url,
                        'status': status,
                        'status_display': status_display,
                        'squad_leader': squad_leader,
                        'squad_owner': squad_leader,
                        'mode': cache_info.get('mode', ''),
                        'time_playing': cache_info.get('time_playing', ''),
                        'last_check': info.get('last_check', datetime.now()).strftime('%H:%M:%S'),
                        'is_online': is_online,
                        'is_squad_leader': is_squad_leader,
                        'original_target': original_target
                    })
            yield f"data: {json.dumps(targets)}\n\n"
            time.sleep(3)
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

# ==================== API ROUTES ====================
@app.route('/api/refresh-all-status', methods=['GET', 'POST'])
def api_refresh_all_status():
    if request.method == 'GET':
        password = request.args.get('pass', '')
    else:
        data = request.get_json() or {}
        password = data.get('pass', '') or request.args.get('pass', '')
    
    is_logged_in = session.get('logged_in', False)
    
    if not is_logged_in and password != ADMIN_PASSWORD:
        return jsonify({
            'success': False,
            'message': 'Unauthorized! Please login or provide valid password.',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        with active_spam_lock:
            targets = list(active_spam_targets.keys())
        
        if not targets:
            return jsonify({
                'success': True,
                'message': 'No active targets to refresh',
                'refreshed': 0,
                'targets': []
            })
        
        def refresh_worker():
            for uid in targets:
                try:
                    update_target_status(uid)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"{R}❌ Error refreshing {uid}: {e}{RS}")
        
        thread = Thread(target=refresh_worker, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Refreshing status for {len(targets)} targets...',
            'refreshed': len(targets),
            'targets': targets,
            'status': 'started',
            'method': request.method,
            'authenticated_by': 'session' if is_logged_in else 'password'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}',
            'refreshed': 0
        }), 500

@app.route('/api/refresh-target-status/<uid>', methods=['GET', 'POST'])
def api_refresh_target_status(uid):
    if request.method == 'GET':
        password = request.args.get('pass', '')
    else:
        data = request.get_json() or {}
        password = data.get('pass', '') or request.args.get('pass', '')
    
    is_logged_in = session.get('logged_in', False)
    
    if not is_logged_in and password != ADMIN_PASSWORD:
        return jsonify({
            'success': False,
            'message': 'Unauthorized! Please login or provide valid password.',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        if not uid or not uid.isdigit():
            return jsonify({
                'success': False,
                'message': 'Invalid UID format!'
            }), 400
        
        with active_spam_lock:
            if uid not in active_spam_targets:
                return jsonify({
                    'success': False,
                    'message': f'Target {uid} is not active'
                }), 404
        
        status = update_target_status(uid)
        
        with active_spam_lock:
            info = active_spam_targets.get(uid, {})
            elapsed = (datetime.now() - info.get('start_time', datetime.now())).total_seconds() / 60 if info.get('start_time') else 0
        
        cache_info = target_status_cache.get(uid, {})
        
        return jsonify({
            'success': True,
            'message': f'Status updated for {uid}',
            'uid': uid,
            'status': status,
            'method': request.method,
            'authenticated_by': 'session' if is_logged_in else 'password',
            'details': {
                'status': status,
                'mode': cache_info.get('mode', ''),
                'squad_leader': cache_info.get('squad_leader', ''),
                'time_playing': cache_info.get('time_playing', ''),
                'is_online': cache_info.get('is_online', False),
                'elapsed_minutes': int(elapsed),
                'last_check': info.get('last_check', datetime.now()).strftime('%H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/check-target/<uid>', methods=['GET', 'POST'])
def api_check_target(uid):
    if request.method == 'GET':
        password = request.args.get('pass', '')
    else:
        data = request.get_json() or {}
        password = data.get('pass', '') or request.args.get('pass', '')
    
    is_logged_in = session.get('logged_in', False)
    
    if not is_logged_in and password != ADMIN_PASSWORD:
        return jsonify({
            'success': False,
            'message': 'Unauthorized! Please login or provide valid password.',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        if not uid or not uid.isdigit():
            return jsonify({
                'success': False,
                'message': 'Invalid UID format!'
            }), 400
        
        is_active = uid in active_spam_targets
        status_info = check_target_status_sync(uid)
        status = status_info.get('status', 'UNKNOWN')
        cache_info = target_status_cache.get(uid, {})
        
        return jsonify({
            'success': True,
            'uid': uid,
            'is_active_target': is_active,
            'status': status,
            'method': request.method,
            'authenticated_by': 'session' if is_logged_in else 'password',
            'details': {
                'status': status,
                'mode': status_info.get('mode', ''),
                'squad_owner': status_info.get('squad_owner', ''),
                'room_uid': status_info.get('room_uid', ''),
                'players': status_info.get('players', ''),
                'time_playing': status_info.get('time_playing', ''),
                'is_online': status not in ['OFFLINE', 'NO_RESPONSE', 'ERROR', 'TIMEOUT'],
                'last_check': cache_info.get('last_check', 'Never'),
                'room_info': status_info.get('room_info', {})
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/all-targets-status', methods=['GET', 'POST'])
def api_all_targets_status():
    if request.method == 'GET':
        password = request.args.get('pass', '')
    else:
        data = request.get_json() or {}
        password = data.get('pass', '') or request.args.get('pass', '')
    
    is_logged_in = session.get('logged_in', False)
    
    if not is_logged_in and password != ADMIN_PASSWORD:
        return jsonify({
            'success': False,
            'message': 'Unauthorized! Please login or provide valid password.',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        with active_spam_lock:
            targets = []
            for uid, info in active_spam_targets.items():
                elapsed = (datetime.now() - info.get('start_time', datetime.now())).total_seconds() / 60 if info.get('start_time') else 0
                status = info.get('status', 'UNKNOWN')
                cache_info = target_status_cache.get(uid, {})
                
                targets.append({
                    'uid': uid,
                    'status': status,
                    'mode': cache_info.get('mode', ''),
                    'squad_leader': cache_info.get('squad_leader', ''),
                    'time_playing': cache_info.get('time_playing', ''),
                    'is_online': info.get('is_online', False),
                    'elapsed_minutes': int(elapsed),
                    'last_check': info.get('last_check', datetime.now()).strftime('%H:%M:%S'),
                    'type': info.get('type', 'full'),
                    'is_squad_leader': info.get('is_squad_leader', False),
                    'original_target': info.get('original_target', '')
                })
        
        return jsonify({
            'success': True,
            'total_targets': len(targets),
            'targets': targets,
            'timestamp': datetime.now().isoformat(),
            'method': request.method,
            'authenticated_by': 'session' if is_logged_in else 'password'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/refresh-batch-status', methods=['GET', 'POST'])
def api_refresh_batch_status():
    if request.method == 'GET':
        password = request.args.get('pass', '')
        uids_param = request.args.get('uids', '')
        if uids_param:
            uids = [uid.strip() for uid in uids_param.split(',') if uid.strip().isdigit()]
        else:
            with active_spam_lock:
                uids = list(active_spam_targets.keys())
    else:
        data = request.get_json() or {}
        password = data.get('pass', '') or request.args.get('pass', '')
        uids = data.get('uids', [])
        if not uids:
            with active_spam_lock:
                uids = list(active_spam_targets.keys())
        elif isinstance(uids, str):
            uids = [uid.strip() for uid in uids.split(',') if uid.strip().isdigit()]
    
    is_logged_in = session.get('logged_in', False)
    
    if not is_logged_in and password != ADMIN_PASSWORD:
        return jsonify({
            'success': False,
            'message': 'Unauthorized! Please login or provide valid password.',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    try:
        if not uids:
            return jsonify({
                'success': True,
                'message': 'No targets to refresh',
                'refreshed': 0,
                'targets': []
            })
        
        with active_spam_lock:
            active_uids = [uid for uid in uids if uid in active_spam_targets]
        
        if not active_uids:
            return jsonify({
                'success': False,
                'message': 'No active targets found in the provided list',
                'refreshed': 0
            }), 404
        
        def refresh_worker():
            for uid in active_uids:
                try:
                    update_target_status(uid)
                    time.sleep(0.3)
                except Exception as e:
                    print(f"{R}❌ Error refreshing {uid}: {e}{RS}")
        
        thread = Thread(target=refresh_worker, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Refreshing status for {len(active_uids)} targets...',
            'refreshed': len(active_uids),
            'targets': active_uids,
            'status': 'started',
            'method': request.method,
            'authenticated_by': 'session' if is_logged_in else 'password'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}',
            'refreshed': 0
        }), 500

@app.route('/api/refresh-status-with-details', methods=['GET', 'POST'])
@login_required
def api_refresh_status_with_details():
    try:
        with active_spam_lock:
            targets = list(active_spam_targets.keys())
        
        if not targets:
            return jsonify({
                'success': True,
                'message': 'No active targets',
                'targets': []
            })
        
        refreshed_targets = []
        
        for uid in targets:
            try:
                status = update_target_status(uid)
                with active_spam_lock:
                    info = active_spam_targets.get(uid, {})
                    elapsed = (datetime.now() - info.get('start_time', datetime.now())).total_seconds() / 60 if info.get('start_time') else 0
                
                cache_info = target_status_cache.get(uid, {})
                
                refreshed_targets.append({
                    'uid': uid,
                    'status': status,
                    'mode': cache_info.get('mode', ''),
                    'squad_leader': cache_info.get('squad_leader', ''),
                    'time_playing': cache_info.get('time_playing', ''),
                    'is_online': info.get('is_online', False),
                    'elapsed_minutes': int(elapsed)
                })
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"{R}❌ Error refreshing {uid}: {e}{RS}")
                refreshed_targets.append({
                    'uid': uid,
                    'status': 'ERROR',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': f'Refreshed {len(refreshed_targets)} targets',
            'refreshed': len(refreshed_targets),
            'targets': refreshed_targets,
            'method': request.method,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/profile-info/<uid>')
def get_profile_info(uid):
    if not uid or not uid.isdigit():
        return jsonify({'success': False, 'message': 'Invalid UID!'}), 400
    
    try:
        url = f"https://mahir-info-api.vercel.app/info?uid={uid}"
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code == 200:
            return jsonify(resp.json())
        
        url2 = f"https://mahir-info-api.vercel.app/short_info?uid={uid}"
        resp2 = requests.get(url2, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp2.status_code == 200:
            return jsonify(resp2.json())
        
        return jsonify({'success': False, 'message': 'Profile not found'}), 404
        
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': 'Request timeout'}), 504
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/spam/start', methods=['GET'])
def api_get_start_spam():
    uid = request.args.get('uid')
    password = request.args.get('pass')
    added_by = request.args.get('added_by', 'TORIKUL').strip() or 'TORIKUL'
    reason = request.args.get('reason', 'Manual Start').strip() or 'Manual Start'
    
    if password != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Invalid password!'}), 401
    
    if not uid or not uid.isdigit():
        return jsonify({'success': False, 'message': 'Invalid UID format!'}), 400
    
    success, message = start_spam(uid, 'full', added_by, reason)
    return jsonify({
        'success': success, 
        'message': message,
        'added_by': added_by,
        'reason': reason
    })

@app.route('/api/spam/start/<uid>', methods=['GET'])
@login_required
def api_get_start_spam_path(uid):
    if not uid or not uid.isdigit():
        return jsonify({'success': False, 'message': 'Invalid UID format!'}), 400
    
    success, message = start_spam(uid, 'full')
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop', methods=['GET'])
def api_get_stop_spam():
    uid = request.args.get('uid')
    password = request.args.get('pass')
    
    if password != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Invalid password!'}), 401
    
    if not uid or not uid.isdigit():
        return jsonify({'success': False, 'message': 'Invalid UID format!'}), 400
    
    success, message = stop_spam(uid)
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop/<uid>', methods=['GET'])
@login_required
def api_get_stop_spam_path(uid):
    if not uid or not uid.isdigit():
        return jsonify({'success': False, 'message': 'Invalid UID format!'}), 400
    
    success, message = stop_spam(uid)
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop-all', methods=['GET'])
def api_get_stop_all():
    password = request.args.get('pass')
    
    if password != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Invalid password!'}), 401
    
    success, message = stop_all_spam()
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop-all', methods=['GET'])
@login_required
def api_get_stop_all_session():
    success, message = stop_all_spam()
    return jsonify({'success': success, 'message': message})

@app.route('/api/status', methods=['GET'])
def api_get_status():
    password = request.args.get('pass')
    
    if password != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Invalid password!'}), 401
    
    return jsonify({'success': True, 'data': get_spam_status()})

@app.route('/api/status', methods=['GET'])
@login_required
def api_get_status_session():
    return jsonify({'success': True, 'data': get_spam_status()})

@app.route('/api/accounts', methods=['GET'])
def api_get_accounts():
    password = request.args.get('pass')
    
    if password != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Invalid password!'}), 401
    
    with connected_clients_lock:
        accounts = list(connected_clients.keys())
    return jsonify({'success': True, 'accounts': accounts})

@app.route('/api/accounts', methods=['GET'])
@login_required
def api_get_accounts_session():
    with connected_clients_lock:
        accounts = list(connected_clients.keys())
    return jsonify({'success': True, 'accounts': accounts})

@app.route('/api/accounts/count', methods=['GET'])
@login_required
def api_get_accounts_count():
    try:
        global ACCOUNTS
        total = len(ACCOUNTS)
        return jsonify({
            'success': True,
            'total': total,
            'group': total,
            'room': 0
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/upload/accs', methods=['POST'])
@login_required
def upload_accs():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return jsonify({'success': False, 'message': 'Only .txt files allowed'}), 400
    
    try:
        content = file.read().decode('utf-8')
        with open('accs.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        
        global ACCOUNTS
        ACCOUNTS = load_unified_accounts('accs.txt')
        
        Thread(target=run_accounts, daemon=True).start()
        
        return jsonify({
            'success': True, 
            'message': 'Unified accounts uploaded', 
            'total': len(ACCOUNTS),
            'group': len([a for a in ACCOUNTS if a['type'] == 'group']),
            'room': 0
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/get/accs')
@login_required
def download_accs():
    if os.path.exists('accs.txt'):
        with open('accs.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/plain', headers={'Content-Disposition': 'attachment;filename=accs.txt'})
    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/api/reset-accounts', methods=['POST'])
@login_required
def api_reset_accounts():
    success, message = reset_accounts()
    return jsonify({'success': success, 'message': message})

@app.route('/api/spam/start', methods=['POST'])
@login_required
def api_post_start_spam():
    data = request.get_json()
    uid_input = data.get('uid', '').strip()
    added_by = data.get('added_by', 'TORIKUL').strip() or 'TORIKUL'
    reason = data.get('reason', 'Manual Start').strip() or 'Manual Start'
    
    if not uid_input:
        return jsonify({'success': False, 'message': 'UID required!'}), 400
    
    raw_uids = re.split(r'[,\s]+', uid_input)
    results = []

    for target in raw_uids:
        target = target.strip()
        if target.isdigit() and 8 <= len(target) <= 12:
            success, message = start_spam(target, 'full', added_by, reason)
            results.append({'uid': target, 'success': success, 'message': message})
        else:
            results.append({'uid': target, 'success': False, 'message': 'Invalid length (8-12 digits required)'})
    
    return jsonify({'success': True, 'results': results})

@app.route('/api/stop', methods=['POST'])
@login_required
def api_post_stop_spam():
    data = request.get_json()
    uid = data.get('uid', '').strip()
    
    if not uid or not uid.isdigit():
        return jsonify({'success': False, 'message': 'Valid UID required!'}), 400
    
    success, message = stop_spam(uid)
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop-all', methods=['POST'])
@login_required
def api_post_stop_all():
    success, message = stop_all_spam()
    return jsonify({'success': success, 'message': message})

@app.route('/api/targets', methods=['GET'])
def api_targets():
    password = request.args.get('pass')
    if password != ADMIN_PASSWORD and password != TARGETS_PASSWORD and not session.get('logged_in') and not session.get('targets_view'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    with active_spam_lock:
        targets = []
        for uid, info in active_spam_targets.items():
            start_time = info.get('start_time')
            elapsed = (datetime.now() - start_time).total_seconds() if start_time else 0
            status = info.get('status', 'UNKNOWN')
            squad_leader = info.get('squad_leader', '')
            is_online = info.get('is_online', False)
            is_squad_leader = info.get('is_squad_leader', False)
            original_target = info.get('original_target', '')
            
            status_display = status
            if status == 'SOLO': status_display = '🟢 Solo'
            elif status == 'INSQUAD': status_display = '🔵 In Squad'
            elif status == 'INGAME': status_display = '🟡 In Game'
            elif status == 'IN_ROOM': status_display = '🟠 In Room'
            elif status == 'OFFLINE': status_display = '⚪ Offline'
            else: status_display = '⚪ Unknown'
            
            banner_url = info.get('banner_url', f"https://mahir-banner-api.vercel.app/uid={uid}")
            
            cache_info = target_status_cache.get(uid, {})
            targets.append({
                'uid': uid,
                'type': 'SQUAD' if is_squad_leader else info.get('type', 'full'),
                'elapsed_minutes': int(elapsed/60),
                'banner_url': banner_url,
                'status': status,
                'status_display': status_display,
                'squad_leader': squad_leader,
                'squad_owner': squad_leader,
                'mode': cache_info.get('mode', ''),
                'time_playing': cache_info.get('time_playing', ''),
                'last_check': info.get('last_check', datetime.now()).strftime('%H:%M:%S'),
                'is_online': is_online,
                'is_squad_leader': is_squad_leader,
                'original_target': original_target,
                'added_by': info.get('added_by', 'TORIKUL'),
                'reason': info.get('reason', 'Manual Start'),
                'added_time': info.get('start_time', datetime.now()).isoformat() if info.get('start_time') else None
            })
    return jsonify({'success': True, 'targets': targets})

@app.route('/health')
def health_check():
    try:
        with connected_clients_lock:
            clients_count = len(connected_clients)
        
        with active_spam_lock:
            targets_count = len(active_spam_targets)
        
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
        except:
            memory_mb = 0
        
        return jsonify({
            'status': 'healthy',
            'clients': clients_count,
            'targets': targets_count,
            'memory_mb': round(memory_mb, 2),
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/stream/console')
def stream_console():
    def generate():
        console_logs = []
        while True:
            yield f"data: {json.dumps(console_logs[-20:])}\n\n"
            time.sleep(1)
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/download/targets', methods=['GET'])
@login_required
def download_targets_file():
    if os.path.exists('target.txt'):
        with open('target.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/plain', headers={'Content-Disposition': 'attachment;filename=target.txt'})
    return jsonify({'success': False, 'message': 'target.txt not found'}), 404

@app.route('/api/download/squad_data', methods=['GET'])
@login_required
def download_squad_data_file():
    if os.path.exists(SQUAD_DATA_FILE):
        with open(SQUAD_DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/json', headers={'Content-Disposition': 'attachment;filename=squad_data.json'})
    return jsonify({'success': False, 'message': 'squad_data.json not found'}), 404

@app.route('/api/upload/targets', methods=['POST'])
@login_required
def upload_targets_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return jsonify({'success': False, 'message': 'Only .txt files allowed'}), 400
    
    try:
        content = file.read().decode('utf-8')
        
        with open('target.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        
        uids = []
        for line in content.splitlines():
            line = line.strip()
            if line and line.isdigit() and 8 <= len(line) <= 12:
                uids.append(line)
        
        started = []
        failed = []
        for uid in uids:
            success, message = start_spam(uid, 'full')
            if success:
                started.append(uid)
            else:
                failed.append({'uid': uid, 'reason': message})
        
        return jsonify({
            'success': True,
            'message': f'Uploaded target.txt with {len(uids)} UIDs. Started: {len(started)}, Failed: {len(failed)}',
            'started': started,
            'failed': failed,
            'total': len(uids)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/upload/squad_data', methods=['POST'])
@login_required
def upload_squad_data_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.json'):
        return jsonify({'success': False, 'message': 'Only .json files allowed'}), 400
    
    try:
        content = file.read().decode('utf-8')
        data = json.loads(content)
        
        with open(SQUAD_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
        current_time = datetime.now()
        restored = 0
        expired = 0
        
        for uid, info in data.items():
            try:
                start_time = datetime.fromisoformat(info['start_time'])
                if (current_time - start_time).total_seconds() < SQUAD_JOIN_DURATION:
                    start_spam(uid, 'squad')
                    restored += 1
                else:
                    expired += 1
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': f'Uploaded squad_data.json with {len(data)} entries. Restored: {restored}, Expired: {expired}',
            'total': len(data),
            'restored': restored,
            'expired': expired
        })
        
    except json.JSONDecodeError:
        return jsonify({'success': False, 'message': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/squad-leaders', methods=['GET'])
@login_required
def get_squad_leaders():
    try:
        data = load_squad_json()
        current_time = datetime.now()
        leaders = []
        
        for uid, info in data.items():
            start_time = datetime.fromisoformat(info['start_time'])
            elapsed = (current_time - start_time).total_seconds()
            remaining = max(0, SQUAD_JOIN_DURATION - elapsed)
            is_expired = remaining <= 0
            
            target_info = {}
            if uid in active_spam_targets:
                target_info = active_spam_targets[uid]
            
            leaders.append({
                'uid': uid,
                'original_target': info.get('original_target', ''),
                'start_time': start_time.isoformat(),
                'elapsed_minutes': int(elapsed / 60),
                'remaining_minutes': int(remaining / 60),
                'is_expired': is_expired,
                'status': target_info.get('status', 'UNKNOWN'),
                'is_online': target_info.get('is_online', False),
                'spam_active': uid in active_spam_targets
            })
        
        leaders.sort(key=lambda x: (x['is_expired'], -x['remaining_minutes']))
        
        return jsonify({
            'success': True,
            'total': len(leaders),
            'leaders': leaders,
            'expired_count': len([l for l in leaders if l['is_expired']]),
            'active_count': len([l for l in leaders if not l['is_expired']])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/squad-leaders/cleanup', methods=['POST'])
@login_required
def cleanup_squad_leaders():
    try:
        data = load_squad_json()
        current_time = datetime.now()
        removed = []
        kept = {}
        
        for uid, info in data.items():
            start_time = datetime.fromisoformat(info['start_time'])
            elapsed = (current_time - start_time).total_seconds()
            
            if elapsed >= SQUAD_JOIN_DURATION:
                with active_spam_lock:
                    if uid in active_spam_targets:
                        del active_spam_targets[uid]
                    if uid in target_status_cache:
                        del target_status_cache[uid]
                removed.append(uid)
            else:
                kept[uid] = info
        
        save_squad_json(kept)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {len(removed)} expired squad leaders',
            'removed': removed,
            'kept_count': len(kept),
            'removed_count': len(removed)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/squad-leaders/remove/<uid>', methods=['POST'])
@login_required
def remove_squad_leader(uid):
    try:
        data = load_squad_json()
        
        if uid not in data:
            return jsonify({'success': False, 'message': f'UID {uid} not found in squad_data.json'}), 404
        
        stop_spam(uid)
        del data[uid]
        save_squad_json(data)
        
        return jsonify({
            'success': True,
            'message': f'Removed squad leader {uid}',
            'uid': uid
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/cleanup/expired-targets', methods=['POST'])
@login_required
def cleanup_expired_targets():
    try:
        with active_spam_lock:
            targets_to_remove = []
            current_time = datetime.now()
            
            for uid, info in active_spam_targets.items():
                start_time = info.get('start_time')
                if start_time:
                    elapsed = (current_time - start_time).total_seconds()
                    if elapsed >= SQUAD_JOIN_DURATION and info.get('is_squad_leader', False):
                        targets_to_remove.append(uid)
        
        removed = []
        for uid in targets_to_remove:
            success, _ = stop_spam(uid)
            if success:
                removed.append(uid)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {len(removed)} expired squad leader targets',
            'removed': removed,
            'removed_count': len(removed)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/download/master', methods=['GET'])
@login_required
def download_master_file():
    """Download master_acc.txt file"""
    filename = "master_acc.txt"
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/plain', headers={'Content-Disposition': f'attachment;filename={filename}'})
    return jsonify({'success': False, 'message': 'master_acc.txt not found'}), 404

@app.route('/api/upload/master', methods=['POST'])
@login_required
def upload_master_file():
    """Upload master_acc.txt file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return jsonify({'success': False, 'message': 'Only .txt files allowed'}), 400
    
    try:
        content = file.read().decode('utf-8')
        with open('master_acc.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # লগইন সেশন রিসেট করতে
        with _lk:
            _cx.clear()
        
        return jsonify({'success': True, 'message': 'master_acc.txt uploaded successfully! Session refreshed.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# ==================== TEMPLATES ====================
LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TORIKUL SYSTEM | Secure Login</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Rajdhani', sans-serif; }
        body { background: #05050a; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; overflow: hidden; }
        #matrix-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; }
        .login-box { background: rgba(10, 10, 25, 0.8); border: 1px solid rgba(255, 0, 127, 0.3); border-radius: 16px; padding: 50px 35px; width: 100%; max-width: 420px; backdrop-filter: blur(15px); text-align: center; position: relative; z-index: 1; box-shadow: 0 0 60px rgba(255, 0, 127, 0.1); }
        .login-box h1 { font-family: 'Orbitron', sans-serif; font-size: 2.2rem; background: linear-gradient(135deg, #ff007f, #7f00ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; }
        .login-box p.sub { color: #00ffcc; text-transform: uppercase; letter-spacing: 4px; margin-bottom: 35px; font-size: 0.85rem; }
        .input-group { position: relative; margin-bottom: 25px; }
        .input-group i { position: absolute; left: 15px; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.3); font-size: 1.1rem; }
        .input-group input { width: 100%; padding: 15px 15px 15px 45px; background: rgba(0, 0, 0, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; color: #fff; font-size: 1.1rem; outline: none; transition: 0.3s; }
        .input-group input:focus { border-color: #ff007f; box-shadow: 0 0 20px rgba(255, 0, 127, 0.15); }
        .btn-login { width: 100%; padding: 16px; background: linear-gradient(135deg, #ff007f, #7f00ff); border: none; border-radius: 10px; color: #fff; font-size: 1.2rem; font-weight: 700; cursor: pointer; transition: 0.3s; letter-spacing: 2px; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 5px 30px rgba(255, 0, 127, 0.3); }
        .error { color: #ff4444; margin-top: 15px; font-weight: 600; }
        .footer-text { color: rgba(255,255,255,0.2); font-size: 0.7rem; margin-top: 20px; letter-spacing: 1px; }
    </style>
</head>
<body>
    <canvas id="matrix-canvas"></canvas>
    <div class="login-box">
        <h1>TORIKUL SYSTEM</h1>
        <p class="sub">Access Control Panel</p>
        <form action="/login" method="POST">
            <div class="input-group"><i class="fas fa-key"></i><input type="password" name="password" placeholder="Enter Security Password" required></div>
            <button type="submit" class="btn-login"><i class="fas fa-unlock-alt"></i> UNLOCK</button>
            {% if error %}<div class="error"><i class="fas fa-exclamation-circle"></i> {{ error }}</div>{% endif %}
        </form>
        <div class="footer-text">TORIKUL ENGINE v3.3</div>
    </div>
    <script>
        const canvas = document.getElementById('matrix-canvas'); const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&'.split('');
        const fontSize = 14; const columns = canvas.width / fontSize; const drops = Array(Math.floor(columns)).fill(1);
        function drawMatrix() {
            ctx.fillStyle = 'rgba(5, 5, 10, 0.05)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#ff007f'; ctx.font = fontSize + 'px monospace';
            drops.forEach((y, i) => { const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, y * fontSize);
                if (y * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0; drops[i]++; });
        }
        setInterval(drawMatrix, 35);
        window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });
    </script>
</body>
</html>'''

TARGETS_LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 TARGETS | TORIKUL</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Rajdhani', sans-serif; }
        body { background: #05050a; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; overflow: hidden; }
        #matrix-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; }
        .login-box { background: rgba(10, 10, 25, 0.8); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 16px; padding: 50px 35px; width: 100%; max-width: 420px; backdrop-filter: blur(15px); text-align: center; position: relative; z-index: 1; box-shadow: 0 0 60px rgba(0, 212, 255, 0.1); }
        .login-box h1 { font-family: 'Orbitron', sans-serif; font-size: 2.2rem; background: linear-gradient(135deg, #00d4ff, #7f00ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; }
        .login-box p.sub { color: #ff007f; text-transform: uppercase; letter-spacing: 4px; margin-bottom: 35px; font-size: 0.85rem; }
        .input-group { position: relative; margin-bottom: 25px; }
        .input-group i { position: absolute; left: 15px; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.3); font-size: 1.1rem; }
        .input-group input { width: 100%; padding: 15px 15px 15px 45px; background: rgba(0, 0, 0, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; color: #fff; font-size: 1.1rem; outline: none; transition: 0.3s; }
        .input-group input:focus { border-color: #00d4ff; box-shadow: 0 0 20px rgba(0, 212, 255, 0.15); }
        .btn-login { width: 100%; padding: 16px; background: linear-gradient(135deg, #00d4ff, #7f00ff); border: none; border-radius: 10px; color: #fff; font-size: 1.2rem; font-weight: 700; cursor: pointer; transition: 0.3s; letter-spacing: 2px; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 5px 30px rgba(0, 212, 255, 0.3); }
        .error { color: #ff4444; margin-top: 15px; font-weight: 600; }
        .footer-text { color: rgba(255,255,255,0.2); font-size: 0.7rem; margin-top: 20px; letter-spacing: 1px; }
    </style>
</head>
<body>
    <canvas id="matrix-canvas"></canvas>
    <div class="login-box">
        <h1><i class="fas fa-crosshairs"></i> TARGETS</h1>
        <p class="sub">View Active Targets</p>
        <form action="/targets" method="POST">
            <div class="input-group"><i class="fas fa-key"></i><input type="password" name="password" placeholder="Enter Target Password" required></div>
            <button type="submit" class="btn-login"><i class="fas fa-unlock-alt"></i> VIEW TARGETS</button>
            {% if error %}<div class="error"><i class="fas fa-exclamation-circle"></i> {{ error }}</div>{% endif %}
        </form>
        <div class="footer-text">TORIKUL TARGET VIEWER v1.0</div>
    </div>
    <script>
        const canvas = document.getElementById('matrix-canvas'); const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&'.split('');
        const fontSize = 14; const columns = canvas.width / fontSize; const drops = Array(Math.floor(columns)).fill(1);
        function drawMatrix() {
            ctx.fillStyle = 'rgba(5, 5, 10, 0.05)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00d4ff'; ctx.font = fontSize + 'px monospace';
            drops.forEach((y, i) => { const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, y * fontSize);
                if (y * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0; drops[i]++; });
        }
        setInterval(drawMatrix, 35);
        window.addEventListener('resize', () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; });
    </script>
</body>
</html>'''

TARGETS_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 TARGETS | TORIKUL SYSTEM</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #060417, #0e0b30, #130a24); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .logo { font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #ffd700, #ffaa00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo i { -webkit-text-fill-color: initial; color: #ffd700; }
        .search-box { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .search-box input { padding: 10px 16px; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: rgba(0,0,0,0.4); color: #fff; font-size: 0.95rem; font-family: monospace; outline: none; min-width: 180px; transition: 0.3s; }
        .search-box input:focus { border-color: #ffd700; box-shadow: 0 0 20px rgba(255,215,0,0.1); }
        .search-box button { padding: 10px 16px; border: none; border-radius: 8px; background: linear-gradient(135deg, #ffd700, #ffaa00); color: #000; font-weight: 600; cursor: pointer; transition: 0.3s; font-size: 0.9rem; }
        .search-box button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(255,215,0,0.3); }
        .btn { padding: 8px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: 0.3s; font-size: 0.85rem; }
        .btn-outline { background: transparent; border: 1px solid rgba(255,255,255,0.15); color: #fff; }
        .btn-outline:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.3); }
        .count-badge { background: rgba(255, 215, 0, 0.15); padding: 6px 16px; border-radius: 20px; font-size: 0.95rem; color: #ffd700; }
        .footer { text-align: center; color: rgba(255,255,255,0.15); font-size: 0.75rem; margin-top: 30px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.03); }
        .refresh-btn { background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.2); color: #ffd700; padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 0.8rem; transition: 0.3s; }
        .refresh-btn:hover { background: rgba(255,215,0,0.2); }

        .target-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; margin-top: 25px; }
        .target-card { 
            background: rgba(20, 20, 50, 0.7); 
            border-radius: 14px; 
            overflow: hidden; 
            border: 1px solid rgba(255,255,255,0.06); 
            backdrop-filter: blur(10px); 
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
            animation: fadeIn 0.5s ease forwards; 
            opacity: 0; 
            transform: translateY(20px); 
            cursor: pointer;
        }
        .target-card:nth-child(1) { animation-delay: 0.05s; }
        .target-card:nth-child(2) { animation-delay: 0.10s; }
        .target-card:nth-child(3) { animation-delay: 0.15s; }
        .target-card:nth-child(4) { animation-delay: 0.20s; }
        .target-card:nth-child(5) { animation-delay: 0.25s; }
        .target-card:nth-child(6) { animation-delay: 0.30s; }
        .target-card:nth-child(7) { animation-delay: 0.35s; }
        .target-card:nth-child(8) { animation-delay: 0.40s; }
        @keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }
        .target-card:hover { transform: translateY(-4px) scale(1.01); border-color: rgba(255, 215, 0, 0.3); box-shadow: 0 12px 40px rgba(255, 215, 0, 0.1); }
        .target-card img { width: 100%; height: auto; display: block; border-bottom: 1px solid rgba(255,255,255,0.05); pointer-events: none; }

        .target-row {
            display: flex;
            flex-direction: column;
            padding: 10px 14px;
            background: rgba(0,0,0,0.4);
            gap: 6px;
        }
        .target-row .top-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 6px;
        }
        .target-row .uid-section {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .target-row .uid {
            font-family: monospace;
            font-weight: 700;
            color: #ffd700;
            font-size: 0.95rem;
            text-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
        }
        .target-row .badge-type {
            font-size: 0.55rem;
            padding: 2px 10px;
            border-radius: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge-type.squad { background: rgba(255, 215, 0, 0.2); color: #ffd700; border: 1px solid rgba(255, 215, 0, 0.2); }
        .badge-type.full { background: rgba(255, 0, 127, 0.2); color: #ff007f; border: 1px solid rgba(255, 0, 127, 0.15); }
        .badge-type.room { background: rgba(0, 212, 255, 0.15); color: #00d4ff; border: 1px solid rgba(0, 212, 255, 0.12); }
        .badge-type.auto { background: rgba(0, 255, 204, 0.15); color: #00ffcc; border: 1px solid rgba(0, 255, 204, 0.12); }

        .target-row .time-section {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.7rem;
            color: rgba(255,255,255,0.35);
        }
        .target-row .time-section i { color: #ffd700; font-size: 0.6rem; }

        .target-row .meta-info {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 4px 12px;
            font-size: 0.6rem;
            color: rgba(255,255,255,0.3);
            padding-top: 4px;
            border-top: 1px solid rgba(255,255,255,0.04);
            margin-top: 2px;
        }
        .target-row .meta-info .added-by {
            color: #ffd700;
            font-weight: 600;
        }
        .target-row .meta-info .reason {
            color: rgba(255,255,255,0.5);
            font-style: italic;
        }
        .target-row .meta-info .added-time {
            color: rgba(255,255,255,0.2);
            font-size: 0.55rem;
        }
        .target-row .meta-info .badge-label {
            background: rgba(255,215,0,0.08);
            padding: 1px 8px;
            border-radius: 8px;
            color: rgba(255,215,0,0.5);
            font-size: 0.5rem;
            text-transform: uppercase;
        }

        .empty-state { color: rgba(255,255,255,0.3); text-align: center; padding: 60px 20px; width: 100%; font-size: 1.2rem; }
        .empty-state i { font-size: 3rem; display: block; margin-bottom: 15px; color: rgba(255,255,255,0.1); }

        .search-result { margin-top: 20px; padding: 15px; background: rgba(255,215,0,0.05); border-radius: 12px; border: 1px solid rgba(255,215,0,0.1); display: none; }
        .search-result .result-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px; flex-wrap: wrap; gap: 10px; }
        .search-result .result-item .meta { display: flex; gap: 10px; flex-wrap: wrap; font-size: 0.8rem; color: rgba(255,255,255,0.5); }
        .search-result .result-item .meta .added { color: #ffd700; }
        .search-result .result-item .meta .reason-text { color: rgba(255,255,255,0.4); font-style: italic; }

        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 1000; justify-content: center; align-items: center; padding: 20px; animation: fadeIn 0.3s ease; }
        .modal-overlay.active { display: flex; }
        .modal-box { background: rgba(15, 15, 40, 0.95); border: 1px solid rgba(255, 215, 0, 0.2); border-radius: 20px; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 30px; position: relative; box-shadow: 0 20px 80px rgba(0,0,0,0.8); animation: slideUp 0.3s ease; }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .modal-close { position: absolute; top: 15px; right: 20px; font-size: 1.8rem; color: rgba(255,255,255,0.4); cursor: pointer; transition: 0.3s; background: none; border: none; }
        .modal-close:hover { color: #ffd700; transform: rotate(90deg); }
        .modal-header { display: flex; gap: 20px; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .modal-avatar { width: 80px; height: 80px; border-radius: 50%; border: 3px solid #ffd700; object-fit: cover; }
        .modal-name { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #ffd700, #ffaa00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .modal-uid { font-family: monospace; color: rgba(255,255,255,0.5); font-size: 0.9rem; }
        .modal-level { background: rgba(255,215,0,0.2); color: #ffd700; padding: 2px 12px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }
        .modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0; }
        .modal-item { background: rgba(255,255,255,0.03); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.04); }
        .modal-item .label { font-size: 0.6rem; text-transform: uppercase; color: rgba(255,255,255,0.3); letter-spacing: 1px; }
        .modal-item .value { font-weight: 600; font-size: 0.95rem; margin-top: 2px; color: #fff; }
        .modal-item .value.highlight { color: #ffd700; }
        .modal-item .value.gold { color: #ffd700; }
        .modal-item .value.pink { color: #ff007f; }
        .modal-item .value.green { color: #00ffcc; }
        .modal-clan { background: rgba(255,215,0,0.05); padding: 12px 16px; border-radius: 10px; border: 1px solid rgba(255,215,0,0.08); margin: 10px 0; }
        .modal-clan .clan-name { color: #ffd700; font-weight: 600; font-size: 1.1rem; }
        .modal-clan .clan-detail { color: rgba(255,255,255,0.4); font-size: 0.75rem; margin-top: 2px; }
        .modal-signature { color: rgba(255,255,255,0.5); font-style: italic; font-size: 0.85rem; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px; border-left: 3px solid #ffd700; margin: 10px 0; word-break: break-word; }
        .modal-loading { text-align: center; padding: 40px; color: rgba(255,255,255,0.3); }
        .modal-loading i { font-size: 2.5rem; display: block; margin-bottom: 15px; color: #ffd700; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .modal-error { text-align: center; padding: 30px; color: #ff4444; }
        .modal-error i { font-size: 2.5rem; display: block; margin-bottom: 15px; }

        @media (max-width: 600px) { 
            .target-grid { grid-template-columns: 1fr; } 
            .header { flex-direction: column; text-align: center; } 
            .search-box { width: 100%; justify-content: center; } 
            .search-box input { flex: 1; min-width: 120px; } 
            .modal-grid { grid-template-columns: 1fr; } 
            .modal-header { flex-direction: column; text-align: center; } 
            .target-row .top-row { flex-direction: column; align-items: stretch; text-align: center; } 
            .target-row .uid-section { justify-content: center; } 
            .target-row .time-section { justify-content: center; } 
            .target-row .meta-info { justify-content: center; } 
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo"><i class="fas fa-crosshairs"></i> TARGETS</div>
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Search UID..." onkeypress="if(event.key==='Enter') searchTarget()">
                <button onclick="searchTarget()"><i class="fas fa-search"></i></button>
                <button onclick="clearSearch()" class="btn btn-outline" style="padding: 8px 12px;"><i class="fas fa-times"></i></button>
            </div>
            <span class="count-badge"><i class="fas fa-bullseye"></i> <span id="targetCount">0</span> Active</span>
            <button class="refresh-btn" onclick="refreshTargets()"><i class="fas fa-sync-alt"></i> Refresh</button>
            <a href="/targets/logout" class="btn btn-outline"><i class="fas fa-sign-out-alt"></i> EXIT</a>
        </div>
    </div>
    
    <div id="searchResult" class="search-result">
        <h4 style="margin-bottom:10px;color:#ffd700;"><i class="fas fa-search"></i> Search Result</h4>
        <div id="searchResultContent"></div>
    </div>
    
    <div id="targetGrid" class="target-grid">
        <div class="empty-state"><i class="fas fa-crosshairs"></i> No active targets</div>
    </div>
    
    <div class="footer">TORIKUL TARGET VIEWER v2.0 | <i class="fas fa-bolt" style="color:#ffd700;"></i> Click on any target card for full profile</div>
</div>

<div class="modal-overlay" id="profileModal">
    <div class="modal-box">
        <button class="modal-close" onclick="closeModal()">&times;</button>
        <div id="modalContent">
            <div class="modal-loading"><i class="fas fa-spinner"></i> Loading profile...</div>
        </div>
    </div>
</div>

<script>
    const targetGrid = document.getElementById('targetGrid');
    const targetCount = document.getElementById('targetCount');

    function formatDate(timestamp) {
        if (!timestamp) return 'N/A';
        try {
            const d = new Date(parseInt(timestamp) * 1000);
            return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch { return timestamp; }
    }

    function getRankEmoji(rank) {
        if (rank <= 100) return '🏆';
        if (rank <= 500) return '🥇';
        if (rank <= 1000) return '🥈';
        if (rank <= 2000) return '🥉';
        return '⭐';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getBadgeClass(type) {
        const t = (type || '').toUpperCase();
        if (t === 'SQUAD' || t === 'SQUAD LEADER') return 'squad';
        if (t === 'FULL' || t === 'FULL SPAM') return 'full';
        if (t === 'ROOM') return 'room';
        if (t === 'AUTO' || t === 'SYSTEM') return 'auto';
        return 'full';
    }

    function getDisplayType(type) {
        const t = (type || '').toUpperCase();
        if (t === 'SQUAD' || t === 'SQUAD LEADER') return '👑 SQUAD';
        if (t === 'FULL' || t === 'FULL SPAM') return '⚡ FULL';
        if (t === 'ROOM') return '🚪 ROOM';
        if (t === 'AUTO' || t === 'SYSTEM') return '🤖 AUTO';
        return '⚡ FULL';
    }

    function getAddedByLabel(addedBy) {
        if (!addedBy || addedBy === 'SYSTEM') return '🤖 SYSTEM';
        if (addedBy === 'TORIKUL') return '👤 TORIKUL';
        return `👤 ${escapeHtml(addedBy)}`;
    }

    function renderTargets(targets) {
        targetCount.textContent = targets.length;
        if (!targets || targets.length === 0) {
            targetGrid.innerHTML = '<div class="empty-state"><i class="fas fa-crosshairs"></i> No active targets</div>';
            return;
        }
        targetGrid.innerHTML = targets.map((t, index) => {
            const badgeClass = getBadgeClass(t.type);
            const displayType = getDisplayType(t.type);
            const addedBy = t.added_by || 'TORIKUL';
            const reason = t.reason || 'Manual Start';
            const timeAgo = t.elapsed_minutes || 0;
            const timeText = timeAgo < 60 ? `${timeAgo}m` : `${Math.floor(timeAgo/60)}h ${timeAgo%60}m`;
            const addedTime = t.added_time ? new Date(t.added_time).toLocaleTimeString() : '';
            
            return `
            <div class="target-card" style="animation-delay: ${index * 0.04}s" onclick="openProfile('${t.uid}')">
                <img src="${t.banner_url}" 
                     alt="Banner" 
                     onerror="this.onerror=null; this.src='https://mahir-photo-url.vercel.app/image/Picsart_26-06-20_16-14-53-925.jpg';">
                <div class="target-row">
                    <div class="top-row">
                        <div class="uid-section">
                            <span class="uid">🎯 ${t.uid}</span>
                            <span class="badge-type ${badgeClass}">${displayType}</span>
                        </div>
                        <div class="time-section">
                            <i class="fas fa-clock"></i>
                            <span>${timeText}</span>
                        </div>
                    </div>
                    <div class="meta-info">
                        <span class="added-by">${getAddedByLabel(addedBy)}</span>
                        <span class="reason">💬 ${escapeHtml(reason)}</span>
                        ${addedTime ? `<span class="added-time">🕐 ${addedTime}</span>` : ''}
                        ${t.is_squad_leader ? `<span class="badge-label">👑 LEADER</span>` : ''}
                    </div>
                </div>
            </div>
            `;
        }).join('');
    }

    function refreshTargets() {
        fetch('/api/targets?pass=HUNTERTORIKUL')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    renderTargets(data.targets);
                    const btn = document.querySelector('.refresh-btn');
                    const orig = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check"></i> Updated';
                    setTimeout(() => btn.innerHTML = orig, 2000);
                }
            })
            .catch(() => {});
    }

    async function openProfile(uid) {
        const modal = document.getElementById('profileModal');
        const content = document.getElementById('modalContent');
        modal.classList.add('active');
        content.innerHTML = `<div class="modal-loading"><i class="fas fa-spinner"></i> Loading profile...</div>`;

        try {
            const resp = await fetch(`/api/profile-info/${uid}`);
            if (!resp.ok) {
                const errorData = await resp.json();
                throw new Error(errorData.message || 'Failed to fetch profile');
            }
            const data = await resp.json();

            const basic = data.basicInfo || {};
            const clan = data.clanBasicInfo || {};
            const captain = data.captainBasicInfo || {};
            const social = data.socialInfo || {};
            const credit = data.creditScoreInfo || {};
            const diamond = data.diamondCostRes || {};
            const pet = data.petInfo || {};

            const nickname = basic.nickname || 'Unknown';
            const level = basic.level || '?';
            const rank = basic.rank || 'N/A';
            const csRank = basic.csRank || 'N/A';
            const badgeCnt = basic.badgeCnt || 0;
            const liked = basic.liked || 0;
            const accountAge = basic.accountAge || 'N/A';
            const lastLogin = formatDate(basic.lastLoginAt);
            const created = formatDate(basic.createAt);
            const clanName = clan.clanName || 'No Guild';
            const clanLevel = clan.clanLevel || '?';
            const clanMembers = clan.memberNum || '?';
            const clanCapacity = clan.capacity || '?';
            const signature = social.signature || 'No signature';
            const creditScore = credit.creditScore || '?';
            const diamondCost = diamond.diamondCost || '?';
            const petName = pet.name || 'No pet';
            const petLevel = pet.level || '?';
            const region = basic.region || 'N/A';
            const clanId = clan.clanId || '';
            const avatarUrl = basic.headPic ? `https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/${basic.headPic}.png` : '';

            content.innerHTML = `
                <div class="modal-header">
                    ${avatarUrl ? `<img class="modal-avatar" src="${avatarUrl}" onerror="this.style.display='none'" alt="Avatar">` : `<div class="modal-avatar" style="background:linear-gradient(135deg,#ffd700,#ffaa00);display:flex;align-items:center;justify-content:center;font-size:2rem;">${nickname.charAt(0)}</div>`}
                    <div>
                        <div class="modal-name">${escapeHtml(nickname)}</div>
                        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:4px;">
                            <span class="modal-uid">UID: ${uid}</span>
                            <span class="modal-level">Lv.${level}</span>
                            <span style="font-size:0.7rem;color:rgba(255,255,255,0.3);">${region}</span>
                        </div>
                    </div>
                </div>
                <div class="modal-grid">
                    <div class="modal-item"><div class="label">🏆 BR Rank</div><div class="value highlight">${getRankEmoji(rank)} ${rank}</div></div>
                    <div class="modal-item"><div class="label">⚔️ CS Rank</div><div class="value gold">${getRankEmoji(csRank)} ${csRank}</div></div>
                    <div class="modal-item"><div class="label">📛 Badges</div><div class="value pink">${badgeCnt} badges</div></div>
                    <div class="modal-item"><div class="label">❤️ Likes</div><div class="value green">${liked.toLocaleString()}</div></div>
                    <div class="modal-item"><div class="label">📅 Account Age</div><div class="value">${accountAge}</div></div>
                    <div class="modal-item"><div class="label">💎 Diamond Cost</div><div class="value gold">${diamondCost}</div></div>
                    <div class="modal-item"><div class="label">⭐ Credit Score</div><div class="value ${creditScore >= 90 ? 'green' : creditScore >= 70 ? 'gold' : 'pink'}">${creditScore}</div></div>
                    <div class="modal-item"><div class="label">🐾 Pet</div><div class="value">${escapeHtml(petName)} (Lv.${petLevel})</div></div>
                    <div class="modal-item" style="grid-column:1/-1;"><div class="label">🕐 Last Login</div><div class="value" style="color:rgba(255,255,255,0.6);">${lastLogin}</div></div>
                    <div class="modal-item" style="grid-column:1/-1;"><div class="label">📆 Created</div><div class="value" style="color:rgba(255,255,255,0.4);">${created}</div></div>
                </div>
                <div class="modal-clan">
                    <div class="clan-name">🏛️ ${escapeHtml(clanName)}</div>
                    <div class="clan-detail">Level ${clanLevel} · ${clanMembers}/${clanCapacity} members</div>
                    ${captain.nickname ? `<div class="clan-detail">👑 Leader: ${escapeHtml(captain.nickname)} (${captain.accountId})</div>` : ''}
                    ${clanId ? `<div class="clan-detail" style="font-size:0.65rem;color:rgba(255,255,255,0.2);">Clan ID: ${clanId}</div>` : ''}
                </div>
                ${signature && signature !== 'No signature' ? `<div class="modal-signature">💬 "${escapeHtml(signature)}"</div>` : ''}
                <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center;border-top:1px solid rgba(255,255,255,0.05);padding-top:12px;">
                    <span style="font-size:0.6rem;color:rgba(255,255,255,0.2);">📡 Data from mahir-info-api.vercel.app</span>
                    <span style="font-size:0.6rem;color:rgba(255,255,255,0.1);">|</span>
                    <span style="font-size:0.6rem;color:rgba(255,215,0,0.3);">❤️ TORIKUL SYSTEM</span>
                </div>
            `;
        } catch (error) {
            content.innerHTML = `
                <div class="modal-error">
                    <i class="fas fa-exclamation-circle"></i>
                    <div>Failed to load profile</div>
                    <div style="font-size:0.7rem;color:rgba(255,255,255,0.3);margin-top:8px;">${escapeHtml(error.message)}</div>
                    <button onclick="openProfile('${uid}')" style="margin-top:15px;padding:8px 20px;background:linear-gradient(135deg,#ffd700,#ffaa00);border:none;border-radius:8px;color:#000;cursor:pointer;font-weight:600;">Retry</button>
                </div>
            `;
        }
    }

    function closeModal() {
        document.getElementById('profileModal').classList.remove('active');
    }
    document.getElementById('profileModal').addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
    });

    function searchTarget() {
        const uid = document.getElementById('searchInput').value.trim();
        if (!uid || !/^\\d+$/.test(uid)) {
            alert('Please enter a valid UID!');
            return;
        }
        fetch(`/api/targets?pass=HUNTERTORIKUL`)
            .then(r => r.json())
            .then(data => {
                const resultDiv = document.getElementById('searchResult');
                const contentDiv = document.getElementById('searchResultContent');
                if (data.success) {
                    const target = data.targets.find(t => t.uid === uid);
                    if (target) {
                        resultDiv.style.display = 'block';
                        contentDiv.innerHTML = `
                            <div class="result-item">
                                <div>
                                    <strong style="color:#ffd700;font-family:monospace;font-size:1.1rem;">🎯 ${target.uid}</strong>
                                    <button onclick="openProfile('${target.uid}')" style="margin-left:10px;padding:4px 12px;background:linear-gradient(135deg,#ffd700,#ffaa00);border:none;border-radius:6px;color:#000;cursor:pointer;font-size:0.7rem;font-weight:600;">📋 View Profile</button>
                                </div>
                                <div class="meta">
                                    <span class="added">👤 ${target.added_by || 'TORIKUL'}</span>
                                    <span class="reason-text">💬 ${target.reason || 'Manual Start'}</span>
                                    ${target.is_squad_leader ? '<span style="color:#ffd700;">👑 SQUAD LEADER</span>' : ''}
                                    ${target.original_target ? `<span>🎯 From: ${target.original_target}</span>` : ''}
                                    ${target.mode ? `<span>🎮 ${target.mode}</span>` : ''}
                                    <span style="background:rgba(255,215,0,0.15);padding:2px 8px;border-radius:6px;color:#ffd700;">${target.type}</span>
                                </div>
                            </div>
                        `;
                    } else {
                        resultDiv.style.display = 'block';
                        contentDiv.innerHTML = `<div style="color:#ff4444;padding:10px;">❌ Target ${uid} not found in active targets</div>`;
                    }
                }
            })
            .catch(() => alert('Error searching target!'));
    }

    function clearSearch() {
        document.getElementById('searchResult').style.display = 'none';
        document.getElementById('searchInput').value = '';
    }

    fetch('/api/targets?pass=HUNTERTORIKUL')
        .then(r => r.json())
        .then(data => {
            if (data.success) renderTargets(data.targets);
        })
        .catch(() => {});
</script>
</body>
</html>'''

# ==================== HTML_TEMPLATE - আপডেটেড ভার্সন (File Manager সহ) ====================
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 TORIKUL SYSTEM - SPAM CONTROL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #060417, #0e0b30, #130a24); min-height: 100vh; color: #fff; padding: 20px; }
        #matrix-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; opacity: 0.3; }
        .container { max-width: 1400px; margin: 0 auto; position: relative; z-index: 1; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 20px; flex-wrap: wrap; gap: 15px; }
        .logo { font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #ff007f, #7f00ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo i { -webkit-text-fill-color: initial; color: #ff007f; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: rgba(255,255,255,0.03); backdrop-filter: blur(15px); border-radius: 12px; padding: 15px; text-align: center; border: 1px solid rgba(255,255,255,0.06); transition: 0.3s; }
        .stat-card:hover { transform: translateY(-3px); border-color: rgba(255,0,127,0.2); }
        .stat-card i { font-size: 1.5rem; margin-bottom: 5px; color: #ff007f; }
        .stat-card h3 { font-size: 0.7rem; color: rgba(255,255,255,0.4); margin-bottom: 3px; text-transform: uppercase; letter-spacing: 1px; }
        .stat-card .value { font-size: 1.8rem; font-weight: 800; }
        .controls-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .control-card { background: rgba(255,255,255,0.02); backdrop-filter: blur(15px); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.06); }
        .control-card h3 { font-size: 0.95rem; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
        .control-card h3 i { color: #ff007f; }
        .input-group { display: flex; gap: 10px; flex-wrap: wrap; }
        .input-group input, .input-group select { flex: 1; padding: 10px 14px; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(0,0,0,0.4); color: #fff; font-size: 0.9rem; outline: none; transition: 0.3s; min-width: 120px; }
        .input-group input:focus, .input-group select:focus { border-color: #ff007f; box-shadow: 0 0 15px rgba(255,0,127,0.1); }
        .input-group select option { background: #1a1a2e; color: #fff; }
        .btn { padding: 10px 18px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: linear-gradient(135deg, #ff007f, #7f00ff); color: #fff; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(255,0,127,0.3); }
        .btn-danger { background: linear-gradient(135deg, #ff0844, #ffb199); color: #fff; }
        .btn-danger:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(255,8,68,0.3); }
        .btn-warning { background: linear-gradient(135deg, #ffaa00, #ff6600); color: #000; }
        .btn-warning:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(255,170,0,0.3); }
        .btn-outline { background: transparent; border: 1px solid rgba(255,255,255,0.15); color: #fff; }
        .btn-outline:hover { background: rgba(255,255,255,0.05); }
        .btn-sm { padding: 6px 12px; font-size: 0.75rem; }
        .btn-success { background: linear-gradient(135deg, #00b09b, #96c93d); color: #fff; }
        .btn-success:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,176,155,0.3); }
        .btn-refresh { background: linear-gradient(135deg, #00d4ff, #7f00ff); color: #fff; animation: glow 2s infinite; }
        .btn-refresh:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 5px 30px rgba(0,212,255,0.4); }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 20px rgba(0,212,255,0.2); } 50% { box-shadow: 0 0 40px rgba(0,212,255,0.4); } }
        .upload-area { border: 2px dashed rgba(255,255,255,0.08); border-radius: 8px; padding: 15px; text-align: center; cursor: pointer; transition: 0.3s; }
        .upload-area:hover { border-color: rgba(255,0,127,0.3); background: rgba(255,0,127,0.03); }
        .upload-area.dragover { border-color: #ff007f; background: rgba(255,0,127,0.05); }
        .upload-area i { font-size: 1.5rem; color: rgba(255,255,255,0.2); }
        .upload-area p { font-size: 0.8rem; color: rgba(255,255,255,0.3); }
        .active-list { max-height: 400px; overflow-y: auto; margin-top: 10px; }
        .active-item { background: rgba(30,30,40,0.6); padding: 12px 14px; margin: 5px 0; border-radius: 8px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-left: 3px solid #ff007f; gap: 8px; }
        .active-item .main-info { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; flex: 1; }
        .active-uid { font-family: monospace; font-weight: bold; color: #ff007f; font-size: 13px; }
        .active-status { font-size: 10px; padding: 2px 10px; border-radius: 10px; }
        .active-status.solo { background: rgba(0, 255, 204, 0.2); color: #00ffcc; }
        .active-status.insquad { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
        .active-status.ingame { background: rgba(255, 170, 0, 0.2); color: #ffaa00; }
        .active-status.in_room { background: rgba(255, 100, 0, 0.2); color: #ff6400; }
        .active-status.offline { background: rgba(255, 68, 68, 0.2); color: #ff4444; }
        .active-status.unknown { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.4); }
        .active-type { font-size: 10px; color: rgba(255,255,255,0.4); background: rgba(255,255,255,0.05); padding: 2px 10px; border-radius: 10px; }
        .active-time { font-size: 10px; color: rgba(255,255,255,0.3); }
        .active-meta { font-size: 9px; color: rgba(255,255,255,0.25); display: flex; flex-wrap: wrap; gap: 4px 12px; width: 100%; margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.03); }
        .active-meta .added-by { color: #ffd700; }
        .active-meta .reason { color: rgba(255,255,255,0.4); font-style: italic; }
        .active-meta .time-ago { color: rgba(255,255,255,0.2); }
        .stop-small { background: #eb3349; color: white; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 10px; font-weight: bold; transition: 0.2s; }
        .stop-small:hover { background: #c0392b; }
        .account-item { background: rgba(30,30,40,0.4); padding: 3px 10px; margin: 3px 4px; border-radius: 6px; font-family: monospace; font-size: 10px; color: #4facfe; display: inline-block; }
        .console-box { background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; height: 200px; padding: 12px; font-family: 'Courier New', monospace; font-size: 0.7rem; color: #00ffcc; overflow-y: auto; }
        .console-box .line { opacity: 0; animation: fadeLine 0.3s forwards; border-bottom: 1px solid rgba(255,255,255,0.03); padding: 2px 0; }
        @keyframes fadeLine { to { opacity: 1; } }
        .toast { position: fixed; bottom: 20px; right: 20px; background: rgba(0,0,0,0.9); padding: 12px 20px; border-radius: 8px; z-index: 999; color:#fff; display:flex; align-items:center; gap:8px; border:1px solid rgba(255,255,255,0.1); animation: slideIn 0.3s cubic-bezier(0.175,0.885,0.32,1.275); }
        .toast.success { border-color: #00b09b; }
        .toast.error { border-color: #ff0844; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        .status-dot.online { background: #00ffcc; animation: pulse 1s infinite; }
        .status-dot.offline { background: #ff4444; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        .feature-badge { display: inline-block; background: rgba(0, 212, 255, 0.1); color: #00d4ff; padding: 2px 10px; border-radius: 10px; font-size: 0.6rem; margin-left: 5px; }
        .footer { text-align: center; color: rgba(255,255,255,0.15); font-size: 0.7rem; margin-top: 25px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.03); }
        .console-success { color: #00ffcc; }
        .console-error { color: #ff3366; }
        .console-warning { color: #ffaa00; }
        .console-info { color: #4facfe; }
        .reset-info { font-size: 0.7rem; color: rgba(255,255,255,0.3); margin-top: 5px; }
        .refresh-status-text { font-size: 0.7rem; color: rgba(255,255,255,0.4); margin-top: 8px; padding: 8px 12px; background: rgba(0,0,0,0.3); border-radius: 6px; border-left: 3px solid #00d4ff; }
        .refresh-status-text .highlight { color: #00ffcc; }
        .refresh-status-text .error { color: #ff4444; }
        .squad-leader-item { background: rgba(255,215,0,0.05); border-left: 3px solid #ffd700; padding: 8px 12px; margin: 4px 0; border-radius: 6px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; font-size: 0.8rem; gap: 6px; }
        .squad-leader-item .uid { color: #ffd700; font-family: monospace; font-weight: bold; }
        .squad-leader-item .expired { color: #ff4444; }
        .squad-leader-item .active { color: #00ffcc; }

        .file-manager-btn { 
            background: linear-gradient(135deg, #ffd700, #ff8c00); 
            color: #000; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 10px; 
            font-size: 1rem; 
            font-weight: 700; 
            cursor: pointer; 
            transition: 0.3s; 
            display: inline-flex; 
            align-items: center; 
            gap: 10px;
            box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3);
        }
        .file-manager-btn:hover { 
            transform: translateY(-3px) scale(1.02); 
            box-shadow: 0 8px 40px rgba(255, 215, 0, 0.5);
        }
        .file-manager-btn i { font-size: 1.3rem; }

        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(10px); z-index: 1000; justify-content: center; align-items: center; padding: 20px; }
        .modal-overlay.active { display: flex; }
        .modal-box { background: rgba(20, 20, 50, 0.95); border: 1px solid rgba(255, 215, 0, 0.3); border-radius: 20px; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 30px; position: relative; box-shadow: 0 20px 80px rgba(0,0,0,0.9); animation: slideUp 0.3s ease; }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .modal-close { position: absolute; top: 15px; right: 20px; font-size: 2rem; color: rgba(255,255,255,0.4); cursor: pointer; transition: 0.3s; background: none; border: none; }
        .modal-close:hover { color: #ffd700; transform: rotate(90deg); }
        .modal-title { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg, #ffd700, #ff8c00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }
        .modal-title i { -webkit-text-fill-color: initial; color: #ffd700; }

        .file-grid-modal { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .file-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 18px; transition: 0.3s; }
        .file-card:hover { border-color: rgba(255,215,0,0.2); background: rgba(255,215,0,0.03); }
        .file-card .file-name { font-size: 1rem; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 8px; }
        .file-card .file-name i { color: #ffd700; }
        .file-card .file-info { font-size: 0.7rem; color: rgba(255,255,255,0.3); margin: 6px 0 12px 0; }
        .file-card .file-actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .file-card .file-actions .btn { flex: 1; min-width: 70px; justify-content: center; font-size: 0.75rem; padding: 8px 12px; }
        .file-card .file-actions .btn-edit { background: linear-gradient(135deg, #00d4ff, #0088ff); color: #fff; }
        .file-card .file-actions .btn-edit:hover { box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3); }
        .file-card .file-actions .btn-download { background: linear-gradient(135deg, #00b09b, #96c93d); color: #fff; }
        .file-card .file-actions .btn-download:hover { box-shadow: 0 4px 20px rgba(0, 176, 155, 0.3); }
        .file-card .file-actions .btn-upload { background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000; }
        .file-card .file-actions .btn-upload:hover { box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3); }
        .file-card .file-actions input[type="file"] { display: none; }

        .file-editor-area { margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px; }
        .file-editor-area textarea { width: 100%; height: 250px; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; color: #00ffcc; font-family: 'Courier New', monospace; font-size: 0.8rem; padding: 12px; outline: none; resize: vertical; }
        .file-editor-area textarea:focus { border-color: #ffd700; }
        .file-editor-area .editor-actions { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
        .file-editor-area .editor-actions .btn { flex: 0 0 auto; }

        .upload-area-modal { border: 2px dashed rgba(255,215,0,0.2); border-radius: 8px; padding: 20px; text-align: center; cursor: pointer; transition: 0.3s; margin-top: 10px; }
        .upload-area-modal:hover { border-color: rgba(255,215,0,0.4); background: rgba(255,215,0,0.03); }
        .upload-area-modal i { font-size: 2rem; color: rgba(255,215,0,0.3); }
        .upload-area-modal p { font-size: 0.8rem; color: rgba(255,255,255,0.3); margin-top: 5px; }

        @media (max-width: 768px) { 
            .controls-grid { grid-template-columns: 1fr; } 
            .input-group { flex-direction: column; } 
            .btn { width: 100%; justify-content: center; } 
            .header { flex-direction: column; text-align: center; } 
            .file-grid-modal { grid-template-columns: 1fr; } 
            .active-item .main-info { flex-direction: column; align-items: flex-start; } 
            .modal-box { padding: 20px; }
            .file-manager-btn { width: 100%; justify-content: center; }
        }
    </style>
</head>
<body>
    <canvas id="matrix-canvas"></canvas>
    <div class="container">
        <div class="header">
            <div>
                <div class="logo"><i class="fas fa-bolt"></i> TORIKUL SYSTEM</div>
                <div style="color: rgba(255,255,255,0.3); font-size:0.8rem;">
                    SPAM CONTROL ENGINE v3.3
                    <span class="feature-badge"><i class="fas fa-sync"></i> Auto Status Check (5s)</span>
                    <span class="feature-badge"><i class="fas fa-users"></i> Squad Auto-Join (2h)</span>
                    <span class="feature-badge"><i class="fas fa-layer-group"></i> GROUP ONLY</span>
                    <span class="feature-badge"><i class="fas fa-info-circle"></i> Added By & Reason</span>
                </div>
            </div>
            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <button class="file-manager-btn" onclick="openFileManager()">
                    <i class="fas fa-folder-open"></i> 📁 FILE MANAGER
                </button>
                <a href="/targets" class="btn btn-outline btn-sm"><i class="fas fa-crosshairs"></i> TARGETS</a>
                <span class="status-dot online" id="statusDot"></span>
                <span id="statusText" style="color:rgba(255,255,255,0.4);font-size:0.8rem;">Live</span>
                <a href="/logout" class="btn btn-outline btn-sm"><i class="fas fa-sign-out-alt"></i> LOGOUT</a>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card"><i class="fas fa-bullseye"></i><h3>ACTIVE TARGETS</h3><div class="value" id="activeCount">0</div></div>
            <div class="stat-card"><i class="fas fa-robot"></i><h3>BOT ACCOUNTS</h3><div class="value" id="botCount">0</div></div>
            <div class="stat-card"><i class="fas fa-users"></i><h3>SQUAD LEADERS</h3><div class="value" id="squadCount">0</div></div>
            <div class="stat-card"><i class="fas fa-file-alt"></i><h3>ACCOUNTS IN FILE</h3><div class="value" id="fileAccCount">0</div></div>
        </div>

        <div class="controls-grid">
            <div class="control-card">
                <h3><i class="fas fa-upload" style="color:#ff007f;"></i> UPLOAD ACCOUNTS</h3>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <div class="upload-area" id="accsUpload" style="flex:1; min-width:150px;">
                        <i class="fas fa-file-alt"></i>
                        <p>📁 accs.txt (ACCOUNTS)</p>
                        <input type="file" id="accsFileInput" accept=".txt" style="display:none;">
                        <div id="accsStatus" style="font-size:0.7rem;color:rgba(255,255,255,0.3);margin-top:4px;">No file</div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:6px; min-width:120px;">
                        <button class="btn btn-success btn-sm" onclick="resetAccounts()"><i class="fas fa-sync-alt"></i> RESET ACCOUNTS</button>
                        <div class="reset-info"><i class="fas fa-info-circle"></i> Manual reset only</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- SQUAD LEADER MANAGEMENT -->
        <div class="control-card" style="margin-bottom:20px; border: 1px solid rgba(255,215,0,0.15);">
            <h3><i class="fas fa-crown" style="color:#ffd700;"></i> SQUAD LEADER MANAGEMENT</h3>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
                <button class="btn btn-gold btn-sm" onclick="refreshSquadLeaders()"><i class="fas fa-sync-alt"></i> Refresh List</button>
                <button class="btn btn-danger btn-sm" onclick="cleanupExpiredSquadLeaders()"><i class="fas fa-trash"></i> Cleanup Expired (2h+)</button>
                <button class="btn btn-warning btn-sm" onclick="cleanupExpiredTargets()"><i class="fas fa-broom"></i> Cleanup Expired Targets</button>
            </div>
            <div id="squadLeaderList" class="squad-list">
                <div style="color:rgba(255,255,255,0.3); text-align:center; padding:15px;">Loading squad leaders...</div>
            </div>
            <div style="font-size:0.6rem; color:rgba(255,255,255,0.2); margin-top:5px;">
                <i class="fas fa-info-circle"></i> Squad leaders expire after 2 hours. Click cleanup to remove expired ones.
            </div>
        </div>

        <div class="controls-grid">
            <div class="control-card">
                <h3><i class="fas fa-fire" style="color:#ff007f;"></i> START SPAM</h3>
                <div style="font-size:0.7rem; color:rgba(255,255,255,0.4); margin-bottom:8px;">Group/Squad Spam + Badge Spam (All accounts are Group)</div>
                <div class="input-group" style="flex-direction:column; gap:8px;">
                    <input type="text" id="spamUid" placeholder="Target UID(s) (comma separated)" style="width:100%;">
                    <div style="display:flex; gap:8px; flex-wrap:wrap; width:100%;">
                        <input type="text" id="spamAddedBy" placeholder="Added By (e.g. TORIKUL)" style="flex:1; min-width:100px;" value="TORIKUL">
                        <input type="text" id="spamReason" placeholder="Reason (e.g. revenge)" style="flex:2; min-width:150px;" value="Manual Start">
                        <button class="btn btn-primary" onclick="startSpam()" style="flex:0 0 auto;"><i class="fas fa-play"></i> START</button>
                    </div>
                </div>
            </div>
            <div class="control-card">
                <h3><i class="fas fa-stop" style="color:#ff0844;"></i> STOP</h3>
                <div class="input-group">
                    <input type="text" id="stopUid" placeholder="Target UID to stop">
                    <button class="btn btn-danger" onclick="stopSingleSpam()"><i class="fas fa-power-off"></i> STOP</button>
                </div>
                <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
                    <button class="btn btn-warning" onclick="stopAllSpam()" style="flex:1;"><i class="fas fa-stop-circle"></i> STOP ALL</button>
                </div>
            </div>
        </div>

        <!-- STATUS REFRESH -->
        <div class="control-card" style="margin-bottom:20px; border: 1px solid rgba(0, 212, 255, 0.15);">
            <h3><i class="fas fa-sync-alt" style="color:#00d4ff;"></i> STATUS REFRESH</h3>
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                <button class="btn btn-refresh" onclick="refreshAllStatus()" style="flex:1; min-width:180px; padding:12px 20px; font-size:0.95rem;">
                    <i class="fas fa-sync-alt"></i> 🔄 REFRESH ALL TARGETS STATUS
                </button>
                <div style="display:flex; gap:6px; flex-wrap:wrap; flex:1;">
                    <input type="text" id="refreshSingleUid" placeholder="Single UID" style="padding:10px 14px; border:1px solid rgba(255,255,255,0.08); border-radius:8px; background:rgba(0,0,0,0.4); color:#fff; font-family:monospace; outline:none; min-width:120px; flex:1;">
                    <button class="btn btn-outline" onclick="refreshSingleTarget()" style="padding:10px 16px;">
                        <i class="fas fa-sync"></i> Refresh
                    </button>
                </div>
            </div>
            <div id="refreshStatus" class="refresh-status-text">
                <i class="fas fa-info-circle"></i> Click the button above to refresh status of all active targets
                <span style="float:right; font-size:0.6rem; color:rgba(255,255,255,0.2);">Last refresh: <span id="lastRefreshTime">Never</span></span>
            </div>
        </div>

        <div class="control-card" style="margin-bottom:20px;">
            <h3><i class="fas fa-list"></i> ACTIVE TARGETS <span style="font-size:0.6rem; color:rgba(255,255,255,0.3);">(Status auto-check every 5s)</span></h3>
            <div id="activeList" class="active-list">
                <div style="color:rgba(255,255,255,0.3); text-align:center; padding:15px;">No active targets</div>
            </div>
        </div>

        <div class="control-card" style="margin-bottom:20px;">
            <h3><i class="fas fa-terminal"></i> LIVE CONSOLE</h3>
            <div class="console-box" id="consoleBox">
                <div class="line"><span style="color:rgba(255,255,255,0.3);">[System]</span> <span class="console-success">TORIKUL SPAM ENGINE v3.3 Initialized</span></div>
                <div class="line"><span style="color:rgba(255,255,255,0.3);">[System]</span> <span class="console-info">GROUP ONLY - No Room Spam</span></div>
                <div class="line"><span style="color:rgba(255,255,255,0.3);">[System]</span> <span class="console-info">Added By & Reason tracking enabled</span></div>
                <div class="line"><span style="color:rgba(255,255,255,0.3);">[System]</span> <span class="console-info">Status check every 5 seconds</span></div>
                <div class="line"><span style="color:rgba(255,255,255,0.3);">[System]</span> <span class="console-info">Squad auto-join enabled (2 hours duration)</span></div>
            </div>
        </div>

        <div class="control-card">
            <h3><i class="fas fa-robot"></i> CONNECTED ACCOUNTS</h3>
            <div id="accountsContainer">
                <span style="color:rgba(255,255,255,0.3); font-size:0.8rem;">Loading...</span>
            </div>
        </div>

        <div class="footer">TORIKUL SYSTEM v3.3 | <i class="fas fa-code"></i> Engine by TORIKUL | GROUP ONLY | Added By & Reason Tracking | Status Check: 5s | Squad Auto-Join: 2hours</div>
    </div>

    <!-- ===== FILE MANAGER MODAL ===== -->
    <div class="modal-overlay" id="fileManagerModal">
        <div class="modal-box">
            <button class="modal-close" onclick="closeFileManager()">&times;</button>
            <div class="modal-title"><i class="fas fa-folder-open"></i> 📁 FILE MANAGER</div>
            <p style="color:rgba(255,255,255,0.3); margin-bottom:20px; font-size:0.9rem;">
                View, Edit, Download, and Upload all system files from one place.
            </p>

            <div class="file-grid-modal" id="fileGrid">
                <!-- Files will be dynamically loaded here -->
                <div style="text-align:center; padding:30px; color:rgba(255,255,255,0.3); width:100%;">
                    <i class="fas fa-spinner fa-spin" style="font-size:2rem;"></i><br>
                    Loading files...
                </div>
            </div>

            <!-- File Editor Area -->
            <div class="file-editor-area" id="fileEditorArea" style="display:none;">
                <h4 style="color:#ffd700; margin-bottom:8px;"><i class="fas fa-edit"></i> Edit File: <span id="editingFileName" style="color:#fff;"></span></h4>
                <textarea id="fileEditorContent"></textarea>
                <div class="editor-actions">
                    <button class="btn btn-success" onclick="saveFileEdit()"><i class="fas fa-save"></i> Save Changes</button>
                    <button class="btn btn-warning" onclick="cancelFileEdit()"><i class="fas fa-times"></i> Cancel</button>
                    <span id="editStatus" style="color:rgba(255,255,255,0.3); font-size:0.8rem; margin-left:10px;"></span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('matrix-canvas'); const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&'.split('');
        const fontSize = 12; const columns = canvas.width / fontSize; const drops = Array(Math.floor(columns)).fill(1);
        function drawMatrix() {
            ctx.fillStyle = 'rgba(5, 5, 10, 0.05)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#ff007f'; ctx.font = fontSize + 'px monospace';
            drops.forEach((y, i) => {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.globalAlpha = 0.3 + Math.random() * 0.3;
                ctx.fillText(text, i * fontSize, y * fontSize);
                ctx.globalAlpha = 1;
                if (y * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0; drops[i]++;
            });
        }
        setInterval(drawMatrix, 50);

        function showToast(msg, type='info') {
            const t = document.createElement('div');
            t.className = `toast ${type}`;
            const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
            t.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i> ${msg}`;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 4000);
        }

        // ===== FILE MANAGER =====
        const FILE_LIST = [
            { name: 'target.txt', icon: 'fa-crosshairs', desc: 'Target UIDs list' },
            { name: 'accs.txt', icon: 'fa-users', desc: 'Account credentials' },
            { name: 'master_acc.txt', icon: 'fa-key', desc: 'Master account ID/PW' },
            { name: 'squad_data.json', icon: 'fa-crown', desc: 'Squad leader data' }
        ];

        let currentEditingFile = null;

        function openFileManager() {
            document.getElementById('fileManagerModal').classList.add('active');
            renderFileList();
        }

        function closeFileManager() {
            document.getElementById('fileManagerModal').classList.remove('active');
            document.getElementById('fileEditorArea').style.display = 'none';
            currentEditingFile = null;
        }

        function renderFileList() {
            const grid = document.getElementById('fileGrid');
            grid.innerHTML = FILE_LIST.map(file => `
                <div class="file-card">
                    <div class="file-name"><i class="fas ${file.icon}"></i> ${file.name}</div>
                    <div class="file-info">${file.desc}</div>
                    <div class="file-actions">
                        <button class="btn btn-edit btn-sm" onclick="editFile('${file.name}')"><i class="fas fa-edit"></i> Edit</button>
                        <button class="btn btn-download btn-sm" onclick="downloadFile('${file.name}')"><i class="fas fa-download"></i> Download</button>
                        <button class="btn btn-upload btn-sm" onclick="document.getElementById('uploadInput_${file.name}').click()"><i class="fas fa-upload"></i> Upload</button>
                        <input type="file" id="uploadInput_${file.name}" accept=".txt,.json" style="display:none;" onchange="uploadFile('${file.name}', this)">
                    </div>
                </div>
            `).join('');
        }

        function downloadFile(filename) {
            const urls = {
                'target.txt': '/api/download/targets',
                'accs.txt': '/api/get/accs',
                'master_acc.txt': '/api/download/master?t=' + Date.now(),
                'squad_data.json': '/api/download/squad_data'
            };
            const url = urls[filename];
            if (url) {
                window.location.href = url;
                showToast(`Downloading ${filename}...`, 'info');
            } else {
                showToast('Download not available for this file', 'error');
            }
        }

        function uploadFile(filename, input) {
            const file = input.files[0];
            if (!file) return;

            const urls = {
                'target.txt': '/api/upload/targets',
                'accs.txt': '/api/upload/accs',
                'master_acc.txt': '/api/upload/master',
                'squad_data.json': '/api/upload/squad_data'
            };

            const url = urls[filename];
            if (!url) {
                showToast('Upload not available for this file', 'error');
                return;
            }

            const fd = new FormData();
            fd.append('file', file);
            showToast(`Uploading ${filename}...`, 'info');

            fetch(url, { method: 'POST', body: fd })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        showToast(`✅ ${d.message}`, 'success');
                        refreshStatus();
                        refreshSquadLeaders();
                        if (filename === 'master_acc.txt') {
                            setTimeout(() => location.reload(), 2000);
                        }
                    } else {
                        showToast(`❌ Upload failed: ${d.message}`, 'error');
                    }
                })
                .catch(() => showToast('Upload failed', 'error'));
            input.value = '';
        }

        function editFile(filename) {
            currentEditingFile = filename;
            const editorArea = document.getElementById('fileEditorArea');
            const fileNameSpan = document.getElementById('editingFileName');
            const contentArea = document.getElementById('fileEditorContent');
            const statusSpan = document.getElementById('editStatus');

            fileNameSpan.textContent = filename;
            editorArea.style.display = 'block';
            contentArea.value = 'Loading...';
            statusSpan.textContent = '';

            const downloadUrls = {
                'target.txt': '/api/download/targets',
                'accs.txt': '/api/get/accs',
                'master_acc.txt': '/api/download/master',
                'squad_data.json': '/api/download/squad_data'
            };

            const url = downloadUrls[filename];
            if (!url) {
                contentArea.value = 'Error: Cannot load this file for editing';
                return;
            }

            fetch(url)
                .then(r => {
                    if (!r.ok) throw new Error('Failed to load file');
                    return r.text();
                })
                .then(text => {
                    contentArea.value = text;
                    statusSpan.textContent = '✅ Loaded successfully';
                    statusSpan.style.color = '#00ffcc';
                })
                .catch(err => {
                    contentArea.value = `Error loading file: ${err.message}`;
                    statusSpan.textContent = '❌ Failed to load';
                    statusSpan.style.color = '#ff4444';
                });
        }

        function saveFileEdit() {
            const filename = currentEditingFile;
            const content = document.getElementById('fileEditorContent').value;
            const statusSpan = document.getElementById('editStatus');

            if (!filename) {
                showToast('No file is being edited', 'error');
                return;
            }

            const blob = new Blob([content], { type: 'text/plain' });
            const file = new File([blob], filename);

            const urls = {
                'target.txt': '/api/upload/targets',
                'accs.txt': '/api/upload/accs',
                'master_acc.txt': '/api/upload/master',
                'squad_data.json': '/api/upload/squad_data'
            };

            const url = urls[filename];
            if (!url) {
                showToast('Save not available for this file', 'error');
                return;
            }

            const fd = new FormData();
            fd.append('file', file);
            statusSpan.textContent = '⏳ Saving...';
            statusSpan.style.color = '#ffaa00';

            fetch(url, { method: 'POST', body: fd })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        statusSpan.textContent = '✅ Saved successfully!';
                        statusSpan.style.color = '#00ffcc';
                        showToast(`✅ ${d.message}`, 'success');
                        refreshStatus();
                        refreshSquadLeaders();
                        if (filename === 'master_acc.txt') {
                            setTimeout(() => location.reload(), 2000);
                        }
                    } else {
                        statusSpan.textContent = `❌ Save failed: ${d.message}`;
                        statusSpan.style.color = '#ff4444';
                        showToast(`❌ Save failed: ${d.message}`, 'error');
                    }
                })
                .catch(err => {
                    statusSpan.textContent = `❌ Error: ${err.message}`;
                    statusSpan.style.color = '#ff4444';
                    showToast('Save failed', 'error');
                });
        }

        function cancelFileEdit() {
            document.getElementById('fileEditorArea').style.display = 'none';
            currentEditingFile = null;
            document.getElementById('editStatus').textContent = '';
        }

        document.getElementById('fileManagerModal').addEventListener('click', function(e) {
            if (e.target === this) closeFileManager();
        });

        // ===== REFRESH FUNCTIONS =====
        function refreshAllStatus() {
            const statusDiv = document.getElementById('refreshStatus');
            const btn = document.querySelector('.btn-refresh');
            const lastRefreshSpan = document.getElementById('lastRefreshTime');
            
            statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin" style="color:#00d4ff;"></i> 🔄 Refreshing all targets status...';
            statusDiv.style.color = '#00ffcc';
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
            
            fetch('/api/refresh-all-status', { method: 'GET' })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(d => {
                if (d.success) {
                    const now = new Date();
                    const timeStr = now.toLocaleTimeString();
                    if (lastRefreshSpan) lastRefreshSpan.textContent = timeStr;
                    
                    statusDiv.innerHTML = `<i class="fas fa-check-circle" style="color:#00ffcc;"></i> ✅ ${d.message} (${d.refreshed} targets) 
                        <span style="float:right; font-size:0.6rem; color:rgba(255,255,255,0.2);">Updated: ${timeStr}</span>`;
                    statusDiv.style.color = '#00ffcc';
                    showToast(`✅ ${d.message}`, 'success');
                    refreshStatus();
                    
                    const consoleBox = document.getElementById('consoleBox');
                    const line = document.createElement('div');
                    line.className = 'line';
                    line.innerHTML = `<span style="color:rgba(255,255,255,0.3);">[Refresh]</span> <span class="console-success">✅ Refreshed ${d.refreshed} targets</span>`;
                    consoleBox.appendChild(line);
                    consoleBox.scrollTop = consoleBox.scrollHeight;
                } else {
                    statusDiv.innerHTML = `<i class="fas fa-exclamation-circle" style="color:#ff4444;"></i> ❌ ${d.message}`;
                    statusDiv.style.color = '#ff4444';
                    showToast(`❌ ${d.message}`, 'error');
                }
            })
            .catch((err) => {
                statusDiv.innerHTML = `<i class="fas fa-exclamation-circle" style="color:#ff4444;"></i> ❌ Refresh failed: ${err.message}`;
                statusDiv.style.color = '#ff4444';
                showToast('❌ Refresh failed', 'error');
            })
            .finally(() => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-sync-alt"></i> 🔄 REFRESH ALL TARGETS STATUS';
            });
        }

        function refreshSingleTarget() {
            const uid = document.getElementById('refreshSingleUid').value.trim();
            if (!uid) { showToast('Enter a valid UID!', 'error'); return; }
            if (!/^\\d+$/.test(uid)) { showToast('Invalid UID format!', 'error'); return; }
            
            const statusDiv = document.getElementById('refreshStatus');
            const lastRefreshSpan = document.getElementById('lastRefreshTime');
            
            statusDiv.innerHTML = `<i class="fas fa-spinner fa-spin" style="color:#00d4ff;"></i> 🔄 Refreshing target ${uid}...`;
            statusDiv.style.color = '#00ffcc';
            
            fetch(`/api/refresh-target-status/${uid}`, { method: 'GET' })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(d => {
                if (d.success) {
                    const now = new Date();
                    const timeStr = now.toLocaleTimeString();
                    if (lastRefreshSpan) lastRefreshSpan.textContent = timeStr;
                    
                    statusDiv.innerHTML = `<i class="fas fa-check-circle" style="color:#00ffcc;"></i> ✅ ${d.message} - Status: <span class="highlight">${d.details.status}</span>
                        <span style="float:right; font-size:0.6rem; color:rgba(255,255,255,0.2);">Updated: ${timeStr}</span>`;
                    statusDiv.style.color = '#00ffcc';
                    showToast(`✅ ${d.message}`, 'success');
                    refreshStatus();
                    document.getElementById('refreshSingleUid').value = '';
                    
                    const consoleBox = document.getElementById('consoleBox');
                    const line = document.createElement('div');
                    line.className = 'line';
                    line.innerHTML = `<span style="color:rgba(255,255,255,0.3);">[Refresh]</span> <span class="console-success">✅ ${uid} → ${d.details.status}</span>`;
                    consoleBox.appendChild(line);
                    consoleBox.scrollTop = consoleBox.scrollHeight;
                } else {
                    statusDiv.innerHTML = `<i class="fas fa-exclamation-circle" style="color:#ff4444;"></i> ❌ ${d.message}`;
                    statusDiv.style.color = '#ff4444';
                    showToast(`❌ ${d.message}`, 'error');
                }
            })
            .catch((err) => {
                statusDiv.innerHTML = `<i class="fas fa-exclamation-circle" style="color:#ff4444;"></i> ❌ Refresh failed: ${err.message}`;
                statusDiv.style.color = '#ff4444';
                showToast('❌ Refresh failed', 'error');
            });
        }

        // ===== SQUAD LEADER FUNCTIONS =====
        function refreshSquadLeaders() {
            const list = document.getElementById('squadLeaderList');
            list.innerHTML = '<div style="color:rgba(255,255,255,0.3); text-align:center; padding:15px;">Loading...</div>';
            
            fetch('/api/squad-leaders')
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        if (d.leaders && d.leaders.length > 0) {
                            list.innerHTML = d.leaders.map(l => `
                                <div class="squad-leader-item">
                                    <div>
                                        <span class="uid">👑 ${l.uid}</span>
                                        ${l.is_expired ? '<span class="expired">⏰ EXPIRED</span>' : `<span class="active">⏱ ${l.remaining_minutes}m remaining</span>`}
                                        <span style="font-size:0.6rem; color:rgba(255,255,255,0.3);">(Started: ${l.elapsed_minutes}m ago)</span>
                                    </div>
                                    <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
                                        ${l.original_target ? `<span style="font-size:0.6rem; color:rgba(255,255,255,0.3);">🎯 From: ${l.original_target}</span>` : ''}
                                        <span style="font-size:0.6rem; color:${l.is_online ? '#00ffcc' : '#ff4444'};">
                                            ${l.is_online ? '🟢 Online' : '⚪ Offline'}
                                        </span>
                                        ${!l.is_expired ? `<button class="btn btn-danger btn-sm" onclick="removeSquadLeader('${l.uid}')" style="padding:2px 8px; font-size:0.6rem;">✕</button>` : ''}
                                    </div>
                                </div>
                            `).join('');
                        } else {
                            list.innerHTML = '<div style="color:rgba(255,255,255,0.3); text-align:center; padding:15px;">No squad leaders found</div>';
                        }
                    } else {
                        list.innerHTML = `<div style="color:#ff4444; text-align:center; padding:15px;">❌ ${d.message}</div>`;
                    }
                })
                .catch(() => {
                    list.innerHTML = '<div style="color:#ff4444; text-align:center; padding:15px;">❌ Failed to load squad leaders</div>';
                });
        }

        function cleanupExpiredSquadLeaders() {
            if (!confirm('⚠️ Remove all expired squad leaders (>2 hours)?')) return;
            showToast('Cleaning up expired squad leaders...', 'info');
            
            fetch('/api/squad-leaders/cleanup', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        showToast(`✅ ${d.message}`, 'success');
                        refreshSquadLeaders();
                        refreshStatus();
                    } else {
                        showToast(`❌ ${d.message}`, 'error');
                    }
                })
                .catch(() => showToast('❌ Cleanup failed', 'error'));
        }

        function cleanupExpiredTargets() {
            if (!confirm('⚠️ Clean up expired targets from active list?')) return;
            showToast('Cleaning up expired targets...', 'info');
            
            fetch('/api/cleanup/expired-targets', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        showToast(`✅ ${d.message}`, 'success');
                        refreshStatus();
                    } else {
                        showToast(`❌ ${d.message}`, 'error');
                    }
                })
                .catch(() => showToast('❌ Cleanup failed', 'error'));
        }

        function removeSquadLeader(uid) {
            if (!confirm(`⚠️ Remove squad leader ${uid} from squad_data.json?`)) return;
            
            fetch(`/api/squad-leaders/remove/${uid}`, { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        showToast(`✅ ${d.message}`, 'success');
                        refreshSquadLeaders();
                        refreshStatus();
                    } else {
                        showToast(`❌ ${d.message}`, 'error');
                    }
                })
                .catch(() => showToast('❌ Failed to remove', 'error'));
        }

        function resetAccounts() {
            if (!confirm('⚠️ Reset all accounts? This will disconnect and reconnect all bots.')) return;
            showToast('Resetting accounts...', 'info');
            fetch('/api/reset-accounts', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        showToast(d.message, 'success');
                        refreshStatus();
                    } else {
                        showToast(d.message || 'Reset failed', 'error');
                    }
                })
                .catch(() => showToast('Error resetting accounts', 'error'));
        }

        function getAccountCount() {
            fetch('/api/accounts/count')
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        document.getElementById('fileAccCount').textContent = d.total;
                    }
                })
                .catch(() => {});
        }

        function uploadFileOld(file) {
            const fd = new FormData(); fd.append('file', file);
            fetch('/api/upload/accs', { method: 'POST', body: fd })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        document.getElementById('accsStatus').innerHTML = `✅ ${d.total} accounts`;
                        showToast(d.message, 'success');
                        refreshStatus();
                        getAccountCount();
                    } else showToast(d.message, 'error');
                }).catch(() => showToast('Upload failed', 'error'));
        }

        document.getElementById('accsUpload').addEventListener('click', () => document.getElementById('accsFileInput').click());
        document.getElementById('accsFileInput').addEventListener('change', function(e) { if (this.files.length) uploadFileOld(this.files[0]); });

        const uploadEl = document.getElementById('accsUpload');
        uploadEl.addEventListener('dragover', e => { e.preventDefault(); uploadEl.classList.add('dragover'); });
        uploadEl.addEventListener('dragleave', () => uploadEl.classList.remove('dragover'));
        uploadEl.addEventListener('drop', e => { e.preventDefault(); uploadEl.classList.remove('dragover'); const files = e.dataTransfer.files; if (files.length) uploadFileOld(files[0]); });

        function startSpam() {
            const uid = document.getElementById('spamUid').value.trim();
            const addedBy = document.getElementById('spamAddedBy').value.trim() || 'TORIKUL';
            const reason = document.getElementById('spamReason').value.trim() || 'Manual Start';
            
            if (!uid) { showToast('Enter target UID(s)!', 'error'); return; }
            const uids = uid.split(',').map(u => u.trim()).filter(u => /^\\d+$/.test(u));
            if (!uids.length) { showToast('Invalid UID(s)!', 'error'); return; }
            
            fetch('/api/spam/start', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ uid: uid, added_by: addedBy, reason: reason }) 
            })
            .then(r => r.json())
            .then(d => { 
                if (d.success) { 
                    showToast(`Started spam on ${uids.length} target(s) by ${addedBy}`, 'success'); 
                    refreshStatus(); 
                    document.getElementById('spamUid').value = '';
                } else showToast(d.message || 'Failed', 'error'); 
            })
            .catch(() => showToast('Error', 'error'));
        }

        function stopSingleSpam() {
            const uid = document.getElementById('stopUid').value.trim();
            if (!uid) { showToast('Enter target UID!', 'error'); return; }
            if (!/^\\d+$/.test(uid)) { showToast('Invalid UID!', 'error'); return; }
            fetch(`/api/stop/${uid}`)
                .then(r => r.json())
                .then(d => { if (d.success) { showToast(d.message, 'success'); document.getElementById('stopUid').value = ''; refreshStatus(); } else showToast(d.message, 'error'); })
                .catch(() => showToast('Error', 'error'));
        }

        function stopAllSpam() { if (!confirm('⚠️ Stop all spam?')) return; fetch('/api/stop-all').then(r => r.json()).then(d => { if (d.success) { showToast(d.message, 'success'); refreshStatus(); } }).catch(() => showToast('Error', 'error')); }

        function quickStop(uid) { document.getElementById('stopUid').value = uid; stopSingleSpam(); }

        function getStatusLabel(status) {
            const labels = { 'SOLO': '🟢 Solo', 'INSQUAD': '🔵 In Squad', 'INGAME': '🟡 In Game', 'IN_ROOM': '🟠 In Room', 'OFFLINE': '⚪ Offline', 'SOCIAL_ISLAND': '🟣 Social Island', 'MATCHMAKING': '🟣 Matchmaking', 'UNKNOWN': '⚪ Unknown' };
            return labels[status] || '⚪ Unknown';
        }
        function getStatusClass(status) { const map = { 'SOLO': 'solo', 'INSQUAD': 'insquad', 'INGAME': 'ingame', 'IN_ROOM': 'in_room', 'OFFLINE': 'offline' }; return map[status] || 'unknown'; }

        function refreshStatus() {
            fetch('/api/status?pass=TORIKULJOD')
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        const s = d.data;
                        document.getElementById('activeCount').textContent = s.active_count || 0;
                        document.getElementById('botCount').textContent = s.accounts_count || 0;
                        const squadCount = s.active_targets ? s.active_targets.filter(t => t.is_squad_leader).length : 0;
                        document.getElementById('squadCount').textContent = squadCount;
                        
                        const list = document.getElementById('activeList');
                        if (s.active_targets && s.active_targets.length > 0) {
                            list.innerHTML = s.active_targets.map(t => `
                                <div class="active-item">
                                    <div class="main-info">
                                        <span class="active-uid">🎯 ${t.uid}</span>
                                        <span class="active-status ${getStatusClass(t.status)}">${t.status_display || getStatusLabel(t.status)}</span>
                                        ${t.is_squad_leader ? `<span style="font-size:10px;color:#ffd700;">👑 SQUAD LEADER</span>` : ''}
                                        ${t.squad_leader ? `<span style="font-size:10px;color:#ff007f;">👥 L:${t.squad_leader}</span>` : ''}
                                        <span class="active-type">${t.type}</span>
                                        <span class="active-time">${t.elapsed_minutes}m</span>
                                    </div>
                                    <button class="stop-small" onclick="quickStop('${t.uid}')">STOP</button>
                                    <div class="active-meta">
                                        <span class="added-by">👤 ${t.added_by || 'TORIKUL'}</span>
                                        <span class="reason">💬 ${t.reason || 'Manual Start'}</span>
                                        ${t.added_time ? `<span class="time-ago">🕐 ${new Date(t.added_time).toLocaleTimeString()}</span>` : ''}
                                    </div>
                                </div>
                            `).join('');
                        } else {
                            list.innerHTML = '<div style="color:rgba(255,255,255,0.3); text-align:center; padding:15px;">No active targets</div>';
                        }
                    }
                }).catch(() => {});
            fetch('/api/accounts?pass=TORIKULJOD')
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        const c = document.getElementById('accountsContainer');
                        if (d.accounts && d.accounts.length > 0) { c.innerHTML = d.accounts.map(a => `<span class="account-item">${a}</span>`).join(''); }
                        else { c.innerHTML = '<span style="color:rgba(255,255,255,0.3);">No accounts connected</span>'; }
                    }
                }).catch(() => {});
            getAccountCount();
        }

        setInterval(refreshStatus, 5000);
        refreshStatus();
        refreshSquadLeaders();
        
        document.getElementById('spamUid').addEventListener('keypress', e => { if (e.key === 'Enter') startSpam(); });
        document.getElementById('stopUid').addEventListener('keypress', e => { if (e.key === 'Enter') stopSingleSpam(); });
        document.getElementById('refreshSingleUid').addEventListener('keypress', e => {
            if (e.key === 'Enter') { e.preventDefault(); refreshSingleTarget(); }
        });
    </script>
</body>
</html>'''

# ==================== MAIN ====================
def main():
    print(f"""
    {C}{BOLD}
    ╔══════════════════════════════════════════════════════════════════════╗
    ║              🎯 TORIKUL SPAM SYSTEM v3.3 🎯                           ║
    ║                                                                      ║
    ║     📁 accs.txt → Group/Squad Spam + Badge Spam (All Group)         ║
    ║                                                                      ║
    ║     ✅ Group/Squad Spam + Badge Spam (All accounts are Group)        ║
    ║     ✅ Auto Status Check: Every 3 seconds                           ║
    ║     ✅ Squad Auto-Join: 2 hours                                  ║
    ║     ✅ File Manager: Download/Upload/Edit targets.txt, accs.txt,     ║
    ║        master_acc.txt & squad_data.json                             ║
    ║     ✅ Squad Leader Management: View & Cleanup expired               ║
    ║     ✅ Target Viewer: /targets (Pass: HUNTERTORIKUL)                  ║
    ║                                                                      ║
    ║     🌐 Web Panel: http://127.0.0.1:8080                             ║
    ║     🔑 Admin Pass: TORIKULJOD                                         ║
    ║     🎯 Target Pass: HUNTERTORIKUL                                     ║
    ║     👑 Developer: TORIKUL                                             ║
    ╚══════════════════════════════════════════════════════════════════════╝
    {RS}
    """)

    # Start status checker thread
    status_thread = Thread(target=status_checker_thread, daemon=True)
    status_thread.start()
    print(f"{G}✅ Status checker thread started (every {STATUS_CHECK_INTERVAL}s){RS}")

    # ২. প্রথমবার একাউন্ট রান করা
    Thread(target=run_accounts, daemon=True).start()

    # ৩. কিছুক্ষণ অপেক্ষা করে বাকি টার্গেটগুলো লোড করা
    time.sleep(1)
    clean_and_load_squad_targets()
    load_saved_targets()

    port = int(os.environ.get("PORT", 8080))
    # ৪. ফ্লাস্ক অ্যাপ রান করা
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        os.system("pip install aiohttp")

    try:
        from protobuf_decoder.protobuf_decoder import Parser
    except ImportError:
        os.system("pip install protobuf-decoder")

    main()