from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class BookingForm(FlaskForm):
    passenger_name = StringField('Passenger Name', validators=[DataRequired()])
    submit = SubmitField('Book Now')