# ai/routes.py
from flask import jsonify
from flask_login import login_required

from . import ai_bp
from .gemini_client import generate_text


@ai_bp.get("/ping")
@login_required
def ping():
    """
    Verify Gemini integration: call the model and return OK + short response.
    Returns JSON { "ok": true, "text": "..." } or { "ok": false, "error": "..." } with 500.
    """
    try:
        text = generate_text("Spune 'OK' si spune modelul folosit.")
        return jsonify({"ok": True, "text": text})
    except Exception as e:
        err = str(e).strip()
        # Never expose secrets in response
        if "GEMINI_API_KEY" in err or "api_key" in err or len(err) > 200:
            err = "Integration error (check configuration)."
        return jsonify({"ok": False, "error": err}), 500
