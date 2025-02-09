# Imports

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openpyxl import load_workbook

import random as r
import string as s

from .models import Presentation, Student

# CONSTANTS
DB_URL = "sqlite:///wbgym.db"
CHARACTERS = s.ascii_letters + s.digits

from . import db

# Load German words from a separate file
def load_german_words():
    try:
        with open("german_words.txt", "r", encoding="utf-8") as file:
            words = [line.strip() for line in file if line.strip()]
            return words
    except FileNotFoundError:
        print("Error: german_words.txt not found!")
        return ["defaultword"]  # Fallback in case file is missing

GERMAN_WORDS = load_german_words()

# --------------------------------------------------
# Helper Functions


def addStudent(ENGINE, student_id, last_name, first_name, grade, logincode):
    new_student = Student(
        student_id=student_id,
        last_name=last_name,
        first_name=first_name,
        grade=grade,
        logincode=logincode,
    )

    # Create a new session
    Session = sessionmaker(bind=ENGINE)
    session = Session()

    # Add and commit the new student to the database
    session.add(new_student)
    session.commit()
    session.close()


def logincode_exists(c):
    return db.session.query(Student).filter_by(logincode=c).first() is not None


def generateLoginCode():

    # Select a random German word
    word = r.choice(GERMAN_WORDS)
    
    # Generate 5 random digits
    numbers = "".join(r.choices(s.digits, k=5))

    logincode = f"{word}{numbers}"

    # Ensure uniqueness
    if logincode_exists(logincode):
        return generateLoginCode()
    else:
        return logincode


    # if mine is wrong or does not work, use this one

    #logincode = "".join(r.choice(CHARACTERS) for _ in range(8))

    #if logincode_exists(logincode):
       # return generateLoginCode()
    #else:
       # return logincode


def addPresentation(ENGINE, presentation_id, title, presenter, abstract, grades):
    new_presentation = Presentation(
        presentation_id=presentation_id,
        title=title,
        presenter=presenter,
        abstract=abstract,
        grades=grades,
    )

    # Create a new session
    Session = sessionmaker(bind=ENGINE)
    session = Session()

    # Add and commit the new student to the database
    session.add(new_presentation)
    session.commit()
    session.close()


# ------------------------------------------------------------------------------
# This is the place where the magic happens ✨✨✨


def FileHandler(file):
    ENGINE = create_engine(DB_URL)
    db.metadata.create_all(ENGINE)
    workbook = load_workbook(f"app/data/tdw/uploads/workbook.xlsx")
    print("Loaded File...")

    # Get the Students
    sheet1 = workbook.worksheets[0]

    for row_index, row in enumerate(
        sheet1.iter_rows(min_row=2, values_only=True), start=2
    ):
        student_id = row[0]  # Column A (ID)
        last_name = row[1]  # Column B (Last Name)
        first_name = row[2]  # Column C (First Name)
        grade = row[4]  # Column E (Grade)
        logincode = generateLoginCode()

        addStudent(ENGINE, student_id, last_name, first_name, grade, logincode)

    # Get the Presentations
    sheet2 = workbook.worksheets[2]

    for row_index, row in enumerate(
        sheet2.iter_rows(min_row=2, values_only=True), start=2
    ):
        presentation_id = row[0]
        title = row[1]
        presenter = row[2]
        abstract = row[3]

        grades = []
        g = 5
        for grade in row[4:11]:
            if grade == -1:
                grades.append(g)
            else:
                pass
            g += 1

        grades = str(grades)[1:-1]

        addPresentation(ENGINE, presentation_id, title, presenter, abstract, grades)





