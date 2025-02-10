from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wbgym.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here'

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    with app.app_context():
        # Import models here to avoid circular imports
        from . import models
        db.create_all()

        # Register blueprints inside app context
        from .gog_views import gog
        from .views import main_views
        from .auth import auth

        app.register_blueprint(gog, url_prefix='/gog')
        app.register_blueprint(main_views, url_prefix='/')
        app.register_blueprint(auth, url_prefix='/auth')

    return app
