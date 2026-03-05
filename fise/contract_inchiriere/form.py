from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Optional, Length, Regexp
from wtforms.validators import Optional, Length
from fise.chirie.form import ChirieForm as ContractForm

class ChirieForm(FlaskForm):
    data_vizionarii = DateField("Data vizionării", validators=[DataRequired()])
    ora_vizionarii = TimeField("Ora vizionării", validators=[DataRequired()])

    nume = StringField("Nume complet vizitator", validators=[DataRequired(), Length(min=2, max=120)])

    telefon = StringField(
        "Număr de telefon",
        validators=[
            DataRequired(),
            Regexp(r"^\+?\d{9,15}$", message="Telefon invalid (ex: 07..., +40...).")
        ],
    )
    email = StringField("Mail", validators=[Optional(), Email(message="Email invalid.")])

    tip_imobil = StringField("Tip imobil", validators=[DataRequired(), Length(min=2, max=80)])
    adresa_locuintei = StringField("Adresa locuinței", validators=[DataRequired(), Length(min=3, max=200)])

    comision_procent = StringField(
        "Comision (%)",
        validators=[
            DataRequired(),
            Regexp(r"^\d{1,3}(\.\d{1,2})?$", message="Ex: 50 sau 50.5")
        ],
    )
