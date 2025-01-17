from flask import Flask, render_template, request, redirect, url_for, Blueprint

gog = Blueprint("gog", __name__)


@gog.route("/")
def redirectToLogin():
    return redirect("/gog/login")


@gog.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pass
    elif request.method == "GET":
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


@gog.route("ranking")
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