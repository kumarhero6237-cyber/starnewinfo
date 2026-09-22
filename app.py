# INFO API SRC BYY
# POWERED BY : @STAR_GMR
# CHANNEL : @STAR_METHODE
import asyncio
import time
import httpx
import json
import os
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from cachetools import TTLCache
from typing import Tuple
from proto import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
from google.protobuf import json_format, message
from google.protobuf.message import Message
from Crypto.Cipher import AES
import base64

# ---------- Config ----------

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB55"
USERAGENT = "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)"
SUPPORTED_REGIONS = ["IND"]
ACCOUNT_GENERATOR_URL = os.environ.get("ACCOUNT_GENERATOR_URL", "/api/generate-ind")
ACCOUNT_GENERATOR_KEY = os.environ.get("ACCOUNT_GENERATOR_KEY", "CHANGE-ME-GENERATOR-KEY")
GUEST_FILE = os.environ.get("GUEST_FILE", "guests.json")
GENERATOR_TIMEOUT = float(os.environ.get("GENERATOR_TIMEOUT", "30"))
APP_DEBUG_VERSION = "IND-GUEST-RECOVERY-DEBUG-2026-09-22-v2"

# ---------- App Setup ----------

app = Flask(__name__)
CORS(app)
cache = TTLCache(maxsize=100, ttl=300)
cached_tokens = defaultdict(dict)
uid_region_cache = {}

# ---------- Single active IND guest ----------
GUEST_CREDENTIALS = {"IND": []}
guest_refresh_lock = __import__("threading").Lock()

# ----------- Helper Functions ------------

def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    aes = AES.new(key, AES.MODE_CBC, iv)
    return aes.encrypt(pad(plaintext))

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    instance = message_type()
    instance.ParseFromString(encoded_data)
    return instance

async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

def find_protobuf_start(data: bytes) -> int:
    """
    LoginRes protobuf hamesha field markers ke saath start hota hai.
    Yeh function response me se woh index dhoondhta hai jahan se valid
    protobuf start hota hai (junk bytes skip karne ke liye).
    """
    # Method 1: "IND" pattern (region field: \x12\x03IND) ke saath
    idx = data.find(b'\x12\x03IND')
    if idx != -1:
        for i in range(idx - 1, max(idx - 20, -1), -1):
            if data[i] == 0x08:
                return i

    # Method 2: JWT token marker (B\xe7\x05eyJ) ke saath
    jwt_marker = data.find(b'B\xe7\x05eyJ')
    if jwt_marker != -1:
        for i in range(jwt_marker - 1, max(jwt_marker - 200, -1), -1):
            if data[i] == 0x08:
                return i

    # Method 3: Fallback — pehla \x08 dhoondo
    return data.find(b'\x08')

# ---------- Load Guest Credentials (at module import) ----------

def load_guests_from_file():
    global GUEST_CREDENTIALS
    try:
        with open(GUEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ind = data.get("IND", []) if isinstance(data, dict) else data
        if isinstance(ind, str):
            ind = [ind]
        GUEST_CREDENTIALS = {"IND": [ind[0]] if ind else []}
        print(f"✅ Active IND guest loaded: {len(GUEST_CREDENTIALS['IND'])}")
    except Exception as e:
        print(f"❌ Could not load {GUEST_FILE}: {e}")
        GUEST_CREDENTIALS = {"IND": []}

load_guests_from_file()

def get_account_credentials(region: str) -> str:
    if region.upper() != "IND":
        raise ValueError("Only IND region is supported")
    guests = GUEST_CREDENTIALS.get("IND", [])
    if not guests:
        raise ValueError("No active IND guest credential")
    return guests[0]

def write_active_guest(credential: str):
    if not credential.startswith("uid=") or "&password=" not in credential:
        raise ValueError("Invalid generated credential")
    tmp = GUEST_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"IND": [credential]}, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, GUEST_FILE)
    GUEST_CREDENTIALS["IND"] = [credential]
    cached_tokens.clear()
    uid_region_cache.clear()
    cache.clear()

def resolve_generator_url() -> str:
    url = ACCOUNT_GENERATOR_URL.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return request.host_url.rstrip("/") + url
    raise ValueError("ACCOUNT_GENERATOR_URL must be an absolute URL or start with '/'")


