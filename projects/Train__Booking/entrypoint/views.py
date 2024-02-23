from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Train, Booking
from forms import BookingForm

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
def index():
    trains = Train.query.all()
    return render_template('index.html', trains=trains)

@main_blueprint.route('/book', methods=['GET', 'POST'])
def book():
    form = BookingForm()
    if form.validate_on_submit():
        booking = Booking(passenger_name=form.passenger_name.data, train_id=form.train.data)
        db.session.add(booking)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('book.html', form=form)