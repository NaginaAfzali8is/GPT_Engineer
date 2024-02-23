from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Train(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    origin = db.Column(db.String(64), nullable=False)
    destination = db.Column(db.String(64), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    seats = db.Column(db.Integer, nullable=False)

    bookings = db.relationship('Booking', backref='train', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passenger_name = db.Column(db.String(64), nullable=False)
    train_id = db.Column(db.Integer, db.ForeignKey('train.id'), nullable=False)