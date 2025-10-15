#subdomain\src\app\pt_admin_views.py
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    send_file
)

from sqlalchemy import text

import json
import os
import zipfile

from .pt_filehandler import FileHandlerPT

from .models import PTStudent, PTPresentation, PTSelection
from . import db
from .pt_logincode_export import export_logincodes as export_logincodesPT
from .pt_selection_export import SelectionExporter as SelectionExporterPT

pt_admin_views = Blueprint("pt_admin_views", __name__, static_folder="static")

# ------------------------------------------------------------------
# Decorator
from functools import wraps


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            # Preserve the original URL for redirect after login
            return redirect(f"/admin_login?next={request.url}")
        return f(*args, **kwargs)

    return decorated_function


# ------------------------------------------------------------------
# Routing for PT admin views

@pt_admin_views.route("/admin/pt/panel", methods=["GET", "POST"])  # Added /admin prefix
@admin_required
def pt_Panel():
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        ms = module_status["modules"]["PT"]
    return render_template("admin/pt_panel.html", status=ms)


@pt_admin_views.route("/admin/pt/upload_file", methods=["POST"])
@admin_required
def pt_upload_file():
    if "file" not in request.files:
        return redirect("/admin/pt/panel")  # Use absolute path
    file = request.files["file"]
    if file.filename == "":
        return redirect("/admin/pt/panel")  # Use absolute path
    
    # Create upload directory if it doesn't exist
    upload_dir = "app/data/pt/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Check if this is a names file upload
    file_type = request.form.get("file_type", "data")
    
    if file_type == "names":
        # Save as names file
        file_path = os.path.join(upload_dir, "names_workbook.xlsx")
        file.save(file_path)
        print("Names file uploaded successfully")
    else:
        # Save as regular data file
        file_path = os.path.join(upload_dir, "workbook.xlsx")
        file.save(file_path)
        FileHandlerPT()
        print("Data file uploaded and processed successfully")

    return redirect("/admin/pt/panel")  # Use absolute path


@pt_admin_views.route("/admin/pt/module_status", methods=["POST"])
@admin_required
def pt_module_status():
    with open("app/data/module_status.json", "r") as f:
        data = json.load(f)

    current_status = data["modules"]["PT"]

    if current_status == "active":
        data["modules"]["PT"] = "inactive"
    else:
        data["modules"]["PT"] = "active"

    with open("app/data/module_status.json", "w") as f:
        json.dump(data, f, indent=4)

    return redirect("/admin/pt/panel")  # Use absolute path

@pt_admin_views.route("/admin/pt/export_logincodes", methods=["POST"])
@admin_required
def pt_export_logincodes_route():
    if request.method == "POST":
        export_logincodesPT()
        return redirect("/admin/pt/panel")  # Use absolute path
    
@pt_admin_views.route("/admin/pt/download_logincodes", methods=["GET"])  # Added /admin prefix
@admin_required
def pt_download_logincodes():  # Ensure this function is used for the pt route
    download_dir = "./data/pt/downloads"
    return send_from_directory(download_dir, "PT_Logincodes.zip", as_attachment=True)


@pt_admin_views.route("/admin/pt/export_wishes", methods=["POST"])
@admin_required
def pt_export_wishes():
    try:
        print("Starting PT wishes export...")
        result_file_path = SelectionExporterPT(db)
        if result_file_path and os.path.exists(result_file_path):
            print(f"Export successful, file created at: {result_file_path}")
            return redirect("/admin/pt/panel")
        else:
            print("Export failed - no file created")
            return redirect("/admin/pt/panel")
    except Exception as e:
        print(f"Error exporting wishes: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")  # Use absolute path


@pt_admin_views.route("/admin/pt/download_wishes", methods=["GET"])
@admin_required
def pt_download_wishes():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(current_dir, 'data', 'pt', 'downloads')
        file_name = "Kurs_Wuensche.xlsx"
        file_path = os.path.join(download_dir, file_name)
        print(f"Looking for file at: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        if not os.path.exists(file_path):
            print("File not found, creating export first...")
            result_file_path = SelectionExporterPT(db)
            if not result_file_path or not os.path.exists(result_file_path):
                print("Could not create export file")
                return redirect("/admin/pt/panel")
        return send_from_directory(
            download_dir,
            file_name,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(f"Error downloading wishes: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")  # Use absolute path