from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length


class AgentProfileForm(FlaskForm):
    agent_name = StringField("Nume agent", validators=[DataRequired(), Length(min=2, max=120)])
    agent_phone = StringField("Telefon agent", validators=[Length(max=20)])


class AgencyProfileForm(FlaskForm):
    name = StringField("Nume agenție (ex: X SRL)", validators=[DataRequired(), Length(min=2, max=150)])
    hq_address = StringField("Sediu social", validators=[DataRequired(), Length(min=2, max=200)])
    orc_number = StringField("Nr. ORC", validators=[DataRequired(), Length(min=2, max=60)])
    cui = StringField("CUI", validators=[DataRequired(), Length(min=2, max=60)])
    iban = StringField("IBAN", validators=[DataRequired(), Length(min=4, max=80)])
    bank = StringField("Banca", validators=[DataRequired(), Length(min=2, max=80)])
    administrator = StringField("Administrator", validators=[DataRequired(), Length(min=2, max=120)])
