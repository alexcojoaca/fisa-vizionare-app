from io import BytesIO
from pathlib import Path
import base64
from datetime import datetime

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


def render_contract_pdf_bytes(data: dict) -> bytes:
    """
    IMPORTANT: versiunea asta citește din payload-ul tău actual:

    data = {
      "agency": {...},
      "agent": {...},
      "contract": {
        "owner_name": "...",
        "owner_address": "...",
        "owner_phone": "...",
        "owner_email": "...",
        "owner_id_type": "ci/pasaport",
        "owner_cnp": "...",
        "owner_ci_series": "...",
        "owner_passport_no": "...",
        "owner_citizenship": "...",

        "tenant_name": "...",
        "tenant_address": "...",
        "tenant_phone": "...",
        "tenant_email": "...",
        "tenant_id_type": "ci/pasaport",
        "tenant_cnp": "...",
        "tenant_ci_series": "...",
        "tenant_passport_no": "...",
        "tenant_citizenship": "...",

        "property_type": "...",
        "property_rooms": "...",
        "property_mp": "...",
        "property_address": "...",

        "start_date": "...",
        "end_date": "...",
        "duration_months": "...",
        "pay_day": "...",

        "rent_amount": "...",
        "rent_currency": "EUR/RON",
        "deposit_amount": "...",
        "paid_today_total": "...",

        "bank_name": "...",
        "bank_iban": "...",
        "bank_swift": "...",

        "pets_allowed": "yes/no",
        "notice_days": "...",
        "notes": "...",
      },
      "signature_owner_dataurl": "...optional...",
      "signature_tenant_dataurl": "...optional...",
    }
    """
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

    def hline(gap_before=0.2 * cm, gap_after=0.55 * cm):
        nonlocal y
        ensure(gap_before + gap_after + 0.3 * cm)
        y -= gap_before
        c.setLineWidth(0.6)
        c.setStrokeGray(0.70)
        c.line(left, y, width - right, y)
        c.setStrokeGray(0)
        y -= gap_after

    def title(text: str):
        nonlocal y
        ensure(2.2 * cm)
        set_font(True, 16)
        c.drawCentredString(width / 2, y, text)
        y -= 0.85 * cm

    def subtitle(text: str):
        nonlocal y
        ensure(1.2 * cm)
        set_font(False, 10.5)
        c.drawCentredString(width / 2, y, text)
        y -= 0.75 * cm

    def section_head(nr: str, text: str):
        nonlocal y
        ensure(1.3 * cm)
        set_font(True, 11.7)
        c.drawString(left, y, f"{nr}. {text}")
        y -= 0.55 * cm

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
        # linie simplă: "Label: value" (cu wrap)
        text = f"{label}: {value}" if value else f"{label}: —"
        para(text, size=size, leading=leading, gap=gap, indent=0)

    def s(d: dict, key: str, default="") -> str:
        v = (d or {}).get(key, default)
        return (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))

    contract = data.get("contract", {}) or {}
    agency = data.get("agency", {}) or {}
    agent = data.get("agent", {}) or {}

    # helpers for composed bits – text complet pentru identificare în contract
    def fmt_id_block(prefix: str):
        """Returnează fraza completă de identificare: 'identificat(ă) cu ...' sau ''."""
        id_type = s(contract, f"{prefix}_id_type", "").lower()
        if id_type == "pasaport":
            pno = s(contract, f"{prefix}_passport_no", "")
            cit = s(contract, f"{prefix}_citizenship", "")
            if pno and cit:
                return f"identificat(ă) cu pașaport cu numărul {pno}, de nationalitate {cit}"
            if pno:
                return f"identificat(ă) cu pașaport cu numărul {pno}"
            if cit:
                return f"identificat(ă) cu pașaport, de nationalitate {cit}"
            return "identificat(ă) cu pașaport"
        elif id_type == "ci":
            cnp = s(contract, f"{prefix}_cnp", "")
            ci = s(contract, f"{prefix}_ci_series", "")
            if cnp and ci:
                return f"identificat(ă) cu CI având CNP {cnp}, cu numărul {ci}"
            if cnp:
                return f"identificat(ă) cu CI având CNP {cnp}"
            if ci:
                return f"identificat(ă) cu CI cu numărul {ci}"
            return "identificat(ă) cu act de identitate (CI)"
        else:
            cnp = s(contract, f"{prefix}_cnp", "")
            ci = s(contract, f"{prefix}_ci_series", "")
            pno = s(contract, f"{prefix}_passport_no", "")
            cit = s(contract, f"{prefix}_citizenship", "")
            if pno or cit:
                if pno and cit:
                    return f"identificat(ă) cu pașaport cu numărul {pno}, de nationalitate {cit}"
                if pno:
                    return f"identificat(ă) cu pașaport cu numărul {pno}"
                return f"identificat(ă) cu pașaport, de nationalitate {cit}"
            if cnp or ci:
                if cnp and ci:
                    return f"identificat(ă) cu CI având CNP {cnp}, cu numărul {ci}"
                if cnp:
                    return f"identificat(ă) cu CI având CNP {cnp}"
                return f"identificat(ă) cu CI cu numărul {ci}"
            return ""

    def money(amount: str, currency: str):
        a = (amount or "").strip()
        cur = (currency or "").strip() or "EUR"
        return f"{a} {cur}" if a else "—"

    # ---------------- HEADER ----------------
    title("CONTRACT DE ÎNCHIRIERE")
    subtitle("")

    # date signed – dacă nu vine, punem “astăzi” (discret)
    date_signed = s(contract, "date_signed", "")
    if date_signed:
        c.drawString(left, y, f"Data încheierii: {date_signed}")
        y -= 0.65 * cm


    set_font(False, 10.6)
    ensure(0.9 * cm)
    y -= 0.6 * cm

    hline()

    # ---------------- 1. PĂRȚILE ----------------
    section_head("1", "PĂRȚILE CONTRACTANTE")

    owner_name = s(contract, "owner_name", "")
    owner_addr = s(contract, "owner_address", "")
    owner_phone = s(contract, "owner_phone", "")
    owner_email = s(contract, "owner_email", "")

    tenant_name = s(contract, "tenant_name", "")
    tenant_addr = s(contract, "tenant_address", "")
    tenant_phone = s(contract, "tenant_phone", "")
    tenant_email = s(contract, "tenant_email", "")

    owner_id = fmt_id_block('owner')
    owner_id_text = f"{owner_id}, " if owner_id else ""
    para(
        f"1.1. {owner_name or '________________________'}, "
        f"cu domiciliul în {owner_addr or '________________________'}, "
        f"{owner_id_text}"
        f"număr de telefon. {owner_phone or '__________'}, adresă de mail {owner_email or '__________'} denumit în continuare proprietar.",
        gap=0.25 * cm,
    )

    tenant_id = fmt_id_block('tenant')
    tenant_id_text = f"{tenant_id}, " if tenant_id else ""
    para(
        f"1.2. {tenant_name or '________________________'} "
        f"cu domiciliul în {tenant_addr or '________________________'}, "
        f"{tenant_id_text}"
        f"număr de telefon. {tenant_phone or '__________'}, adresă de mail {tenant_email or '__________'} denumit în continuare chiriaș.",
        gap=0.35 * cm,
    )

    hline()

    # ---------------- 2. OBIECT / IMOBIL ----------------
    section_head("2", "OBIECTUL CONTRACTULUI. DESCRIEREA IMOBILULUI")

    ptype = s(contract, "property_type", "")
    rooms = s(contract, "property_rooms", "")
    mp = s(contract, "property_mp", "")
    paddr = s(contract, "property_address", "")

    bits = []
    if ptype:
        bits.append(ptype)
    if rooms:
        bits.append(f"{rooms} camere")
    if mp:
        bits.append(f"{mp} mp")

    descr = " ".join(bits).strip()
    if descr:
        para(f"2.1. Proprietarul oferă spre folosință Chiriașului următorul imobil {descr}.")
    else:
        para("2.1. Proprietarul dă în folosință Chiriașului imobilul ce face obiectul prezentului contract.")

    para(
        f"2.2. Imobilul este situat la adresa: {paddr or '________________________'}."
    )

    para(
        "2.3. Proprietarul declară, pe propria răspundere că deține dreptul de proprietate asupra imobilului, "
        "că imobilul nu este scos din circuitul civil și nu este"
        "grevat de sarcini sau drepturi reale care ar putea afecta sau împiedica închirierea acestuia."
    )

    hline()

    # ---------------- 3. DOTĂRI / PREDARE ----------------
    section_head("3", "DOTĂRI. PREDAREA-PRIMIREA")

    para(
        "3.1. Predarea imobilului se va realiza în stare corespunzătoare folosinței, "
        "cu dotările și bunurile existente la data predării, conform procesului-verbal de predare-primire, "
        "dacă părțile aleg să întocmească un asemenea document."
    )

    hline()

    # ---------------- 4. SUBÎNCHIRIERE ----------------
    section_head("4", "SUBÎNCHIRIEREA ȘI CEDAREA FOLOSINȚEI")

    para(
        "4.1. Chiriașul nu poate subînchiria, ceda sau transmite folosința imobilului (total ori parțial), "
        "sub nicio formă, fără acordul scris al Proprietarului."
    )

    hline()

    # ---------------- 5. DURATA ----------------
    section_head("5", "DURATA CONTRACTULUI")

    start_date = s(contract, "start_date", "")
    end_date = s(contract, "end_date", "")
    duration_months = s(contract, "duration_months", "")

    dur = "5.1. Prezentul contract se încheie"
    if start_date and end_date:
        dur += f" pe perioada {start_date} până pe {end_date}"
    elif start_date:
        dur += f" începând cu data de {start_date}"
    elif end_date:
        dur += f" până la data de {end_date}"
    else:
        dur += " pe perioada convenită de părți"

    if duration_months:
        dur += f", pentru o durată de {duration_months} luni"
    dur += "."

    para(dur)
    para(
        "5.2. Contractul poate fi prelungit prin acordul părților, consemnat în scris (act adițional).",
        gap=0.35 * cm,
    )

    hline()

    # ---------------- 6. CHIRIE / GARANȚIE ----------------
    section_head("6", "CHIRIA, GARANȚIA ȘI MODALITATEA DE PLATĂ")

    rent_amount = s(contract, "rent_amount", "")
    rent_currency = s(contract, "rent_currency", "EUR") or "EUR"
    deposit_amount = s(contract, "deposit_amount", "")
    paid_today_total = s(contract, "paid_today_total", "")
    pay_day = s(contract, "pay_day", "")

    para(f"6.1. Chiria lunară este stabilită la valoarea de {money(rent_amount, rent_currency)}.")

    if deposit_amount:
        para(f"6.2. Garanția (depozitul) este de {money(deposit_amount, rent_currency)} și are rolul de a acoperi eventuale prejudicii și/sau obligații restante.")
    else:
        para("6.2. Părțile pot conveni o garanție (depozit) pentru acoperirea eventualelor prejudicii și/sau obligații restante.")

    if paid_today_total:
        para(f"6.3. La semnarea prezentului contract, s-a achitat suma totală de {money(paid_today_total, rent_currency)} (chirie și/sau garanție, după caz).")
    else:
        para("6.3. La semnarea prezentului contract, părțile pot consemna suma totală achitată (chirie și/sau garanție, după caz).")

    para(
        "6.4. Garanția se restituie la încetarea contractului, după predarea imobilului și după stingerea tuturor obligațiilor "
        "(chirie, utilități, eventuale daune). În situația constatării unor prejudicii, Proprietarul are dreptul de a reține "
        "din garanție contravaloarea acestora, justificat prin documente și/sau constatări."
    )

    if pay_day:
        para(f"6.5. Chiria se achită lunar, până cel târziu la data de {pay_day} a fiecărei luni calendaristice.")
    else:
        para("6.5. Chiria se achită lunar la data convenită de părți.")

    # bancă – doar dacă există
    bank_name = s(contract, "bank_name", "")
    bank_iban = s(contract, "bank_iban", "")
    bank_swift = s(contract, "bank_swift", "")

    if bank_name or bank_iban or bank_swift:
        para("6.6. Plățile se pot efectua și prin transfer bancar în contul Proprietarului:", gap=0.15 * cm)
        if bank_name:
            kv("Titular", bank_name)
        if bank_iban:
            kv("IBAN", bank_iban)
        if bank_swift:
            kv("SWIFT", bank_swift)
        para("", gap=0.10 * cm)

    hline()

    # ---------------- 7. UTILITĂȚI ----------------
    section_head("7", "UTILITĂȚI ȘI ALTE CHELTUIELI")

    para(
        "7.1. Chiriașul suportă costurile utilităților și ale serviciilor aferente folosinței imobilului "
        "(apă, energie electrică, gaze, internet/cablu, întreținere, salubritate etc.), în baza facturilor/documentelor justificative."
    )

    hline()

    # ---------------- 8. FOLOSINȚĂ / OBLIGAȚII ----------------
    section_head("8", "DREPTURI ȘI OBLIGAȚII PRIVIND FOLOSINȚA")

    para(
        "8.1. Chiriașul va folosi imobilul cu prudență și diligență, respectând destinația locativă și regulile de conviețuire. "
        "Chiriașul se obligă să păstreze curățenia, să respecte orele legale de liniște și să nu aducă modificări fără acordul scris al Proprietarului."
    )

    para(
        "8.2. Este interzisă desfășurarea de activități comerciale în imobil și/sau stabilirea sediului social ori a punctului de lucru, "
        "fără acordul scris al Proprietarului.",
        gap=0.35 * cm,
    )

    hline()

    # ---------------- 9. ANIMALE (doar dacă e bifat Acceptate sau Neacceptate) ----------------
    pets_allowed = s(contract, "pets_allowed", "").strip().lower()
    if pets_allowed == "yes":
        section_head("9", "ANIMALE DE COMPANIE")
        para(
            "9.1. Părțile convin că animalele de companie sunt acceptate în imobil, cu condiția respectării igienei, "
            "a liniștii publice și a evitării deteriorărilor. Chiriașul răspunde integral pentru orice prejudicii "
            "cauzate de animale și suportă costurile de curățare sau reparație, după caz."
        )
        hline()
    elif pets_allowed == "no":
        section_head("9", "ANIMALE DE COMPANIE")
        para(
            "9.1. Părțile convin că animalele de companie nu sunt permise în imobil. Nerespectarea acestei clauze "
            "poate constitui motiv de încetare a contractului și poate atrage răspunderea Chiriașului pentru "
            "eventualele prejudicii produse."
        )
        hline()

    # ---------------- 10. ÎNCETARE / PREAVIZ ----------------
    section_head("10", "ÎNCETAREA CONTRACTULUI. PREAVIZ")

    notice_days = s(contract, "notice_days", "")
    if notice_days:
        para(
            f"10.1. Denunțarea unilaterală se poate realiza cu un preaviz de {notice_days} zile, prin notificare scrisă transmisă celeilalte părți."
        )
    else:
        para(
            "10.1. Denunțarea unilaterală se poate realiza cu un preaviz rezonabil, stabilit de comun acord, prin notificare scrisă."
        )

    para(
        "10.2. La încetare, Chiriașul va preda imobilul în starea în care l-a primit, cu uzura normală aferentă folosinței. "
        "Eventualele daune se constată și se evaluează de părți, urmând a fi acoperite conform înțelegerii și legislației aplicabile.",
        gap=0.35 * cm,
    )

    hline()

    # ---------------- 11. ACCESUL PROPRIETARULUI ÎN IMOBIL ----------------
    section_head("11", "ACCESUL PROPRIETARULUI ÎN IMOBIL")

    notice_days = s(contract, "notice_days", "")
    if notice_days:
        para(
            f"11.1. Proprietarul are dreptul de a avea acces în imobil, cu notificarea prealabilă a Chiriașului, într-un termen rezonabil, pentru verificarea"
             "stării imobilului, efectuarea de reparații, citirea contoarelor sau alte situații justificate"
        )
    else:
        para(
            "11.2. În caz de urgență (avarii, incendii, inundații sau alte situații care pot produce prejudicii), Proprietarul poate avea acces în imobil"
            "fără notificare prealabilă."
        )

        para("", gap=0.35 * cm)


    hline()

    # ---------------- 12. NEPLATA CHIRIEI ----------------
    section_head("12", "NEPLATA CHIRIEI")

    para(
        "12.1. În cazul întârzierii la plată, Proprietarul are dreptul de a solicita penalități de întârziere, conform înțelegerii"
        "părților sau legislației aplicabile, și/sau de a proceda la rezilierea contractului. "
        "Proprietarul are dreptul de a reține din garanție sumele datorate cu titlu de chirie restantă, utilități neachitate sau alte"
        "prejudicii cauzate de Chiriaș."
    )


    hline()

    # ---------------- 13. REZILIEREA CONTRACTULUI PENTRU CULPĂ ----------------
    section_head("13", "REZILIEREA CONTRACTULUI PENTRU CULPĂ")

    para(
        "13.1. Proprietarul poate rezilia prezentul contract, fără acordarea unui termen de preaviz, în cazul încălcării"
        "grave a obligațiilor contractuale de către Chiriaș, inclusiv, dar fără a se limita la:"
        "a) neplata chiriei și/sau a utilităților;"
        "b) producerea de distrugeri sau deteriorări semnificative ale imobilului;"
        "c) subînchirierea, cedarea sau transmiterea folosinței imobilului fără acordul scris al Proprietarului;"
        "d) desfășurarea de activități ilegale sau contrare destinației imobilului."
        "13.2. Rezilierea produce efecte de la data comunicării notificării scrise către Chiriaș."

    )


    hline()

    # ---------------- 14. FORȚA MAJORĂ ----------------
    section_head("14", "FORȚA MAJORĂ")

    para(
        "14.1. Niciuna dintre părți nu răspunde pentru neexecutarea sau executarea cu întârziere a obligațiilor"
        "contractuale, dacă aceasta este cauzată de un eveniment de forță majoră, așa cum este definit de lege."
        "14.2. Partea care invocă forța majoră are obligația de a notifica cealaltă parte în cel mai scurt timp și de a lua"
        "toate măsurile rezonabile pentru limitarea efectelor acestui eveniment."

    )


    hline()

    # ---------------- 11. GDPR ----------------
    section_head("11", "PRELUCRAREA DATELOR CU CARACTER PERSONAL")

    para(
        "11.1. Părțile declară că au luat la cunoștință faptul că datele personale furnizate în legătură cu prezentul contract "
        "vor fi prelucrate exclusiv pentru executarea obligațiilor contractuale și pentru îndeplinirea obligațiilor legale, "
        "în conformitate cu Regulamentul (UE) 2016/679 (GDPR) și legislația națională aplicabilă."
    )

    # ---------------- 12. OBSERVAȚII ----------------
    notes = s(contract, "notes", "")
    if notes:
        hline()
        section_head("12", "Proces verbal (Predare/Primire)")
        para(notes, gap=0.45 * cm)

    # ---------------- SEMNĂTURI ----------------
    hline()
    section_head("13", "SEMNĂTURI")

    # semnături opționale — doar dacă există
    owner_sig = _dataurl_to_imagereader(data.get("signature_owner_dataurl", ""))
    tenant_sig = _dataurl_to_imagereader(data.get("signature_tenant_dataurl", ""))

    sig_w = 7.2 * cm
    sig_h = 2.6 * cm
    left_sig_x = left
    right_sig_x = width - right - sig_w

    # Calculează cât spațiu REAL consumă blocul de semnături
    needed = (
    0.45 * cm   # rândul "Proprietar / Chiriaș" + spațiu mic
    + sig_h     # chenar + semnătură
    + 0.55 * cm # spațiu sub chenar
    + 0.55 * cm # rândul "Nume: ..."
    + 0.35 * cm # buffer discret
)

    ensure(needed)

    set_font(True, 10.5)
    c.drawString(left_sig_x, y, "Proprietar")
    c.drawString(right_sig_x, y, "Chiriaș")
    y -= 0.40 * cm

    # chenare fine (profi)
    c.setLineWidth(0.8)
    c.setStrokeGray(0.35)
    c.rect(left_sig_x, y - sig_h, sig_w, sig_h, stroke=1, fill=0)
    c.rect(right_sig_x, y - sig_h, sig_w, sig_h, stroke=1, fill=0)
    c.setStrokeGray(0)

    # desenează doar dacă există (altfel rămâne chenarul gol, curat)
    if owner_sig:
        c.drawImage(
        owner_sig,
        left_sig_x + 0.2 * cm,
        y - sig_h + 0.2 * cm,
        width=sig_w - 0.4 * cm,
        height=sig_h - 0.4 * cm,
        preserveAspectRatio=True,
        mask="auto",
    )

    if tenant_sig:
        c.drawImage(
        tenant_sig,
        right_sig_x + 0.2 * cm,
        y - sig_h + 0.2 * cm,
        width=sig_w - 0.4 * cm,
        height=sig_h - 0.4 * cm,
        preserveAspectRatio=True,
        mask="auto",
    )

    # spațiu mai mic sub semnături (ca să nu împingă aiurea)
    y -= (sig_h + 0.55 * cm)

    set_font(False, 10.4)
    c.drawString(left_sig_x, y, f"Nume: {owner_name or '________________________'}")
    c.drawString(right_sig_x, y, f"Nume: {tenant_name or '________________________'}")
    y -= 0.75 * cm

    footer()
    c.showPage()
    c.save()
    return buffer.getvalue()
