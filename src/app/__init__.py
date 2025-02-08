from flask import Flask
from flask import render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# Importing Views
from .views import views
from .auth import auth
from .admin_views import admin_views
from .gog_views import gog
from .tdw_views import tdw

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(admin_views, url_prefix="/admin")
    app.register_blueprint(gog, url_prefix="/gog")
    app.register_blueprint(tdw, url_prefix="/tdw")

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///wbgym.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)

    from .models import Student, Presentation

    return app
