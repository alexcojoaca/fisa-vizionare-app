from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class DailyActivityForm(FlaskForm):
    """Raport zilnic: vizionări, deal-uri, note."""
    viewings_count = IntegerField("Vizionări", default=0, validators=[Optional(), NumberRange(min=0)])
    deals_closed_count = IntegerField("Deal-uri închise", default=0, validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField("Notițe", validators=[Optional(), Length(max=500)])


class QuickAddForm(FlaskForm):
    """Form pentru adăugare rapidă – doar titlu."""
    title = StringField("Titlu", validators=[DataRequired(), Length(min=1, max=255)])


class TaskForm(FlaskForm):
    title = StringField("Titlu", validators=[DataRequired(), Length(min=1, max=255)])
    description = TextAreaField("Descriere / detalii", validators=[Optional(), Length(max=5000)])
    due_date = DateField("Data limită", validators=[Optional()], format="%Y-%m-%d")
    priority = SelectField(
        "Prioritate",
        choices=[("low", "Scăzută"), ("medium", "Medie"), ("high", "Ridicată")],
        default="medium",
    )
    status = SelectField(
        "Status",
        choices=[
            ("open", "Deschis"),
            ("in-progress", "În lucru"),
            ("done", "Finalizat"),
        ],
        default="open",
    )
    tags = StringField("Tag-uri (separate prin virgulă)", validators=[Optional(), Length(max=255)])
