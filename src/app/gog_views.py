from flask import Flask, render_template, request, redirect, url_for, Blueprint
import sqlalchemy
from .models import User  # Import the User model

gog = Blueprint("gog", __name__)

DATABASE = "wbgym.db"  # Update this to the path of your SQLite database


def get_db_connection():
    conn = sqlalchemy.connect(DATABASE)
    conn.row_factory = sqlalchemy.Row
    return conn


@gog.route("/")
def redirectToLogin():
    return redirect("/gog/login")


@gog.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()

        if user and User.check_password(user["password_hash"], password):
            return redirect(url_for("gog.dashboard"))
        else:
            return render_template("gog/gog_login.html", error="Invalid credentials")

    return render_template("gog/gog_login.html")


@gog.route("/dashboard")
def dashboard():
    return render_template("gog/gog_dashboard.html")


@gog.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_setup.html")


@gog.route("/ranking")
def ranking():
    return render_template("gog/gog_ranking.html")


@gog.route("/teamManagement", methods=["GET", "POST"])
def teamManagement():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_teamManagement.html")


@gog.route("/logs", methods=["GET", "POST"])
def logs():
    if request.method == "POST":
        pass
    else:
        return render_template("gog/gog_logs.html")
