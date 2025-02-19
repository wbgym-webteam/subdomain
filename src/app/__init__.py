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

    # this is how it was before
    # app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Use environment variable if set, otherwise generate a secure random key #### remove this if you want to use how it was before
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    ####

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///wbgym.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        # from .models import Student, Presentation

        # Importing Views
        from .views import views
        from .auth import auth
        from .admin_views import admin_views
        from .gog_views import gog
        from .tdw_views import tdw

        app.register_blueprint(views, url_prefix="/")
        app.register_blueprint(auth, url_prefix="/")
        app.register_blueprint(admin_views, url_prefix="/admin")
        app.register_blueprint(gog, url_prefix="/gog")
        app.register_blueprint(tdw, url_prefix="/tdw")

        # db.drop_all()
        db.create_all()

        return app
