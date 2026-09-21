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
SUPPORTED_REGIONS = [
    "IND", "SG", "ID", "BR", "VN", "US", "SAC", "NA",
    "RU", "TH", "TW", "BD", "PK", "ME", "CIS", "EUROPE"
]

# ---------- App Setup ----------

app = Flask(__name__)
CORS(app)
cache = TTLCache(maxsize=100, ttl=300)
cached_tokens = defaultdict(dict)
uid_region_cache = {}

# ---------- Guest Rotation Globals ----------

GUEST_CREDENTIALS = {}          # region -> list of credential strings
region_index = defaultdict(int) # current guest index per region
region_calls = defaultdict(int) # call counter per region
ROTATION_THRESHOLD = 2          # rotate after every N calls

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
        print(f"Current working directory: {os.getcwd()}")
        print(f"Files in directory: {os.listdir('.')}")
        with open('guests.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        for region in SUPPORTED_REGIONS:
            if region not in data or not data[region]:
                data[region] = []
        GUEST_CREDENTIALS = data
        print("✅ Guests loaded from guests.json")
        print(f"Loaded regions: {list(GUEST_CREDENTIALS.keys())}")
    except Exception as e:
        print(f"❌ Could not load guests.json: {e}")
        GUEST_CREDENTIALS = {}

load_guests_from_file()

# ---------- Guest Rotation Management ----------

def manage_rotation(region: str):
    global region_calls, region_index, cached_tokens
    region_calls[region] += 1
    if region_calls[region] % ROTATION_THRESHOLD == 0:
        guest_list = GUEST_CREDENTIALS.get(region, [])
        if guest_list:
            region_index[region] = (region_index[region] + 1) % len(guest_list)
            if region in cached_tokens:
                del cached_tokens[region]
            print(f"🔄 Rotated guest for {region} to index {region_index[region]}")

# ---------- Guest Credentials (No Hardcoded) ----------

def get_account_credentials(region: str) -> str:
    guest_list = GUEST_CREDENTIALS.get(region.upper(), [])
    idx = region_index[region.upper()]
    if guest_list and idx < len(guest_list):
        return guest_list[idx]
    raise ValueError(f"No guest credentials available for region {region}")

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
    api_key = request.args.get('key', '')
    if api_key != 'RAM-SAGAR':
        return jsonify({"error": "Invalid or missing API key"}), 401
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "Please provide UID"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        regions_to_try = []
        if uid in uid_region_cache:
            regions_to_try.append(uid_region_cache[uid])
        for region in SUPPORTED_REGIONS:
            if region not in regions_to_try:
                regions_to_try.append(region)

        for region in regions_to_try:
            guest_list = GUEST_CREDENTIALS.get(region.upper(), [])
            if not guest_list:
                print(f"⚠️ No guest credentials available for {region}")
                continue
            print(f"\n🔎 Trying UID {uid} in {region} with {len(guest_list)} guest credential(s)")
            for credential_index in range(len(guest_list)):
                try:
                    print(f"➡️ [{region}] Trying guest {credential_index + 1}/{len(guest_list)}")
                    data = loop.run_until_complete(GetAccountInformation(uid, "7", region, "/GetPlayerPersonalShow", credential_index=credential_index))
                    if data:
                        uid_region_cache[uid] = region
                        print(f"✅ UID {uid} FOUND using {region} guest #{credential_index + 1}")
                        return json.dumps(data, indent=2), 200, {'Content-Type': 'application/json'}
                except Exception as e:
                    print(f"❌ [{region}] guest #{credential_index + 1} failed: {type(e).__name__}: {e}")
                    continue
            print(f"⏭️ All guests failed for {region}; trying next region...")
        return jsonify({"error": "UID not found or no working guest available for any region"}), 404
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
        region_index.clear()
        region_calls.clear()
        cached_tokens.clear()
        return jsonify({'message': 'Guests reloaded and tokens invalidated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "loaded_regions": list(GUEST_CREDENTIALS.keys()),
        "total_guests": {r: len(GUEST_CREDENTIALS[r]) for r in GUEST_CREDENTIALS},
        "cached_tokens": list(cached_tokens.keys())
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)