async def generate_replacement_guest():
    generator_url = resolve_generator_url()
    print(f"🔄 [GENERATOR] URL={generator_url}")
    print(f"🔄 [GENERATOR] Host={request.host} | ACCOUNT_GENERATOR_URL={ACCOUNT_GENERATOR_URL}")
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(GENERATOR_TIMEOUT),
            follow_redirects=True
        ) as client:
            r = await client.post(
                generator_url,
                headers={
                    "X-Generator-Key": ACCOUNT_GENERATOR_KEY,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={"region": "IND", "count": 1}
            )
    except Exception as e:
        print(f"❌ Generator connection failed: {type(e).__name__}: {e}")
        raise ValueError(f"Generator connection failed: {type(e).__name__}")

    print(f"🔄 [GENERATOR] HTTP {r.status_code} | content_type={r.headers.get('content-type', '')} | body={r.text[:1000]!r}")
    if r.status_code not in (200, 201):
        print(f"❌ [GENERATOR] HTTP {r.status_code}: {r.text[:1000]}")
        raise ValueError(f"Generator HTTP {r.status_code}: {r.text[:300]}")

    try:
        data = r.json()
    except Exception as e:
        print(f"❌ Generator returned non-JSON response: {r.text[:500]}")
        raise ValueError("Generator returned invalid JSON") from e

    if not data.get("ok"):
        print(f"❌ Generator returned failure: {data.get('error', 'unknown')}")
        raise ValueError(data.get("error", "Generator failed"))

    uid = str(data.get("uid", "")).strip()
    password = str(data.get("password", "")).strip()
    if not uid or not password:
        raise ValueError("Generator returned incomplete credentials")

    credential = f"uid={uid}&password={password}"
    write_active_guest(credential)
    print(f"♻️ Active IND guest replaced: {uid}")
    return credential

async def ensure_working_guest():
    current = get_account_credentials("IND")
    if await create_jwt("IND", account=current, credential_index=0):
        return True
    print("⚠️ Active guest failed; requesting exactly one replacement...")
    with guest_refresh_lock:
        latest = get_account_credentials("IND") if GUEST_CREDENTIALS.get("IND") else None
        if latest != current and latest:
            if await create_jwt("IND", account=latest, credential_index=0):
                return True
        await generate_replacement_guest()
    return await create_jwt("IND", account=get_account_credentials("IND"), credential_index=0)

# -------------- Token Generation (async) --------------

async def get_access_token(account: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data=payload, headers=headers)
        data = resp.json()
        return data.get("access_token", "0"), data.get("open_id", "0")


async def create_jwt(region: str, account: str = None, credential_index: int = None):
    """Generate JWT; optionally force a specific guest credential."""
    try:
        guest_list = GUEST_CREDENTIALS.get(region.upper(), [])
        if account is None:
            if credential_index is not None:
                if credential_index < 0 or credential_index >= len(guest_list):
                    raise ValueError(f"Invalid credential index {credential_index} for {region}")
                account = guest_list[credential_index]
            else:
                account = get_account_credentials(region)
    except ValueError as e:
        print(f"❌ {e}")
        return False

    try:
        token_val, open_id = await get_access_token(account)
        if token_val == "0" or open_id == "0":
            print(f"❌ INVALID GUEST CREDS [{region}] guest_idx={credential_index}")
            return False

        body = json.dumps({"open_id": open_id, "open_id_type": "4", "login_token": token_val, "orign_platform_type": "4"})
        proto_bytes = await json_to_proto(body, FreeFire_pb2.LoginReq())
        payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, proto_bytes)
        url = "https://loginbp.ppmainecoonghj.com/MajorLogin"
        headers = {
            'User-Agent': USERAGENT, 'Accept': "*/*", 'Accept-Encoding': "deflate, gzip",
            'X-Ga-Sv': "1789534056", 'Authorization': "Bearer", 'X-Ga': "v1 1",
            'Releaseversion': RELEASEVERSION, 'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.12f1", 'PlAy_VeR': "1.132.1", 'Ob_VeR': RELEASEVERSION
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, data=payload, headers=headers)
        print(f"=== [{region}] HTTP {resp.status_code} | guest_idx={credential_index} | Content-Length: {len(resp.content)} ===")
        start_idx = find_protobuf_start(resp.content)
        if start_idx == -1:
            print(f"❌ [{region}] guest_idx={credential_index} protobuf start not found")
            return False
        try:
            msg = json.loads(json_format.MessageToJson(decode_protobuf(resp.content[start_idx:], FreeFire_pb2.LoginRes)))
        except Exception as parse_err:
            print(f"❌ [{region}] guest_idx={credential_index} PROTO FAIL: {parse_err}")
            return False
        token_str = msg.get("token", "")
        if not token_str:
            print(f"❌ [{region}] guest_idx={credential_index} empty token")
            return False
        cached_tokens[region] = {
            'token': f"Bearer {token_str}", 'region': msg.get('lockRegion', region) or region,
            'server_url': msg.get('serverUrl', '0'), 'expires_at': time.time() + 25200,
            'credential_index': credential_index
        }
        print(f"✅ TOKEN OK [{region}] guest_idx={credential_index} | lock={msg.get('lockRegion','')}")
        return True
    except Exception as e:
        print(f"❌ TOKEN GENERATION FAILED [{region}] guest_idx={credential_index}: {type(e).__name__}: {e}")
        return False


# -------------- Token Info (Lazy Generation) --------------

async def get_token_info(region: str) -> Tuple[str, str, str]:
    info = cached_tokens.get(region)

    if info and time.time() < info['expires_at']:
        return info['token'], info['region'], info['server_url']

    print(f"⏳ Generating token for {region} on demand...")
    await create_jwt(region)
    info = cached_tokens.get(region)
    if not info:
        raise ValueError(f"Failed to generate token for region {region}")
    return info['token'], info['region'], info['server_url']

