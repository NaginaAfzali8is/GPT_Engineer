import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///train_booking.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False