import os
import json
import time
import hmac
import uuid
import codecs
import hashlib
import random
import requests
import urllib3
import threading
import concurrent.futures
import traceback
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
from proto import MajorLoginRes_pb2

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

dEvIcEs = [
    "Asus ASUS_I005DA", "SM-G998B", "CPH2095", "Pixel 6", "OnePlus 9 Pro",
    "Samsung Galaxy S23 Ultra", "iPhone 14 Pro Max", "Xiaomi 13 Pro",
    "Redmi Note 10 Pro", "Moto G100", "OPPO Find X3", "Vivo X60 Pro"
]

cArRiErS = [
    "ATM Mobils", "Jio", "Airtel", "Vodafone Idea", "BSNL", "T-Mobile",
    "Verizon", "AT&T", "Orange", "Telenor", "O2"
]

GPUS = [
    "Adreno (TM) 640", "Mali-G78", "PowerVR Rogue",
    "Adreno 660", "Mali-G610", "Apple A15 GPU", "Adreno 730"
]

cLiEnT_iD = 100067
cLiEnT_sEcReT = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"

tOtAl_AcCoUnTs = 1
oUtPuT_fIlE = "accounts.json"
bAcKuP_lOg = "accounts_backup.jsonl"
mAx_WoRkErS = 1
rEtRy_CoUnT = 5
bAsE_dElAy = 0
GENERATOR_API_KEY = os.environ.get("GENERATOR_API_KEY", "CHANGE-ME-GENERATOR-KEY")
GENERATOR_PORT = int(os.environ.get("GENERATOR_PORT", "5002"))
generator_app = Flask(__name__)
sHaReD_cOoKiE = "datadome=nmP601L~4DvFBNemgIhE2d3Y~tR68_GHUaV8WhUdKLhjg74S_YsRWpOCnYL8cNtz58Olr_SEm1GSttQImpJO1j15k2AGGY~bFDp0hfrk6p0Dv_JZSGXJUGhhY_QsQ~5H"



def cRoWnX_vArInT_eNcOdE(n):
    if n < 0:
        n += 1 << 64
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

def cRoWnX_bUiLd_FiElD(field_num, value):
    if isinstance(value, bool):
        return cRoWnX_vArInT_eNcOdE((field_num << 3) | 0) + cRoWnX_vArInT_eNcOdE(1 if value else 0)
    if isinstance(value, int):
        return cRoWnX_vArInT_eNcOdE((field_num << 3) | 0) + cRoWnX_vArInT_eNcOdE(value)
    if isinstance(value, (str, bytes)):
        data = value.encode("utf-8") if isinstance(value, str) else value
        return cRoWnX_vArInT_eNcOdE((field_num << 3) | 2) + cRoWnX_vArInT_eNcOdE(len(data)) + data
    if isinstance(value, dict):
        sub = cRoWnX_aSsEmBlE_pRoTo(value)
        return cRoWnX_vArInT_eNcOdE((field_num << 3) | 2) + cRoWnX_vArInT_eNcOdE(len(sub)) + sub
    raise TypeError(f"Unsupported type: {type(value)}")

def cRoWnX_aSsEmBlE_pRoTo(fields: dict) -> bytes:
    packet = b""
    for k in sorted(fields.keys(), key=lambda x: int(x)):
        v = fields[k]
        fn = int(k)
        if isinstance(v, list):
            for item in v:
                packet += cRoWnX_bUiLd_FiElD(fn, item)
        else:
            packet += cRoWnX_bUiLd_FiElD(fn, v)
    return packet

def cRoWnX_aEs_EnCrYpT(plain: bytes) -> bytes:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(plain, AES.block_size))

def cRoWnX_sErVeR_uRl(region):
    reg = region.upper()
    if reg == "IND":
        return "https://client.ind.freefiremobile.com"
    elif reg in ["BR", "US", "SAC", "NA"]:
        return "https://client.us.freefiremobile.com"
    else:
        return "https://clientbp.ggpolarbear.com"

