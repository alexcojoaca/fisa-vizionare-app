"""
Deterministic assistant logic: watchlist parsing, marketplace search, price/zone normalization.
No external AI; fuzzy matching with RapidFuzz for zones.
"""
import re
from typing import Any

from rapidfuzz import fuzz, process


def normalize_price(value: Any) -> int | None:
    """Parse price from human input: 150.000, 180k, 180k euro, sub 180k -> int or None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    s = str(value).strip().lower()
    # "150.000", "180 000", "180k", "180k euro", "sub 180k"
    s = s.replace(" ", "").replace(".", "").replace(",", "")
    s = re.sub(r"k\b", "000", s)
    s = re.sub(r"eur(o|os)?", "", s)
    s = re.sub(r"sub\s*", "", s)
    s = re.sub(r"\D", "", s)
    if not s:
        return None
    try:
        n = int(s)
        return n if n >= 0 else None
    except ValueError:
        return None


def fuzzy_match_zone(user_input: str, zone_names: list[str], score_cutoff: int = 60) -> str | None:
    """
    Return best matching full zone name from zone_names, or None.
    user_input: e.g. "Aviatiei", "Pipera"
    zone_names: e.g. ["Sector 1 - Aviatorilor", "Sector 2 - Pipera"]
    """
    if not user_input or not zone_names:
        return None
    inp = user_input.strip()
    if not inp:
        return None
    # Build choices: full names + short names (part after " - "), map short -> full
    choice_to_full = {}
    for z in zone_names:
        choice_to_full[z] = z
        if " - " in z:
            short = z.split(" - ", 1)[-1].strip()
            if short:
                choice_to_full[short] = z
    choices = list(choice_to_full.keys())
    result = process.extractOne(inp, choices, scorer=fuzz.ratio, score_cutoff=score_cutoff)
    if not result:
        return None
    name, score, _ = result
    return choice_to_full.get(name)


# Intent detection (simple keyword-based)
WATCHLIST_TRIGGERS = [
    "salvează", "salvez", "salveaza", "adaug", "adauga", "am un", "vreau sa salvez",
    "vreau să salvez", "salveaza", "watchlist", "watch list", "listă", "lista",
    "apartament", "camera", "camere", "aviatiei", "pipera", "sector", "sub ", "pana in", "până în",
]
SEARCH_TRIGGERS = [
    "cereri", "cerere", "exista", "există", "sunt cereri", "ce cereri", "caut", "cauta",
    "gasesti", "găsești", "match", "potriviri", "aviatiei", "pipera", "sector",
]


def is_watchlist_intent(text: str) -> bool:
    """Heuristic: user wants to save a property to watchlist."""
    if not text or len(text) < 5:
        return False
    t = text.strip().lower()
    for w in WATCHLIST_TRIGGERS:
        if w in t:
            return True
    # Number + zone-like (e.g. "2 camere 150000 aviatiei")
    if re.search(r"\d+\s*(camere|k|\.?\d{3})", t) and re.search(r"[a-zăâîșț]{3,}", t):
        return True
    return False


def is_search_intent(text: str) -> bool:
    """Heuristic: user wants to check marketplace requests."""
    if not text or len(text) < 3:
        return False
    t = text.strip().lower()
    for w in SEARCH_TRIGGERS:
        if w in t:
            return True
    return False


def parse_watchlist_from_text(text: str, zone_names: list[str]) -> dict[str, Any]:
    """
    Extract zone, price_min, price_max, rooms from user message.
    Returns dict with keys: zone (str|None), price_min, price_max, rooms, title (generated).
    """
    out = {"zone": None, "price_min": None, "price_max": None, "rooms": None, "title": ""}
    t = text.strip()

    # Rooms: "2 camere", "3 camere", "4+"
    rooms_m = re.search(r"(\d+)\s*camere?", t, re.I)
    if rooms_m:
        try:
            out["rooms"] = int(rooms_m.group(1))
        except ValueError:
            pass
    if out["rooms"] is None:
        rooms_m = re.search(r"(\d+)\s*cam", t, re.I)
        if rooms_m:
            try:
                out["rooms"] = int(rooms_m.group(1))
            except ValueError:
                pass

    # Prices: "150.000", "sub 180k", "140-160k", "pana in 180000"
    numbers = re.findall(r"(?:sub|până în|pana in|max|până|pana)?\s*(\d[\d.\s,]*\d|\d+)\s*(?:k|eur|euro)?", t, re.I)
    prices = []
    for n in numbers:
        val = normalize_price(n)
        if val is not None:
            prices.append(val)
    if "sub" in t.lower() or "până" in t.lower() or "pana" in t.lower() or "max" in t.lower():
        if prices:
            out["price_max"] = max(prices)
    elif len(prices) >= 2:
        out["price_min"] = min(prices)
        out["price_max"] = max(prices)
    elif len(prices) == 1:
        out["price_max"] = prices[0]

    # Zone: try to match a word or phrase against zone_names
    words = re.findall(r"[A-Za-zĂÂÎȘȚăâîșț]+(?:\s+[A-Za-zĂÂÎȘȚăâîșț]+)*", t)
    for w in words:
        if len(w) < 3:
            continue
        matched = fuzzy_match_zone(w, zone_names, score_cutoff=55)
        if matched:
            out["zone"] = matched
            break
    if not out["zone"] and zone_names:
        for z in zone_names:
            short = z.split(" - ")[-1].strip() if " - " in z else z
            if short.lower() in t.lower():
                out["zone"] = z
                break

    # Title
    parts = []
    if out["zone"]:
        parts.append(out["zone"].split(" - ")[-1] if " - " in out["zone"] else out["zone"])
    if out["rooms"]:
        parts.append(f"{out['rooms']} camere")
    if out["price_min"] is not None or out["price_max"] is not None:
        if out["price_min"] is not None and out["price_max"] is not None:
            parts.append(f"{out['price_min']:,}-{out['price_max']:,} €".replace(",", "."))
        elif out["price_max"] is not None:
            parts.append(f"până {out['price_max']:,} €".replace(",", "."))
    out["title"] = ", ".join(parts) if parts else "Salvat din asistent"

    return out
