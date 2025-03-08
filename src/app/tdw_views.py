# Module Import
from flask import Flask, render_template, request, redirect, url_for, Blueprint, session
import sqlalchemy
from sqlalchemy import text
from .models import Student, Presentation

# Importing DB for sqlalchemy
from . import db

# Blueprint
tdw = Blueprint("tdw", __name__)

# ---------------------------------------------------------------
# TDW Routes
# ---------------------------------------------------------------
#
# This is the view that the logged in student will see


@tdw.route("/", methods=["GET", "POST"])
def selection():
    # Checks if the user is logged in
    if session.get("logged_in", True) == True:
        if request.method == "POST":
            pass  # idk you can delete this but be careful pls :D
        else:
            # Get the student id from the session storage
            student_id = session.get("tdw_student_id")
            if student_id is None:
                return redirect("/login")
            student_id = str(student_id)

            # DB Query to get the student's name and grade
            db_current_student = db.session.execute(
                db.select(
                    Student.first_name, Student.last_name, Student.grade
                ).filter_by(id=student_id)
            ).one_or_none()

            # It creates a dictoionary from the query result to access the values by key
            current_student = dict(db_current_student._mapping)

            # Extraction of the student's name for display on the template
            full_name = (
                f'{current_student["first_name"]} {current_student["last_name"]}'
            )

            # The grade is relevant for the options that will be displayed
            grade = current_student["grade"]

            # Get the presentations
            #
            # So the dictionary will be having the presentation_id as the key and the value will be a list of the presentation's title, presenter and abstract
            presentations_dict = dict()
            presentations_list = list()

            db_presentations = db.session.execute(db.select(Presentation)).all()

            for presentation in db_presentations:
                if str(grade) in presentation[0].grades:
                    presentations_list.append(str(presentation[0].title))
                    presentations_list.append(str(presentation[0].presenter))
                    presentations_list.append(str(presentation[0].abstract))
                    # Ik it is kinda goofy but it works, so you need to customize the string yk
                    presentation_id = str(presentation[0]).split()[1][0:-1]
                    # Here it enters the presentation (list) into the dictionary
                    presentations_dict[presentation_id] = presentations_list
                    # Now it clears up the list for the next presentation
                    presentations_list = list()

            # Get the ALREADY chosen presentations
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

            # When rendering the template, the student's name, the presentations and the already chosen presentations are passed as arguments, so they will be displayed on the site
            return render_template(
                "tdw/tdw_selection.html",
                student=full_name,
                presentations=presentations_dict,
                chosen_presentations=chosen_presentations,
            )
    else:
        return redirect("/login")


#
# This view will never be displayed, because the only accepted method is POST (not to confuse w/ the classic GET Method)
# But it does the magic behind the selection :o


@tdw.route("/submit_selection", methods=["POST"])
def submit_selection():
    if request.method == "POST":
        # first thing it needs to work is the student_id and the chosen presentations by the students
        student_id = str(session["tdw_student_id"])
        # it gets the chosen presentations from the form in the html template.
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


@tdw.route("/logout")
def logout():
    # Remove the user's session
    session.pop("tdw_student_id", None)
    return redirect("/login")
