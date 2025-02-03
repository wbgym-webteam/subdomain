from flask import Blueprint, render_template, request, redirect, session

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pass
    else:
        return render_template("login.html")


@auth.route("/admin-login", methods=["GET", "POST"])
def adminLogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # FIXME
        if username == "admin" and password == "admin":
            redirect("/admin-dashboard")

    return render_template("admin/admin_login.html")
