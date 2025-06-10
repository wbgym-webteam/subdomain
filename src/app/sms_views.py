from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# TODO: Import the models from the models.py file
from .models import StudentSMS, Course, Student_course

from . import db

sms = Blueprint("sms", __name__)

# ---------------------------------------------------------------
# SMS Routes
# ---------------------------------------------------------------
#
# This is the view that the logged in student will see


@sms.route("/", methods=["GET", "POST"])
def selection():
    # Checks if the user is logged in
    if session.get("logged_in", True) == True:
        if request.method == "POST":
            pass  # idk you can delete this but be careful pls :D
        else:
            # Get the student id from the session storage
            student_id = session.get("sms_student_id")
            if student_id is None:
                return redirect("/login")
            student_id = str(student_id)

            # DB Query to get the student's grade (no names stored)
            try:
                db_current_student = db.session.execute(
                    db.select(
                        StudentSMS.grade
                    ).filter_by(Student_id=student_id)
                ).one_or_none()

                if db_current_student is None:
                    print(f"No student found with ID: {student_id}")
                    return redirect("/login")

                # It creates a dictionary from the query result to access the values by key
                current_student = dict(db_current_student._mapping)

                # Use student ID as display name since no names are stored
                full_name = f"Student {student_id}"

                # The grade is relevant for the options that will be displayed
                grade = current_student["grade"]
            except Exception as e:
                print(f"Error fetching student data: {e}")
                return redirect("/login")

            # Get the courses - create list of dictionaries for template
            courses_list = []

            try:
                db_courses = db.session.execute(db.select(Course)).all()
                
                # Debug: Check if courses exist
                print(f"Total courses found: {len(db_courses)}")
                print(f"Student grade: {grade}")

                for course in db_courses:
                    course_obj = course[0]
                    print(f"Course: {course_obj.course_title}, Min Grade: {course_obj.course_minimum_grade}, Max Grade: {course_obj.course_maximum_grade}")
                    
                    # Check if grade is within range - handle None values
                    min_grade = course_obj.course_minimum_grade or 1
                    max_grade = course_obj.course_maximum_grade or 13
                    
                    if min_grade <= grade <= max_grade:
                        # Create course dictionary matching template expectations
                        course_dict = {
                            'id': course_obj.course_id,
                            'name': course_obj.course_title or 'Unnamed Course',
                            'hosts': course_obj.course_hosts or 'TBD',
                            'teacher': course_obj.course_Overseers or 'TBD',
                            'available_spots': course_obj.course_maximum_people or 0,
                            'description': course_obj.course_description or 'No description available'
                        }
                        courses_list.append(course_dict)
                        print(f"Added course: {course_dict['name']}")

                print(f"Final courses list length: {len(courses_list)}")
            except Exception as e:
                print(f"Error fetching courses: {e}")
                courses_list = []

            # Get the ALREADY chosen courses with priorities - use correct table name
            chosen_courses = {}
            try:
                # Use ORM query instead of raw SQL
                results = db.session.execute(
                    db.select(Student_course.Course_id, Student_course.weight)
                    .filter_by(Student_id=int(student_id))
                ).all()

                if results:
                    for result in results:
                        chosen_courses[str(result[0])] = result[1]
                        print(f"Found existing selection: Course {result[0]}, Priority {result[1]}")
            except Exception as e:
                print(f"Error fetching existing selections: {e}")
                chosen_courses = {}

            # When rendering the template, pass courses as list for the template
            return render_template(
                "sms/sms_selection.html",
                student=full_name,
                courses=courses_list,
                chosen_courses=chosen_courses,
            )
    else:
        return redirect("/login")


#
# This view will never be displayed, because the only accepted method is POST (not to confuse w/ the classic GET Method)
# But it does the magic behind the selection :o


@sms.route("/submit_selection", methods=["POST"])
def submit_selection():
    try:
        # Ensure 'sms_student_id' exists in the session
        if "sms_student_id" not in session:
            print("Error: 'sms_student_id' not found in session.")
            return redirect("/login")  # Redirect to login if not set

        student_id = str(session["sms_student_id"])

        # Collect wish selections from form
        wish_selections = {}
        for key, value in request.form.items():
            if key.startswith('wish_') and value:
                course_id = key.replace('wish_', '')
                priority = int(value)
                wish_selections[course_id] = priority

        try:
            # Clear existing selections for this student - use correct table name
            db.session.execute(
                db.delete(Student_course).filter_by(Student_id=int(student_id))
            )

            # Insert new wish-based selections using ORM
            for course_id, priority in wish_selections.items():
                new_selection = Student_course(
                    Student_id=int(student_id),
                    Course_id=int(course_id),
                    weight=priority
                )
                db.session.add(new_selection)

            db.session.commit()
            print(f"Successfully saved {len(wish_selections)} selections for student {student_id}")

        except Exception as e:
            print(f"Error saving selections: {e}")
            db.session.rollback()

        return redirect(url_for('sms.selection', success='true'))

    except Exception as e:
        print(f"Unexpected error: {e}")
        return redirect("/login")


@sms.route("/logout")
def logout():
    # Remove the user's session
    session.pop("sms_student_id", None)
    session.pop("logged_in", None)
    return redirect("/login")
