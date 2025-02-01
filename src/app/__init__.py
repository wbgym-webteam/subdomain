from flask import Flask
from flask import render_template, redirect
import sqlalchemy

from .migrations import migrate

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
    # db = sqlalchemy.connect("wbgym.db")
    # migrate(db)

    return app
