# Fișă de Vizionare – Aplicație pentru agenți imobiliari

Aplicația **Fișă de Vizionare** este o platformă web pentru agenți imobiliari, care centralizează documente de vizionare, contracte, prestații de servicii, un marketplace între agenți, task-uri (To-Do) și un asistent contextual. Toate utilizatorii sunt tratați ca **agenți**; funcționalitățile sunt adaptate pentru documente profesionale și colaborare între agenți.

---

## Ce face aplicația

- **Fișe de vizionare** (chirie și vânzare) – completare date, generare PDF, trimitere link către client pentru semnare la distanță.  
- **Contract de închiriere** – generare contract și PDF.  
- **Prestații de servicii** – formular și documente pentru tranzacții imobiliare (comision, contract etc.).  
- **Marketplace** – cereri și anunțuri între agenți (cumpărare/închiriere, zone, buget, tip imobil), cu **potriviri automate** (posibile colaborări).  
- **To-Do** – task-uri personale (termen, prioritate, status), cu raport PDF.  
- **Asistent** – ghid pe pagină, FAQ, notificări (anunțuri admin, expirare abonament), **posibile colaborări** din marketplace și task-uri „Ce am de făcut azi”.  
- **Cont și acces** – abonament plătit sau acțiuni gratuite limitate (1x chirie, 1x vânzare); suport WhatsApp pentru activare/prelungire.

---

## Sisteme și module

### 1. Autentificare și cont (**auth**, **account**)
- Înregistrare, logare, deconectare.
- Schimbare parolă și email.
- Session versioning pentru „Deconectează de pe alte dispozitive” (din admin).

### 2. Control acces (**access_control**)
- Verificare cont activ (plătit) sau acțiuni gratuite rămase.
- Trial pe acțiuni: 1 fișă chirie gratuită și 1 fișă vânzare gratuită per cont, fără abonament.
- Limită dispozitive per cont (device guard).
- Redirect la modal „Activează accesul” când funcția necesită cont plătit.

### 3. Fișe de vizionare (**fise/chirie**, **fise/vanzare**)
- **Chirie**: formular (dată/ora vizionare, tip imobil, adresă, comision, date vizitator). Generare PDF fișă de vizionare. Link remote cu token: clientul completează datele și semnează; agentul vede fișa semnată și poate descărca PDF.
- **Vânzare**: același flux (formular → PDF → link remote → semnare la distanță).
- Date agent/agenție preluate din profilul utilizatorului (UserProfile).

### 4. Contract de închiriere (**fise/contract_inchiriere**)
- Formular pentru contract de închiriere.
- Generare PDF contract.

### 5. Prestații de servicii (**fise/prestari_servicii**)
- Formular pentru tranzacții imobiliare: beneficiar (PF/PJ), date imobil, comision, TVA, nr. contract, dată contract.
- Generare document/PDF prestații.

### 6. Marketplace (**marketplace**)
- **Cereri** (cumpărător): tip (cumpărare/închiriere), tip imobil (apartament, casă, teren, birou etc.), zone (multi-select), buget min/max, camere, an construcție, descriere, urgent, contact. Listare cu filtre, sortare (fair rotation, newest, buget). Quota: 5 cereri gratuite la 30 zile + sloturi plătite.
- **Anunțuri** (vânzător): tip (vânzare/închiriere), tip imobil, zone, preț, camere, suprafețe, etaj, an construcție, parcare, comision, titlu, descriere. Listare similară. Quota: 3 anunțuri gratuite la 30 zile + sloturi plătite.
- **Profilul meu**: rezumat cereri + anunțuri, editare/ștergere.
- **Posibile colaborări (matching)**:
  - La salvare/actualizare cerere sau anunț se recalculează potrivirile.
  - Reguli: zonă comună, același tip (cumpărare/închiriere) și tip imobil, camere compatibile. Buget: la **închiriere** ±100 €; la **vânzare** ±10% din prețul anunțului.
  - Fiecare potrivire este afișată în asistent ca „posibilă colaborare”, cu titlu (ex. „Apartament 2 camere”) și link direct la cerere/anunț. Ambele părți sunt notificate; notificarea dispare după ce userul deschide secțiunea. Colaborările sunt valabile până la ștergerea cererii sau anunțului.
- Statistici: număr potriviri în ultimele 3 luni (pentru rapoarte).

### 7. To-Do (**todo**)
- Task-uri personale: titlu, descriere, termen (dată/ora), prioritate, status (open, in-progress, done), tag-uri.
- Listare, filtre, paginare. Raport PDF cu task-urile (ex. pentru ziua curentă sau perioadă).

