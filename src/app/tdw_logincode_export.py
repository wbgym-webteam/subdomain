from docx import Document
from docx.shared import Pt
from sqlalchemy import text
import zipfile
import os
import os

from . import db


def get_class(grade, grade_selector):
    query = db.session.execute(
        text(
            f"SELECT first_name, last_name, logincode FROM students WHERE grade = {grade} AND grade_selector = {grade_selector} ORDER BY last_name, first_name"
        )
    ).fetchall()
    return query


def get_sek2(grade):
    query = db.session.execute(
        text(
            f"SELECT first_name, last_name, logincode FROM students WHERE grade = {grade} ORDER BY last_name, first_name"
        )
    ).fetchall()
    return query


def zip_files():
    directory = "./app/data/tdw/downloads"
    with zipfile.ZipFile("data/tdw/downloads/TdW_Logincodes.zip", "w") as zipf:
        for file in os.listdir(directory):
            if file.endswith(".docx"):
                zipf.write(os.path.join(directory, file), file)


def export_logincodes():
    print(os.getcwd())
    output_dir = os.getenv("OUTPUT_DIR", "./app/data/tdw/downloads")

    for grade in range(5, 13, 1):
        for grade_selector in range(1, 5, 1):
            if grade == 11 or grade == 12 or grade == 5 or grade == 6:
                print(f"Exporting grade {grade}")
                query = get_sek2(grade)
            else:
                print(f"Exporting grade {grade}/{grade_selector}")
                query = get_class(grade, grade_selector)

            if len(query) > 0 or query is not None:
                doc = Document()
                if grade == 11 or grade == 12 or grade == 5 or grade == 6:
                    doc.add_heading(f"TDW Login Codes {grade}", 0)
                else:
                    doc.add_heading(f"TDW Login Codes {grade}/{grade_selector}", 0)

                table = doc.add_table(rows=1, cols=3)
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

                if grade == 11 or grade == 12 or grade == 5 or grade == 6:
                    doc.save(os.path.join(output_dir, f"TdW_Logincodes_{grade}.docx"))
                    print(f"Finished grade {grade}")
                else:
                    doc.save(
                        os.path.join(
                            output_dir, f"TdW_Logincodes_{grade}_{grade_selector}.docx"
                        )
                    )
                    print(f"Finished grade {grade}/{grade_selector}")

    # zip_files()
