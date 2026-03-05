from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Optional, Length, Regexp


class ChirieForm(FlaskForm):
    data_vizionarii = DateField("Data vizionării", validators=[DataRequired()])
    ora_vizionarii = TimeField("Ora vizionării", validators=[DataRequired()])

    nume = StringField(
        "Nume complet",
        validators=[DataRequired(), Length(min=2, max=120)]
    )

    # ✅ CNP scos complet

    telefon = StringField(
        "Număr de telefon",
        validators=[DataRequired(), Length(min=6, max=20)]
    )

    email = StringField(
        "Mail (opțional)",
        validators=[Optional(), Email(message="Email invalid.")]
    )

    tip_imobil = StringField(
        "Tip imobil (ex. Apartament cu 2 camere)",
        validators=[DataRequired(), Length(min=2, max=80)]
    )

    adresa_locuintei = StringField(
        "Adresa completă a imobilului",
        validators=[DataRequired(), Length(min=3, max=200)]
    )

    comision_procent = StringField(
        "Comision (ex. 50% plus TVA)",
        validators=[
            DataRequired(),
            Regexp(
                r"^[A-Za-z0-9ăâîșțĂÂÎȘȚ %.+\-_/]{1,50}$",
                message="Introduceți un comision valid (ex: 50%, negociabil, 10% + TVA)"
            ),
        ],
    )
