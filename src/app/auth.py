from flask import Blueprint, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import json
import os

from .models import Student, PTStudent

auth = Blueprint("auth", __name__)
from . import db


def logincode_exists(c):
    student_id = db.session.execute(
        db.select(Student.id).filter_by(logincode=c)
    ).one_or_none()
    if student_id == None:
        return False
    return str(student_id[0])


def pt_logincode_exists(c):
    student_id = db.session.execute(
        db.select(PTStudent.id).filter_by(logincode=c)
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

        print(f"Form data: {request.form}")  # Debug print
        print(f"Module status: {module_status}")  # Debug print

        if (
            request.form.get("event") == "tdw"
            and module_status["modules"]["TdW"] == "active"
        ):
            logincode = request.form.get("logincode")
            student_id = logincode_exists(logincode)
            print(f"TdW login attempt - student_id: {student_id}")
            if student_id:
                session["tdw_student_id"] = student_id
                session["logged_in"] = True
                return redirect("/tdw")
            else:
                return render_template("login.html")
        elif (
            request.form.get("event") == "pt"
            and module_status["modules"].get("PT", "inactive") == "active"  # Use .get() with default
        ):
            logincode = request.form.get("logincode")
            student_id = pt_logincode_exists(logincode)
            print(f"PT login attempt - logincode: {logincode}, student_id: {student_id}")
            if student_id:
                session["pt_student_id"] = student_id
                session["logged_in"] = True
                print(f"PT login successful, redirecting to /pt")
                return redirect("/pt")
            else:
                print("PT login failed - invalid logincode")
                return render_template("login.html")
        elif (
            request.form.get("event") == "sms"
            and module_status["modules"]["SmS"] == "active"
        ):
            pass
        # TODO: add the logic here, when the module is in dev
        else:
            print(f"No matching event or module inactive")
            return render_template("login.html")
    else:
        return render_template("login.html")


@auth.route("/admin_login", methods=["GET", "POST"])
def adminLogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        env_admin_usernames = os.getenv("ADMIN_USERNAMES", "")
        env_admin_passwords = os.getenv("ADMIN_PASSWORDS", "")

        admin_usernames = [u.strip() for u in env_admin_usernames.split(",")]
        admin_passwords = [p.strip() for p in env_admin_passwords.split(",")]

        # Check if username/password pair is valid
        if username in admin_usernames and password in admin_passwords:
            session["admin_logged_in"] = True
            return redirect("/admin/tdw/panel")

    return render_template("admin/admin_login.html")


# When the SmS module comes, we need a normal admin panel which links to the sms admin panel and the tdw admin panel
