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
        return render_template("gog_login.html")


@gog.route("/dashboard")
def home():
    return render_template("gog_dashboard.html")
