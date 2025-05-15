# Imports

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text

from openpyxl import load_workbook

import random as r
import string as s

from .models import StudentSMS, Student_course, Hosts, Course

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
        db.select(StudentSMS).filter_by(id=student_id)
    ).scalar_one_or_none()

    if existing_student:
        print(existing_student.last_name)
        print(f"Student with ID {student_id} already exists.")
        return existing_student  # Avoid duplicate entry

    try:
        new_student = StudentSMS(
            id=student_id,
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


# ------------------------------------------------------------------------------
# This is the place where the magic happens ✨✨✨




