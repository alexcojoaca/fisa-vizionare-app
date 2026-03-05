# Conținut pentru Asistent: ghiduri pagină + FAQ. Un singur loc (dict), fără AI.
# PAGE_GUIDES[page_id] = { "name", "intro", "bullets", "tip" }
# FAQ = listă de { "q", "a" } cu search pe q.

# Prețuri abonament (folosite în FAQ și răspunsuri)
PRICING = {
    "lunar_ron": 25,
    "lunar_eur": 4.90,
    "3luni_ron": 67,
    "3luni_eur": 13.50,
    "6luni_ron": 120,
    "6luni_eur": 24,
}

PAGE_GUIDES = {
    "home": {
        "name": "Pagina principală",
        "intro": "Bine ai venit! De aici poți ajunge rapid la tot ce îți oferă aplicația: fișe de vizionare, contracte, Marketplace și lista de task-uri.",
        "bullets": [
            "Fișe de vizionare – pentru chirie sau vânzare, cu semnare pe loc sau prin link trimis clientului",
            "Contracte și documente – închiriere, prestări servicii",
            "Marketplace – cereri și anunțuri între agenți",
            "To-Do – îți organizezi vizionările și task-urile",
        ],
        "tip": "Meniul din colțul dreapta sus îți arată toate opțiunile.",
    },
    "about": {
        "name": "Despre aplicație",
        "intro": "Aici găsești informații despre aplicație și cum te ajută în munca de agent imobiliar.",
        "bullets": [
            "Citești ce poate face aplicația și ce beneficii ai",
            "Poți reveni oricând la meniu sau la pagina principală",
        ],
        "tip": "Pentru răspunsuri la întrebări frecvente, deschide tab-ul „Întreabă” din asistent.",
    },
    "menu": {
        "name": "Meniu principal",
        "intro": "Din meniu îți completezi datele de agent și ale agenției – astfel se completează automat în fișe și contracte.",
        "bullets": [
            "Date agent și agenție – apar automat în documente (fișe de vizionare)",
            "Lista fișelor semnate de la distanță (Remote) – vezi dacă clienți tăi au semnat",
            "Opțiune de deconectare",
        ],
        "tip": "Completează odată profilul – nu mai completezi manual pe fiecare document.",
    },
    "marketplace_list": {
        "name": "Lista cereri",
        "intro": "Aici vezi cererile postate de alți agenți: cine caută să cumpere sau să închirieze. Poți filtra după zonă, buget sau număr de camere.",
        "bullets": [
            "Filtrezi după zonă, buget, camere sau tip (cumpărare/închiriere)",
            "Adaugi cerere nouă cu butonul „Adaugă cerere”",
         
        ],
        "tip": "În asistent, la „Alerte cereri”, poți primi notificări pentru criterii alese.",
    },
    "marketplace_detail": {
        "name": "Detalii cerere",
        "intro": "Vezi toate detaliile cererii: zone, buget, camere, descriere. Cu abonament activ vezi și cum poți contacta agentul.",
        "bullets": [
            "Citești descrierea completă a cererii",
            "Cu abonament – vezi date de contact pentru colaborare",
            "Poți reveni la listă sau la Marketplace",
        ],
        "tip": "Cererile sunt valabile 30 zile; după aceea dispar din listă.",
    },
    "marketplace_form_new": {
        "name": "Cerere nouă",
        "intro": "Adaugi o cerere: tip (cumpărare sau închiriere), zone, buget, camere și o scurtă descriere. Alți agenți vor vedea cererea în listă.",
        "bullets": [
            "Alegi tip cerere și tip imobil",
            "Completezi zone (cel puțin una), buget (opțional), camere",
            "Salvezi – cererea este vizibilă 30 zile",
        ],
        "tip": "Ai un număr limitat de cereri pe 30 zile; pentru mai multe, contactează suportul.",
    },
    "marketplace_form_edit": {
        "name": "Editează cererea",
        "intro": "Aici poți modifica cererea ta: zone, buget, camere sau descrierea. Schimbă ce ai nevoie și salvează.",
        "bullets": [
            "Modifici zonele, bugetul, numărul de camere sau textul",
            "Apeși Salvează și cererea se actualizează",
        ],
        "tip": "Cererea rămâne vizibilă 30 zile; perioada nu se schimbă după editare.",
    },
    "marketplace_hub": {
        "name": "Marketplace",
        "intro": "Aici alegi ce vrei să faci: să vezi cererile altor agenți (caută cumpărători/închiriasi) sau anunțurile cu imobile (oferte de vânzare/închiriere).",
        "bullets": [
            "Cereri – când cauți sau pui tu cereri (cumpărător/închirias caută)",
            "Anunțuri – când cauți sau pui tu anunțuri (agentul oferă imobil)",
            "Din acest ecran ajungi rapid la ambele liste",
        ],
        "tip": "Pentru cereri și oferte ale tale, folosește „Profilul meu” sau „Anunțurile mele” / „Cererile mele”.",
    },
    "marketplace_offers_list": {
        "name": "Lista anunțuri (oferte)",
        "intro": "Aici vezi toate anunțurile: imobile puse la dispoziție de alți agenți. Poți filtra după zonă, preț sau tip.",
        "bullets": [
            "Vezi anunțurile de vânzare sau închiriere",
            "Filtrezi după zonă, preț, camere",
            "Adaugi anunț nou cu butonul „Adaugă anunț”",
        ],
        "tip": "Cu abonament activ vezi și datele de contact ale agentului care a postat anunțul.",
    },
    "marketplace_offer_detail": {
        "name": "Detalii anunț",
        "intro": "Aici vezi toate detaliile anunțului: zonă, preț, descriere. Dacă ai abonament, vezi și cum poți contacta agentul.",
        "bullets": [
            "Citești descrierea completă a imobilului",
            "Cu abonament activ vezi telefon/contact pentru colaborare",
            "Poți reveni la listă sau la Marketplace",
        ],
        "tip": "Anunțurile sunt valabile 30 zile; după aceea dispar din listă și trebuiesc actualizate.",
    },
    "marketplace_form_new_offer": {
        "name": "Anunț nou",
        "intro": "Adaugi un anunț de imobil (vânzare sau închiriere). Completezi zona, prețul, descrierea – și anunțul apare pentru alți agenți.",
        "bullets": [
            "Alegi tip: vânzare sau închiriere și tip imobil",
            "Completezi zone, preț, camere, descriere",
            "Salvezi – anunțul este vizibil 30 zile",
        ],
        "tip": "Ai un număr limitat de anunțuri pe 30 zile; pentru mai multe, contactează suportul.",
    },
    "marketplace_form_edit_offer": {
        "name": "Editează anunțul",
        "intro": "Modifici anunțul tău: preț, zonă, descriere sau alte detalii. Salvezi și modificările apar imediat.",
        "bullets": [
            "Schimbi ce vrei: preț, zone, descriere etc.",
            "Apeși Salvează",
        ],
        "tip": "După editare, anunțul rămâne vizibil conform celor 30 zile.",
    },
    "marketplace_profile": {
        "name": "Profilul meu (Marketplace)",
        "intro": "Aici vezi cererile și anunțurile tale: ce ai postat tu. Poți edita, șterge sau adăuga altele noi.",
        "bullets": [
            "Vezi cererile tale și anunțurile tale",
            "Editezi sau ștergi oricare",
            "Adaugi cerere nouă sau anunț nou",
        ],
        "tip": "Sloturile (câte cereri/anunțuri ai) se eliberează când ștergi sau când expiră după 30 zile.",
    },
    "marketplace_my_offers": {
        "name": "Anunțurile mele",
        "intro": "Lista anunțurilor pe care le-ai postat tu. Poți vedea, edita sau șterge fiecare anunț.",
        "bullets": [
            "Vezi toate anunțurile tale active",
            "Deschizi un anunț pentru detalii sau editare",
            "Poți adăuga anunț nou",
        ],
        "tip": "Când ștergi un anunț, slotul devine liber și poți pune altul.",
    },
    "marketplace_my_requests": {
        "name": "Cererile mele",
        "intro": "Aici sunt cererile pe care le-ai adăugat tu (caută cumpărător/închirias). Le poți edita sau șterge.",
        "bullets": [
            "Vezi toate cererile tale",
            "Editezi sau ștergi oricare cerere",
            "Adaugi cerere nouă dacă ai sloturi libere",
        ],
        "tip": "Fiecare cerere ocupă un slot; după 30 zile expiră și slotul se eliberează.",
    },
    "fisa_chirie": {
        "name": "Fișă vizionare chirie",
        "intro": "Completezi data și ora vizionării, tip imobil, adresă și comision. Apoi poți genera PDF sau trimite clientului un link pentru semnare la distanță.",
        "bullets": [
            "Completezi datele vizionării și comisionul",
            "Previzualizezi documentul înainte de semnare",
            "Semnare pe loc sau „Trimite link de semnare” – clientul semnează de pe telefon",
        ],
        "tip": "Link-ul poate fi trimis pe WhatsApp; clientul semnează fără să aibă cont în aplicație.",
    },
    "fisa_vanzare": {
        "name": "Fișă vizionare vânzare",
        "intro": "La fel ca la chirie: completezi data, ora, adresă, comision. Apoi generezi PDF sau link de semnare pentru client.",
        "bullets": [
            "Completezi datele vizionării și comisionul",
            "Semnare pe loc – se generează PDF pe care îl descarci",
            "Sau trimiți link – clientul semnează de pe telefon",
        ],
        "tip": "Clientul poate semna ușor de pe telefon folosind link-ul trimis.",
    },
    "chirie_done": {
        "name": "Fișă chirie finalizată",
        "intro": "Fișa a fost generată cu succes. Poți descărca PDF-ul sau trimite link-ul clientului.",
        "bullets": [
            "Descărci PDF-ul sau trimiți link-ul clientului",
            "În meniu, la „Lista Remote”, vezi dacă clientul a semnat",
        ],
        "tip": "După semnarea la distanță, PDF-ul este disponibil 3 zile – descarcă-l în timp.",
    },
    "vanzare_done": {
        "name": "Fișă vânzare finalizată",
        "intro": "Fișa este gata. Poți descărca PDF-ul și să îl trimiți clientului (email, WhatsApp).",
        "bullets": [
            "Descărci PDF-ul",
            "Îl trimiți clientului pe email sau WhatsApp",
        ],
        "tip": "Documentele semnate la distanță se șterg automat după 3 zile – descarcă-le la timp.",
    },
    "remote_chirie": {
        "name": "Semnare la distanță (chirie)",
        "intro": "Completezi fișa și semnezi tu; aplicația creează un link unic. Îl trimiți clientului – el deschide pe telefon și semnează.",
        "bullets": [
            "Completezi datele vizionării și comisionul",
            "Semnezi tu ca agent",
            "Trimiți link-ul pe WhatsApp sau email",
            "Clientul semnează; statusul îl vezi în Lista Remote",
        ],
        "tip": "Link-ul se folosește o singură dată; e sigur și personal.",
    },
    "remote_vanzare": {
        "name": "Semnare la distanță (vânzare)",
        "intro": "Același mod: completezi, semnezi tu, trimiți link-ul; clientul semnează de pe telefon.",
        "bullets": [
            "Completezi și semnezi ca agent",
            "Trimiți link-ul; clientul semnează",
            "PDF-ul apare în Lista Remote după semnare",
        ],
        "tip": "Documentul poate fi descărcat 3 zile după semnare.",
    },
    "remote_list": {
        "name": "Lista fișe Remote",
        "intro": "Aici vezi toate fișele pentru care ai dat link de semnare la distanță: care sunt semnate și care nu.",
        "bullets": [
            "Vezi statusul: nesemnată sau semnată",
            "După semnare descarci PDF-ul",
            "Documentele dispar automat după 3 zile",
        ],
        "tip": "Descarcă PDF-urile semnate înainte să expire termenul de 3 zile.",
    },
    "contract_inchiriere": {
        "name": "Contract închiriere",
        "intro": "Generezi un contract standard de închiriere. Completezi datele părților, imobilul, sumele și termenul – și obții un PDF gata de folosit.",
        "bullets": [
            "Completezi formularul: părți, imobil, sume, termen",
            "Previzualizezi și descarci PDF-ul",
            "Poți semna sau printa – ai un draft clar și complet",
        ],
        "tip": "Datele din profilul agent se completează automat în contract.",
    },
    "contract_done": {
        "name": "Contract generat",
        "intro": "Contractul a fost generat. Îl poți descărca în PDF sau tipări.",
        "bullets": [
            "Descărci PDF-ul",
            "Poți crea un nou contract din meniu",
        ],
        "tip": "Salvează o copie la tine pentru arhivă.",
    },
    "prestari_servicii": {
        "name": "Prestări servicii",
        "intro": "Generezi documente PDF pentru acorduri de prestări servicii între tine și client (beneficiar).",
        "bullets": [
            "Completezi datele necesare pentru document",
            "Previzualizezi și descarci PDF-ul",
        ],
        "tip": "Folosește acest modul când închei acorduri de prestări servicii cu clienții.",
    },
    "prestari_done": {
        "name": "Prestări servicii finalizate",
        "intro": "Documentul a fost generat. Îl poți descărca și păstra pentru evidență.",
        "bullets": [
            "Descărci PDF-ul",
            "Poți genera un nou document din meniu",
        ],
        "tip": "Păstrează o copie pentru dosar.",
    },
    "todo": {
        "name": "Lista task-uri (To-Do)",
        "intro": "Aici îți organizezi vizionările și task-urile: ce e restant, ce e azi, ce e în viitor. Poți adăuga, edita sau marca ca făcut.",
        "bullets": [
            "Vezi task-urile grupate: restante, azi, viitor",
            "Adaugi task nou: titlu, termen, prioritate",
            "Editezi sau marchezi ca finalizat",
            "Pentru alerte la o oră exactă folosește „Amintește-mi” din asistent",
        ],
        "tip": "„Amintește-mi” îți trimite o notificare la data și ora pe care le alegi.",
    },
    "todo_form": {
        "name": "Task nou sau editare",
        "intro": "Adaugi un task nou sau modifici unul existent: titlu, termen limită, prioritate.",
        "bullets": [
            "Completezi titlul și data limită",
            "Poți seta prioritatea (scăzută, medie, mare)",
            "Salvezi – task-ul apare în listă",
        ],
        "tip": "Pentru o alertă la o oră exactă, folosește tab-ul „Amintește-mi” din asistent.",
    },
    "payments": {
        "name": "Plăți / Abonament",
        "intro": "Vezi prețurile abonamentului și cum îl poți activa. Pentru activare contactează suportul pe WhatsApp.",
        "bullets": [
            "1 lună: 25 RON / 4,90 €",
            "3 luni: 67 RON / 13,50 €",
            "6 luni: 120 RON / 24 €",
            "Contactează suportul pentru activare",
        ],
        "tip": "Fără abonament activ nu vei vedea datele de contact pe cererile și anunțurile din Marketplace.",
    },
    "account_profile": {
        "name": "Profil / Cont",
        "intro": "Datele tale (nume, firmă, IBAN etc.) apar automat în fișe și contracte. Aici le completezi și îți poți schimba parola.",
        "bullets": [
            "Completezi nume, firmă, IBAN – se completează singur în documente",
            "Schimbi emailul sau parola din setări cont",
        ],
        "tip": "Completează odată profilul – nu mai completezi manual pe fiecare document.",
    },
    "agency_profile": {
        "name": "Profil agenție",
        "intro": "Datele agenției tale. Se completează automat în documente unde e nevoie.",
        "bullets": [
            "Completezi datele agenției",
            "Acestea apar în fișe și contracte unde e cazul",
        ],
        "tip": "Le găsești și în meniu, la Date agent / agenție.",
    },
    "terms": {
        "name": "Termeni și condiții",
        "intro": "Termenii și condițiile de utilizare ale aplicației.",
        "bullets": [
            "Citești termenii de utilizare",
            "Poți reveni la acasă sau la meniu",
        ],
        "tip": "Pentru întrebări folosește tab-ul „Întreabă” din asistent.",
    },
    "privacy": {
        "name": "Confidențialitate",
        "intro": "Cum tratăm datele tale și ce drepturi ai (politica de confidențialitate).",
        "bullets": [
            "Informații despre datele prelucrate",
            "Poți reveni la meniu sau la pagina principală",
        ],
        "tip": "Pentru orice nelămurire, contactează suportul.",
    },
    "team": {
        "name": "Echipă & Performanță",
        "intro": "Modul pentru echipe: manager și agenți. Creezi echipa, adaugi agenți, dai task-uri și urmărești performanța.",
        "bullets": [
            "Manager: dashboard cu statistici, agenți, task-uri, sumar lunar",
            "Agent: raport zilnic, task-uri de la manager, statistici personale",
        ],
        "tip": "Din acest ecran accesezi dashboard-ul sau lista de agenți.",
    },
    "team_dashboard": {
        "name": "Dashboard Echipă",
        "intro": "Aici vezi rata de conversie și deal-uri închise. Apasă „Vezi mai multe” pentru statistici detaliate.",
        "bullets": [
            "Rata conversie și deal-uri în ultima săptămână",
            "Sumar lunar cu vizionări, deal-uri, sumă per lună",
            "Butonul Acasă te duce înapoi la pagina principală",
        ],
        "tip": "Poți șterge echipa din partea de jos dacă nu mai ai nevoie de ea.",
    },
    "team_agents": {
        "name": "Agenții echipei",
        "intro": "Lista agenților. Apasă pe un agent pentru detalii. Adaugi agenți prin email; ei trebuie să confirme invitația.",
        "bullets": [
            "Fiecare rând: nume, vizionări azi, deal-uri, sumă 30 zile, task-uri open",
            "Apasă pe un agent pentru a vedea detalii complete",
        ],
        "tip": "Poți șterge un agent din pagina de detalii.",
    },
    "team_agent_detail": {
        "name": "Detalii agent",
        "intro": "Statistici complete ale agentului: vizionări, deal-uri, sumă, istoric și task-uri.",
        "bullets": [
            "Vezi performanța pe 7 și 30 zile",
            "Istoric rapoarte zilnice și task-uri primite",
            "Butonul Șterge agent îl elimină din echipă",
        ],
        "tip": None,
    },
    "team_agent_dashboard": {
        "name": "Echipa mea (Agent)",
        "intro": "Raport zilnic: vizionări, deal-uri, sumă totală. Task-uri de la manager.",
        "bullets": [
            "Completezi „Ce ai făcut azi?” și salvezi",
            "Apasă „Vezi statistica ta” pentru statistici personale",
            "Primești task-uri de la manager, le marchezi ca finalizate",
            "Poți ieși din echipă din acest ecran",
        ],
        "tip": "Task-urile noi apar cu badge; apasă „Am văzut” când le-ai citit.",
    },
    "team_tasks": {
        "name": "Task-uri echipă",
        "intro": "Task-urile pe care le-ai dat agenților. Fiecare arată pentru cine e (toți sau nume).",
        "bullets": [
            "Adaugă task nou și alege agenții",
            "Task-urile mai vechi de 7 zile se șterg prin Curățare DB",
        ],
        "tip": None,
    },
    "team_create": {
        "name": "Creează echipă",
        "intro": "Aici creezi echipa ta. Introduce un nume și vei deveni manager.",
        "bullets": [
            "După creare vei putea adăuga agenți și să le dai task-uri",
        ],
        "tip": None,
    },
    "team_invitation": {
        "name": "Invitație în echipă",
        "intro": "Ai fost invitat într-o echipă. Acceptă pentru a primi task-uri și a raporta activitatea.",
        "bullets": [
            "Accept: devii membru și ai acces la dashboard",
            "Refuz: invitația dispare",
        ],
        "tip": None,
    },
    "generic": {
        "name": "Această pagină",
        "intro": "Poți explora meniul și toate modulele aplicației. Asistentul te ajută cu explicații pe înțelesul tuturor.",
        "bullets": [
            "Meniul principal îți arată toate opțiunile",
            "În asistent găsești ghiduri simple și răspunsuri la întrebări frecvente",
        ],
        "tip": "Folosește tab-urile din asistent: Ghid pagină, Întreabă.",
    },
}


