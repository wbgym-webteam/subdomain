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

            student_id = row[0]  # Column A (ID)
            last_name = row[1]  # Column B (Last Name)
            first_name = row[2]  # Column C (First Name)
            grade = row[4]  # Column E (Grade)

            addStudent(ENGINE, student_id, last_name, first_name, grade)
    except IntegrityError:
        pass

    # Get the Presentations
    sheet2 = workbook.worksheets[2]

    try:
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

            addPresentation(EGNINE, presentation_id, title, presenter, abstract, grades)
    except IntegrityError:
        pass


# Who ever will see this code... Please forgive me. But that was the smoothest way to resolve this issue duh. :)
