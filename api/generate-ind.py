import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from account_generator_service import generator_app


def app(environ, start_response):
    # Vercel invokes this Python function at /api/generate-ind.
    # Normalize the incoming path so the generator's Flask root route
    # is always reached, regardless of whether Vercel passes the prefix.
    path = environ.get("PATH_INFO", "")
    if path in ("", "/", "/api/generate-ind", "/api/generate-ind/"):
        environ["PATH_INFO"] = "/"
    return generator_app.wsgi_app(environ, start_response)
