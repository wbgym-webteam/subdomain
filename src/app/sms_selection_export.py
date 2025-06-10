from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
from openpyxl import load_workbook, Workbook
import os


def get_selections_from_db(db):
    try:
        # Retrieve the data from the student_course table
        return db.session.execute(
            text(
                "SELECT Student_id AS student_id, Course_id AS course_id, weight AS weight FROM student_course"
            )
        ).mappings().all()  # Use .mappings() to return rows as dictionaries
    except IntegrityError:
        db.session.rollback()
        print("Error fetching selections from database.")
        return []


def get_students_from_workbook(file_path=None):
    try:
        # Use relative path if no file_path is provided
        if file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, 'data', 'sms', 'students.xlsx')
        
        # Check if file exists before trying to load it
        if not os.path.exists(file_path):
            print(f"Student workbook not found at: {file_path}")
            return {}
        
        workbook = load_workbook(file_path)
        sheet = workbook.worksheets[0]  # Assuming student data is in the first sheet
        students = {}
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Skip header row
            student_id = row[0]
            if student_id is not None:
                students[student_id] = {
                    "first_name": row[2],
                    "last_name": row[1],
                    "grade": row[4],
                }
        return students
    except Exception as e:
        print(f"Error loading workbook: {e}")
        return {}


def SelectionExporter(db, file_path=None):
    try:
        # Use relative path if no file_path is provided
        if file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, 'data', 'sms', 'downloads', 'Kurs_Wuensche.xlsx')
        
        print(f"Attempting to export selections to: {file_path}")
        
        # Ensure the directory exists
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

        # Check if file exists and delete it
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted existing file: {file_path}")

        # Fetch selections from the database (ordered by student_id, then by weight)
        selections = db.session.execute(
            text("SELECT Student_id AS user_id, Course_id AS course_id, weight FROM student_course ORDER BY Student_id ASC, weight ASC")
        ).mappings().all()

        print(f"Selections fetched: {len(selections)}")

        # Create a new workbook (always create fresh)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SMS_Selections"

        # Add headers
        headers = ["student_id", "course_id", "weight"]
        sheet.append(headers)

        # Add selections (students with wishes)
        if selections:
            for selection in selections:
                print(f"Processing selection: {selection}")
                if "user_id" in selection and "course_id" in selection and "weight" in selection:
                    sheet.append([selection["user_id"], selection["course_id"], selection["weight"]])
                else:
                    print(f"Skipping invalid selection: {selection}")
        else:
            print("No selections found - creating empty file with headers only")

        # Save the workbook
        workbook.save(file_path)
        print(f"SUCCESS: Selections exported to {file_path}")
        print(f"File exists after save: {os.path.exists(file_path)}")
        
        return file_path  # Return the file path for download
        
    except Exception as e:
        print(f"ERROR in SelectionExporter: {e}")
        import traceback
        traceback.print_exc()
        return None
