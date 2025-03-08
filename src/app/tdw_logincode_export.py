from docx import Document
from sqlalchemy import text
import zipfile
import os

from . import db


def get_class(grade, grade_selector):
    query = db.session.execute(
        text(
            f"SELECT first_name, last_name, logincode FROM students WHERE grade = {grade} AND grade_selector = {grade_selector} ORDER BY last_name, first_name"
        )
    ).fetchall()
    return query


def zip_files():
    directory = "data/tdw/downloads"
    with zipfile.ZipFile("data/tdw/downloads/TdW_Logincodes.zip", "w") as zipf:
        for file in os.listdir(directory):
            if file.endswith(".docx"):
                zipf.write(os.path.join(directory, file), file)


def export_logincodes():
    for grade in range(5, 12, 1):
        for grade_selector in range(1, 5, 1):
            print(f"Exporting grade {grade}/{grade_selector}")
            query = getClass(grade, grade_selector)
            if len(query) > 0 or query is not None:
                doc = Document()
                doc.add_heading(f"TDW Login Codes {grade}/{grade_selector}", 0)
                for row in query:
                    table = doc.add_table(rows=len(query), cols=3)
                    hdr_cells = table.rows[0].cells
                    hdr_cells[0].text = "First Name"
                    hdr_cells[1].text = "Last Name"
                    hdr_cells[2].text = "Login Code"
                    for row in query:
                        row_cells = table.add_row().cells
                        row_cells[0].text = row.first_name
                        row_cells[1].text = row.last_name
                        row_cells[2].text = row.logincode
                doc.save(
                    f"/app/data/tdw/downloads/TdW_Logincodes_{grade}_{grade_selector}.docx"
                )
                print(f"Finished grade {grade}/{grade_selector}")

    zip_files()
