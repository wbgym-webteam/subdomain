from docx import Document
from docx.shared import Pt
from sqlalchemy import text
from openpyxl import load_workbook
import zipfile
import os

from . import db


def get_class_with_names(grade, grade_selector):
    # Get student data from database (without names)
    db_students = db.session.execute(
        text(
            f"SELECT Student_id, logincode FROM students_sms WHERE grade = {grade} AND grade_selector = {grade_selector} ORDER BY Student_id"
        )
    ).fetchall()
    
    # Load names from Excel file
    try:
        workbook = load_workbook("app/data/sms/uploads/workbook.xlsx")
        sheet = workbook.worksheets[0]
        
        # Create mapping of student_id to names
        student_names = {}
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] is None:
                break
            student_id = row[0]
            first_name = row[2] or ""  # Column C
            last_name = row[1] or ""   # Column B
            student_names[student_id] = (first_name, last_name)
        
        # Combine database data with Excel names
        result = []
        for db_student in db_students:
            student_id = db_student[0]
            logincode = db_student[1]
            if student_id in student_names:
                first_name, last_name = student_names[student_id]
                # Create a mock object with attributes
                class StudentRecord:
                    def __init__(self, first_name, last_name, logincode):
                        self.first_name = first_name
                        self.last_name = last_name
                        self.logincode = logincode
                
                result.append(StudentRecord(first_name, last_name, logincode))
        
        return sorted(result, key=lambda x: (x.last_name, x.first_name))
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []


def get_sek2_with_names(grade):
    # Get student data from database (without names)
    db_students = db.session.execute(
        text(
            f"SELECT Student_id, logincode FROM students_sms WHERE grade = {grade} ORDER BY Student_id"
        )
    ).fetchall()
    
    # Load names from Excel file
    try:
        workbook = load_workbook("app/data/sms/uploads/workbook.xlsx")
        sheet = workbook.worksheets[0]
        
        # Create mapping of student_id to names
        student_names = {}
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] is None:
                break
            student_id = row[0]
            first_name = row[2] or ""  # Column C
            last_name = row[1] or ""   # Column B
            student_names[student_id] = (first_name, last_name)
        
        # Combine database data with Excel names
        result = []
        for db_student in db_students:
            student_id = db_student[0]
            logincode = db_student[1]
            if student_id in student_names:
                first_name, last_name = student_names[student_id]
                # Create a mock object with attributes
                class StudentRecord:
                    def __init__(self, first_name, last_name, logincode):
                        self.first_name = first_name
                        self.last_name = last_name
                        self.logincode = logincode
                
                result.append(StudentRecord(first_name, last_name, logincode))
        
        return sorted(result, key=lambda x: (x.last_name, x.first_name))
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []


def zip_files():
    directory = os.getenv("OUTPUT_DIR", "./app/data/sms/downloads")
    zip_file_path = os.path.join(directory, "SmS_Logincodes.zip")

    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    with zipfile.ZipFile(zip_file_path, "w") as zipf:
        for file in os.listdir(directory):
            if file.endswith(".docx"):
                zipf.write(os.path.join(directory, file), file)

    print("Zipped files successfully.")


def export_logincodes():
    print(os.getcwd())
    output_dir = os.getenv("OUTPUT_DIR", "./app/data/sms/downloads")
    os.makedirs(output_dir, exist_ok=True)

    for grade in range(5, 13, 1):
        for grade_selector in range(1, 5, 1):
            if grade == 11 or grade == 12 or grade == 5 or grade == 6:
                print(f"Exporting grade {grade}")
                query = get_sek2_with_names(grade)
            else:
                print(f"Exporting grade {grade}/{grade_selector}")
                query = get_class_with_names(grade, grade_selector)

            if len(query) > 0:
                doc = Document()
                # ----------------------------------------------------------------
                # Add a title
                if grade == 11 or grade == 12 or grade == 5 or grade == 6:
                    doc.add_heading(f"SMS Login Codes {grade}", 0)
                else:
                    doc.add_heading(f"SMS Login Codes {grade}/{grade_selector}", 0)

                # ----------------------------------------------------------------
                # Add a table
                table = doc.add_table(rows=1, cols=3)

                # Add spacing between rows for data rows only
                table.style = "Table Grid"
                
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = "First Name"
                hdr_cells[1].text = "Last Name"
                hdr_cells[2].text = "Login Code"

                headers = ["First Name", "Last Name", "Login Code"]
                for i, header in enumerate(headers):
                    cell = table.cell(0, i)
                    cell.text = header

                    # Set font size and make it bold
                    for paragraph in cell.paragraphs:
                        run = paragraph.runs[0]
                        run.bold = True
                        run.font.size = Pt(14)

                for row in query:
                    row_cells = table.add_row().cells
                    row_cells[0].text = row.first_name
                    row_cells[1].text = row.last_name
                    row_cells[2].text = row.logincode

                for row in table.rows[1:]:  # Skip the header row
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            paragraph.paragraph_format.space_after = Pt(14)
                            paragraph.paragraph_format.space_before = Pt(14)
                            paragraph.paragraph_format.line_spacing = Pt(14)

                if grade == 11 or grade == 12 or grade == 5 or grade == 6:
                    doc.save(os.path.join(output_dir, f"SmS_Logincodes_{grade}.docx"))
                    print(f"Finished grade {grade}")
                else:
                    doc.save(
                        os.path.join(
                            output_dir, f"SmS_Logincodes_{grade}_{grade_selector}.docx"
                        )
                    )
                    print(f"Finished grade {grade}/{grade_selector}")

    zip_files()