def cRoWnX_rAnDoM_nIcKnAmE():
    prefixes = ["Miwo","Nexo","Viro","Zyro","Kiro","Rivo","Luno","Mivo","Xeno","Aero"]
    exp = {"0":"⁰","1":"¹","2":"²","3":"³","4":"⁴","5":"⁵","6":"⁶","7":"⁷","8":"⁸","9":"⁹"}
    prefix = random.choice(prefixes)
    number = f"{random.randint(0, 99999):05d}"
    return prefix + "".join(exp[d] for d in number)

def cRoWnX_mAjOr_ReGiStEr(session, nickname, access_token, open_id, region="IND"):
    print("sending request to /MajorRegister")
    reg_upper = region.upper()
    base = "loginbp.common.ggbluefox.com" if reg_upper in ("ME", "TH") else "loginbp.ggblueshark.com"
    url = f"https://{base}/MajorRegister"

    nickname = nickname or cRoWnX_rAnDoM_nIcKnAmE()
    nickname = nickname[:12]

    lang = {
        "IND":"hi", "BR":"pt", "US":"en", "ID":"id", "TH":"th",
        "VN":"vi", "ME":"ar", "SG":"ms", "PK":"ur", "BD":"bn",
        "EUROPE":"fr", "RU":"ru", "NA":"na", "SAC":"es", "TW":"zh"
    }.get(reg_upper, "en")

    xor_key = [
        0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,
        0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
        0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,
        0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30
    ]
    encoded = "".join(chr(ord(c) ^ xor_key[i % len(xor_key)]) for i, c in enumerate(open_id))
    unicode_esc = "".join(c if 32 <= ord(c) <= 126 else f"\\u{ord(c):04x}" for c in encoded)
    field_bytes = codecs.decode(unicode_esc, "unicode_escape").encode("latin1")

    fields = {
        "1": nickname, "2": access_token, "3": open_id, "5": 102000007,
        "6": 4, "7": 1, "13": 1, "14": field_bytes, "15": lang,
        "16": 2, "20": "2.127.16", "21": 1
    }
    encrypted = cRoWnX_aEs_EnCrYpT(cRoWnX_aSsEmBlE_pRoTo(fields))
    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "X-Ga-Sv": "1789534056",
        "Host": base,
        "ReleaseVersion": "OB55",
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2022.3.47f1",
    }
    try:
        resp = session.post(url, headers=headers, data=encrypted, timeout=15)
    except requests.RequestException as e:
        print(f"ERROR: {e}")
        return None

    if resp.status_code == 200:
        print("/MajorRegister 200 OK")
        return nickname
    else:
        print(f"STATUS: {resp.status_code} {resp.reason}")
        print("RESPONSE TEXT:")
        print(resp.text)
        return None

