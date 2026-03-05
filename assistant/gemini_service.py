"""
Gemini 1.5 Flash integration for the internal assistant.
- System context: KNOWLEDGE_BASE only (no hallucinations).
- Optional structured output: intent + params for watchlist / marketplace / tasks.
"""
import json
import re
import os
from typing import Any

# Lazy import so app works without GEMINI_API_KEY
_gen_model = None


def _get_model():
    global _gen_model
    if _gen_model is not None:
        return _gen_model
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _gen_model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=_build_system_instruction(),
        )
        return _gen_model
    except Exception:
        return None


def _build_system_instruction() -> str:
    from .knowledge_base import KNOWLEDGE_BASE, SYSTEM_INSTRUCTION
    return (
        SYSTEM_INSTRUCTION + "\n\n=== BAZA DE CUNOȘTINȚE (singura sursă de adevăr) ===\n\n"
        + KNOWLEDGE_BASE
        + "\n\n=== REGULI PENTRU RĂSPUNS ===\n"
        "1. Pentru întrebări despre aplicație, prețuri, pași, acces, telefoane: răspunde doar din baza de cunoștințe de mai sus, în text normal.\n"
        "2. Doar dacă utilizatorul EXPRIMĂ CLAR că vrea să salveze un imobil (ex: 'Am un apartament 2 camere Aviatiei 150k', 'Salvează Pipera sub 180.000'), răspunde DOAR cu acest JSON, fără niciun alt text: "
        '{"intent":"watchlist_add","zone":"nume zonă din mesaj sau null","price_min":număr sau null,"price_max":număr sau null,"rooms":număr sau null}\n'
        "3. Doar dacă utilizatorul EXPRIMĂ CLAR că vrea să caute cereri în marketplace (ex: 'Există cereri în Aviatiei?', 'Ce e sub 180k în Pipera?'), răspunde DOAR cu: "
        '{"intent":"marketplace_search","zone":"nume zonă sau null","price_min":null,"price_max":număr sau null,"rooms":număr sau null}\n'
        "4. Doar dacă utilizatorul întreabă despre taskuri/sarcini (ex: 'Ce taskuri am azi?', 'Ce urmează?'), răspunde DOAR cu: "
        '{"intent":"task_summary"}\n'
        "5. Pentru orice altceva: răspunde în text normal, concis și util. Nu inventa prețuri sau pași care nu sunt în baza de cunoștințe."
    )


def is_available() -> bool:
    return _get_model() is not None


def ask(user_message: str) -> tuple[str | None, dict[str, Any] | None]:
    """
    Send user message to Gemini. Returns (text_response, structured_intent).
    - If Gemini returns a JSON intent (watchlist_add, marketplace_search, task_summary), structured_intent is set and text_response may be None.
    - Otherwise text_response is the reply and structured_intent is None.
    """
    model = _get_model()
    if not model:
        return None, None
    try:
        response = model.generate_content(
            user_message.strip(),
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
            },
        )
        if not response or not response.text:
            return None, None
        text = response.text.strip()
        # Try to extract JSON intent (single line or code block)
        parsed = _extract_intent(text)
        if parsed:
            return None, parsed
        return text, None
    except Exception:
        return None, None


def _extract_intent(gemini_text: str) -> dict[str, Any] | None:
    """Extract intent JSON from Gemini response. Returns dict or None."""
    # Look for ```json ... ``` or single line {"intent": ...}
    patterns = [
        r"```(?:json)?\s*(\{[^`]+\})\s*```",
        r"(\{\s*\"intent\"\s*:\s*\"[^\"]+\"[^}]*\})",
    ]
    for pat in patterns:
        m = re.search(pat, gemini_text, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(1).strip())
                if isinstance(obj, dict) and obj.get("intent") in ("watchlist_add", "marketplace_search", "task_summary"):
                    return obj
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def format_marketplace_response(count: int, items_summary: list[str], has_more: bool) -> str:
    """Ask Gemini to format marketplace results into a short, friendly reply (optional; can be done in backend to save cost)."""
    model = _get_model()
    if not model:
        return _fallback_marketplace_text(count, items_summary)
    try:
        prompt = (
            f"Utilizatorul a căutat cereri. Rezultat: {count} cereri găsite. "
            f"Rezumat: " + "; ".join(items_summary[:5]) + ". "
            "Scrie un răspuns scurt (1-2 propoziții) în română, prietenos, și spune că poate vedea cererile (fără a inventa linkuri). Fără JSON."
        )
        resp = model.generate_content(prompt, generation_config={"temperature": 0.3, "max_output_tokens": 150})
        if resp and resp.text:
            return resp.text.strip()
    except Exception:
        pass
    return _fallback_marketplace_text(count, items_summary)


def _fallback_marketplace_text(count: int, items_summary: list[str]) -> str:
    if count == 0:
        return "Nu am găsit cereri care se potrivesc. Încearcă alte zone sau buget."
    lines = [f"Am găsit **{count}** cereri care se potrivesc:"] + items_summary[:5]
    return "\n".join(lines) + "\n\nVrei să le vezi?"


def format_task_summary(tasks_for_user: list[dict]) -> str:
    """Ask Gemini to summarize user's tasks into a short reply."""
    model = _get_model()
    if not model:
        return _fallback_task_text(tasks_for_user)
    try:
        prompt = (
            "Rezumat taskuri utilizator (titlu, status, prioritate, due_date):\n"
            + json.dumps(tasks_for_user, ensure_ascii=False, indent=0)
            + "\n\nScrie un răspuns scurt în română (2-4 propoziții): ce are de făcut, ce e urgent/azi, ce e finalizat. Fără JSON. Prietenos."
        )
        resp = model.generate_content(prompt, generation_config={"temperature": 0.3, "max_output_tokens": 256})
        if resp and resp.text:
            return resp.text.strip()
    except Exception:
        pass
    return _fallback_task_text(tasks_for_user)


def _fallback_task_text(tasks: list[dict]) -> str:
    if not tasks:
        return "Nu ai taskuri în listă. Poți adăuga din meniul To-Do."
    open_count = sum(1 for t in tasks if t.get("status") != "done")
    return f"Ai **{len(tasks)}** taskuri în total, **{open_count}** deschise. Verifică în To-Do ce urmează."
