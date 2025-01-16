from flask import Flask
from flask import render_template, redirect
import sqlite3

from .migrations import migrate

# Importing Views
from .views import views
from .auth import auth
from .gog_views import gog


def create_app():
    app = Flask(__name__)

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(gog, url_prefix="/gog")

    db = sqlite3.connect("wbgym.db")
    migrate(db)

    return app
