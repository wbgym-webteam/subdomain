from flask import Flask, render_template, request, redirect, url_for, Blueprint, session
import sqlalchemy
from sqlalchemy import text
from .models import PTStudent, PTPresentation, PTSelection, PTAssignment

# Importing DB for sqlalchemy
from . import db

# Blueprint
pt = Blueprint("pt", __name__)

# ---------------------------------------------------------------
# TDW Routes
# ---------------------------------------------------------------
#
# This is the view that the logged in student will see


@pt.route("/", methods=["GET", "POST"])
def selection():
    # Checks if the user is logged in
    if session.get("logged_in", True) == True:
        if request.method == "POST":
            pass  # idk you can delete this but be careful pls :D
        else:
            # Get the student id from the session storage
            student_id = session.get("pt_student_id")  # Changed from tdw_student_id
            if student_id is None:
                return redirect("/login")
            student_id = str(student_id)

            # Check if assignments have been made
            assignments_query = db.session.execute(
                text("""
                    SELECT p.title, p.presenter, p.slot, p.column, p.room, p.description
                    FROM pt_assignments a
                    JOIN pt_presentations p ON a.presentation_id = p.id
                    WHERE a.student_id = :student_id
                    ORDER BY p.slot
                """),
                {"student_id": student_id}
            ).all()
            
            # If assignments exist, show them instead of selection interface
            if assignments_query:
                # DB Query to get the student's name and grade
                db_current_student = db.session.execute(
                    db.select(
                        PTStudent.first_name, PTStudent.last_name, PTStudent.grade
                    ).filter_by(id=student_id)
                ).one_or_none()

                current_student = dict(db_current_student._mapping)
                full_name = (
                    f'{current_student["first_name"]} {current_student["last_name"]}'
                )
                
                return render_template(
                    "pt/pt_assignments.html",
                    student=full_name,
                    assignments=assignments_query
                )

            # DB Query to get the student's name and grade
            db_current_student = db.session.execute(
                db.select(
                    PTStudent.first_name, PTStudent.last_name, PTStudent.grade
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

            # Get the presentations organized by columns
            presentations_by_column = {}
            
            db_presentations = db.session.execute(db.select(PTPresentation)).all()

            for presentation in db_presentations:
                pres = presentation[0]
                column = pres.column
                if column not in presentations_by_column:
                    presentations_by_column[column] = {}
                
                # Create a key for merging courses with same name and description
                merge_key = f"{pres.title}|{pres.description}"
                
                if merge_key not in presentations_by_column[column]:
                    presentations_by_column[column][merge_key] = {
                        'id': f"merged_{hash(merge_key)}",  # Unique ID for merged course
                        'presentation_ids': [],  # List of actual presentation IDs
                        'title': pres.title,
                        'description': pres.description,
                        'teacher': pres.presenter,
                        'hosts': pres.room,
                        'rooms': [pres.room]  # Track all rooms
                    }
                else:
                    # Add room to existing merged course if different
                    if pres.room not in presentations_by_column[column][merge_key]['rooms']:
                        presentations_by_column[column][merge_key]['rooms'].append(pres.room)
                        presentations_by_column[column][merge_key]['hosts'] += f", {pres.room}"
                
                # Add the actual presentation ID to the merged course
                presentations_by_column[column][merge_key]['presentation_ids'].append(pres.id)
            
            # Convert to list format for template
            for column in presentations_by_column:
                presentations_by_column[column] = list(presentations_by_column[column].values())

            # Get existing selections with rankings - use any ranking from merged courses
            existing_selections = {}
            rows = db.session.execute(
                text("SELECT presentation_id, ranking FROM pt_selections WHERE student_id = :sid"),
                {"sid": student_id},
            ).all()
            
            # Map rankings to merged courses
            for presentation_id, ranking in rows:
                # Find which merged course this presentation belongs to
                for column_presentations in presentations_by_column.values():
                    for merged_course in column_presentations:
                        if presentation_id in merged_course['presentation_ids']:
                            existing_selections[merged_course['id']] = int(ranking or 0)
                            break

            # When rendering the template, pass organized data
            return render_template(
                "pt/pt_selection.html",
                student=full_name,
                presentations_by_column=presentations_by_column,
                existing_selections=existing_selections,
            )
    else:
        return redirect("/login")


#
# This view will never be displayed, because the only accepted method is POST (not to confuse w/ the classic GET Method)
# But it does the magic behind the selection :o


@pt.route("/submit_selection", methods=["POST"])
def submit_selection():
    if request.method == "POST":
        student_id = str(session["pt_student_id"])
        
        # Clear existing selections for this student
        db.session.execute(
            text(f"DELETE FROM pt_selections WHERE student_id = {student_id}")
        )
        db.session.commit()
        
        # Process rankings for each column
        form_data = request.form.to_dict()
        
        for key, ranking in form_data.items():
            if key.startswith('ranking_'):
                presentation_id = key.replace('ranking_', '')
                try:
                    ranking_value = int(ranking)
                    if ranking_value > 0:  # Only save if ranked (not 0)
                        db.session.execute(
                            text(
                                f"INSERT INTO pt_selections (student_id, presentation_id, ranking) VALUES ({student_id}, {presentation_id}, {ranking_value})"
                            )
                        )
                except ValueError:
                    continue  # Skip invalid rankings
        
        db.session.commit()
    
    return redirect("/pt")


@pt.route("/logout", methods=["POST"])
def logout():
    # Remove the user's session
    session.pop("pt_student_id", None)
    return redirect("/login")