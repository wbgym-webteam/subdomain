from flask import Blueprint, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import json
import os

from .models import Student, StudentSMS

auth = Blueprint("auth", __name__)
from . import db


def logincode_exists(c):
    student_id = db.session.execute(
        db.select(Student.id).filter_by(logincode=c)
    ).one_or_none()
    if student_id == None:
        return False
    return str(student_id[0])


def sms_logincode_exists(c):
    student_id = db.session.execute(
        db.select(StudentSMS.Student_id).filter_by(logincode=c)
    ).one_or_none()
    if student_id == None:
        return False
    return str(student_id[0])


@auth.route("/login", methods=["GET", "POST"])
def login():
    session["logged_in"] = False
    # Load module status for both POST and GET requests
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        tdw_module_status = module_status["modules"]["TdW"]
        sms_module_status = module_status["modules"]["SmS"]

    if request.method == "POST":
        if request.form.get("event") == "tdw" and tdw_module_status == "active":
            logincode = request.form.get("logincode")
            student_id = logincode_exists(logincode)
            print(student_id)
            if student_id:
                session["tdw_student_id"] = student_id
                session["logged_in"] = True
                return redirect("/tdw")
            else:
                return render_template(
                    "login.html",
                    tdw_module_status=tdw_module_status,
                    sms_module_status=sms_module_status,
                    error="Ungültiger Login-Code für TdW",
                )
        elif request.form.get("event") == "sms" and sms_module_status == "active":
            logincode = request.form.get("logincode")
            student_id = sms_logincode_exists(logincode)
            print(student_id)
            if student_id:
                session["sms_student_id"] = student_id
                session["logged_in"] = True
                return redirect("/sms")
            else:
                return render_template(
                    "login.html",
                    tdw_module_status=tdw_module_status,
                    sms_module_status=sms_module_status,
                    error="Ungültiger Login-Code für SmS",
                )
        else:
            return render_template(
                "login.html",
                tdw_module_status=tdw_module_status,
                sms_module_status=sms_module_status,
                error="Bitte wählen Sie ein aktives Modul",
            )
    else:
        return render_template(
            "login.html",
            tdw_module_status=tdw_module_status,
            sms_module_status=sms_module_status,
        )


@auth.route("/admin_login", methods=["GET", "POST"])
def adminLogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        env_admin_username = os.getenv("ADMIN_USERNAME")
        env_admin_password = os.getenv("ADMIN_PASSWORD")

        if username == env_admin_username and password == env_admin_password:
            session["admin_logged_in"] = True
            return redirect("/admin/tdw/panel")

    return render_template("admin/admin_login.html")


# When the SmS module comes, we need a normal admin panel which links to the sms admin panel and the tdw admin panel
