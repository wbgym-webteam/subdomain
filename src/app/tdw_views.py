from flask import Flask, render_template, request, redirect, url_for, Blueprint, session
import sqlalchemy
from sqlalchemy import text
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
            presentations_dict = dict()
            presentations_list = list()

            db_presentations = db.session.execute(db.select(Presentation)).all()

            for presentation in db_presentations:
                if str(grade) in presentation[0].grades:
                    presentations_list.append(str(presentation[0].title))
                    presentations_list.append(str(presentation[0].presenter))
                    presentations_list.append(str(presentation[0].abstract))
                    presentation_id = str(presentation[0]).split()[1][0:-1]
                    presentations_dict[presentation_id] = presentations_list
                    presentations_list = list()

            # Get the chosen presentations
            chosen_presentations = list()
            results = db.session.execute(
                text(
                    f"SELECT presentation_id FROM selections WHERE student_id = {student_id}"
                )
            ).all()

            if results is None:
                chosen_presentations = []
            else:
                for result in results:
                    chosen_presentations.append(str(result[0]))

            return render_template(
                "tdw/tdw_selection.html",
                student=full_name,
                presentations=presentations_dict,
                chosen_presentations=chosen_presentations,
            )
    else:
        return redirect("/login")


@tdw.route("/submit_selection", methods=["POST"])
def submit_selection():
    if request.method == "POST":
        student_id = str(session["tdw_student_id"])
        chosen_presentations = request.form.getlist("options")

        # Insert new Presentation Selections
        for presentation_id in chosen_presentations:
            query_result = db.session.execute(
                text(
                    f"SELECT * FROM selections WHERE student_id = {student_id} AND presentation_id = {presentation_id}"
                )
            ).one_or_none()
            if query_result is None:
                db.session.execute(
                    text(
                        f"INSERT INTO selections (student_id, presentation_id) VALUES ({student_id}, {presentation_id})"
                    )
                )
                db.session.commit()
            else:
                pass

        chosen_presentations_str = (
            str(chosen_presentations)
            .replace("[", "(")
            .replace("]", ")")
            .replace('"', "")
        )

        query_result = db.session.execute(
            text(
                f"SELECT presentation_id FROM selections WHERE student_id = {student_id} AND presentation_id NOT IN {chosen_presentations_str}"
            )
        ).all()

        if query_result is not None:
            for result in query_result:
                db.session.execute(
                    text(
                        f"DELETE FROM selections WHERE student_id = {student_id} AND presentation_id = {str(result[0])}"
                    )
                )
                db.session.commit()
    return redirect("/tdw")
