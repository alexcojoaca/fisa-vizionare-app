"""Generate PDF for Contract de prestări servicii imobiliare (ReportLab)."""
from io import BytesIO
from pathlib import Path
import base64

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    base_dir = Path(__file__).resolve().parents[1]
    fonts_dir = base_dir / "static" / "Fonts"
    regular_path = fonts_dir / "NotoSans-Regular.ttf"
    bold_path = fonts_dir / "NotoSans-Bold.ttf"
    if not regular_path.exists() or not bold_path.exists():
        raise FileNotFoundError("NotoSans fonts not found")
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


def render_prestari_pdf_bytes(data: dict) -> bytes:
    """
    Generate Contract de prestări servicii imobiliare PDF.

    data = {
      "agency": {
        "name": "...",
        "hq_address": "...",
        "orc_number": "...",
        "cui": "...",
        "iban": "...",
        "bank": "...",
        "administrator": "...",
      },
      "beneficiar": {
        "nume": "...",
        "cnp_cui": "...",
        "adresa": "...",
        "telefon": "...",
        "email": "...",
      },
      "obiect": {
        "tip_tranzactie": "inchiriere/vanzare/cumparare",
        "imobil_tip": "...",
        "imobil_descriere": "...",
        "imobil_adresa": "...",
      },
      "comision": 4570.00,
      "nr_contract": "...",
      "data_contractului": "dd.mm.yyyy",
      "signature_beneficiar_dataurl": "...",
      "signature_prestator_dataurl": "...",
      "signature_meta": {...},
    }
    """
    _register_fonts()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

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
        # Footer note about electronic generation
        footer_text = "Document generat electronic • Semnat de beneficiar olograf/digital"
        footer_y = 0.5 * cm
        c.drawCentredString(width / 2, footer_y, footer_text)
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

    def title(text: str):
        nonlocal y
        ensure(2.2 * cm)
        set_font(True, 16)
        c.drawCentredString(width / 2, y, text)
        y -= 0.85 * cm

    def section_head(nr: str, text: str):
        nonlocal y
        ensure(1.3 * cm)
        set_font(True, 11.7)
        c.drawString(left, y, f"Art. {nr} {text}")
        y -= 0.55 * cm

    def hline(gap_before=0.2 * cm, gap_after=0.55 * cm):
        nonlocal y
        ensure(gap_before + gap_after + 0.3 * cm)
        y -= gap_before
        c.setLineWidth(0.6)
        c.setStrokeGray(0.70)
        c.line(left, y, width - right, y)
        c.setStrokeGray(0)
        y -= gap_after

    def s(d: dict, key: str, default="") -> str:
        v = (d or {}).get(key, default)
        return (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))

    agency = data.get("agency", {}) or {}
    agent = data.get("agent", {}) or {}
    agent_name = (agent.get("name") or "").strip() or "Agent"
    beneficiar = data.get("beneficiar", {}) or {}
    obiect = data.get("obiect", {}) or {}
    currency = s(data, "currency", "RON")
    comision_tva = s(data, "comision_tva", "fara")
    comision_raw = s(data, "comision", "4570.00")  # Raw string exactly as typed by user
    nr_contract = s(data, "nr_contract", "")
    data_contract = s(data, "data_contractului", "")

    tip_tranz = s(obiect, "tip_tranzactie", "")
    tip_tranz_label = {
        "inchiriere": "închiriere",
        "vanzare": "vânzare",
        "cumparare": "cumpărare",
    }.get(tip_tranz, tip_tranz)

    # ---------- HEADER ----------
    title("CONTRACT DE PRESTĂRI SERVICII IMOBILIARE")
    ensure(0.5 * cm)

    if nr_contract:
        set_font(False, 10)
        c.drawString(left, y, f"Nr. contract: {nr_contract}")
        y -= 0.4 * cm
    if data_contract:
        set_font(False, 10)
        c.drawString(left, y, f"Data: {data_contract}")
        y -= 0.6 * cm

    hline()

    # ---------- PĂRȚILE CONTRACTANTE ----------
    set_font(True, 11.7)
    c.drawString(left, y, "PĂRȚILE CONTRACTANTE")
    y -= 0.5 * cm

    # Prestator (Agenția) — same source as fișe: UserProfile / agency profile
    # Use placeholders when empty so PDF always shows full structure
    agency_name = agency.get("name", "") or "__________"
    agency_hq = agency.get("hq_address", "") or "__________"
    agency_orc = agency.get("orc_number", "") or "__________"
    agency_cui = agency.get("cui", "") or "__________"
    agency_iban = agency.get("iban", "") or "__________"
    agency_bank = agency.get("bank", "") or "__________"
    agency_admin = agency.get("administrator", "") or "__________"

    para(
        f"PRESTATOR: {agency_name}, cu sediul în {agency_hq}, "
        f"înregistrată la ORC sub nr. {agency_orc}, CUI {agency_cui}, "
        f"cont IBAN {agency_iban}, banca {agency_bank}, reprezentată de {agency_admin}, "
        "denumit în continuare Prestator.",
        gap=0.3 * cm,
    )

    # Beneficiar
    ben_tip = s(beneficiar, "tip", "pf")
    ben_nume = s(beneficiar, "nume", "________________________")
    ben_cnp = s(beneficiar, "cnp", "")
    ben_cui = s(beneficiar, "cui", "")
    ben_adresa = s(beneficiar, "adresa", "")
    ben_telefon = s(beneficiar, "telefon", "")
    ben_email = s(beneficiar, "email", "")

    # Dynamic CNP/CUI text based on beneficiary type
    if ben_tip == "pf" and ben_cnp:
        ben_id = f", identificat prin CNP {ben_cnp}"
    elif ben_tip == "pj" and ben_cui:
        ben_id = f", identificată prin CUI {ben_cui}"
    else:
        ben_id = ""

    ben_addr = f", cu domiciliul în {ben_adresa}" if ben_adresa else ""
    ben_tel = f", telefon {ben_telefon}" if ben_telefon else ""
    ben_mail = f", email {ben_email}" if ben_email else ""

    para(
        f"BENEFICIAR: {ben_nume}{ben_id}{ben_addr}{ben_tel}{ben_mail}, denumit în continuare Beneficiar.",
        gap=0.4 * cm,
    )

    hline()

    # ---------- Art. 1 Obiectul contractului ----------
    section_head("1", "Obiectul contractului")

    imobil_tip = s(obiect, "imobil_tip", "")
    imobil_adresa = s(obiect, "imobil_adresa", "")

    para(
        f"Prezentul contract are ca obiect prestarea de servicii imobiliare de către Prestator în favoarea Beneficiarului, "
        f"respectiv intermedierea pentru {tip_tranz_label} a unui imobil situat la adresa: {imobil_adresa or '________________________'}.",
        gap=0.25 * cm,
    )

    if imobil_tip:
        para(
            f"Tip imobil: {imobil_tip}.",
            gap=0.2 * cm,
        )

    para(
        "Prestatorul se obligă să presteze servicii de intermediere imobiliară conform legislației în vigoare și să "
        "asigure finalizarea tranzacției în condițiile stabilite de părți.",
        gap=0.3 * cm,
    )

    # Exclusivity clause
    para(
        "1.1. Prezentul contract este neexclusiv, ceea ce înseamnă că Beneficiarul are dreptul să colaboreze cu alți " 
        "agenți imobiliari sau să finalizeze tranzacția prin alte mijloace, fără a fi obligat să plătească comisionul " 
        "dacă tranzacția nu a fost intermediată de Prestator.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 2 Termen de executare / Durata ----------
    section_head("2", "Termen de executare / Durata")

    para(
        "Contractul se încheie pentru o perioadă determinată, până la finalizarea tranzacției imobiliare sau până la "
        "expirarea termenului de valabilitate stabilit de părți.",
        gap=0.25 * cm,
    )

    para(
        "Prestatorul se obligă să înceapă prestarea serviciilor imediat după semnarea prezentului contract și să "
        "depună toate eforturile necesare pentru finalizarea tranzacției în cel mai scurt timp posibil.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 3 Prețul și condițiile de plată ----------
    section_head("3", "Prețul și condițiile de plată")

    # Currency handling
    if currency == "EUR":
        currency_text = "euro"
        currency_label = "EUR"
    else:
        currency_text = "lei"
        currency_label = "RON"

    # VAT wording: + TVA or (fără TVA)
    if comision_tva == "cu":
        tva_text = " + TVA"
    else:
        tva_text = " (fără TVA)"

    # Use raw commission string exactly as typed (no reformatting)
    para(
        f"Prețul serviciilor prestate de către Prestator este de {comision_raw} {currency_text}{tva_text}, reprezentând comisionul "
        "de intermediere imobiliară.",
        gap=0.25 * cm,
    )

    # Commission due moment - clearly specified
    para(
        "3.1. Comisionul devine exigibil și se va plăti de către Beneficiar în termen de maximum 5 zile calendaristice "
        "de la semnarea contractului de închiriere/vânzare/cumpărare sau de la data semnării actului autentic, după caz. "
        "Comisionul este datorat indiferent dacă Beneficiarul finalizează tranzacția direct sau prin intermediul Prestatorului, "
        "dacă tranzacția a fost inițiată în perioada de valabilitate a prezentului contract.",
        gap=0.25 * cm,
    )

    para(
        f"Plata se va efectua prin transfer bancar în contul Prestatorului: IBAN {agency_iban}, la banca {agency_bank}.",
        gap=0.25 * cm,
    )

    para(
        "Factura fiscală va fi emisă de Prestator în termen de maximum 5 zile calendaristice de la finalizarea "
        "tranzacției sau la cererea Beneficiarului.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 4 Obligațiile părților ----------
    section_head("4", "Obligațiile părților")

    para(
        "4.1. Prestatorul se obligă să:",
        gap=0.2 * cm,
    )

    para(
        "a) presteze servicii de intermediere imobiliară în conformitate cu legislația în vigoare;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "b) depună toate eforturile necesare pentru identificarea și prezentarea de către Beneficiar a imobilelor "
        "care corespund cerințelor acestuia;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "c) asigure organizarea și desfășurarea vizionărilor imobilelor;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "d) asiste Beneficiarul în negocierile privind condițiile tranzacției;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "e) asigure finalizarea tranzacției în condițiile stabilite de părți.",
        indent=0.3 * cm,
        gap=0.25 * cm,
    )

    para(
        "4.2. Beneficiarul se obligă să:",
        gap=0.2 * cm,
    )

    para(
        "a) furnizeze Prestatorului toate informațiile necesare pentru identificarea imobilelor care corespund "
        "cerințelor sale;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "b) participe la vizionările imobilelor organizate de Prestator;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "c) respecte termenii de plată ai comisionului stabilit în prezentul contract;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "d) informeze Prestatorul despre orice modificări privind cerințele sale sau despre finalizarea tranzacției.",
        indent=0.3 * cm,
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 5 Răspunderea contractuală ----------
    section_head("5", "Răspunderea contractuală")

    para(
        "5.1. Prestatorul răspunde pentru prestarea serviciilor în conformitate cu standardele profesionale și cu "
        "legislația în vigoare.",
        gap=0.2 * cm,
    )

    para(
        "5.2. Beneficiarul răspunde pentru plata comisionului în termenul stabilit și pentru furnizarea de informații "
        "corecte și complete.",
        gap=0.2 * cm,
    )

    para(
        "5.3. În cazul neplății comisionului în termenul stabilit, Beneficiarul va plăti penalități de întârziere "
        "de 0,1% pe zi de întârziere.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 6 Încetarea contractului ----------
    section_head("6", "Încetarea contractului")

    para(
        "6.1. Contractul se încetează prin:",
        gap=0.2 * cm,
    )

    para(
        "a) finalizarea tranzacției imobiliare și plata comisionului;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "b) acordul părților;",
        indent=0.3 * cm,
        gap=0.15 * cm,
    )

    para(
        "c) denunțarea unilaterală de către oricare dintre părți, cu notificare prealabilă de minimum 7 zile calendaristice.",
        indent=0.3 * cm,
        gap=0.25 * cm,
    )

    para(
        "6.2. În cazul încetării contractului înainte de finalizarea tranzacției, Beneficiarul va plăti comisionul "
        "pentru serviciile deja prestate de Prestator, proporțional cu efortul depus.",
        gap=0.25 * cm,
    )

    # Anti-circumvention clause
    para(
        "6.3. Clauză anti-ocolire: În cazul încetării contractului, Beneficiarul nu poate ocoli Prestatorul pentru a "
        "evita plata comisionului. Astfel, dacă în termen de 6 (șase) luni de la încetarea contractului, Beneficiarul "
        "finalizează o tranzacție cu un imobil care a fost prezentat sau discutat în cadrul prestării serviciilor de "
        "către Prestator, Beneficiarul rămâne obligat să plătească comisionul stabilit în prezentul contract.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 7 Confidențialitate și protecția datelor (GDPR) ----------
    section_head("7", "Confidențialitate și protecția datelor (GDPR)")

    para(
        "7.1. Părțile se obligă să păstreze confidențialitatea informațiilor obținute în cadrul prestării serviciilor.",
        gap=0.2 * cm,
    )

    para(
        "7.2. Prestatorul se obligă să prelucreze datele cu caracter personal ale Beneficiarului în conformitate cu "
        "Regulamentul General privind Protecția Datelor (GDPR) și cu legislația națională în vigoare.",
        gap=0.2 * cm,
    )

    para(
        "7.3. Beneficiarul are dreptul de a solicita accesul, rectificarea, ștergerea sau portabilitatea datelor sale "
        "cu caracter personal, conform prevederilor GDPR.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- Art. 8 Dispoziții finale ----------
    section_head("8", "Dispoziții finale")

    para(
        "8.1. Orice modificare a prezentului contract se va face prin act adițional semnat de ambele părți.",
        gap=0.2 * cm,
    )

    # Governing law & jurisdiction
    para(
        "8.2. Prezentul contract este supus legislației române. Orice litigiu ce ar putea apărea între părți va fi "
        "rezolvat pe cale amiabilă sau, în caz contrar, de către instanțele competente din România, în conformitate "
        "cu prevederile Codului de procedură civilă.",
        gap=0.2 * cm,
    )

    # Force majeure clause
    para(
        "8.3. În cazul apariției unor evenimente de forță majoră (cutremure, inundații, războaie, pandemii, măsuri "
        "guvernamentale sau alte evenimente independente de voința părților), care împiedică îndeplinirea obligațiilor "
        "contractuale, părțile nu vor fi considerate în întârziere sau încălcare a contractului. Părțile se obligă să se "
        "informeze reciproc despre apariția unor astfel de evenimente în termen de 7 zile calendaristice.",
        gap=0.2 * cm,
    )

    # Contract date = signing date (from form; default today)
    entry_date = data_contract if data_contract else "__.__.____"
    para(
        f"8.4. Prezentul contract intră în vigoare la data de {entry_date}, data semnării de către părți.",
        gap=0.3 * cm,
    )

    hline()

    # ---------- SEMNĂTURI — clean 2-column layout with signature lines ----------
    sig_block_h = 4.5 * cm
    ensure(sig_block_h)
    col_w = max_w / 2.0
    center_left = left + col_w / 2.0
    center_right = left + col_w + col_w / 2.0

    set_font(False, 10.6)
    c.drawCentredString(width / 2, y, "Semnături")
    y -= 0.6 * cm

    # Column labels (centered in each column)
    set_font(True, 10)
    c.drawCentredString(center_left, y, "BENEFICIAR")
    c.drawCentredString(center_right, y, "PRESTATOR / AGENT")
    y -= 0.5 * cm

    # Signature images area (above lines)
    sig_img_h = 1.4 * cm
    sig_img_w_max = 3.8 * cm
    sig_img_y = y - sig_img_h - 0.2 * cm

    # Left column: Beneficiar signature image (if present)
    sig_ben = _dataurl_to_imagereader(data.get("signature_beneficiar_dataurl"))
    if sig_ben:
        try:
            sw, sh = sig_ben.getSize()
            scale = min(sig_img_w_max / sw, sig_img_h / sh, 1.0)
            dw, dh = sw * scale, sh * scale
            c.drawImage(sig_ben, center_left - dw / 2, sig_img_y + (sig_img_h - dh) / 2, width=dw, height=dh)
        except Exception:
            pass

    # Right column: Prestator/Agent signature image (if present)
    sig_prest = _dataurl_to_imagereader(data.get("signature_prestator_dataurl"))
    if sig_prest:
        try:
            sw, sh = sig_prest.getSize()
            scale = min(sig_img_w_max / sw, sig_img_h / sh, 1.0)
            dw, dh = sw * scale, sh * scale
            c.drawImage(sig_prest, center_right - dw / 2, sig_img_y + (sig_img_h - dh) / 2, width=dw, height=dh)
        except Exception:
            pass

    # Signature lines (horizontal lines under images)
    line_y = sig_img_y - 0.3 * cm
    line_w = col_w - 0.5 * cm
    line_left_x = left + 0.25 * cm
    line_right_x = left + col_w + 0.25 * cm

    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(line_left_x, line_y, line_left_x + line_w, line_y)
    c.line(line_right_x, line_y, line_right_x + line_w, line_y)

    y = line_y - 0.4 * cm

    # Names below signature lines (centered in each column)
    set_font(False, 9.5)
    ben_name_display = ben_nume if ben_nume else "________________________"
    c.drawCentredString(center_left, y, ben_name_display[:40])
    
    # Right column: Agent name + Agency name
    agent_display = agent_name[:30] if agent_name else "Agent"
    c.drawCentredString(center_right, y, agent_display)
    y -= 0.35 * cm
    c.drawCentredString(center_right, y, (agency_name or "__________")[:40])
    y -= 0.5 * cm

    footer()
    c.save()
    return buffer.getvalue()
