from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired
from models import Train

class BookingForm(FlaskForm):
    passenger_name = StringField('Passenger Name', validators=[DataRequired()])
    train = SelectField('Train', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Book')

    def __init__(self, *args, **kwargs):
        super(BookingForm, self).__init__(*args, **kwargs)
        self.train.choices = [(train.id, train.name) for train in Train.query.all()]