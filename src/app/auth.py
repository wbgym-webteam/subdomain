from flask import Blueprint, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import json

auth = Blueprint("auth", __name__)
db = SQLAlchemy()


def logincode_exists(c):
    return db.session.query(Student).filter_by(logincode=c).first() is not None


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get the status of the models
        with open("app/data/module_status.json", "r") as f:
            module_status = json.load(f)

        if request.form.get("options") == "tdw" and module_status["TdW"] == "Active":
            logincode = request.form.get("logincode")
            student = logincode_exists(logincode)
            if student:
                session["tdw.student_id"] = student.student_id
                return redirect("/tdw")  # Redirect to a student dashboard or home page
            else:
                return render_template("login.html", error="Invalid login code")
        elif request.form.get("options") == "sms" and module_status["SmS"] == "Active":
            pass
        # TODO: add the logic here, when the module is in dev
        else:
            return render_template("login.html", error="Module not available for login")
    else:
        return render_template("login.html")


@auth.route("/tdw_logout")
def tdw_logout():
    session.pop("tdw.student_id", None)
    return redirect("/login")  # Redirect to a student dashboard or home page


@auth.route("/admin_login", methods=["GET", "POST"])
def adminLogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # FIXME
        if username == "admin" and password == "admin":
            redirect("/admin_dashboard")

    return render_template("admin/admin_login.html")
