from flask import Flask
from flask import render_template, redirect
import sqlite3
from migrations import migrate

db = sqlite3.connect("wbgym.db")
migrate(db)

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login(request):
    if request.method == "POST":
        pass
        # Login Logic
    else:
        return render_template("login.html")