def cRoWnX_mAjOr_LoGiN(session, access_token, open_id, lang="zh"):
    print("sending request to /MajorLogin")
    url = "https://loginbp.ppmainecoonghj.com/MajorLogin"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    model = random.choice(dEvIcEs)
    carrier = random.choice(cArRiErS)
    gpu = random.choice(GPUS)
    user_id = f"Google|{uuid.uuid4()}"

    fields = {
        3: now, 4: "free fire", 5: 1, 7: "2.127.13",
        8: "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)", 9: "Handheld",
        10: carrier, 11: "WIFI", 12: 1334, 13: 750, 14: "300",
        15: "ARMv7 VFPv3 NEON VMH | 2400 | 2", 16: 1993, 17: gpu,
        18: "OpenGL ES 3.2", 19: user_id, 20: "105.235.139.91",
        21: lang, 22: open_id, 23: "4", 24: "Handheld", 25: model,
        29: access_token, 30: 1, 41: carrier, 42: "WIFI",
        57: "7428b253defc164018c604a1ebbfebdf", 60: 32936, 61: 29430,
        62: 2479, 63: 900, 64: 30823, 65: 32936, 66: 30823, 67: 32936,
        73: 1, 74: "/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm",
        76: 1, 77: "2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk",
        78: 3, 79: 1, 81: "32", 83: "2019118692", 86: "OpenGLES2",
        87: 16383, 88: 4, 92: 9075, 93: "android",
        94: "KqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2",
        95: 111227, 97: 1, 98: 1, 99: "4", 100: "4",
        102: bytes.fromhex("47 51 40 4f 00 0e 5e 00 44 06 55 41 0e 50 4d 0d 13 68 5a 07 54 06 0c 6d 5c 56 0e 6a 59 56 3b 0b 55 35")
    }

    encrypted = cRoWnX_aEs_EnCrYpT(cRoWnX_aSsEmBlE_pRoTo(fields))
    headers = {
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "X-Ga-Sv": "1789534056",
        "ReleaseVersion": "OB55",
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2022.3.47f1",
    }
    try:
        resp = session.post(url, headers=headers, data=encrypted, timeout=15)
    except requests.RequestException as e:
        print(f"ERROR: {e}")
        return None, None

    if resp.status_code == 200:
        print("/MajorLogin 200 OK")
        try:
            payload = resp.content[64:]
            res_msg = getattr(MajorLoginRes_pb2, "MajorLoginRes", None)
            if res_msg is None:
                res_msg = list(MajorLoginRes_pb2.DESCRIPTOR.message_types_by_name.values())[0]._concrete_class()
            else:
                res_msg = res_msg()
            res_msg.ParseFromString(payload)
            print(MessageToJson(res_msg, indent=2))
            token = getattr(res_msg, "token", None) or getattr(res_msg, "jwt", None)
            acc_id = getattr(res_msg, "accountId", "") or getattr(res_msg, "account_id", "")
            return token, str(acc_id)
        except Exception as e:
            print(f"Error parsing protobuf: {e}")
            return None, None
    else:
        print(f"STATUS: {resp.status_code} {resp.reason}")
        print("RESPONSE TEXT:")
        print(resp.text)
        return None, None

def cRoWnX_cHoOsE_rEgIoN(session, jwt_token, region):
    print("sending request to /ChooseRegion")
    url = "https://loginbp.ppmainecoonghj.com/ChooseRegion"
    plain = cRoWnX_aSsEmBlE_pRoTo({"1": region})
    encrypted = cRoWnX_aEs_EnCrYpT(plain)
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; M2101K7AG Build/SKQ1.210908.001)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
    }
    try:
        resp = session.post(url, headers=headers, data=encrypted, timeout=15)
    except requests.RequestException as e:
        print(f"ERROR: {e}")
        return False

    if resp.status_code == 200:
        print("/ChooseRegion 200 OK")
        return True
    else:
        print(f"STATUS: {resp.status_code} {resp.reason}")
        print("RESPONSE TEXT:")
        print(resp.text)
        return False

def cRoWnX_cAlL_gEt_LoGiN_dAtA(session, jwt, open_id, region, platform_type="8"):
    print("sending request to /GetLoginData")
    base_url = cRoWnX_sErVeR_uRl(region)
    host = base_url.replace("https://", "")
    url = f"{base_url}/GetLoginData"

    fields = {
        3: time.strftime("%Y-%m-%d %H:%M:%S"), 4: "free fire", 5: 1, 7: "1.126.15",
        8: "Android OS 10 / API-29 (QP1A.190711.020/1617006012)", 9: "Handheld",
        10: "T-Mobile", 11: "WIFI", 12: 1600, 13: 720, 14: "320",
        15: "ARM64 FP ASIMD AES | 2301 | 8", 16: 2799, 17: "PowerVR Rogue GE8320",
        18: "OpenGL ES 3.2 build 1.1@5425693", 19: "Google|9f7d6b8b-b10c-454a-852d-06332cd498eb",
        20: "8.8.8.8", 21: "en", 22: open_id, 23: platform_type, 24: "Handheld",
        25: "realme RMX2189", 26: "US", 29: jwt, 30: 1, 41: "T-Mobile", 42: "WIFI",
        57: "1ac4b80ecf0478a44203bf8fac6120f5", 60: 19799, 61: 1198, 62: 5056,
        64: 1430, 65: 19999, 66: 1198, 67: 19799, 70: 4, 73: 2,
        74: "/data/app/com.dts.freefireth-FFifmAAfKh0HbXBegWOzaxw==/lib/arm64", 76: 1,
        77: "4c322aeb56444feaa151d1ea91a8f7f2|/data/app/com.dts.freefireth-FFifmAAfKh0HbXBegWOzaxw==/base.apk",
        78: 6, 79: 2, 81: "64", 83: "2019120816", 86: "OpenGLES2", 87: 3071, 88: 8,
        90: "New York", 91: "NY", 92: 10001, 93: "3rd_party",
        94: "KqsHTw+Xui+7NiknuVG39jBvqfcBIE++vNayjgpDtOGFORTYgMixv5qmFWsOvq136YMoizYxRRPFTZxTOkFnCjln760=",
        95: 111207, 96: '{"cur_rate":null,"support_etc2":false}', 97: 1, 99: "30",
        100: "38", 102: "47504412000e085134",
    }
    encrypted = cRoWnX_aEs_EnCrYpT(cRoWnX_aSsEmBlE_pRoTo(fields))
    headers = {
        "Host": host,
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "Authorization": f"Bearer {jwt}",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2022.3.47f1",
    }
    try:
        resp = session.post(url, headers=headers, data=encrypted, timeout=15)
    except requests.RequestException as e:
        print(f"ERROR: {e}")
        return False

    if resp.status_code == 200:
        print("/GetLoginData 200 OK")
        return True
    else:
        print(f"STATUS: {resp.status_code} {resp.reason}")
        print("RESPONSE TEXT:")
        print(resp.text)
        return False