def get_page_guide(page_id: str) -> dict:
    """Returnează ghidul pentru page_id; fallback la generic."""
    if not page_id or page_id == "unknown":
        page_id = "generic"
    return PAGE_GUIDES.get(page_id) or PAGE_GUIDES["generic"]


# FAQ: răspunsuri simple, ușor de înțeles de toată lumea. Fiecare: { "q", "a", "tags" }.
FAQ_ITEMS = [
    {
        "q": "Ce este aplicația și la ce ajută?",
        "a": "Aplicația te ajută să creezi rapid fișe de vizionare (chirie sau vânzare), contracte de închiriere și documente de prestări servicii. Poți trimite clienților un link pentru semnare de pe telefon, fără cont. Are și Marketplace pentru colaborare între agenți și o listă de task-uri (To-Do). E făcută pentru agenții imobiliari.",
        "tags": "aplicatie fisa vizionare agent",
    },
    {
        "q": "Cum creez o fișă de vizionare pentru chirie?",
        "a": "Meniul principal → Chirie. Completezi data și ora vizionării, tip imobil, adresă, comision. Apoi previzualizezi documentul și alegi: fie generezi PDF, fie apeși „Trimite link de semnare” și trimiți link-ul clientului pentru semnare la distanță.",
        "tags": "fisa chirie vizionare pdf",
    },
    {
        "q": "Cum creez o fișă de vizionare pentru vânzare?",
        "a": "Meniul principal → Vânzare. E la fel ca la chirie: completezi datele vizionării, previzualizezi, apoi PDF sau link de semnare pentru client.",
        "tags": "fisa vanzare vizionare pdf",
    },
    {
        "q": "Cum funcționează semnarea la distanță (Remote)?",
        "a": "În fișa de vizionare (chirie sau vânzare) apeși „Trimite link de semnare către client”. Completezi și semnezi tu; aplicația creează un link unic. Îl trimiți pe WhatsApp sau email. Clientul deschide pe telefon, completează și semnează – fără cont. După semnare vezi statusul în Meniu → Lista fișelor semnate de la distanță (Remote) și poți descărca PDF-ul. Documentul poate fi descărcat 3 zile.",
        "tags": "remote link semnare whatsapp client",
    },
    {
        "q": "Unde văd fișele semnate și statusurile?",
        "a": "Meniul principal → Lista fișelor semnate de la distanță (Remote). Acolo vezi toate fișele pentru care ai dat link: care sunt semnate și care nu. După ce clientul semnează, descarci PDF-ul. Documentele dispar automat după 3 zile – descarcă-le la timp.",
        "tags": "lista remote status pdf descarca",
    },
    {
        "q": "Cum generez contractul de închiriere?",
        "a": "Meniul principal → Contract închiriere. Completezi datele părților, imobilul, sumele, termenul. Dacă ai completat profilul agent (din Meniu), datele apar deja în document. Apoi previzualizezi și descarci PDF-ul.",
        "tags": "contract inchiriere pdf descarca",
    },
    {
        "q": "Prestări servicii – ce e și când îl folosesc?",
        "a": "E pentru documente PDF de prestări servicii între tine și client. Îl folosești când închei astfel de acorduri. Completezi datele, previzualizezi și descarci PDF-ul.",
        "tags": "prestari servicii document pdf",
    },
    {
        "q": "Cum adaug un task sau o vizionare în To-Do?",
        "a": "Meniul principal → Task-uri (To-Do). Acolo adaugi task nou: titlu, termen, prioritate. Pentru o alertă la o oră exactă (ex: „Amintește-mi mâine la 10”) folosește tab-ul „Amintește-mi” din asistent – primești notificare la momentul ales.",
        "tags": "todo task vizionare notita reminder",
    },
    {
        "q": "Cum caut cereri în Marketplace?",
        "a": "Marketplace → Cereri (sau din meniu). Vezi lista de cereri; poți filtra după zonă, buget, camere, tip (cumpărare/închiriere). Butonul „Filtre” îți arată toate opțiunile.",
        "tags": "marketplace cereri caut filtre",
    },
    {
        "q": "Cum adaug o cerere în Marketplace?",
        "a": "Pe pagina de cereri → buton „Adaugă cerere”. Completezi tip (cumpărare/închiriere), tip imobil, zone (cel puțin una), buget (opțional), camere și descriere. Salvezi – cererea e vizibilă 30 zile. Ai un număr limitat de cereri pe 30 zile; pentru mai multe, contactează suportul.",
        "tags": "marketplace adaug cerere",
    },
    {
        "q": "Ce sunt anunțurile (ofertele) din Marketplace?",
        "a": "Sunt imobile puse la dispoziție de agenți: de vânzare sau de închiriere. Tu poți căuta anunțuri potrivite sau poți pune tu anunțuri. Marketplace → Anunțuri. Cu abonament activ vezi și datele de contact ale agentului.",
        "tags": "marketplace anunturi oferte",
    },
    {
        "q": "Cât durează cererile și anunțurile?",
        "a": "Atât cererile cât și anunțurile sunt valabile 30 zile de la postare. După 30 zile dispar din listă. Poți adăuga din nou dacă ai nevoie. Limita de cereri/anunțuri pe 30 zile se aplică per cont.",
        "tags": "marketplace expirare 30 zile",
    },
    {
        "q": "Care sunt prețurile abonamentului?",
        "a": "lunar: 12 €  \nO dată la 3 luni: 30 €\nO data la 6 luni: 54 €\n\nApasă butonul de mai jos pentru a contacta suportul și a activa abonamentul.",
        "tags": "abonament pret plati",
    },
    {
        "q": "Cum activez abonamentul?",
        "a": "Apasă butonul de mai jos – te redirecționează direct pe WhatsApp la suport. Te ghidează pas cu pas pentru activare.",
        "tags": "abonament activare",
    },
    {
        "q": "Cum contactez suportul?",
        "a": "Apasă butonul de mai jos – se deschide direct chat-ul pe WhatsApp cu suportul.",
        "tags": "suport contact whatsapp tehnic",
    },
]


def get_faq_items(search_query: str = ""):
    """Returnează lista de FAQ; dacă search_query e dat, filtrează după q și tags (case-insensitive)."""
    q = (search_query or "").strip().lower()
    if not q:
        return list(FAQ_ITEMS)
    out = []
    for item in FAQ_ITEMS:
        if q in item["q"].lower() or q in (item.get("tags") or "").lower():
            out.append(item)
        elif any(q in word for word in item["q"].lower().split()):
            out.append(item)
    return out
