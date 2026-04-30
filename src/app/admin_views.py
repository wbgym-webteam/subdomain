from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    send_file,
    flash
)

from sqlalchemy import text

import json

from .tdw_filehandler import FileHandler
from .tdw_logincode_export import export_logincodes
from .tdw_selection_export import SelectionExporter

from .sms_filehandler import FileHandler as FileHandlerSMS
from .sms_logincode_export import export_logincodes as export_logincodesSMS
from .sms_selection_export import SelectionExporter as SelectionExporterSMS
from .sms_selection_engine import run_engine as run_sms_engine
from .sms_assignment_export import AssignmentExporter as AssignmentExporterSMS
from . import db
from .models import StudentSMS, Student_course, Course, SMSAssignment

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
        return redirect("/admin/sms/panel")
    file = request.files["file"]
    if file.filename == "":
        return redirect("/admin/sms/panel")

    file.save("app/data/sms/uploads/workbook.xlsx")
    FileHandlerSMS()
    print("Data file uploaded and processed successfully")

    return redirect("/admin/sms/panel")


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
    if "names_file" not in request.files or request.files["names_file"].filename == "":
        return redirect("/admin/sms/panel")
    names_file = request.files["names_file"]
    zip_buffer = export_logincodesSMS(names_file)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="SmS_Logincodes.zip",
        mimetype="application/zip"
    )

    
        


@admin_views.route("/admin/sms/export_selections", methods=["POST"])
@admin_required
def sms_export_selections():
    if "names_file" not in request.files or request.files["names_file"].filename == "":
        return redirect("/admin/sms/panel")
    names_file = request.files["names_file"]
    buffer = SelectionExporterSMS(db, names_file)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Kurs_Wuensche.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@admin_views.route("/admin/sms/run_engine", methods=["POST"])
@admin_required
def sms_run_engine():
    try:
        stats = run_sms_engine(db)
        flash(
            f"Engine completed. Session 1: {stats['assigned_session1']}, "
            f"Session 2: {stats['assigned_session2']}, "
            f"Unassigned slots: {stats['unassigned']}, "
            f"Happiness score: {stats['total_happiness']}.",
            "success"
        )
    except Exception as e:
        flash(f"Engine error: {e}", "error")
    return redirect("/admin/sms/panel")


@admin_views.route("/admin/sms/export_assignments", methods=["POST"])
@admin_required
def sms_export_assignments():
    if "names_file" not in request.files or request.files["names_file"].filename == "":
        return redirect("/admin/sms/panel")
    names_file = request.files["names_file"]
    buffer = AssignmentExporterSMS(db, names_file)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Kurs_Zuteilungen.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )