from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wbgym.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here'

    db.init_app(app)

    with app.app_context():
        # Import models here to avoid circular imports
        from . import models
        db.create_all()

        # Register blueprints inside app context
        from .gog_views import gog
        from .views import views
        from .auth import auth

        app.register_blueprint(gog, url_prefix='/gog')
        app.register_blueprint(views, url_prefix='/views')
        app.register_blueprint(auth, url_prefix='/auth')

    return app
