from flask import Flask
from flask import render_template, redirect
import sqlite3

# from migrations import migrate

# Importing Views
from .views import views
from .auth import auth
from .GoG_views import GoG


def create_app():
    app = Flask(__name__)

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(GoG, url_prefix="/gog")

    # db = sqlite3.connect("wbgym.db")
    # migrate(db)

    return app
