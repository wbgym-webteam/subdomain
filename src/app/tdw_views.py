from flask import Flask, render_template, request, redirect, url_for, Blueprint, session
import sqlalchemy
from .models import Student, Presentation

from . import db

tdw = Blueprint("tdw", __name__)


@tdw.route("/", methods=["GET", "POST"])
def selection():
    if session["tdw_student_id"]:
        if request.method == "POST":
            pass
        else:
            # Get the student
            student_id = str(session["tdw_student_id"])
            db_current_student = db.session.execute(
                db.select(
                    Student.first_name, Student.last_name, Student.grade
                ).filter_by(id=student_id)
            ).one_or_none()

            current_student = dict(db_current_student._mapping)

            full_name = (
                f'{current_student["first_name"]} {current_student["last_name"]}'
            )
            grade = current_student["grade"]

            # Get the presentations
            presentations_list = list()

            db_presentations = db.session.execute(db.select(Presentation)).all()

            for presentation in db_presentations:
                if str(grade) in presentation[0].grades:
                    presentations_list.append(presentation)

            return render_template(
                "tdw/tdw_selection.html",
                student=full_name,
                presentations=presentations_list,
            )
    else:
        return redirect("/login")
