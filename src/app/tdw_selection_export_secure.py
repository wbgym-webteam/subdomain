#subdomain\src\app\tdw_selection_export_secure.py
# This secure version reads names from the Excel file in RAM during export
# Names are never stored in the database, only matched by ID
# Files are generated entirely in RAM and never saved to disk

from sqlalchemy.sql import text
from openpyxl import Workbook
import io


def SelectionExporterSecureRAM(db, names_map):
    """
    Export selections using names from RAM only.
    Generates Excel file in RAM and returns a BytesIO buffer.
    names_map: dictionary with student_id as key and {'first': ..., 'last': ...} as value
    """
    try:
        # ---------------------------------------------------------
        # 1. Fetch Data from DB
        # ---------------------------------------------------------
        # We order by student_id to make the list readable
        print("Fetching selections from database...")
        selections = db.session.execute(
            text("SELECT student_id, presentation_id FROM selections ORDER BY student_id ASC")
        ).mappings().all()

        print(f"Selections fetched: {len(selections)}")

        # ---------------------------------------------------------
        # 2. Create Excel File in RAM
        # ---------------------------------------------------------
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Selections"

        # Add Headers
        headers = ["student_id", "first_name", "last_name", "presentation_id"]
        sheet.append(headers)

        # Add Data with names from RAM
        if selections:
            for row in selections:
                # We access columns by name because we used .mappings()
                s_id = row["student_id"]
                p_id = row["presentation_id"]

                # Get names from RAM
                first_name = ""
                last_name = ""
                if s_id in names_map:
                    first_name = names_map[s_id]['first']
                    last_name = names_map[s_id]['last']

                sheet.append([s_id, first_name, last_name, p_id])
        else:
            print("No selections found in database.")

        # ---------------------------------------------------------
        # 3. Save to RAM Buffer
        # ---------------------------------------------------------
        excel_buffer = io.BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)

        print(f"SUCCESS: Selections exported to RAM buffer")
        return excel_buffer

    except Exception as e:
        print(f"ERROR in SelectionExporterSecureRAM: {e}")
        # Print full error trace for debugging
        import traceback
        traceback.print_exc()
        return None
