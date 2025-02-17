from flask import Flask, render_template, request, redirect, url_for, Blueprint, session
import sqlalchemy
from .models import Student, Presentation

from . import db

tdw = Blueprint("tdw", __name__)


@tdw.route("/", methods=["GET", "POST"])
def selection():
    if session["tdw.student_id"]:
        if request.method == "POST":
            pass
        else:
            # Get the student
            current_student = db.session.execute(
                db.select(Student.first_name, Student.last_name, Student.grade)
                .filter_by(id=session["tdw.student_id"])
                .mappings()
                .one_or_none()
            )
            full_name = (
                f'{current_student["first_name"]} {current_student["last_name"]}'
            )
            grade = current_student["grade"]

            # Get the presentations
            presentations_list = list()

            db_presentations = db.session.execute(
                db.select(
                    Presentation.id,
                    Presentation.title,
                    Presentation.presenter,
                    Presentation.abstract,
                    Presentation.grades,
                )
            )

            for presentation in db_presentations:
                if grade in db_presentations["grades"]:
                    presentations_list.append(presentation)

            return render_template(
                "tdw/tdw_selection.html",
                student=full_name,
                presentations=presentation_list,
            )
    else:
        return redirect("/login")
