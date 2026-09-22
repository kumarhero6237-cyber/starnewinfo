import os
import sys
import traceback
from pathlib import Path

from flask import Flask, request, jsonify

# Make project root importable on Vercel.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEBUG_VERSION = "GENERATOR-DEBUG-2026-09-22-v2"

try:
    from account_generator_service import (
        GENERATOR_API_KEY,
        cRoWnX_lOaD_eXiStInG_uIdS,
        cRoWnX_cReAtE_aCcOuNt,
        cRoWnX_rAnDoM_nIcKnAmE,
    )
    IMPORT_OK = True
    IMPORT_ERROR = None
except Exception as exc:
    IMPORT_OK = False
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

app = Flask(__name__)


def _authorized():
    expected = os.environ.get("GENERATOR_API_KEY", GENERATOR_API_KEY if IMPORT_OK else "")
    supplied = request.headers.get("X-Generator-Key", "")
    return bool(expected) and supplied == expected


def _generate():
    if not IMPORT_OK:
        return jsonify({
            "ok": False,
            "stage": "generator-import",
            "debug_version": DEBUG_VERSION,
            "error": "account_generator_service import failed",
            "detail": IMPORT_ERROR,
        }), 500

    if not _authorized():
        return jsonify({
            "ok": False,
            "stage": "generator-auth",
            "debug_version": DEBUG_VERSION,
            "error": "Unauthorized",
        }), 401

    try:
        existing = cRoWnX_lOaD_eXiStInG_uIdS()
        print(f"[GENERATOR DEBUG] Existing UID count: {len(existing)}")

        account = cRoWnX_cReAtE_aCcOuNt(
            index=1,
            existing_uids=existing,
            nickname=cRoWnX_rAnDoM_nIcKnAmE(),
            region="IND",
        )

        if not account:
            return jsonify({
                "ok": False,
                "stage": "account-creation",
                "debug_version": DEBUG_VERSION,
                "error": "Account creation failed",
                "detail": "cRoWnX_cReAtE_aCcOuNt returned None",
            }), 502

        return jsonify({
            "ok": True,
            "stage": "complete",
            "debug_version": DEBUG_VERSION,
            "uid": str(account.get("uid", "")),
            "password": str(account.get("password", "")),
            "account_id": str(account.get("account_id", "")),
            "name": str(account.get("name", "")),
            "region": "IND",
        }), 201

    except Exception as exc:
        print("[GENERATOR DEBUG] Exception during account generation:")
        traceback.print_exc()
        return jsonify({
            "ok": False,
            "stage": "account-creation",
            "debug_version": DEBUG_VERSION,
            "error": "Account generation exception",
            "exception_type": type(exc).__name__,
            "detail": str(exc),
        }), 500


# Vercel can pass different PATH_INFO values depending on routing.
# Keep all relevant POST paths mapped to the same handler.
@app.route("/", methods=["POST"])
@app.route("/generate-ind", methods=["POST"])
@app.route("/api/generate-ind", methods=["POST"])
def generate_ind():
    print(
        f"[GENERATOR DEBUG] Incoming POST path={request.path} "
        f"full_path={request.full_path} host={request.host}"
    )
    return _generate()


@app.route("/", methods=["GET"])
@app.route("/generate-ind", methods=["GET"])
@app.route("/api/generate-ind", methods=["GET"])
def generator_health():
    return jsonify({
        "ok": True,
        "service": "IND account generator",
        "debug_version": DEBUG_VERSION,
        "import_ok": IMPORT_OK,
        "import_error": IMPORT_ERROR,
        "message": "Use POST with X-Generator-Key to generate an IND account.",
    }), 200
