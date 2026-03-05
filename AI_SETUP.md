# AI (Gemini) setup

This app uses the **google-genai** SDK and a central client in `ai/gemini_client.py`. No API keys are hardcoded; everything is driven by environment variables.

## 1. Environment variables

- **`GEMINI_API_KEY`** (required): Your Gemini API key (e.g. from [Google AI Studio](https://aistudio.google.com/)).
- **`GEMINI_MODEL`** (optional): Model name. Default: `gemini-2.0-flash`.

Create or edit `.env` in the app directory (`fisa_vizionare_app/`):

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

Never commit `.env` or log the API key.

## 2. Dependencies

Install with:

```powershell
cd fisa_vizionare_app
pip install -r requirements.txt
```

This includes `python-dotenv` (loads `.env`) and `google-genai` (Gemini SDK).

## 3. Smoke test (standalone)

From the **app directory** (`fisa_vizionare_app`), run:

```powershell
cd c:\Users\alexc\OneDrive\Desktop\fisa-vizionare-python-test\fisa_vizionare_app
python test_gemini.py
```

You should see a short Romanian greeting. Exit code 0 means success.

## 4. Flask integration ping

1. Start the app (from `fisa_vizionare_app`):

   ```powershell
   $env:FLASK_APP = "main.py"
   flask run
   ```

   Or: `python main.py`

2. Log in, then open:

   ```
   http://127.0.0.1:5000/ai/ping
   ```

   Response when OK:

   ```json
   { "ok": true, "text": "..." }
   ```

   On error you get `{ "ok": false, "error": "..." }` and HTTP 500 (no secrets in the body).

## 5. Using the client in code

```python
from ai.gemini_client import generate_text

text = generate_text("Your prompt here.")
```

Raises `RuntimeError` if `GEMINI_API_KEY` is missing or the API call fails. The error message is safe (no key or secrets). Common causes: missing key, wrong model name (use `gemini-2.0-flash`), or 429 quota exceeded (free tier limits).
