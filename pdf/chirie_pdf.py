from io import BytesIO
from pathlib import Path
import base64

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


# --- Font setup (diacritice OK) ---
_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    base_dir = Path(__file__).resolve().parents[1]  # .../fisa_vizionare_app
    fonts_dir = base_dir / "static" / "Fonts"

    regular_path = fonts_dir / "NotoSans-Regular.ttf"
    bold_path = fonts_dir / "NotoSans-Bold.ttf"

    if not regular_path.exists() or not bold_path.exists():
        raise FileNotFoundError(
            "Nu găsesc fonturile NotoSans. Verifică:\n"
            f"- {regular_path}\n"
            f"- {bold_path}\n"
        )

    pdfmetrics.registerFont(TTFont("NotoSans", str(regular_path)))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bold_path)))
    _FONTS_REGISTERED = True


def _dataurl_to_imagereader(dataurl: str):
    """
    Acceptă:
      - data:image/png;base64,AAAA...
      - data:image/jpeg;base64,AAAA...
    Returnează ImageReader sau None.
    """
    if not dataurl:
        return None

    dataurl = (dataurl or "").strip()
    if "base64," not in dataurl:
        return None

    try:
        b64 = dataurl.split("base64,", 1)[1].strip()
        raw = base64.b64decode(b64)
        return ImageReader(BytesIO(raw))
    except Exception:
        return None