def cRoWnX_rAnDoM_uSeR_aGeNt_MsDk():
    devices = [
        "ASUS_AI2401_A", "SM-G998B", "CPH2095", "Pixel 6", "OnePlus 9 Pro",
        "Samsung Galaxy S23 Ultra", "iPhone 14 Pro Max", "Xiaomi 13 Pro",
        "Redmi Note 10 Pro", "Moto G100", "OPPO Find X3", "Vivo X60 Pro",
        "Realme GT 5G", "Nokia 8.3", "OnePlus Nord 2", "Pixel 5a",
        "Samsung A52", "Xiaomi Mi 11", "Poco X3", "LG Velvet"
    ]
    device = random.choice(devices)
    version = random.choice(["9", "10", "11", "12", "13"])
    lang = random.choice(["en", "hi", "id", "th"])
    region = random.choice(["US", "IND", "ID", "TH"])
    app_ver = "2.127.1"
    build = "2019118047"
    return f"GarenaMSDK/4.0.42({device} ;Android {version};{lang};{region};app {app_ver} {build};)"

file_lock = threading.Lock()
success_lock = threading.Lock()
successful_count = 0

def cRoWnX_lOaD_eXiStInG_uIdS():
    uids = set()
    data = []

    if os.path.exists(oUtPuT_fIlE):
        try:
            with open(oUtPuT_fIlE, "r", encoding="utf-8") as f:
                data = json.load(f)
            uids = {acc.get("uid") for acc in data if acc.get("uid")}
        except Exception:
            print("[!] accounts.json corrupt/partial detected, rebuilding from backup log...")
            data = []
            uids = set()

    recovered = 0
    if os.path.exists(bAcKuP_lOg):
        try:
            with open(bAcKuP_lOg, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        acc = json.loads(line)
                    except Exception:
                        continue
                    uid = acc.get("uid")
                    if uid and uid not in uids:
                        data.append(acc)
                        uids.add(uid)
                        recovered += 1
        except Exception as e:
            print(f"[!] Backup log read error: {e}")

    if recovered > 0:
        print(f"[*] Recovered {recovered} accounts from backup log -> rebuilding {oUtPuT_fIlE}")
        tmp = oUtPuT_fIlE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, oUtPuT_fIlE)

    return uids

