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

from .tdw_filehandler import FileHandler
from .tdw_logincode_export import export_logincodes
from .tdw_selection_export import SelectionExporter

from .sms_filehandler import FileHandler as FileHandlerSMS
from .sms_logincode_export import export_logincodes as export_logincodesSMS
from .sms_selection_export import SelectionExporter as SelectionExporterSMS
from . import db
from .models import StudentSMS, Student_course, Course  

admin_views = Blueprint("admin_views", __name__, static_folder="static")


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
# Routing for TDW admin views

# Dashboard functionality removed - using panel structure instead

@admin_views.route("/admin/tdw/panel", methods=["GET", "POST"])  # Added /admin prefix
@admin_required
def tdw_Panel():
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        ms = module_status["modules"]["TdW"]
    return render_template("admin/tdw_panel.html", status=ms)


@admin_views.route("/admin/tdw/upload_file", methods=["POST"])
@admin_required
def tdw_upload_file():
    if "file" not in request.files:
        return redirect("/admin/tdw/panel")  # Use absolute path
    file = request.files["file"]
    if file.filename == "":
        return redirect("/admin/tdw/panel")  # Use absolute path
    file.save("app/data/tdw/uploads/workbook.xlsx")

    FileHandler()
    return redirect("/admin/tdw/panel")  # Use absolute path


@admin_views.route("/admin/tdw/module_status", methods=["POST"])
@admin_required
def tdw_module_status():
    with open("app/data/module_status.json", "r") as f:
        data = json.load(f)

    current_status = data["modules"]["TdW"]

    if current_status == "active":
        data["modules"]["TdW"] = "inactive"
    else:
        data["modules"]["TdW"] = "active"

    with open("app/data/module_status.json", "w") as f:
        json.dump(data, f, indent=4)

    return redirect("/admin/tdw/panel")  # Use absolute path


@admin_views.route("/admin/tdw/export_logincodes", methods=["POST"])
@admin_required
def tdw_export_logincodes_route():
    if request.method == "POST":
        export_logincodes()
        return redirect("/admin/tdw/panel")  # Use absolute path
    
@admin_views.route("/admin/tdw/download_logincodes", methods=["GET"])  # Added /admin prefix
@admin_required
def tdw_download_logincodes():
    download_dir = "./data/tdw/downloads"
    return send_from_directory(download_dir, "TdW_Logincodes.zip", as_attachment=True)
    
@admin_views.route("/admin/tdw/export_selections", methods=["POST"])
@admin_required
def tdw_export_selections():
    if request.method == "POST":
        SelectionExporter(db, "app/data/tdw/uploads/workbook.xlsx")
        return redirect("/admin/tdw/panel")  # Use absolute path
    else:
        return redirect("/admin/tdw/panel")  # Use absolute path

@admin_views.route("/admin/tdw/download_selections")  # Added /admin prefix
@admin_required
def tdw_download_selections():
    uploads_dir = "./data/tdw/uploads"
    return send_from_directory(uploads_dir, "workbook.xlsx", as_attachment=True)


@admin_views.route("/admin/admin_logout")  # Added /admin prefix
@admin_required
def admin_logout():
    session["admin_logged_in"] = False
    return redirect("/admin_login")  # Use absolute path




# ------------------------------------------------------------------
# Routing for SMS admin views

# Reinstate when needed
# @admin_required
# @admin_views.route("/admin_dashboard")
# def adminDashboard():
#     return render_template("admin/admin_dashboard.html")


@admin_views.route("/admin/sms/panel", methods=["GET", "POST"])  # Added /admin prefix
@admin_required
def sms_Panel():
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        ms = module_status["modules"]["SmS"]
    return render_template("admin/sms_panel.html", status=ms)


@admin_views.route("/admin/sms/upload_file", methods=["POST"])
@admin_required
def sms_upload_file():
    if "file" not in request.files:
        return redirect("/admin/sms/panel")  # Use absolute path
    file = request.files["file"]
    if file.filename == "":
        return redirect("/admin/sms/panel")  # Use absolute path
    
    # Check if this is a names file upload
    file_type = request.form.get("file_type", "data")
    
    if file_type == "names":
        # Save as names file
        file.save("app/data/sms/uploads/names_workbook.xlsx")
        print("Names file uploaded successfully")
    else:
        # Save as regular data file
        file.save("app/data/sms/uploads/workbook.xlsx")
        FileHandlerSMS()
        print("Data file uploaded and processed successfully")

    return redirect("/admin/sms/panel")  # Use absolute path


@admin_views.route("/admin/sms/module_status", methods=["POST"])
@admin_required
def sms_module_status():
    with open("app/data/module_status.json", "r") as f:
        data = json.load(f)

    current_status = data["modules"]["SmS"]

    if current_status == "active":
        data["modules"]["SmS"] = "inactive"
    else:
        data["modules"]["SmS"] = "active"

    with open("app/data/module_status.json", "w") as f:
        json.dump(data, f, indent=4)

    return redirect("/admin/sms/panel")  # Use absolute path


@admin_views.route("/admin/sms/export_logincodes", methods=["POST"])
@admin_required
def sms_export_logincodes_route():
    if request.method == "POST":
        export_logincodesSMS()
        return redirect("/admin/sms/panel")  # Use absolute path


@admin_views.route("/admin/sms/download_logincodes", methods=["GET"])  # Added /admin prefix
@admin_required
def sms_download_logincodes():  # Ensure this function is used for the SMS route
    download_dir = "./data/sms/downloads"
    return send_from_directory(download_dir, "SmS_Logincodes.zip", as_attachment=True)

    
        


@admin_views.route("/admin/sms/export_selections", methods=["POST"])
@admin_required
def sms_export_selections():
    try:
        print("Starting SMS selection export...")
        # Use the SelectionExporter with relative path (it will create the path automatically)
        result_file_path = SelectionExporterSMS(db)
        
        if result_file_path and os.path.exists(result_file_path):
            print(f"Export successful, file created at: {result_file_path}")
            # Redirect to panel instead of download to avoid immediate download
            return redirect("/admin/sms/panel")  # Use absolute path
        else:
            print("Export failed - no file created")
            return redirect("/admin/sms/panel")  # Use absolute path
    except Exception as e:
        print(f"Error exporting selections: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/sms/panel")  # Use absolute path


@admin_views.route("/admin/sms/download_selections", methods=["GET"])
@admin_required
def sms_download_selections():
    try:
        # Use relative path from the current file location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(current_dir, 'data', 'sms', 'downloads')
        file_name = "Kurs_Wuensche.xlsx"
        file_path = os.path.join(download_dir, file_name)
        
        print(f"Looking for file at: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            print("File not found, creating export first...")
            # Try to create the file first
            result_file_path = SelectionExporterSMS(db)
            if not result_file_path or not os.path.exists(result_file_path):
                print("Could not create export file")
                return redirect("/admin/sms/panel")  # Use absolute path
        
        return send_from_directory(
            download_dir,
            file_name,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(f"Error downloading selections: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/sms/panel")  # Use absolute path