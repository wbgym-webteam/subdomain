from flask import Flask
from flask import render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
import secrets  # Add this import

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # Use environment variable if set, otherwise use a fixed fallback key
    # WARNING: In production, always set SECRET_KEY environment variable!
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        print("WARNING: SECRET_KEY not set in environment. Using fallback key. Set SECRET_KEY for production!")
        # Use a persistent fallback key (not random) so sessions persist across restarts during development
        # In production, you MUST set the SECRET_KEY environment variable!
        secret_key = "dev-fallback-key-change-in-production"
    app.config["SECRET_KEY"] = secret_key

    # Session configuration
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = False  # Set to True if using HTTPS
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

    # File upload configuration
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max file size

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///wbgym.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        from .models import Student, Presentation, Selection, BlockedPresentation, PTStudent, PTPresentation, PTSelection, PTAssignment

        # Importing Views
        from .views import views
        from .auth import auth
        from .admin_views import admin_views
        from .tdw_views import tdw
        from .pt_views import pt
        from .pt_admin_views import pt_admin_views  # <-- add this import

        app.register_blueprint(views, url_prefix="/")
        app.register_blueprint(auth, url_prefix="/")
        app.register_blueprint(admin_views, url_prefix="/admin")
        app.register_blueprint(tdw, url_prefix="/tdw")
        app.register_blueprint(pt, url_prefix="/pt")
        app.register_blueprint(pt_admin_views, url_prefix="/admin")  # <-- add url_prefix

        # db.drop_all()
        db.create_all()

        return app
