from sqlalchemy.sql import text
from openpyxl import Workbook
import os

def SelectionExporter(db, file_path=None):
    try:
        # ---------------------------------------------------------
        # 1. Setup File Path
        # ---------------------------------------------------------
        # If no path is provided, save it to the downloads folder
        if file_path is None:
            # This ensures we put the file in the downloads folder, not uploads
            file_path = "./app/data/tdw/downloads/TdW_Selections.xlsx"
        
        # Ensure the directory exists
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

        # If a file already exists there, remove it to ensure a clean export
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted old export file: {file_path}")
            except Exception as e:
                print(f"Could not delete old file: {e}")

        # ---------------------------------------------------------
        # 2. Fetch Data from DB
        # ---------------------------------------------------------
        # We order by student_id to make the list readable
        print("Fetching selections from database...")
        selections = db.session.execute(
            text("SELECT student_id, presentation_id FROM selections ORDER BY student_id ASC")
        ).mappings().all()

        print(f"Selections fetched: {len(selections)}")

        # ---------------------------------------------------------
        # 3. Create Excel File
        # ---------------------------------------------------------
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Selections"

        # Add Headers
        # Note: Your table schema didn't show 'weight', so I included only these two.
        headers = ["student_id", "presentation_id"]
        sheet.append(headers)

        # Add Data
        if selections:
            for row in selections:
                # We access columns by name because we used .mappings()
                s_id = row["student_id"]
                p_id = row["presentation_id"]
                
                sheet.append([s_id, p_id])
        else:
            print("No selections found in database.")

        # ---------------------------------------------------------
        # 4. Save
        # ---------------------------------------------------------
        workbook.save(file_path)
        print(f"SUCCESS: Selections exported to {file_path}")
        return file_path

    except Exception as e:
        print(f"ERROR in SelectionExporter: {e}")
        # Print full error trace for debugging
        import traceback
        traceback.print_exc()
        return None