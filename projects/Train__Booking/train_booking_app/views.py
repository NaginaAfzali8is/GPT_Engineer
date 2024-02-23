from flask import Blueprint, render_template, request, redirect, url_for
from .models import db, Train, Booking
from .forms import BookingForm

main = Blueprint('main', __name__)

@main.route('/')
def index():
    trains = Train.query.all()
    return render_template('index.html', trains=trains)

@main.route('/book/<int:train_id>', methods=['GET', 'POST'])
def book(train_id):
    form = BookingForm()
    train = Train.query.get_or_404(train_id)
    if form.validate_on_submit():
        booking = Booking(
            passenger_name=form.passenger_name.data,
            train_id=train.id
        )
        db.session.add(booking)
        db.session.commit()
        return redirect(url_for('main.booking_success'))
    return render_template('booking_form.html', form=form, train=train)

@main.route('/booking_success')
def booking_success():
    return render_template('success.html')

@main.route('/error')
def error():
    return render_template('error.html')