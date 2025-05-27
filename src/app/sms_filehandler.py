# Imports

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text

from openpyxl import load_workbook

import random as r
import string as s

from .models import StudentSMS, Student_course, Course  # Removed Hosts

# CONSTANTS
CHARACTERS = s.ascii_letters + s.digits

from . import db


# --------------------------------------------------
# Helper Functions


# Load German words from a separate file
def load_german_words():
    try:
        with open("app/german_words.txt", "r", encoding="utf-8") as file:
            words = [line.strip() for line in file if line.strip()]
            return words
    except FileNotFoundError:
        print("Error: german_words.txt not found!")
        return ["defaultword"]  # Fallback in case file is missing
    

GERMAN_WORDS = load_german_words()



def create_student(student_id, last_name, first_name, grade, grade_selector, logincode):
    # Check if student already exists
    existing_student = db.session.execute(
        db.select(StudentSMS).filter_by(Student_id=student_id)
    ).scalar_one_or_none()

    if existing_student:
        print(existing_student.last_name)
        print(f"Student with ID {student_id} already exists.")
        return existing_student  # Avoid duplicate entry

    try:
        new_student = StudentSMS(
            Student_id=student_id,  # Corrected from id to Student_id
            last_name=last_name,
            first_name=first_name,
            grade=grade,
            grade_selector=grade_selector,
            logincode=logincode,
        )
        print("Student erfolgreich gespeichert!")
        db.session.add(new_student)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        print(f"IntegrityError: Duplicate ID {student_id}")
    except Exception as e:
        print(
            f"Error while creating a new student #${student_id} {last_name} {first_name}"
        )
        print(e)



def create_course(Course_id, Course_title, Course_description, Course_teacher, Course_min_grade, Course_max_grade, Course_max_people, Course_hosts):
    try:
        new_Course = Course(
            course_id = Course_id,
            course_title = Course_title,
            course_discripton = Course_description,
            course_Overseers = Course_teacher,
            course_minimum_grade = Course_min_grade,
            course_maximum_grade = Course_max_grade,
            course_maximum_people = Course_max_people,
            course_hosts = Course_hosts,
        )
        db.session.add(new_Course)
        db.session.commit()
    except:
        db.session.rollback()
        print(f"Error creating a new Course #${Course_id} ${Course_title}")


def generate_login_code():

    # Select a random German word
    word = r.choice(GERMAN_WORDS)

    # Generate 5 random digits
    numbers = "".join(r.choices(s.digits, k=5))

    logincode = f"{word}{numbers}"

    user_with_logincode = db.session.execute(
        db.select(StudentSMS).filter_by(logincode=logincode)
    ).scalar_one_or_none()

    # Ensure uniqueness
    if user_with_logincode is not None:
        return generate_login_code()

    # print(Student.query().filter_by(logincode=logincode).first())

    return logincode


# ------------------------------------------------------------------------------
# This is the place where the magic happens ✨✨✨

def FileHandler():
    workbook = load_workbook(f"app/data/sms/uploads/workbook.xlsx")
    print("Loaded File...")

    # Clear the database
    db.session.execute(text("DELETE FROM students_sms"))
    db.session.execute(text("DELETE FROM student_course"))
    db.session.execute(text("DELETE FROM courses"))

    # Get the Students
    sheet1 = workbook.worksheets[0]

    for row_index, row in enumerate(
        sheet1.iter_rows(min_row=2, values_only=True), start=2
    ):
        student_id = row[0]  # Column A (ID)
        last_name = row[1]  # Column B (Last Name)
        first_name = row[2]  # Column C (First Name)
        grade = row[4]  # Column E (Grade)
        grade_selector = row[5]  # Column F (Grade Selector)
        logincode = generate_login_code()

        print(
            f"{student_id} {last_name} {first_name} {grade}/{grade_selector} {logincode}"
        )

        if (
            student_id == None
            or last_name == None
            or first_name == None
            or grade == None
        ):
            break

        create_student(
            student_id, last_name, first_name, grade, grade_selector, logincode
        )

    # Get the Presentations
    presentations_sheet = workbook.worksheets[1]

    for row_index, row in enumerate(
        presentations_sheet.iter_rows(min_row=2, values_only=True), start=2
    ):
        course_id = row[0]
        course_title = row[1]
        course_discription = row[2]
        course_teacher = row[3]
        course_min_grade = row[4]
        course_max_grade = row[5]
        course_max_people = row[6]
        course_hosts = row[7]


        #not sure if this is needed
        #grades = []
        #g = 5
        #for grade in row[4:12]:
         #   if grade == -1:
          #      grades.append(g)
           # else:
            #    pass
            #g += 1

        #grades = str(grades)[1:-1]

        print(f"{course_id} {course_title} {course_hosts} {course_title}")

        if (
            course_id == None
            or course_title == None
            or course_discription == None
            or course_teacher == None
            or course_min_grade == None
            or course_max_grade == None
            or course_max_people == None
            or course_hosts == None
        ):
            break

        create_course(course_id, course_title, course_discription, course_teacher, course_min_grade, course_min_grade, course_max_people, course_hosts)


        print(f"{student_id} {course_id}")

        if student_id == None or course_id == None:
            break




