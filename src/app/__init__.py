from flask import Flask
from flask import render_template, redirect
import sqlite3
from migrations import migrate

import views


def create_app():
    app = Flask(__name__)

    db = sqlite3.connect("wbgym.db")
    migrate(db)

    return app
