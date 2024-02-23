from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Train(db.Model):
    __tablename__ = 'trains'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    bookings = db.relationship('Booking', backref='train', lazy=True)
    
    def __repr__(self):
        return f'<Train {self.name}>'

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    passenger_name = db.Column(db.String(64), nullable=False)
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'), nullable=False)
    
    def __repr__(self):
        return f'<Booking {self.passenger_name} on {self.train.name}>'