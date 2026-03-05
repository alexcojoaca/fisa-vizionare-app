from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Optional, Length, Regexp
from wtforms.validators import Optional, Length


class ChirieForm(FlaskForm):
    data_vizionarii = DateField("Data vizionării", validators=[DataRequired()])
    ora_vizionarii = TimeField("Ora vizionării", validators=[DataRequired()])

    nume = StringField("Nume complet vizitator", validators=[DataRequired(), Length(min=2, max=120)])
    cnp = StringField(
        "CNP (opțional, dar recomandat pentru o identificare clară în caz de litigiu)",
        validators=[
            Optional(),
            Regexp(r"^\d{13}$", message="CNP trebuie să aibă 13 cifre.")
        ],
    )
    telefon = StringField(
        "Număr de telefon",
        validators=[
            DataRequired(),
            Regexp(r"^\+?\d{9,15}$", message="Telefon invalid (ex: 07..., +40...).")
        ],
    )
    email = StringField("Mail (obțional)", validators=[Optional(), Email(message="Email invalid.")])

    tip_imobil = StringField("Tip imobil (ex. Apartament cu 2 camere)", validators=[DataRequired(), Length(min=2, max=80)])
    adresa_locuintei = StringField("Adresa completă a imobilului", validators=[DataRequired(), Length(min=3, max=200)])

    comision_procent = StringField(
        "Comision % (ex. 2% plus TVA)",
      validators=[
        DataRequired(),
        Regexp(
            r"^[A-Za-z0-9ăâîșțĂÂÎȘȚ %.+\-_/]{1,50}$",
            message="Introduceți un comision valid (ex: 50%, negociabil, 10% + TVA)"
        )
    ],
)


