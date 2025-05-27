from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
from openpyxl import load_workbook


def get_selections_from_db(db):
    try:
        # Retrieve the data from the db
        return db.session.execute(text("SELECT * FROM student_course")).all()
    except IntegrityError:
        db.session.rollback()
        print("Error fetching selections from database.")
        return

def get_workbook(file_path):
    try:
        workbook = load_workbook(file_path)
        return workbook
    except Exception as e:
        print(f"Error loading workbook: {e}")
        return None
    
def SelectionExporter(db, file_path):
    selections = get_selections_from_db(db)
    workbook = get_workbook(file_path)
    if workbook is None:
        return
    
    sheet = workbook.worksheets[4]
    row = 2
    for selection in selections:
        sheet.cell(row=row, column=1, value=selection.presentation_id)
        sheet.cell(row=row, column=2, value=selection.student_id)
        row += 1
    workbook.save(file_path)
