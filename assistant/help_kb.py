# Help knowledge base: keyword lists -> step-by-step answers (Romanian).
# No AI; deterministic keyword matching.

HELP_KB = [
    {
        "keywords": ["marketplace", "market", "cereri", "cerere", "cum folosesc", "cum functioneaza", "lista cereri"],
        "title": "Cum folosesc marketplace-ul?",
        "steps": [
            "Deschide **Marketplace** din meniu (sau din pagina principală).",
            "Vei vedea lista de cereri: cumpărare sau închiriere, cu zone, buget și descriere.",
            "Folosește **Filtre** pentru zonă, buget, camere sau tip cerere.",
            "Poți **Adăuga cerere** dacă ai un client care caută (buget, zone, camere).",
            "Deschide o cerere pentru detalii. Dacă ai acces activ, vei vedea datele de contact.",
        ],
    },
    {
        "keywords": ["creez cerere", "adaug cerere", "cum adaug", "cerere noua", "noua cerere"],
        "title": "Cum creez o cerere?",
        "steps": [
            "Mergi la **Marketplace** → butonul **Adaugă cerere**.",
            "Alege tipul: **Cumpărare** sau **Închiriere** și tipul imobilului (apartament, casă, teren).",
            "Selectează **cel puțin o zonă** (obligatoriu).",
            "Completează buget minim/maxim (opțional), număr camere, descriere.",
            "Dacă e urgent, bifează **Urgent**. Trimite formularul.",
        ],
    },
    {
        "keywords": ["acces", "accesul", "trial", "abonament", "nu vad", "expirat", "zile ramase"],
        "title": "Cum funcționează accesul?",
        "steps": [
            "Accesul îți permite să vezi **datele de contact** (telefon, etc.) pe cererile din marketplace.",
            "Poți avea **trial** (perioadă limitată) sau **abonament plătit**.",
            "În **Meniu** vezi câte zile îți mai rămân și până când e valabil accesul.",
            "Dacă nu vezi numerele de telefon, probabil accesul a expirat sau nu e activ.",
            "Pentru reactivare sau extindere, folosește link-ul WhatsApp din meniu.",
        ],
    },
    {
        "keywords": ["telefon", "numere", "contact", "nu vad telefon", "date contact"],
        "title": "De ce nu văd numerele de telefon?",
        "steps": [
            "Numerele de telefon (și alte date de contact) sunt afișate **doar dacă ai acces activ**.",
            "Verifică în **Meniu** dacă ai „Acces activ” și câte zile îți mai rămân.",
            "Dacă accesul a expirat, vei vedea doar cererea (zonă, buget, descriere), fără contact.",
            "Pentru a reactiva accesul, folosește butonul **WhatsApp** din meniu și solicită reactivarea.",
        ],
    },
    {
        "keywords": ["todo", "task", "sarcini", "lista sarcini", "cum folosesc todo"],
        "title": "Cum folosesc lista de sarcini (To-Do)?",
        "steps": [
            "Din meniu alege **To-Do** (sau **Sarcini**).",
            "Poți **adauga** sarcini noi: titlu, descriere, termen limită, prioritate.",
            "Poți marca sarcini ca **În desfășurare** sau **Finalizat**.",
            "Lista este doar a ta; nimeni altcineva nu o vede.",
        ],
    },
    {
        "keywords": ["fisa", "vizionare", "pdf", "chirie", "vanzare", "contract"],
        "title": "Fișe și documente",
        "steps": [
            "Din meniu poți accesa **Chirie**, **Vânzare**, **Contract închiriere**, **Prestări servicii**.",
            "Completezi formularele și generezi **PDF** pentru vizionări sau contracte.",
            "Poți trimite link-uri clienților pentru semnare la distanță.",
            "Pentru semnături și date agent, completează **Profil agent** din meniu.",
        ],
    },
]

FALLBACK_MESSAGE = (
    "Nu am găsit exact răspunsul, dar pot să te ajut cu: **Marketplace**, **Cereri**, **Acces**, **Admin**."
    " Scrie ce te interesează (ex: „Cum folosesc marketplace-ul?”) sau apasă „Ce pot face?”."
)


def find_help_answer(text: str) -> tuple[str | None, list[str] | None]:
    """
    Match user text against HELP_KB. Return (title, steps) or (None, None).
    """
    if not text or not isinstance(text, str):
        return None, None
    t = text.strip().lower()
    if not t:
        return None, None
    for entry in HELP_KB:
        for kw in entry["keywords"]:
            if kw in t:
                return entry["title"], entry["steps"]
    return None, None
