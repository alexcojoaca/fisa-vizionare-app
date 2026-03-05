# Internal KNOWLEDGE_BASE for Gemini — app structure, steps, rules, pricing.
# Gemini is ONLY allowed to explain based on this. No hallucinations.

KNOWLEDGE_BASE = """
Aplicația „Fișa de vizionare” este pentru agenți imobiliari. Îi ajută să genereze fișe de vizionare (PDF), contracte, să folosească marketplace-ul de cereri și lista de taskuri.

=== STRUCTURA APLICAȚIEI ===

1. MENIU (pagina principală după login)
   - Afișează profilul utilizatorului, status acces (trial/abonament), zile rămase, link WhatsApp suport.
   - Linkuri către: Chirie, Vânzare, Contract închiriere, Prestări servicii, To-Do, Marketplace, Profil agent, Cont.

2. FIȘĂ DE VIZIONARE (chirie sau vânzare)
   - Chirie: formular pentru vizionare închiriere → generează PDF, poți trimite link client pentru semnare la distanță.
   - Vânzare: la fel pentru vânzare.
   - Pași: completezi formularul (dată/ora vizionare, tip imobil, adresă, comision), previzualizare PDF, descarci sau trimiți link.

3. CONTRACT ÎNCHIRIERE
   - Generează contract de închiriere (PDF) pe baza datelor introduse.
   - Pași: completezi formularul, previzualizare, descărcare.

4. PRESTĂRI SERVICII
   - Documente pentru prestări servicii (PDF).

5. TO-DO (SARCINI)
   - Listă personală de taskuri: titlu, descriere, termen limită, prioritate (low/medium/high), status (open, in-progress, done).
   - Doar utilizatorul își vede taskurile. Poți filtra după status, prioritate, „due today”, overdue.
   - Taskurile finalizate sunt șterse automat după 30 zile.

6. ECHIPĂ & PERFORMANȚĂ
   - Modul pentru echipe de agenți: manager + agenți.
   - Manager: creează echipa, adaugă agenți (prin email; agentul trebuie să confirme invitația), dă task-uri, urmărește performanța (vizionări, deal-uri, sumă), vede sumar lunar și rata de conversie. Poate șterge agenți sau echipa.
   - Agent: confirmă invitația, completează raport zilnic (vizionări, deal-uri, sumă totală), primește task-uri de la manager, poate ieși din echipă. Dashboard cu statistici (azi, săptămână, lună, 3 luni).
   - Acces: Meniu → Echipă & Performanță (sau direct de pe home).

7. MARKETPLACE (CERERI)
   - Listă de cereri de cumpărare/închiriere de la alți agenți/clienți.
   - Filtre: zonă, buget, camere, tip cerere (cumpărare/închiriere), urgent.
   - Poți adăuga cerere nouă (buget, zone, camere etc.). Limita: 10 cereri per 30 zile per utilizator.
   - Pe detaliu cerere: dacă ai ACCES ACTIV vezi datele de contact (telefon etc.). Dacă nu ai acces, vezi doar cererea fără contact.

8. ACCES ȘI VIZIBILITATE TELEFOANE
   - Accesul poate fi trial (perioadă limitată) sau abonament plătit.
   - Numerele de telefon și alte date de contact pe cererile din marketplace sunt vizibile DOAR dacă ai acces activ.
   - Dacă nu vezi telefoanele: verifică în Meniu dacă ai „Acces activ” și câte zile îți mai rămân. Dacă accesul a expirat, contactează suportul pentru reactivare.

9. PROFIL AGENT / AGENCY
   - Date pentru documente (nume agent, semnătură, date agenție). Completează din Meniu pentru ca PDF-urile să conțină datele corecte.

10. CONT
   - Schimbare email, schimbare parolă.

=== PREȚURI ȘI ABONAMENT ===

- Trial: perioadă de probă limitată (detaliile exacte sunt setate de administrator).
- Abonament plătit: prețurile și perioadele se stabilesc cu echipa de vânzări / suport. Nu există prețuri fixe afișate în aplicație; utilizatorii sunt îndrumați să contacteze suportul pentru oferte.

=== SUPORT TEHNIC ===

- WhatsApp: 40764381795 (pentru reactivare acces, probleme tehnice, abonamente).
- Utilizatorii pot folosi butonul WhatsApp din Meniu pentru a genera un mesaj pre-completat cu statusul contului.

=== REGULI IMPORTANTE ===

- Nu divulga date personale ale clienților în afara aplicației.
- Cererile din marketplace expiră după 30 zile și sunt șterse automat.
- Limita de cereri noi: 10 la 30 zile per utilizator.
- Asistentul NU poate modifica sau șterge date din aplicație (în afară de lista personală de watchlist, max 5 elemente). NU poate executa comenzi admin, nu poate vedea parole sau credențiale.
"""

# Used as system instruction for Gemini (no hallucinations, only this knowledge)
SYSTEM_INSTRUCTION = (
    "Ești asistentul intern al aplicației „Fișa de vizionare” pentru agenți imobiliari. "
    "Răspunzi DOAR pe baza bazei de cunoștințe furnizate. Nu inventa informații, prețuri sau pași care nu sunt în baza de cunoștințe. "
    "Răspunzi în română, clar și concis. "
    "Dacă utilizatorul întreabă ceva ce nu este în baza de cunoștințe, spune că nu ai acea informație și oferă un răspuns generic util (ex: contactează suportul WhatsApp 40764381795)."
)
