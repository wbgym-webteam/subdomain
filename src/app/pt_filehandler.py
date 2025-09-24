# Imports

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text

from openpyxl import load_workbook

import random as r
import string as s

from .models import PTStudent, PTPresentation

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


def create_student(student_id, last_name, first_name, email, grade, grade_selector, logincode):
    # Check if student already exists
    existing_student = db.session.execute(
        db.select(PTStudent).filter_by(id=student_id)
    ).scalar_one_or_none()

    if existing_student:
        print(existing_student.last_name)
        print(f"Student with ID {student_id} already exists.")
        return existing_student  # Avoid duplicate entry

    try:
        new_student = PTStudent(
            id=student_id,
            last_name=last_name,
            first_name=first_name,
            email=email,
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


def generate_login_code():

    # Select a random German word
    word = r.choice(GERMAN_WORDS)

    # Generate 5 random digits
    numbers = "".join(r.choices(s.digits, k=5))

    logincode = f"{word}{numbers}"

    user_with_logincode = db.session.execute(
        db.select(PTStudent).filter_by(logincode=logincode)
    ).scalar_one_or_none()

    # Ensure uniqueness
    if user_with_logincode is not None:
        return generate_login_code()

    # print(Student.query().filter_by(logincode=logincode).first())

    return logincode

    # if mine is wrong or does not work, use this one

    # logincode = "".join(r.choice(CHARACTERS) for _ in range(8))

    # if logincode_exists(logincode):
    # return generateLoginCode()
    # else:
    # return logincode