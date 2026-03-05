# FAQ în română pentru asistent. Întrebări prestabilite, răspunsuri ca chat. Fără AI.
# Structure: categories[] cu items: { q, a_html, tags }

KB_RO = {
    "categories": [
        {
            "id": "fisa",
            "title": "Fișă de vizionare",
            "items": [
                {
                    "q": "Cum creez o fișă de vizionare (chirie)?",
                    "a_html": "<p>Meniu → <strong>Chirie</strong> → completezi data/ora vizionare, tip imobil, adresă, comision → Previzualizare → Generezi PDF sau trimiți <strong>link de semnare</strong> către client.</p><p>Clientul deschide link-ul, completează datele și semnează. Nu e nevoie de aplicație.</p>",
                    "tags": "fisa chirie vizionare pdf link",
                },
                {
                    "q": "Cum creez o fișă de vizionare (vânzare)?",
                    "a_html": "<p>Meniu → <strong>Vânzare</strong> → același flux ca la chirie: completezi datele vizionării, previzualizare, apoi PDF sau link de semnare pentru client.</p>",
                    "tags": "fisa vanzare vizionare pdf",
                },
                {
                    "q": "Cum trimiți link de semnare la distanță (remote)?",
                    "a_html": "<p>În fișa de vizionare (chirie sau vânzare) apasă <strong>„Trimite link de semnare către client”</strong>. Aplicația generează un link unic.</p><p>Trimiți linkul pe WhatsApp sau email. Clientul deschide pe telefon, completează și semnează. După semnare poți descărca PDF-ul și vezi statusul în <strong>Lista Remote</strong> (din Meniu).</p>",
                    "tags": "remote link semnare whatsapp client",
                },
                {
                    "q": "Cum văd lista de fișe Remote (semnate la distanță)?",
                    "a_html": "<p>Meniu → <strong>Lista fișelor semnate de la distanță (Remote)</strong> — acolo vezi toate fișele pentru care ai generat link.</p><p>Status: nesemnată / semnată. După semnare poți descărca PDF-ul. Documentele se șterg automat după 3 zile.</p>",
                    "tags": "lista remote semnare status pdf",
                },
                {
                    "q": "Cum descarc PDF-ul după semnare?",
                    "a_html": "<p><strong>Pe loc:</strong> După ce semnați, butonul de descărcare PDF apare în aceeași pagină.</p><p><strong>Remote:</strong> Din Meniu → Lista Remote → la fișa semnată apare opțiunea de descărcare PDF. Fișa este disponibilă 3 zile; după aceea se șterge automat.</p>",
                    "tags": "pdf descarca download semnat",
                },
            ],
        },
        {
            "id": "todo",
            "title": "To-Do / Task-uri",
            "items": [
                {
                    "q": "Cum funcționează To-Do (lista de task-uri)?",
                    "a_html": "<p>Meniu → <strong>Task-uri</strong> (sau To-Do List). Aici îți poți nota vizionări, task-uri, notițe importante.</p><p>Poți adăuga task nou (titlu, termen limită), edita sau marca ca finalizat.</p>",
                    "tags": "todo task lista vizionari notite",
                },
            ],
        },
        {
            "id": "echipa",
            "title": "Echipă & Performanță",
            "items": [
                {
                    "q": "Cum funcționează Echipă & Performanță?",
                    "a_html": "<p><strong>Manager:</strong> Creezi echipa, adaugi agenți prin email. Agentul trebuie să confirme invitația din aplicație. Le dai task-uri, urmărești performanța (vizionări, deal-uri, sumă), vezi sumar lunar și rata de conversie.</p><p><strong>Agent:</strong> Confirmi invitația, completezi raport zilnic (vizionări, deal-uri, sumă), primești task-uri de la manager, poți ieși din echipă. Ai dashboard cu statistici tale.</p>",
                    "tags": "echipa performanta manager agent task raport",
                },
                {
                    "q": "Cum adaug un agent în echipă?",
                    "a_html": "<p>Meniu → Echipă & Performanță → Agenți → Adaugă agent. Introduci emailul. Agentul primește invitație și trebuie să confirme din aplicație (Echipă & Performanță) pentru a fi membru.</p>",
                    "tags": "echipa adauga agent invitatii",
                },
                {
                    "q": "Ce pot face ca agent în echipă?",
                    "a_html": "<p>Completezi raport zilnic (vizionări, deal-uri închise, sumă totală). Vezi task-urile de la manager și le marchezi ca finalizate. Poți vedea statisticile tale (azi, săptămână, lună, 3 luni). Poți ieși din echipă din dashboard.</p>",
                    "tags": "echipa agent raport task statistici",
                },
            ],
        },
        {
            "id": "marketplace",
            "title": "Marketplace cereri",
            "items": [
                {
                    "q": "Cum funcționează Marketplace-ul?",
                    "a_html": "<p>Marketplace-ul este dedicat agenților imobiliari: poți vedea <strong>cereri</strong> de cumpărare/închiriere postate de alți agenți.</p><p>Poți adăuga și tu cereri (zonă, buget, camere). Zona se selectează la fel de intuitiv ca în aplicație. Dacă apare o cerere potrivită, primești notificare în app. Cererile sunt valabile 30 de zile și se șterg automat; pot fi reactivate.</p>",
                    "tags": "marketplace cereri notificare zona buget",
                },
            ],
        },
        {
            "id": "acces",
            "title": "Acces / Abonament",
            "items": [
                {
                    "q": "Unde văd abonamentul și prețurile?",
                    "a_html": "<p>Pagina <strong>Plăți / Abonament</strong> (din meniu sau link din aplicație) îți arată opțiunile și prețurile.</p><p>Pentru activare contactează suportul tehnic (WhatsApp). Fără abonament/trial activ nu vei vedea date de contact pe cererile din Marketplace.</p>",
                    "tags": "abonament pret plati acces",
                },
            ],
        },
        {
            "id": "tehnic",
            "title": "Suport tehnic",
            "items": [
                {
                    "q": "Cum contactez suportul tehnic?",
                    "a_html": "<p>Suport tehnic: <strong>WhatsApp 40764381795</strong>.</p><p>Poți deschide direct WhatsApp din tab-ul „Tehnic” al asistentului sau copia un mesaj prestabilit.</p>",
                    "tags": "suport contact whatsapp tehnic",
                },
            ],
        },
    ],
}


def get_all_faq_items():
    """Flatten all FAQ items with category title for search."""
    out = []
    for cat in KB_RO.get("categories", []):
        for item in cat.get("items", []):
            out.append({
                "q": item.get("q", ""),
                "a_html": item.get("a_html", ""),
                "tags": item.get("tags", ""),
                "category": cat.get("title", ""),
            })
    return out


def search_faq(query: str):
    """Search in q, a_html, tags (case-insensitive)."""
    q = (query or "").strip().lower()
    if not q:
        return get_all_faq_items()
    out = []
    for item in get_all_faq_items():
        text = (item.get("q", "") + " " + item.get("a_html", "") + " " + item.get("tags", "")).lower()
        if q in text:
            out.append(item)
    return out
