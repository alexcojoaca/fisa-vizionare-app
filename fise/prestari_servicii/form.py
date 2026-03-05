from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, DecimalField
from wtforms.validators import DataRequired, Optional, Length, Email, ValidationError


class PrestariForm(FlaskForm):
    # Beneficiar
    beneficiar_tip = SelectField(
        "Tip beneficiar",
        choices=[
            ("pf", "Persoană fizică (CNP)"),
            ("pj", "Persoană juridică (CUI)"),
        ],
        validators=[DataRequired()],
        default="pf",
    )
    beneficiar_nume = StringField(
        "Nume complet / Denumire",
        validators=[DataRequired(), Length(min=2, max=200)]
    )
    beneficiar_cnp = StringField(
        "CNP (opțional)",
        validators=[Optional(), Length(max=50)]
    )
    beneficiar_cui = StringField(
        "CUI (opțional)",
        validators=[Optional(), Length(max=50)]
    )
    beneficiar_adresa = StringField(
        "Adresă (opțional)",
        validators=[Optional(), Length(max=255)]
    )
    beneficiar_telefon = StringField(
        "Telefon",
        validators=[DataRequired(), Length(min=6, max=20)]
    )
    beneficiar_email = StringField(
        "Email",
        validators=[Optional(), Email(message="Email invalid."), Length(max=120)]
    )

    # Obiect (Art. 1)
    tip_tranzactie = SelectField(
        "Tip tranzacție",
        choices=[
            ("inchiriere", "Închiriere"),
            ("vanzare", "Vânzare"),
            ("cumparare", "Cumpărare"),
        ],
        validators=[DataRequired()],
    )
    imobil_tip = StringField(
        "Tip imobil",
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    imobil_adresa = StringField(
        "Adresă imobil",
        validators=[DataRequired(), Length(min=3, max=255)]
    )

    # Preț/Comision (Art. 3)
    currency = SelectField(
        "Monedă",
        choices=[
            ("RON", "RON (lei)"),
            ("EUR", "EUR (euro)"),
        ],
        validators=[DataRequired()],
        default="RON",
    )
    comision_tva = SelectField(
        "TVA",
        choices=[
            ("fara", "Fără TVA"),
            ("cu", "+ TVA"),
        ],
        validators=[DataRequired()],
        default="fara",
    )
    comision = StringField(
        "Comision",
        validators=[DataRequired()],
        default="4570.00",
    )

    def validate_comision(self, field):
        """Validate comision: allow digits, spaces, dots, commas; reject letters/symbols."""
        if not field.data:
            raise ValidationError("Comisionul este obligatoriu.")
        raw = (field.data or "").strip()
        # Allow digits, spaces, dots, commas
        cleaned = raw.replace(" ", "").replace(".", "").replace(",", "")
        if not cleaned.isdigit():
            raise ValidationError("Comisionul trebuie să conțină doar cifre, spații, puncte sau virgule.")
        if len(raw) > 50:
            raise ValidationError("Comisionul este prea lung (maxim 50 caractere).")

    # Nr contract + Data
    nr_contract = StringField(
        "Nr. contract",
        validators=[DataRequired(), Length(min=1, max=50)]
    )
    data_contractului = DateField(
        "Data contractului",
        validators=[DataRequired()],
    )
