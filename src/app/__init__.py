from flask import Flask
from flask import render_template, redirect
import sqlite3
from flask_sqlalchemy import SQLAlchemy

from .migrations import migrate

# Importing Views
from .views import views
from .auth import auth
from .gog_views import gog

#test
db = SQLAlchemy()
#test

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wbgym.db'  # Use SQLAlchemy instead of sqlite3
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable warnings
    db.init_app(app)

    #test
    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(gog, url_prefix="/gog")
    #test
    #db = sqlite3.connect("wbgym.db")  test

    with app.app_context():
        migrate(db)

    return app
