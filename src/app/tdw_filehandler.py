from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openpyxl import load_workbook

DB_URL = "sqlite:///wbgym.db"

db = SQLAlchemy()

# Import the Models
from .models import Presentation, Student


def addStudent(ENGINE, ID, last_name, first_name, grade):
    new_student = Student(ID, last_name, first_name, grade)

    # Create a new session
    Session = sessionmaker(bind=ENGINE)
    session = Session()
    # Add and commit the new student to the database
    session.add(new_user)
    # FIXME: it is probably very slow and inefficient but i don't care (for now)
    session.commit()
    session.close()


def FileHandler(file):
    ENGINE = create_engine(DB_URL)
    db.metadata.create_all(ENGINE)
    workbook = load_workbook(f"app/data/tdw/uploads/workbook.xlsx")
    print("Loaded File...")

    # Get the Students
    sheet1 = workbook[0]

    for row_index, row in enumerate(
        sheet1.iter_rows(min_row=2, values_only=True), start=2
    ):

        id_value = row[0]  # Column A (ID)
        last_name = row[1]  # Column B (Last Name)
        first_name = row[2]  # Column C (First Name)
        grade = row[4]  # Column E (Grade)

        addStudent(ENGINE, id_value, last_name, first_name, grade)