def render_chirie_pdf_bytes(data: dict) -> bytes:
    _register_fonts()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # layout
    left = 2.0 * cm
    right = 2.0 * cm
    top = 2.0 * cm
    bottom = 2.0 * cm

    max_w = width - left - right
    y = height - top
    page_no = 1

    def set_font(bold: bool, size: float):
        c.setFont("NotoSans-Bold" if bold else "NotoSans", size)

    def footer():
        set_font(False, 9)
        c.drawRightString(width - right, 1.15 * cm, f"Pagina {page_no}")

    def new_page():
        nonlocal y, page_no
        footer()
        c.showPage()
        page_no += 1
        y = height - top

    def ensure(h: float):
        nonlocal y
        if y - h < bottom:
            new_page()

    def fits(h: float) -> bool:
        return (y - h) >= bottom

    def title(text: str):
        nonlocal y
        ensure(2.2 * cm)
        set_font(True, 16)
        c.drawCentredString(width / 2, y, text)
        y -= 0.85 * cm

    def section_head(text: str):
        nonlocal y
        ensure(1.2 * cm)
        set_font(True, 11.7)
        c.drawString(left, y, text)
        y -= 0.55 * cm

    def hline(gap_before=0.15 * cm, gap_after=0.45 * cm):
        nonlocal y
        ensure(gap_before + gap_after + 0.3 * cm)
        y -= gap_before
        c.setLineWidth(0.6)
        c.setStrokeGray(0.70)
        c.line(left, y, width - right, y)
        c.setStrokeGray(0)
        y -= gap_after

    def wrap_lines(text: str, font_name: str, size: float):
        words = (text or "").split()
        if not words:
            return []
        lines = []
        buf = ""
        for w in words:
            test = (buf + " " + w).strip()
            if c.stringWidth(test, font_name, size) <= max_w:
                buf = test
            else:
                if buf:
                    lines.append(buf)
                buf = w
        if buf:
            lines.append(buf)
        return lines

    def para(text: str, size=10.6, leading=14, gap=0.25 * cm, indent=0.0):
        nonlocal y
        t = (text or "").strip()
        if not t:
            ensure(gap)
            y -= gap
            return

        font_name = "NotoSans"
        lines = wrap_lines(t, font_name, size)
        need = len(lines) * leading + gap
        ensure(need)

        set_font(False, size)
        x = left + indent
        for ln in lines:
            c.drawString(x, y, ln)
            y -= leading
        y -= gap

    def kv(label: str, value: str, size=10.6, leading=14, gap=0.18 * cm):
        text = f"{label}: {value}" if value else f"{label}: —"
        para(text, size=size, leading=leading, gap=gap)

    def s(d: dict, key: str, default="") -> str:
        v = (d or {}).get(key, default)
        return (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))

    # --- helper: măsoară un paragraf (fără să-l deseneze) ---
    def measure_para(text: str, size=10.6, leading=14, gap=0.25 * cm) -> float:
        t = (text or "").strip()
        if not t:
            return gap
        lines = wrap_lines(t, "NotoSans", size)
        return len(lines) * leading + gap

    # ---------------- DATA ----------------
    viz = data.get("vizionare", {}) or {}
    viz_date = s(viz, "data", "")
    viz_time = s(viz, "ora", "")

    agency = data.get("agency", {}) or {}
    agent = data.get("agent", {}) or {}
    v = data.get("vizitator", {}) or {}
    im = data.get("imobil", {}) or {}

    # meta semnare
    meta = data.get("signature_meta", {}) or {}
    mode = (meta.get("mode") or "").strip().lower()

    # ---------------- CONTENT ----------------
    title("FIȘĂ DE VIZIONARE — ÎNCHIRIERE")

    # Data / Ora pe rânduri separate
    ensure(1.25 * cm)
    set_font(False, 11)

    if mode == "remote":
        c.drawString(left, y, f"Data vizionării: {viz_date or '—'}")
        y -= 0.55 * cm
        c.drawString(left, y, f"Ora vizionării: {viz_time or '—'}")
    else:
        c.drawString(left, y, f"Data vizionării (și semnării): {viz_date or '—'}")
        y -= 0.55 * cm
        c.drawString(left, y, f"Ora vizionării (și semnării): {viz_time or '—'}")

    y -= 0.40 * cm
    hline()

    # 1. PĂRȚI
    section_head("1. PĂRȚI")
    agency_name = agency.get("name", "") or "—"
    agency_hq = agency.get("hq_address", "") or "—"
    orc = agency.get("orc_number", "") or "—"
    cui = agency.get("cui", "") or "—"
    iban = agency.get("iban", "") or "—"
    bank = agency.get("bank", "") or "—"
    admin = agency.get("administrator", "") or "—"

    para(
        "Prestator (Agenție imobiliară): "
        f"{agency_name}, cu sediul social în {agency_hq}, "
        f"înregistrată la ORC sub nr. {orc}, CUI {cui}, "
        f"IBAN {iban}, Banca {bank}, reprezentată legal prin {admin}, "
        "în calitate de Administrator, denumită în continuare „Prestatorul”.",
        size=10.5,
        leading=14,
        gap=0.20 * cm
    )
    kv("Agent imobiliar", (agent.get("name", "") or "—"))
    hline()

    # 2. VIZITATOR
    section_head("2. VIZITATOR (CLIENT)")
    kv("Nume", s(v, "nume", ""))
    kv("Telefon", s(v, "telefon", ""))
    kv("Email", s(v, "email", "") or "—")

    # CI pe rânduri separate
    ci_serie = s(v, "ci_serie", "")
    ci_numar = s(v, "ci_numar", "")
    kv("Act identitate (CI) — serie", ci_serie or "—")
    kv("Act identitate (CI) — număr", ci_numar or "—")

    para(
        "Vizitatorul declară că datele furnizate sunt corecte, reale și îi aparțin. Furnizarea datelor are ca scop organizarea vizionării, "
        "intermedierea și, după caz, dovedirea intermedierii și a consimțământului exprimat prin semnare. "
        "În măsura în care unele date sunt opționale, acestea sunt furnizate voluntar; refuzul furnizării poate limita "
        "posibilitatea dovedirii identității în cazul unei contestări, fără a anula prin sine însuși valoarea prezentei fișe."
    )
    hline()

    # 3. IMOBIL
    section_head("3. IMOBIL VIZIONAT")
    kv("Tip imobil", s(im, "tip", ""))
    kv("Adresă (completă)", s(im, "adresa", ""))

    para(
        "Vizitatorul confirmă că i-au fost prezentate imobilul și informațiile relevante pentru închiriere (caracteristici, condiții, disponibilitate) "
        "prin intermediul Prestatorului/Agentului, iar această introducere la proprietate este element esențial al activității de intermediere."
    )
    hline()

    # 4. OBIECT
    section_head("4. OBIECTUL FIȘEI")
    para(
        "Prin prezenta, Vizitatorul confirmă că a efectuat vizionarea imobilului descris mai sus "
        "prin intermediul Prestatorului, în prezența/participarea Agentului imobiliar, primind informații "
        "despre caracteristicile, starea și condițiile de închiriere ale imobilului."
    )
    para(
        "Prezenta fișă are rol de dovadă a intermedierii și a introducerii Vizitatorului la proprietate, "
        "în scopul protejării dreptului Prestatorului la comision. De asemenea, fișa poate fi utilizată pentru a demonstra "
        "cronologia evenimentelor (vizionare/negociere/închiriere) și legătura dintre vizionarea realizată prin Prestator și tranzacția finală."
    )
    para(
        "Părțile înțeleg că prezenta fișă nu ține loc de contract de închiriere și nu transferă drepturi de proprietate sau folosință; "
        "totuși, ea produce efecte juridice între părți cu privire la confirmarea intermedierii, obligațiile de neeludare și plata comisionului."
    )
    hline()

    # 5. NEELUDARE
    section_head("5. CLAUZĂ DE NEELUDARE A INTERMEDIERII")
    para(
        "Vizitatorul se obligă ca, pe o perioadă de 6 (șase) luni de la data semnării prezentei fișe, "
        "să nu contacteze direct proprietarul imobilului și să nu încheie, direct sau indirect, nicio tranzacție "
        "de închiriere având ca obiect imobilul vizionat, fără participarea Prestatorului."
    )
    para(
        "Interdicția se aplică inclusiv prin persoane interpuse (rude până la gradul IV inclusiv, societăți controlate, "
        "prieteni, colegi sau orice alte persoane interpuse), precum și în situația în care tranzacția se realizează "
        "în condiții identice sau similare celor prezentate la vizionare ori în condiții modificate (preț negociat, durată diferită etc.), "
        "dacă există legătură cu introducerea la proprietate realizată de Prestator."
    )
    para(
        "Încălcarea obligației de mai sus atrage răspunderea contractuală a Vizitatorului, "
        "iar comisionul prevăzut la secțiunea următoare reprezintă prejudiciu minim prezumat rezultat din eludarea intermedierii. "
        "În plus, Prestatorul își rezervă dreptul de a solicita, atunci când este cazul, repararea integrală a prejudiciului dovedit "
        "(inclusiv cheltuieli de recuperare, taxe, onorarii și alte costuri ocazionate de demersurile necesare)."
    )
    hline()

    # 6. COMISION
    section_head("6. COMISION")
    comision = str(data.get("comision_procent", "") or "____").strip() or "____"
    para(
        f"În cazul în care tranzacția de închiriere se finalizează pentru imobilul vizionat (direct sau indirect), "
        f"Vizitatorul se obligă să achite Prestatorului un comision de {comision} din valoarea chiriei lunare, "
        "conform acordului comercial dintre părți."
    )
    para(
        "Comisionul devine exigibil la data semnării contractului de închiriere și/sau la data obținerii folosinței imobilului "
        "(de exemplu primire chei/mutare), oricare intervine prima, întrucât acesta este momentul în care intermedierea produce rezultatul final."
    )
    para(
        "Plata comisionului se va efectua în termen de maximum 7 (șapte) zile calendaristice de la data finalizării tranzacției "
        "(semnarea contractului de închiriere). Neplata la scadență poate conduce la demersuri de recuperare și, după caz, la acțiuni legale."
    )
    hline()

    # 7. ACORD
    section_head("7. ACORD ȘI CONFIRMARE")
    para("Vizitatorul declară și confirmă că:")
    para("• a efectuat vizionarea imobilului prin intermediul Prestatorului;", indent=0.25 * cm)
    para("• a luat la cunoștință conținutul prezentei fișe și îl acceptă integral;", indent=0.25 * cm)
    para("• datele furnizate sunt reale și aparțin Vizitatorului;", indent=0.25 * cm)
    para("• a înțeles clauza de neeludare și efectele acesteia, inclusiv obligația de plată a comisionului în caz de eludare;", indent=0.25 * cm)
    para("• a primit / poate primi o copie electronică a documentului (WhatsApp / e-mail).", indent=0.25 * cm)

    para(
        "Vizitatorul confirmă că a avut posibilitatea de a citi documentul înainte de semnare, că a solicitat lămuriri acolo unde a considerat necesar "
        "și că își exprimă consimțământul în mod liber. Orice neconcordanță observată ulterior va fi comunicată Prestatorului fără întârziere."
    )
    hline()

    # 8. SEMNĂTURĂ ELECTRONICĂ
    section_head("8. SEMNĂTURĂ ELECTRONICĂ")
    para(
        "Prin semnarea prezentului document, inclusiv prin semnătură electronică simplă (trasare pe ecran), "
        "Vizitatorul confirmă acordul integral cu conținutul prezentei fișe."
    )
    para(
        "Documentul poate fi comunicat și păstrat în format electronic, având valoare probatorie conform dispozițiilor legale aplicabile. "
        "Părțile acceptă că forma electronică este adecvată scopului, iar fișa nu poate fi respinsă ca probă doar pentru faptul că este în format electronic."
    )
    para(
        "În situația în care semnarea se face la distanță, părțile acceptă utilizarea elementelor tehnice de trasabilitate (metadate) "
        "pentru a stabili momentul semnării și a lega documentul de persoana care a primit link-ul de semnare, conform secțiunii 9."
    )

    # 9. REMOTE — dovada semnării
    if mode == "remote":
        signed_local = str(meta.get("signed_at_local") or "—").strip()
        tz = str(meta.get("timezone") or "Europe/Bucharest").strip()
        ip = str(meta.get("ip") or "—").strip()

        hline()
        section_head("9. DATE DE IDENTIFICARE ALE SEMNĂRII LA DISTANȚĂ")
        kv("Data/Ora semnării (România)", f"{signed_local} ({tz})")
        kv("Adresă IP", ip)

        para(
            "Elementele de mai sus sunt atașate automat pentru a susține dovada semnării la distanță a documentului "
            "și pentru corelarea fișei cu link-ul transmis Vizitatorului. Aceste date constituie o urmă de audit (audit trail) "
            "care permite, dacă este necesar, reconstituirea cronologiei semnării și demonstrarea faptului că acceptarea a avut loc "
            "printr-o acțiune voluntară a persoanei care a accesat link-ul de semnare."
        )
        para(
            "Data și ora semnării (inclusiv fusul orar) sunt păstrate pentru a stabili momentul exact al exprimării consimțământului și pentru a separa clar "
            "data/ora vizionării de data/ora semnării în cazul în care acestea nu coincid. Această delimitare reduce riscul de contestare privind momentul acceptării "
            "și ajută la stabilirea ordinii evenimentelor (vizionare → comunicare → semnare → eventuală tranzacție)."
        )
        para(
            "Adresa IP este colectată exclusiv în scop de securitate și prevenire a abuzurilor: ajută la identificarea rețelei din care a fost efectuată semnarea, "
            "la detectarea accesului neautorizat, a tentativelor de fraudă și la corelarea tehnică a sesiunii de semnare cu accesarea link-ului. "
            "IP-ul nu este utilizat pentru marketing și nu se folosește pentru localizare precisă, ci doar ca element tehnic de trasabilitate și integritate a procesului."
        )
        para(
            "Accesul la aceste informații este restricționat la personal autorizat, pe principiul „need-to-know”, iar comunicarea către terți se face numai în temei legal "
            "(de exemplu solicitări ale autorităților/instanței) sau atunci când este necesar pentru constatarea, exercitarea sau apărarea unui drept al Prestatorului."
        )

    hline()

    # 10. GDPR
    section_head("10. PROTECȚIA DATELOR (GDPR)")
    para(
        "Operatorul de date cu caracter personal este Prestatorul (Agenția imobiliară) menționat la secțiunea 1. "
        "Datele cu caracter personal sunt prelucrate în conformitate cu Regulamentul (UE) 2016/679 (GDPR) și legislația națională aplicabilă."
    )
    para(
        "Scopurile prelucrării sunt: (i) organizarea și derularea vizionării, (ii) intermedierea tranzacției imobiliare, (iii) comunicarea cu Vizitatorul, "
        "(iv) dovedirea intermedierii și protejarea dreptului Prestatorului la comision, inclusiv prevenirea eludării intermedierii, "
        "(v) securitatea procesului de semnare și prevenirea abuzurilor/fraudei, (vi) apărarea drepturilor în cazul unor litigii și îndeplinirea obligațiilor legale."
    )
    para(
        "Categoriile de date prelucrate pot include: nume, telefon, e-mail, date din actul de identitate (serie/număr — dacă sunt furnizate), "
        "date privind imobilul vizionat și, în cazul semnării la distanță, metadate tehnice precum data/ora semnării, fus orar și adresă IP. "
        "Aceste metadate sunt utilizate strict pentru trasabilitate, securitate și probă, nu pentru profilare sau marketing."
    )
    para(
        "Temeiurile legale ale prelucrării (art. 6 GDPR) sunt: executarea demersurilor precontractuale/contractuale (organizare vizionare, intermediere, comunicare), "
        "interesul legitim al Prestatorului (dovada intermedierii, prevenirea eludării, securitatea semnării și apărarea drepturilor) și, după caz, îndeplinirea obligațiilor legale. "
        "În situațiile în care anumite date sunt opționale, furnizarea lor este voluntară; refuzul nu împiedică în mod automat vizionarea, dar poate limita posibilitatea de probare în caz de contestare."
    )
    para(
        "Datele nu sunt vândute și nu sunt transmise terților în scopuri de marketing. Pot fi comunicate doar către furnizori de servicii necesari funcționării (ex.: servicii IT/găzduire, "
        "comunicare electronică), în baza obligațiilor de confidențialitate și securitate, precum și către autorități/instanțe/consultanți juridici atunci când există obligație legală "
        "sau este necesar pentru constatarea, exercitarea ori apărarea unui drept în instanță."
    )
    para(
        "Durata de stocare: datele sunt păstrate pe perioada necesară îndeplinirii scopurilor de mai sus, inclusiv pe durata în care pot apărea pretenții, contestări sau litigii "
        "privind intermedierea și comisionul, precum și pe duratele cerute de obligațiile legale aplicabile. După expirarea termenelor, datele sunt șterse sau anonimizate, după caz."
    )

    # === AICI e magia: ținem „tail GDPR + semnături” împreună, smart ===
    gdpr_security = (
        "Măsuri de securitate: Prestatorul aplică măsuri tehnice și organizatorice rezonabile pentru protecția datelor (control acces, limitare acces, logare, back-up, "
        "măsuri anti-abuz). Accesul la metadate (IP, loguri) este strict limitat la personal autorizat."
    )
    gdpr_rights = (
        "Drepturile Vizitatorului: dreptul de acces, rectificare, ștergere (în limitele legii), restricționare, opoziție (în special față de prelucrări bazate pe interes legitim), "
        "portabilitate (unde este aplicabil) și dreptul de a depune plângere la Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal (ANSPDCP). "
        "Solicitările se pot transmite Prestatorului folosind datele de contact ale agenției."
    )

    # Semnături - parametri
    sig_w = 7.2 * cm
    sig_h = 2.6 * cm
    left_sig_x = left
    right_sig_x = width - right - sig_w

    # cât costă blocul de semnături (fără să îl rupem)
    sig_line_need = (0.08 * cm + 0.18 * cm + 0.3 * cm)  # hline(gap_before=0.08,gap_after=0.18)
    sig_head_need = 1.2 * cm                              # section_head ensure
    sig_block_need = (
        sig_line_need
        + sig_head_need
        + (0.20 * cm)            # spațiu mic înainte de "Agent/Vizitator"
        + (0.30 * cm)            # după etichete
        + sig_h                  # chenar semnătură
        + (0.35 * cm)            # sub chenar până la nume
        + (0.55 * cm)            # rând nume
        + (1.40 * cm)            # rezervă pt footer / margini
        + (0.25 * cm)            # rezervă mică
    )

    # măsurăm tail-ul GDPR în două moduri:
    # 1) normal (dacă rămâne pe aceeași pagină)
    tail_normal = (
        measure_para(gdpr_security, leading=14, gap=0.25 * cm)
        + measure_para(gdpr_rights, leading=14, gap=0.25 * cm)
    )

    # 2) „umplere” (dacă mutăm pe pagina semnăturilor, creștem puțin spațierea)
    tail_fill = (
        measure_para(gdpr_security, leading=16, gap=0.35 * cm)
        + measure_para(gdpr_rights, leading=16, gap=0.35 * cm)
    )

    # Dacă pe pagina curentă încape tail normal + semnături => le lăsăm aici.
    if fits(tail_normal + sig_block_need):
        para(gdpr_security, leading=14, gap=0.25 * cm)
        para(gdpr_rights, leading=14, gap=0.25 * cm)

        # semnături pe aceeași pagină
        hline(gap_before=0.08 * cm, gap_after=0.18 * cm)
        section_head("SEMNĂTURI")

    else:
        # Nu încape: mutăm tail + semnături pe pagina următoare,
        # DAR cu spațiere ușor mărită (ca să nu fie pagina goală sus).
        new_page()
        para(gdpr_security, leading=16, gap=0.35 * cm)
        para(gdpr_rights, leading=16, gap=0.35 * cm)

        hline(gap_before=0.08 * cm, gap_after=0.18 * cm)
        section_head("SEMNĂTURI")

    # Acum desenăm efectiv semnăturile (ensure doar pe blocul rămas)
    ensure(sig_block_need - (sig_line_need + sig_head_need))  # linia+titlul deja consumate

    set_font(True, 10.5)
    c.drawString(left_sig_x, y, "Agent")
    c.drawString(right_sig_x, y, "Vizitator")
    y -= 0.30 * cm

    # chenare
    c.setLineWidth(0.8)
    c.setStrokeGray(0.35)
    c.rect(left_sig_x, y - sig_h, sig_w, sig_h, stroke=1, fill=0)
    c.rect(right_sig_x, y - sig_h, sig_w, sig_h, stroke=1, fill=0)
    c.setStrokeGray(0)

    agent_sig = _dataurl_to_imagereader(data.get("signature_agent_dataurl", ""))
    visitor_sig = _dataurl_to_imagereader(data.get("signature_visitor_dataurl", ""))

    if agent_sig:
        c.drawImage(
            agent_sig,
            left_sig_x + 0.2 * cm,
            y - sig_h + 0.2 * cm,
            width=sig_w - 0.4 * cm,
            height=sig_h - 0.4 * cm,
            preserveAspectRatio=True,
            mask="auto",
        )

    if visitor_sig:
        c.drawImage(
            visitor_sig,
            right_sig_x + 0.2 * cm,
            y - sig_h + 0.2 * cm,
            width=sig_w - 0.4 * cm,
            height=sig_h - 0.4 * cm,
            preserveAspectRatio=True,
            mask="auto",
        )

    y -= (sig_h + 0.35 * cm)

    set_font(False, 10.4)
    c.drawString(left_sig_x, y, f"Nume: {agent.get('name','') or '________________________'}")
    c.drawString(right_sig_x, y, f"Nume: {s(v, 'nume', '') or '________________________'}")
    y -= 0.40 * cm

    footer()
    c.save()
    return buffer.getvalue()
