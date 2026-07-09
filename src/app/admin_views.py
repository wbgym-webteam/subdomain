#subdomain\src\app\admin_views.py
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory
)

from sqlalchemy import text

import json
import os

from flask import send_file

from .tdw_filehandler_secure import FileHandlerTDWSecure, load_names_map
from .tdw_logincode_export_secure import export_logincodes_secure_ram
from .tdw_selection_export_secure import SelectionExporterSecureRAM
from . import db

admin_views = Blueprint("admin_views", __name__, static_folder="static")


# ------------------------------------------------------------------
# Decorator


from functools import wraps


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("auth.admin_login"))  # Leite zur Login-Seite weiter
        return f(*args, **kwargs)

    return decorated_function


# ------------------------------------------------------------------
# Routing

# Reinstate when needed
# @admin_required
# @admin_views.route("/admin_dashboard")
# def adminDashboard():
#     return render_template("admin/admin_dashboard.html")


@admin_required
@admin_views.route("/tdw/panel", methods=["GET", "POST"])
def tdwPanel():
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        ms = module_status["modules"]["TdW"]
    return render_template("admin/tdw_panel.html", status=ms)


@admin_required
@admin_views.route("/tdw/upload_file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect(url_for("admin_views.tdw_panel"))
    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("admin_views.tdw_panel"))
    file.save("app/data/tdw/uploads/workbook.xlsx")

    FileHandlerTDWSecure()
    return redirect("/admin/tdw/panel")


@admin_required
@admin_views.route("/tdw/module_status", methods=["POST"])
def module_status():
    with open("app/data/module_status.json", "r") as f:
        data = json.load(f)

    current_status = data["modules"]["TdW"]

    if current_status == "active":
        data["modules"]["TdW"] = "inactive"
    else:
        data["modules"]["TdW"] = "active"

    with open("app/data/module_status.json", "w") as f:
        json.dump(data, f, indent=4)

    return redirect("./panel")


@admin_required
@admin_views.route("/tdw/export_logincodes", methods=["POST"])
def export_logincodes_route():
    if request.method == "POST":
        # Require file upload to get names
        if "file" not in request.files:
            return redirect("./panel")
        file = request.files["file"]
        if file.filename == "":
            return redirect("./panel")

        try:
            # Load names into RAM only
            names_map = load_names_map(file)

            # Export using names from RAM (returns BytesIO buffer)
            zip_buffer = export_logincodes_secure_ram(names_map)

            # Send file directly to user without saving to disk
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name="TdW_Logincodes_Secure.zip",
                mimetype="application/zip"
            )
        except Exception as e:
            print(f"Error exporting login codes: {e}")
            import traceback
            traceback.print_exc()
            return redirect("./panel")
    
@admin_required
@admin_views.route("/tdw/download_logincodes")
def download_logincodes():
    download_dir = "./data/tdw/downloads"
    return send_from_directory(download_dir, "TdW_Logincodes.zip", as_attachment=True)
    
@admin_required
@admin_views.route("/tdw/export_selections", methods=["POST"])
def export_selections():
    if request.method == "POST":
        # Require file upload to get names
        if "file" not in request.files:
            return redirect("./panel")
        file = request.files["file"]
        if file.filename == "":
            return redirect("./panel")

        try:
            # Load names into RAM only
            names_map = load_names_map(file)

            # Export using names from RAM (returns BytesIO buffer)
            excel_buffer = SelectionExporterSecureRAM(db, names_map)

            if excel_buffer is None:
                return redirect("./panel")

            # Send file directly to user without saving to disk
            return send_file(
                excel_buffer,
                as_attachment=True,
                download_name="TdW_Selections_Secure.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            print(f"Error exporting selections: {e}")
            import traceback
            traceback.print_exc()
            return redirect("./panel")
    else:
        return redirect("./panel")

@admin_required
@admin_views.route("/tdw/download_selections")
def download_selections():
    downloads_dir = "./data/tdw/downloads"
    return send_from_directory(downloads_dir, "TdW_Selections.xlsx", as_attachment=True)


@admin_required
@admin_views.route("/admin_logout")
def admin_logout():
    session["admin_logged_in"] = False
    return redirect("/admin_login")