### 8. Asistent (**assistant**)
- **Bulă** (widget) pe fiecare pagină: deschide panoul asistentului.
- **Ghid pagină**: „Ești în: [nume pagină]”, intro, bullet points, sfat rapid (conținut din knowledge base, în funcție de page_id).
- **Ce am de făcut azi**: task-uri cu termen azi, nefinalizate, cu link către To-Do.
- **Posibile colaborări**: listă potriviri marketplace (titlu scurt + link către cerere/anunț); marcare „văzut” la deschiderea secțiunii.
- **Întreabă**: FAQ cu căutare; răspunsuri cu eventual link WhatsApp pentru prețuri/suport.
- **Notificări**: anunțuri admin (necitate), reminder expirare abonament (1 zi înainte), notificare „Ai o posibilă colaborare” când există potriviri necitite.
- Limită mesaje/zi pentru API Gemini (rate limit), opțional.

### 9. Meniu și pagini statice (**menu**, **home**)
- Meniu central: linkuri către date agent, date agenție, fișe remote, cont (parolă, email, WhatsApp suport), deconectare.
- Pagini: Despre, Termeni, Confidențialitate, Plăți.

### 10. Admin (**admin**)
- **Utilizatori**: listare, filtre (activ/inactiv, căutare), detalii user (profil, dispozitive, cereri, oferte, fișe remote). Acțiuni: setare paid_ends_at, blocare/deblocare, deconectare pe alte dispozitive, setare limite cereri/oferte, sloturi plătite.
- **Anunțuri**: creare anunț către toți userii (afișat în asistent până la marcarea ca citit).
- **Marketplace**: moderare cereri și oferte (vizualizare, ștergere).
- **Oferte/Cereri**: gestionare cote și sloturi plătite per user.
- **Curățare**: rulare cleanup (manual/auto), istoric, ștergere fișe/contracte expirate, utilizatori inactivi.
- Protecție: doar utilizatori cu rol admin au acces la rutele /admin.

### 11. PDF și fișe temporare (**pdf**, **static/tmp**)
- Generare PDF pentru: fișă chirie, fișă vânzare, contract închiriere, prestații servicii, raport To-Do.
- Fișiere temporare stocate în `static/tmp`; cleanup periodic (scheduler sau manual din admin).

### 12. Alte componente
- **CSRF** pe formulare.
- **Flask-Login** pentru sesiune.
- **SQLAlchemy** + **Alembic** (migrări); suport PostgreSQL (ex. Railway) și SQLite (local).
- **ProxyFix** pentru URL-uri corecte în spatele unui reverse proxy (HTTPS).
- **Scroll la erori**: la validare eșuată (formular), pagina derulează la prima eroare și pune focus pe câmp (script partajat pe toate formularele).

---

## Tehnologii

- **Backend**: Python 3, Flask.
- **Baza de date**: SQLite (dev) / PostgreSQL (producție, ex. Railway).
- **Frontend**: HTML, CSS (premium.css, marketplace.css, assistant.css, todo.css), JavaScript (assistant, marketplace, form-errors-scroll).
- **Template-uri**: Jinja2; layout principal `base_premium.html`.
- **Deploy**: configurare pentru Railway (Procfile, variabile de mediu: `DATABASE_URL`, `SECRET_KEY`, `WHATSAPP_SUPPORT_PHONE`, `PUBLIC_BASE_URL` etc.).

---

## Rezumat

| Sistem            | Scop principal                                                                 |
|-------------------|---------------------------------------------------------------------------------|
| Auth / Account    | Cont, login, parolă, email, suport WhatsApp                                   |
| Access control    | Abonament vs. trial pe acțiuni, limită dispozitive                             |
| Fișe chirie       | Formular vizionare chirie → PDF → link remote → semnare client                 |
| Fișe vânzare      | La fel pentru vânzare                                                          |
| Contract          | Contract închiriere → PDF                                                      |
| Prestații         | Formular tranzacții imobiliare → document/PDF                                 |
| Marketplace       | Cereri + anunțuri, potriviri automate, notificări colaborări                   |
| To-Do             | Task-uri personale, raport PDF                                                 |
| Asistent          | Ghid, FAQ, notificări, posibile colaborări, task-uri azi                       |
| Admin             | Utilizatori, anunțuri, moderare marketplace, cote, cleanup                     |

Aplicația este gândită pentru agenți imobiliari care folosesc fișe de vizionare, contracte și un marketplace intern, cu notificări și asistent integrat în interfață.