# -------------- Account Information --------------

async def GetAccountInformation(uid, unk, region, endpoint, credential_index=None):
    """Fetch player information; credential_index forces a specific guest."""
    if credential_index is None:
        manage_rotation(region)
    payload = await json_to_proto(json.dumps({'a': uid, 'b': unk}), main_pb2.GetPlayerPersonalShow())
    data_enc = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, payload)
    if credential_index is not None:
        guest_list = GUEST_CREDENTIALS.get(region.upper(), [])
        if credential_index < 0 or credential_index >= len(guest_list):
            raise ValueError(f"Guest credential index {credential_index} unavailable for {region}")
        if not await create_jwt(region, account=guest_list[credential_index], credential_index=credential_index):
            raise ValueError(f"Guest credential #{credential_index + 1} failed for {region}")
        info = cached_tokens.get(region)
        token, server = info['token'], info['server_url']
    else:
        token, lock, server = await get_token_info(region)
    if not server or server == '0':
        raise ValueError(f"No valid server URL from guest credential for {region}")
    headers = {
        'User-Agent': USERAGENT, 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream", 'Expect': "100-continue", 'Authorization': token,
        'X-Unity-Version': "2018.4.12f1", 'X-GA': "v1 1", 'ReleaseVersion': RELEASEVERSION
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(server + endpoint, data=data_enc, headers=headers)
    if resp.status_code != 200 or not resp.content:
        raise ValueError(f"Player request failed: HTTP {resp.status_code}")
    try:
        return json.loads(json_format.MessageToJson(decode_protobuf(resp.content, AccountPersonalShow_pb2.AccountPersonalShowInfo)))
    except Exception as e:
        raise ValueError(f"Invalid player response from guest credential: {e}")


# -------------- Cache Decorator --------------

def cached_endpoint(ttl=300):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            key = (request.path, tuple(request.args.items()))
            if key in cache:
                return cache[key]
            res = fn(*a, **k)
            cache[key] = res
            return res
        return wrapper
    return decorator

# -------------- Routes Endpoints --------------

@app.route('/uc-info')
@cached_endpoint()
def get_account_info():
    if request.args.get('key', '') != 'RAM-SAGAR':
        return jsonify({"error": "Invalid or missing API key"}), 401
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "Please provide UID"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        try:
            loop.run_until_complete(ensure_working_guest())
        except Exception as e:
            print(f"❌ Guest recovery failed: {type(e).__name__}: {e}")
            return jsonify({
                "ok": False,
                "error": "Guest service unavailable",
                "stage": "guest-recovery",
                "debug_version": APP_DEBUG_VERSION,
                "generator_url": ACCOUNT_GENERATOR_URL,
                "detail": str(e),
                "exception_type": type(e).__name__
            }), 503

        try:
            data = loop.run_until_complete(
                GetAccountInformation(uid, "7", "IND", "/GetPlayerPersonalShow", credential_index=0)
            )
        except Exception as e:
            print(f"⚠️ Information request failed: {type(e).__name__}: {e}")
            with guest_refresh_lock:
                loop.run_until_complete(generate_replacement_guest())
            if not loop.run_until_complete(
                create_jwt("IND", account=get_account_credentials("IND"), credential_index=0)
            ):
                raise ValueError("Replacement guest token failed")
            data = loop.run_until_complete(
                GetAccountInformation(uid, "7", "IND", "/GetPlayerPersonalShow", credential_index=0)
            )

        if data:
            uid_region_cache[uid] = "IND"
            return json.dumps(data, indent=2), 200, {"Content-Type": "application/json"}
        return jsonify({"error": "UID not found"}), 404
    except Exception as e:
        print(f"❌ UID lookup failed: {type(e).__name__}: {e}")
        return jsonify({"error": "UID lookup failed", "detail": str(e)}), 500
    finally:
        loop.close()


@app.route('/ref-token', methods=['GET', 'POST'])
def refresh_tokens_endpoint():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = []
        for r in SUPPORTED_REGIONS:
            if GUEST_CREDENTIALS.get(r):
                tasks.append(create_jwt(r))
        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks))
        return jsonify({'message': 'Tokens refreshed'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/reload-guests', methods=['GET', 'POST'])
def reload_guests():
    try:
        load_guests_from_file()
        cached_tokens.clear()
        return jsonify({'message': 'Guests reloaded and tokens invalidated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "loaded_regions": ["IND"] if GUEST_CREDENTIALS.get("IND") else [],
        "active_ind_guest": bool(GUEST_CREDENTIALS.get("IND")),
        "total_guests": {"IND": len(GUEST_CREDENTIALS.get("IND", []))},
        "cached_tokens": list(cached_tokens.keys()),
        "account_generator": ACCOUNT_GENERATOR_URL,
        "debug_version": APP_DEBUG_VERSION,
        "generator_timeout": GENERATOR_TIMEOUT
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)