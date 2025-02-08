from flask import Blueprint, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

auth = Blueprint("auth", __name__)
db = SQLAlchemy()


def logincode_exists(c):
    return db.session.query(Student).filter_by(logincode=c).first() is not None


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("options") == "tdw":
            logincode = request.form.get("logincode")
            student = logincode_exists(logincode)
            if student:
                session["tdw.student_id"] = student.student_id
                return redirect(
                    "/tdw"  # TODO: set the right redirect
                )  # Redirect to a student dashboard or home page

            if logincode_exists(logincode):
                db.session.query(student).filter_by(logincode=logincode).first()
        elif request.form.get("options") == "sms":
            pass
        # TODO: add the logic here, when the module is in dev
    else:
        return render_template("login.html")


@auth.route("/tdw_logout", met)
@auth.route("/admin_login", methods=["GET", "POST"])
def adminLogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # FIXME
        if username == "admin" and password == "admin":
            redirect("/admin_dashboard")

    return render_template("admin/admin_login.html")
