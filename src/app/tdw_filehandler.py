from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from openpyxl import load_workbook

DB_URL = "sqlite:///wbgym.db"

db = SQLAlchemy()

# Import the Models
from .models import Presentation, Student


def addStudent(ENGINE, student_id, last_name, first_name, grade):
    new_student = Student(
        student_id=student_id, name=last_name, first_name=first_name, grade=grade
    )

    # Create a new session
    Session = sessionmaker(bind=ENGINE)
    session = Session()

    # Add and commit the new student to the database
    session.add(new_student)
    session.commit()
    session.close()


def FileHandler(file):
    ENGINE = create_engine(DB_URL)
    db.metadata.create_all(ENGINE)
    workbook = load_workbook(f"app/data/tdw/uploads/workbook.xlsx")
    print("Loaded File...")

    # Get the Students
    sheet1 = workbook.worksheets[0]
    try:
        for row_index, row in enumerate(
            sheet1.iter_rows(min_row=2, values_only=True), start=2
        ):

            id_value = row[0]  # Column A (ID)
            last_name = row[1]  # Column B (Last Name)
            first_name = row[2]  # Column C (First Name)
            grade = row[4]  # Column E (Grade)

            addStudent(ENGINE, id_value, last_name, first_name, grade)
    except IntegrityError:
        pass


# Who ever will see this code... Please forgive me. But that was the smoothest way to resolve this issue duh. :)