def cRoWnX_sAvE_aCcOuNt_DaTa(region, account_entry, jwt_entry):
    with file_lock:
        region_file = f"accounts-{region.upper()}.json"
        data = []
        if os.path.exists(region_file):
            try:
                with open(region_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append(account_entry)

        tmp_file = region_file + ".tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, region_file)
        except Exception as e:
            print(f"[!] Save to {region_file} failed: {e}")

        jwt_file = f"jwt-{region.upper()}.json"
        jwt_data = []
        if os.path.exists(jwt_file):
            try:
                with open(jwt_file, "r", encoding="utf-8") as f:
                    jwt_data = json.load(f)
            except Exception:
                jwt_data = []
        jwt_data.append(jwt_entry)

        tmp_jwt = jwt_file + ".tmp"
        try:
            with open(tmp_jwt, "w", encoding="utf-8") as f:
                json.dump(jwt_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_jwt, jwt_file)
        except Exception as e:
            print(f"[!] Save to {jwt_file} failed: {e}")

def cRoWnX_rEgIsTeR_gUeSt(session, password):
    reg_url = f"https://ffmconnect.ppmainecoonghj.com/api/v2/oauth/guest:register"
    reg_payload = {
        "app_id": cLiEnT_iD,
        "client_type": 2,
        "password": password,
        "source": 2
    }
    reg_raw_body = json.dumps(reg_payload, separators=(',', ':'))
    signature = hmac.new(
        cLiEnT_sEcReT.encode('utf-8'),
        reg_raw_body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    reg_headers = {
        "User-Agent": cRoWnX_rAnDoM_uSeR_aGeNt_MsDk(),
        "Authorization": f"Signature {signature}",
        "Cookie": sHaReD_cOoKiE,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    resp = session.post(reg_url, headers=reg_headers, data=reg_raw_body, timeout=15)
    if resp.status_code != 200:
        resp.raise_for_status()
    data = resp.json()
    uid = data.get("data", {}).get("uid")
    if not uid:
        raise Exception("UID missing in response")
    return uid

def cRoWnX_tOkEn_GrAnT(session, uid, password):
    token_url = f"https://ffmconnect.ppmainecoonghj.com/api/v2/oauth/guest/token:grant"
    token_headers = {
        "User-Agent": cRoWnX_rAnDoM_uSeR_aGeNt_MsDk(),
        "Cookie": sHaReD_cOoKiE,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    token_payload = {
        "client_id": cLiEnT_iD,
        "client_secret": cLiEnT_sEcReT,
        "client_type": 2,
        "password": password,
        "response_type": "token",
        "uid": int(uid)
    }
    token_raw_body = json.dumps(token_payload, separators=(',', ':'))
    resp = session.post(token_url, headers=token_headers, data=token_raw_body, timeout=15)
    if resp.status_code != 200:
        resp.raise_for_status()
    token_data = resp.json()
    token_info = token_data.get("data", {})
    open_id = token_info.get("open_id")
    access_token = token_info.get("access_token")
    if not open_id or not access_token:
        raise Exception("Missing open_id or access_token")
    return open_id, access_token

def cRoWnX_cReAtE_aCcOuNt(index=1, existing_uids=None, nickname=None, region="IND"):
    """
    One-account / one-session lifecycle.

    A fresh requests.Session is created for each account creation attempt.
    The same session object is passed through the complete account flow:
    Register -> Token/Login -> MajorRegister -> MajorLogin -> Region -> LoginData.

    After the attempt finishes (success or failure), that session is closed
    and discarded. The next account creation gets a completely new session.
    """
    global successful_count
    existing_uids = existing_uids if existing_uids is not None else set()
    region = "IND"
    nickname = nickname or cRoWnX_rAnDoM_nIcKnAmE()

    password = os.urandom(32).hex().upper()

    # IMPORTANT: exactly one fresh HTTP session for this account attempt.
    session_id = uuid.uuid4().hex
    session = requests.Session()
    session.verify = False

    print(f"[*] Account #{index}: NEW session {session_id[:12]}...")

    try:
        # All account-creation requests below MUST use this same session.
        uid = str(cRoWnX_rEgIsTeR_gUeSt(session, password))
        if uid in existing_uids:
            print(f"[!] Account #{index}: UID {uid} already exists.")
            return None

        open_id, access_token = cRoWnX_tOkEn_GrAnT(session, uid, password)

        reg_name = cRoWnX_mAjOr_ReGiStEr(
            session, nickname, access_token, open_id, region
        )
        if not reg_name:
            return None

        jwt_token, account_id = cRoWnX_mAjOr_LoGiN(
            session, access_token, open_id
        )
        if not jwt_token:
            return None

        if not cRoWnX_cHoOsE_rEgIoN(session, jwt_token, region):
            return None

        final_jwt, final_acc_id = cRoWnX_mAjOr_LoGiN(
            session, access_token, open_id
        )
        if not final_jwt:
            return None

        if final_acc_id:
            account_id = final_acc_id

        if not cRoWnX_cAlL_gEt_LoGiN_dAtA(
            session, final_jwt, open_id, region
        ):
            return None

        account_entry = {
            "uid": uid,
            "password": password,
            "account_id": str(account_id),
            "name": reg_name,
            "region": "IND",
        }
        jwt_entry = {
            "access_token": access_token,
            "token": final_jwt,
            "uid": uid,
            "region": "IND",
        }

        cRoWnX_sAvE_aCcOuNt_DaTa("IND", account_entry, jwt_entry)
        existing_uids.add(uid)

        with success_lock:
            successful_count += 1

        print(
            f"[+] Account #{index} created successfully: "
            f"UID {uid}, name {reg_name}"
        )
        return account_entry

    except Exception as e:
        print(
            f"[!] Account #{index} creation failed: "
            f"{type(e).__name__}: {e}"
        )
        return None

    finally:
        # Never reuse this session for another account.
        try:
            session.close()
        except Exception:
            pass
        print(f"[*] Account #{index}: session {session_id[:12]}... CLOSED/DISCARDED")


@generator_app.route("/generate-ind", methods=["POST"])
@generator_app.route("/api/generate-ind", methods=["POST"])
@generator_app.route("/", methods=["POST"])
def generate_ind_endpoint():
    if request.headers.get("X-Generator-Key", "") != GENERATOR_API_KEY:
        return jsonify({
            "ok": False,
            "stage": "generator-auth",
            "error": "Unauthorized",
            "debug_version": "GENERATOR-SERVICE-DEBUG-2026-09-22-v2"
        }), 401
    try:
        existing = cRoWnX_lOaD_eXiStInG_uIdS()
        account = cRoWnX_cReAtE_aCcOuNt(
            index=1, existing_uids=existing,
            nickname=cRoWnX_rAnDoM_nIcKnAmE(), region="IND"
        )
        if not account:
            return jsonify({"ok": False, "error": "Account creation failed"}), 502
        return jsonify({
            "ok": True, "uid": account["uid"],
            "password": account["password"],
            "account_id": account["account_id"],
            "name": account["name"], "region": "IND"
        }), 201
    except Exception as e:
        print(f"[GENERATOR] Account generation exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return jsonify({
            "ok": False,
            "stage": "account-creation",
            "error": "Account generation failed",
            "exception_type": type(e).__name__,
            "detail": str(e),
            "debug_version": "GENERATOR-SERVICE-DEBUG-2026-09-22-v2"
        }), 500

def run_generator_service():
    generator_app.run(host="0.0.0.0", port=GENERATOR_PORT, debug=False, threaded=False)

def cRoWnX_mAiN():
    global successful_count

    nickname = cRoWnX_rAnDoM_nIcKnAmE()
    region = "IND"

    existing_uids = cRoWnX_lOaD_eXiStInG_uIdS()
    initial_count = len(existing_uids)
    successful_count = initial_count

    print(f"\n[*] Total target accounts: {tOtAl_AcCoUnTs}")
    print(f"[*] Existing accounts: {initial_count}")
    print(f"[*] Selected Region: {region}")
    print(f"[*] Output file: {oUtPuT_fIlE}\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=mAx_WoRkErS) as executor:
        futures = [executor.submit(cRoWnX_cReAtE_aCcOuNt, i, existing_uids, nickname, region) for i in range(1, tOtAl_AcCoUnTs + 1)]
        for _ in concurrent.futures.as_completed(futures):
            pass

    try:
        with open(oUtPuT_fIlE, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        final_count = len(final_data)
    except Exception:
        final_count = successful_count

    print(f"\n[Done] Total Accounts in file: {final_count}")
    print(f"[*] Newly added this run: {final_count - initial_count}")

if __name__ == "__main__":
    if os.environ.get("GENERATOR_CLI", "0") == "1":
        cRoWnX_mAiN()
    else:
        run_generator_service()
