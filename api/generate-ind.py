import os
import sys
import traceback
from pathlib import Path

from flask import Flask, request, jsonify

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEBUG_VERSION = "GENERATOR-DEBUG-2026-09-22-v3"

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
    GENERATOR_API_KEY = ""
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

app = Flask(__name__)


def _authorized():
    expected = os.environ.get("GENERATOR_API_KEY", GENERATOR_API_KEY)
    supplied = request.headers.get("X-Generator-Key", "")
    return bool(expected) and supplied == expected


def _health():
    return jsonify({
        "ok": True,
        "service": "IND account generator",
        "debug_version": DEBUG_VERSION,
        "import_ok": IMPORT_OK,
        "import_error": IMPORT_ERROR,
        "request_path": request.path,
        "request_method": request.method,
        "message": "POST with X-Generator-Key generates one IND account."
    }), 200


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
            "detail": "X-Generator-Key does not match GENERATOR_API_KEY."
        }), 401

    try:
        print(
            f"[GENERATOR DEBUG] POST path={request.path} "
            f"host={request.host}"
        )

        existing = cRoWnX_lOaD_eXiStInG_uIdS()
        print(f"[GENERATOR DEBUG] Existing UID count: {len(existing)}")

        nickname = cRoWnX_rAnDoM_nIcKnAmE()
        print(f"[GENERATOR DEBUG] Generated nickname: {nickname}")

        account = cRoWnX_cReAtE_aCcOuNt(
            index=1,
            existing_uids=existing,
            nickname=nickname,
            region="IND",
        )

        if not account:
            return jsonify({
                "ok": False,
                "stage": "account-creation",
                "debug_version": DEBUG_VERSION,
                "error": "Account creation failed",
                "detail": "cRoWnX_cReAtE_aCcOuNt returned None"
            }), 502

        return jsonify({
            "ok": True,
            "stage": "complete",
            "debug_version": DEBUG_VERSION,
            "uid": str(account.get("uid", "")),
            "password": str(account.get("password", "")),
            "account_id": str(account.get("account_id", "")),
            "name": str(account.get("name", "")),
            "region": "IND"
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


# Exact routes.
@app.route("/", methods=["GET"])
@app.route("/generate-ind", methods=["GET"])
@app.route("/api/generate-ind", methods=["GET"])
def health():
    return _health()


@app.route("/", methods=["POST"])
@app.route("/generate-ind", methods=["POST"])
@app.route("/api/generate-ind", methods=["POST"])
def generate():
    return _generate()


# Catch-all POST is intentional: Vercel can preserve a rewritten function path
# such as /api/generate-ind.py. It prevents a Flask 404 before our diagnostics.
@app.route("/<path:_any_path>", methods=["POST"])
def generate_catch_all(_any_path):
    print(f"[GENERATOR DEBUG] Catch-all POST path={request.path}")
    return _generate()


@app.route("/<path:_any_path>", methods=["GET"])
def health_catch_all(_any_path):
    return _health()
