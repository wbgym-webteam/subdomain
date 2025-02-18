from flask import Blueprint, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import json

from .models import Student

auth = Blueprint("auth", __name__)
from . import db


def logincode_exists(c):
    student_id = db.session.execute(
        db.select(Student.id).filter_by(logincode=c)
    ).one_or_none()
    if student_id == None:
        return False
    return str(student_id[0])


@auth.route("/login", methods=["GET", "POST"])
def login():
    session["logged_in"] = False

    if request.method == "POST":
        # Get the status of the models
        with open("app/data/module_status.json", "r") as f:
            module_status = json.load(f)

        if (
            request.form.get("event") == "tdw"
            and module_status["modules"]["TdW"] == "active"
        ):
            logincode = request.form.get("logincode")
            student_id = logincode_exists(logincode)
            print(student_id)
            if student_id:
                session["tdw_student_id"] = student_id
                session["logged_in"] = True
                return redirect("/tdw")  # Redirect to a student dashboard or home page
            else:
                return render_template("login.html", error="Invalid login code")
        elif (
            request.form.get("event") == "sms"
            and module_status["modules"]["SmS"] == "active"
        ):
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
