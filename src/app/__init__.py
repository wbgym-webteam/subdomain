from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///wbgym.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-here'

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static')
    app.config.from_object(config_class)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wbgym.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here'

    # Update session configuration
    app.config['SESSION_COOKIE_NAME'] = 'admin_session'
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_PROTECTION'] = 'strong'

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    with app.app_context():
        from . import models
        db.create_all()

        from .gog_views import gog
        from .views import main_views
        from .auth import auth
        from .admin_views import admin

        app.register_blueprint(gog, url_prefix='/gog')
        app.register_blueprint(main_views, url_prefix='/')
        app.register_blueprint(auth, url_prefix='/auth')
        app.register_blueprint(admin)

    # Register CLI commands
    from . import cli
    cli.init_app(app)

    return app
