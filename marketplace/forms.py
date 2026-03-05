import re
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, TextAreaField, BooleanField, SelectMultipleField, StringField
from wtforms.validators import InputRequired, Optional, NumberRange, ValidationError

# Reject description if it contains phone-like patterns (RO and generic 9+ digits)
PHONE_IN_DESCRIPTION_PATTERN = re.compile(
    r"(?:0[237]\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d|"
    r"\+\s*40[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d|"
    r"00\s*40[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d[\s.\-]*\d|"
    r"(?:\d[\s.\-]*){8,}\d)",
    re.IGNORECASE,
)

# Reject description if it contains URLs/links
LINK_IN_DESCRIPTION_PATTERN = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|[a-z0-9-]+\.(?:ro|com|org|net)[^\s]*",
    re.IGNORECASE,
)

REQUEST_TYPE_CHOICES = [
    ("cumparare", "Cumpărare"),
    ("inchiriere", "Închiriere"),
]
# Pentru anunțuri (oferte): etichete Vânzare/Închiriere
REQUEST_TYPE_ANUNT_CHOICES = [
    ("cumparare", "Vânzare"),
    ("inchiriere", "Închiriere"),
]
PROPERTY_TYPE_CHOICES = [
    ("apartament", "Apartament"),
    ("casa", "Casă"),
    ("teren", "Teren"),
    ("birou", "Birou"),
    ("spatiu_industrial", "Spațiu industrial"),
]
# Pentru anunțuri: + Spațiu comercial, Birou, Spațiu industrial, Casa/vila
PROPERTY_TYPE_ANUNT_CHOICES = [
    ("apartament", "Apartament"),
    ("casa", "Casă/Vilă"),
    ("teren", "Teren"),
    ("spatiu_comercial", "Spațiu comercial"),
    ("birou", "Birou"),
    ("spatiu_industrial", "Spațiu industrial"),
]
ETAJ_CHOICES = [("P", "Parter"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5+")]


def _coerce_zone_id(x):
    """Coerce zone id; nu ridica ValueError pentru '' sau valori invalide."""
    if x is None or (isinstance(x, str) and not str(x).strip()):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


class BuyerRequestForm(FlaskForm):
    request_type = SelectField(
        "Tip cerere",
        choices=REQUEST_TYPE_CHOICES,
        validators=[InputRequired(message="Selectează tipul cererii.")],
    )
    property_type = SelectField(
        "Tip imobil",
        choices=PROPERTY_TYPE_CHOICES,
        validators=[InputRequired(message="Selectează tipul imobilului.")],
    )
    zone_ids = SelectMultipleField(
        "Zone (minim una)",
        coerce=_coerce_zone_id,
        validators=[InputRequired(message="Trebuie să selectezi cel puțin o zonă.")],
    )
    budget_min = StringField(
        "Buget minim (€)",
        validators=[Optional()],
    )
    budget_max = StringField(
        "Buget maxim (€)",
        validators=[Optional()],
    )
    rooms = IntegerField(
        "Camere",
        validators=[Optional(), NumberRange(min=1, max=20)],
    )
    year_min = IntegerField(
        "An construcție minim",
        validators=[Optional(), NumberRange(min=1900, max=2100)],
    )
    year_max = IntegerField(
        "An construcție maxim",
        validators=[Optional(), NumberRange(min=1900, max=2100)],
    )
    description = TextAreaField(
        "Descriere (opțional)",
        validators=[Optional()],
    )
    urgent = BooleanField("Urgent", default=False, false_values=(False, "0", ""))
    plus_tva = BooleanField("Buget plus TVA", default=False, false_values=(False, "0", ""))
    contact_phone = StringField(
        "Telefon de contact (opțional)",
        validators=[Optional()],
    )
    # Vizibil doar pentru tine: număr al persoanei pentru care cauți (să știi cui îi cauți)
    client_phone_private = StringField(
        "Telefon persoană pentru care cauți (vizibil doar pentru tine)",
        validators=[Optional()],
    )

    def validate_zone_ids(self, field):
        """Cel puțin o zonă validă (nu doar None din coerce)."""
        valid = [z for z in (field.data or []) if z is not None]
        if not valid:
            raise ValidationError("Trebuie să selectezi cel puțin o zonă.")
        field.data = valid

    def parse_budget(self, value):
        """
        Parse budget value from string format to integer.
        Accepts strings like: "100000", "100.000", "100 000", "100.000€", "€100.000", "100 eur", "100 euro"
        Removes spaces, dots, commas (thousand separators), currency symbols, and currency text.
        Returns int value or None if input is empty/invalid.
        """
        if value is None:
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            # Remove spaces, dots, commas (thousand separators)
            s = s.replace(" ", "").replace(".", "").replace(",", "")
            # Remove currency symbols (€, $, £, etc.)
            s = re.sub(r"[€$£¥₹]", "", s, flags=re.IGNORECASE)
            # Remove currency text (eur, euro, ron, lei) - case insensitive
            s = re.sub(r"\b(eur|euro|ron|lei)\b", "", s, flags=re.IGNORECASE)
            s = s.strip()
            # Check if remaining string is digits only
            if not s or not s.isdigit():
                return None
            return int(s)
        return None

    def validate_budget_min(self, field):
        """Validate and normalize budget_min field."""
        if not field.data or not str(field.data).strip():
            # Empty is allowed (Optional validator)
            field.data = None
            return
        
        normalized = self.parse_budget(field.data)
        if normalized is None:
            raise ValidationError("Buget invalid.")
        
        # Store normalized integer in field.data
        field.data = normalized

    def validate_budget_max(self, field):
        """Validate and normalize budget_max field, and check min <= max."""
        if not field.data or not str(field.data).strip():
            # Empty is allowed (Optional validator)
            field.data = None
            return
        
        normalized = self.parse_budget(field.data)
        if normalized is None:
            raise ValidationError("Buget invalid.")
        
        # Store normalized integer in field.data
        field.data = normalized
        
        # Cross-field validation: check min <= max (asigură int pentru comparație)
        min_val = self.budget_min.data
        if min_val is not None and not isinstance(min_val, int):
            min_val = self.parse_budget(min_val) if min_val else None
        if min_val is not None and normalized < min_val:
            raise ValidationError("Bugetul maxim trebuie să fie ≥ minim.")

    def validate_description(self, field):
        if not field.data or not field.data.strip():
            return
        if PHONE_IN_DESCRIPTION_PATTERN.search(field.data):
            raise ValidationError(
                "Te rugăm nu introduce numere de telefon în descriere. Folosește câmpul «Telefon de contact»."
            )
        if LINK_IN_DESCRIPTION_PATTERN.search(field.data):
            raise ValidationError("Te rugăm nu introduce linkuri sau URL-uri în descriere.")

    def validate_contact_phone(self, field):
        if not field.data or not field.data.strip():
            return
        raw = field.data.strip()
        # Allow digits, spaces, +, -, parentheses
        cleaned = re.sub(r"[^\d\s+\-()]", "", raw)
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 10:
            raise ValidationError("Introdu un număr de telefon valid (minim 10 cifre).")
        if len(digits) > 12:
            raise ValidationError("Numărul de telefon este prea lung.")


def _parse_budget(value):
    """Parse price/budget string to int."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        s = value.strip().replace(" ", "").replace(".", "").replace(",", "")
        s = re.sub(r"[€$£¥₹]", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(eur|euro|ron|lei)\b", "", s, flags=re.IGNORECASE)
        s = s.strip()
        if not s or not s.isdigit():
            return None
        return int(s)
    return None


class SellerOfferForm(FlaskForm):
    """Form pentru anunț (ofertă): tip, imobil, preț unic, suprafețe, etaj, an, parcare, comision, contact."""
    request_type = SelectField(
        "Tip anunț",
        choices=REQUEST_TYPE_ANUNT_CHOICES,
        validators=[InputRequired(message="Selectează tipul anunțului (vânzare/închiriere).")],
    )
    property_type = SelectField(
        "Tip imobil",
        choices=PROPERTY_TYPE_ANUNT_CHOICES,
        validators=[InputRequired(message="Selectează tipul imobilului.")],
    )
    zone_ids = SelectMultipleField(
        "Zone (minim una)",
        coerce=_coerce_zone_id,
        validators=[InputRequired(message="Trebuie să selectezi cel puțin o zonă.")],
    )
    price = StringField("Preț imobil (€)", validators=[Optional()])
    price_negotiable = BooleanField("Preț negociabil", default=False, false_values=(False, "0", ""))
    plus_tva = BooleanField("Plus TVA", default=False, false_values=(False, "0", ""))
    rooms = IntegerField("Camere", validators=[Optional(), NumberRange(min=1, max=20)])
    surface_utila = StringField("Suprafață utilă (m²)", validators=[Optional()])
    surface_totala = StringField("Suprafață totală (m²)", validators=[Optional()])
    surface_balcon = StringField("Suprafață balcon (m²)", validators=[Optional()])
    surface_terasa = StringField("Suprafață terasă (m²)", validators=[Optional()])
    surface_curte = StringField("Suprafață curte (m²)", validators=[Optional()])
    anul_constructiei = IntegerField("Anul construcției", validators=[Optional(), NumberRange(min=1900, max=2100)])
    nr_etaje_cladire = IntegerField("Etaje clădire", validators=[Optional(), NumberRange(min=1, max=30)])
    nr_locuri_parcare = IntegerField("Număr locuri parcare", validators=[Optional(), NumberRange(min=0, max=20)])
    offers_commission = BooleanField("Ofer comision", default=False, false_values=(False, "0", ""))
    commission_value = StringField("Comision (ex: 3% sau 500 €)", validators=[Optional()])
    description = TextAreaField("Descriere (opțional)", validators=[Optional()])
    contact_phone = StringField("Telefon de contact (opțional)", validators=[Optional()])
    # Vizibil doar pentru tine: numele proprietarului (să știi cui îi desemnezi anunțul)
    owner_name_private = StringField(
        "Numele proprietarului (vizibil doar pentru tine)",
        validators=[Optional()],
    )

    def validate_zone_ids(self, field):
        """Cel puțin o zonă validă (nu doar None din coerce)."""
        valid = [z for z in (field.data or []) if z is not None]
        if not valid:
            raise ValidationError("Trebuie să selectezi cel puțin o zonă.")
        field.data = valid

    def validate_price(self, field):
        if not field.data or not str(field.data).strip():
            field.data = None
            return
        normalized = _parse_budget(field.data)
        if normalized is None:
            raise ValidationError("Preț invalid.")
        field.data = normalized

    def validate_commission_value(self, field):
        if not self.offers_commission.data:
            return
        if not field.data or not str(field.data).strip():
            raise ValidationError("Dacă oferi comision, completează valoarea.")

    def validate_description(self, field):
        if not field.data or not field.data.strip():
            return
        if PHONE_IN_DESCRIPTION_PATTERN.search(field.data):
            raise ValidationError("Nu introduce numere de telefon în descriere. Folosește câmpul «Telefon de contact».")
        if LINK_IN_DESCRIPTION_PATTERN.search(field.data):
            raise ValidationError("Nu introduce linkuri sau URL-uri în descriere.")

    def validate_contact_phone(self, field):
        if not field.data or not field.data.strip():
            return
        raw = field.data.strip()
        cleaned = re.sub(r"[^\d\s+\-()]", "", raw)
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 10:
            raise ValidationError("Introdu un număr de telefon valid (minim 10 cifre).")
        if len(digits) > 12:
            raise ValidationError("Numărul de telefon este prea lung.")
