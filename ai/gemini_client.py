"""
Centralized Gemini client using the google-genai SDK.
Uses GEMINI_API_KEY and GEMINI_MODEL from environment; never logs or hardcodes keys.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Redact for any debug output (never log the key)
def _redact(key: str) -> str:
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "..." + key[-2:]


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to .env or set the environment variable. See AI_SETUP.md."
        )
    return key


def _get_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"


def generate_text(prompt: str) -> str:
    """
    Call Gemini to generate text for the given prompt.
    Uses GEMINI_MODEL (default: gemini-2.0-flash).
    Returns the generated text.
    Raises RuntimeError if GEMINI_API_KEY is missing or on API errors (message is safe, no secrets).
    """
    from google import genai

    api_key = _get_api_key()
    model = _get_model()

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except Exception as e:
        err_msg = str(e).strip()
        # Never expose key in error
        if api_key in err_msg or "api_key" in err_msg.lower():
            err_msg = "API request failed (check key and model)."
        # Short, safe message for known errors (e.g. 429 quota)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
            err_msg = "Gemini quota exceeded; try again later or check your plan."
        elif "404" in err_msg or "NOT_FOUND" in err_msg:
            err_msg = "Gemini model not found; check GEMINI_MODEL."
        elif len(err_msg) > 300:
            err_msg = "Gemini API error (check key, model, and network)."
        raise RuntimeError(f"Gemini request failed: {err_msg}") from e

    if not response or not getattr(response, "text", None):
        raise RuntimeError("Gemini returned an empty response.")
    return response.text.strip()
