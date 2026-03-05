# Internal knowledge base: predefined Q/A for Help Center. No AI.
# Structure: categories with id, title, items: [{q, a_html, tags, quick_actions}]
# quick_actions: [{type: "open_url", label, url}] or [{type: "copy_text", label, text}]

KB = {
    "categories": [
        {
            "id": "start",
            "title": "Începători / Start rapid",
            "items": [
                {
                    "q": "Cum funcționează aplicația?",
                    "a_html": "<p>Aplicația <strong>Fișa de vizionare</strong> este pentru agenți imobiliari. Oferă:</p><ul><li><strong>Fișe de vizionare</strong> (chirie / vânzare) – generezi PDF și trimiți link clienților pentru semnare</li><li><strong>Contract închiriere</strong> – generezi contract PDF</li><li><strong>Prestări servicii</strong> – documente PDF</li><li><strong>Marketplace</strong> – cereri de cumpărare/închiriere de la alți agenți</li><li><strong>To-Do</strong> – lista ta de taskuri</li></ul><p>Din <strong>Meniu</strong> accesezi toate modulele. Pentru a vedea date de contact pe cereri ai nevoie de <strong>acces activ</strong> (trial sau abonament).</p>",
                    "tags": "start incepatori overview meniu",
                    "quick_actions": [{"type": "open_url", "label": "Deschide Meniul", "url": "/menu/"}],
                },
                {
                    "q": "Cum mă loghez / îmi creez cont?",
                    "a_html": "<p>Pe pagina principală apasă <strong>Autentificare</strong> sau <strong>Înregistrare</strong>. La înregistrare completezi email și parolă. După login vei vedea meniul cu toate opțiunile.</p>",
                    "tags": "login cont inregistrare",
                    "quick_actions": [{"type": "open_url", "label": "Pagina principală", "url": "/"}],
                },
            ],
        },
        {
            "id": "fisa",
            "title": "Fișă de vizionare",
            "items": [
                {
                    "q": "Cum creez o fișă de vizionare?",
                    "a_html": "<p><strong>Chirie:</strong> Meniu → Chirie → completezi data/ora vizionare, tip imobil, adresă, comision → Previzualizare → Generezi PDF sau trimiți link client.</p><p><strong>Vânzare:</strong> Meniu → Vânzare → același flux.</p><p>Poți trimite un <strong>link de semnare la distanță</strong> – clientul deschide link-ul, completează datele și semnează.</p>",
                    "tags": "fisa vizionare chirie vanzare pdf",
                    "quick_actions": [
                        {"type": "open_url", "label": "Fișă chirie", "url": "/chirie/"},
                        {"type": "open_url", "label": "Fișă vânzare", "url": "/vanzare/"},
                    ],
                },
                {
                    "q": "Cum trimit fișa pe WhatsApp?",
                    "a_html": "<p>După ce generezi PDF sau link de semnare, poți copia link-ul și îl trimiți pe WhatsApp. Alternativ, folosește butonul de partajare din browser (Share) și alege WhatsApp.</p>",
                    "tags": "whatsapp trimite partajare",
                },
                {
                    "q": "Ce este semnarea la distanță?",
                    "a_html": "<p>Generezi un <strong>link unic</strong> pentru client. Clientul deschide link-ul pe telefon/calculator, completează nume, telefon, date CI (opțional) și semnează cu degetul sau mouse-ul. Semnătura este salvată și PDF-ul final este generat. Nu e nevoie de aplicație – funcționează în browser.</p>",
                    "tags": "semnare distanta link client",
                },
            ],
        },
        {
            "id": "contract",
            "title": "Contract închiriere",
            "items": [
                {
                    "q": "Cum generez contractul de închiriere?",
                    "a_html": "<p>Meniu → <strong>Contract închiriere</strong> → completezi formularul cu datele părților, imobil, sume, termen → Previzualizare → Descărci PDF.</p><p>Asigură-te că ai completat <strong>Profil agent</strong> (semnătură, date agenție) ca să apară corect în document.</p>",
                    "tags": "contract inchiriere pdf",
                    "quick_actions": [
                        {"type": "open_url", "label": "Contract închiriere", "url": "/contract-inchiriere/"},
                        {"type": "open_url", "label": "Profil agent", "url": "/menu/"},
                    ],
                },
            ],
        },
        {
            "id": "prestari",
            "title": "Prestări servicii",
            "items": [
                {
                    "q": "Cum folosesc Prestări servicii?",
                    "a_html": "<p>Meniu → <strong>Prestări servicii</strong> → completezi datele pentru documentul de prestări servicii → previzualizare și descărcare PDF. Folosești modulul pentru acte/adrese legate de prestări de servicii oferite de agenție.</p>",
                    "tags": "prestari servicii pdf",
                    "quick_actions": [{"type": "open_url", "label": "Prestări servicii", "url": "/prestari-servicii/"}],
                },
            ],
        },
        {
            "id": "marketplace",
            "title": "Marketplace cereri",
            "items": [
                {
                    "q": "Cum folosesc marketplace-ul?",
                    "a_html": "<p>Meniu → <strong>Marketplace</strong>. Vezi lista de cereri (cumpărare/închiriere) cu zone, buget, camere. Poți filtra după zonă, buget, camere, tip. Deschizi o cerere pentru detalii; dacă ai <strong>acces activ</strong>, vezi și datele de contact (telefon).</p><p>Poți și <strong>adauga cerere</strong> dacă ai un client care caută – limita este 10 cereri per 30 zile.</p>",
                    "tags": "marketplace cereri filtre",
                    "quick_actions": [{"type": "open_url", "label": "Marketplace", "url": "/marketplace/"}],
                },
                {
                    "q": "Cum adaug o cerere nouă?",
                    "a_html": "<p>Marketplace → buton <strong>Adaugă cerere</strong> → alege tip (Cumpărare/Închiriere), tip imobil (apartament/casă/teren), selectează <strong>cel puțin o zonă</strong>, buget min/max (opțional), camere, descriere. La salvare cererea apare în listă pentru alți agenți.</p>",
                    "tags": "adaug cerere noua",
                    "quick_actions": [{"type": "open_url", "label": "Adaugă cerere", "url": "/marketplace/new"}],
                },
                {
                    "q": "Ce sunt alarmele pentru cereri?",
                    "a_html": "<p>În asistent, tab <strong>Alarme</strong> poți seta criterii (zone, buget, camere). Când apar cereri noi care se potrivesc, vei vedea un badge „X potriviri” pe Marketplace. Alarme se creează doar din acel tab, nu din chat.</p>",
                    "tags": "alarme cereri notificare",
                },
            ],
        },
        {
            "id": "todo",
            "title": "TODO / Task-uri",
            "items": [
                {
                    "q": "Cum folosesc lista de taskuri?",
                    "a_html": "<p>Meniu → <strong>To-Do</strong>. Vezi taskurile tale, le filtrezi după status (deschis/în lucru/finalizat), prioritate sau dată. Poți adăuga task nou (titlu, descriere, termen limită, prioritate). Taskurile finalizate sunt șterse automat după 30 zile.</p>",
                    "tags": "todo taskuri sarcini",
                    "quick_actions": [
                        {"type": "open_url", "label": "Vezi taskuri", "url": "/todo/"},
                        {"type": "open_url", "label": "Adaugă task", "url": "/todo/new"},
                    ],
                },
                {
                    "q": "Cum adaug un task rapid?",
                    "a_html": "<p>To-Do → <strong>Adaugă task</strong> (sau din asistent tab Task-uri → buton Adaugă task). Completezi titlul (obligatoriu), opțional descriere, data limită, prioritate. La salvare taskul apare în listă.</p>",
                    "tags": "adaug task rapid",
                    "quick_actions": [{"type": "open_url", "label": "Adaugă task", "url": "/todo/new"}],
                },
            ],
        },
        {
            "id": "profil",
            "title": "Profil / Abonament / Acces",
            "items": [
                {
                    "q": "Cum activez abonamentul / accesul?",
                    "a_html": "<p>Accesul (trial sau abonament plătit) îți permite să vezi <strong>datele de contact</strong> pe cererile din marketplace. În <strong>Meniu</strong> vezi statusul: câte zile îți mai rămân, până când e valabil. Pentru activare sau prelungire folosești link-ul <strong>WhatsApp</strong> din meniu – echipa te va ghida.</p>",
                    "tags": "abonament acces trial activare",
                    "quick_actions": [{"type": "open_url", "label": "Meniul (status acces)", "url": "/menu/"}],
                },
                {
                    "q": "De ce nu văd numerele de telefon pe cereri?",
                    "a_html": "<p>Numerele de telefon sunt afișate <strong>doar dacă ai acces activ</strong>. Verifică în Meniu dacă ai „Acces activ” și câte zile îți rămân. Dacă accesul a expirat, vei vedea doar cererea (zonă, buget, descriere), fără contact. Pentru reactivare: WhatsApp din meniu.</p>",
                    "tags": "telefon contact vizibilitate acces",
                },
                {
                    "q": "Cum completez profilul agent / agenție?",
                    "a_html": "<p>Meniu → <strong>Profil agent</strong> (sau link similar). Completezi numele agentului, semnătura (desenată sau încărcată), datele agenției (denumire, sediu, CUI, IBAN etc.). Aceste date apar în PDF-urile generate (fișe, contracte).</p>",
                    "tags": "profil agent semnatura agentie",
                    "quick_actions": [{"type": "open_url", "label": "Meniul", "url": "/menu/"}],
                },
            ],
        },
        {
            "id": "admin",
            "title": "Admin (doar local)",
            "items": [
                {
                    "q": "Cum accesez panoul admin?",
                    "a_html": "<p>Panoul admin este disponibil doar pentru utilizatori cu drepturi de administrator, de obicei în mediul local. Din meniu poți avea link către <strong>Admin</strong> dacă ești admin. Acolo se gestionează utilizatori, moderare cereri etc.</p>",
                    "tags": "admin panou",
                    "quick_actions": [{"type": "open_url", "label": "Meniul", "url": "/menu/"}],
                },
            ],
        },
        {
            "id": "probleme",
            "title": "Probleme comune",
            "items": [
                {
                    "q": "PDF-ul nu se generează / eroare la descărcare",
                    "a_html": "<p>Verifică că ai completat toate câmpurile obligatorii. Dacă eroarea persistă, încearcă alt browser sau șterge cache. Pentru semnare la distanță, asigură-te că link-ul nu a expirat. Contactează suportul tehnic dacă problema continuă.</p>",
                    "tags": "pdf eroare descarcare",
                },
                {
                    "q": "Semnătura nu apare în document",
                    "a_html": "<p>Completează <strong>Profil agent</strong> cu semnătura (desenată în aplicație sau încărcată). Semnătura trebuie salvată înainte de a genera documentul. La documente remote, semnătura vizitatorului se adaugă când clientul completează formularul de semnare.</p>",
                    "tags": "semnatura profil document",
                },
                {
                    "q": "Am uitat parola",
                    "a_html": "<p>Pe pagina de login ar trebui să existe opțiune „Ai uitat parola?” sau similar – vei primi un link pe email pentru resetare. Dacă nu există, contactează suportul tehnic pe WhatsApp.</p>",
                    "tags": "parola reset",
                },
            ],
        },
    ],
}

# Flatten all items with category_id for search
def get_all_items():
    items = []
    for cat in KB["categories"]:
        for item in cat["items"]:
            items.append({**item, "category_id": cat["id"], "category_title": cat["title"]})
    return items


def search_items(query: str):
    """Client-side or server-side: filter items by query in q, tags, or a_html (strip tags)."""
    q = (query or "").strip().lower()
    if not q:
        return get_all_items()
    import re
    out = []
    for item in get_all_items():
        text = (item.get("q") or "") + " " + (item.get("tags") or "") + " " + re.sub(r"<[^>]+>", " ", item.get("a_html") or "")
        if q in text.lower():
            out.append(item)
    return out
