from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class TeamCreateForm(FlaskForm):
    """Form pentru crearea echipei."""
    name = StringField("Nume echipă", validators=[DataRequired(), Length(min=1, max=120)])


class TeamTaskForm(FlaskForm):
    """Form pentru crearea unui task de echipă."""
    title = StringField("Titlu", validators=[DataRequired(), Length(min=1, max=255)])
    description = TextAreaField("Descriere", validators=[Optional(), Length(max=2000)])
    due_date = DateField("Deadline", validators=[DataRequired()], format="%Y-%m-%d")
    priority = SelectField(
        "Prioritate",
        choices=[("low", "Scăzută"), ("medium", "Medie"), ("high", "Ridicată")],
        default="medium",
    )
