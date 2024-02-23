from flask import Flask
from models import db
from views import main_blueprint

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)
    
    with app.app_context():
        db.create_all()  # Create database tables
    
    app.register_blueprint(main_blueprint)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)