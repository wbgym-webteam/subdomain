from flask import Flask
from flask import render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Importing Views
from .views import views
from .auth import auth
from .gog_views import gog
from .tdw_views import tdw


def create_app():
    app = Flask(__name__)

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(gog, url_prefix="/gog")

    # TODO: fix the DB
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///wbgym.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)

    return app
