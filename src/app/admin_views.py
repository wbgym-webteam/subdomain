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

from .tdw_filehandler import FileHandler
from .tdw_logincode_export import export_logincodes
from .tdw_selection_export import SelectionExporter
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

    FileHandler()
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
        export_logincodes()
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
        SelectionExporter(db, "app/data/tdw/uploads/workbook.xlsx")
        return redirect("./panel")
    else:
        return redirect("./panel")

@admin_required
@admin_views.route("/tdw/download_selections")
def download_selections():
    uploads_dir = "./data/tdw/uploads"
    return send_from_directory(uploads_dir, "workbook.xlsx", as_attachment=True)


@admin_required
@admin_views.route("/admin_logout")
def admin_logout():
    session["admin_logged_in"] = False
    return redirect("/admin_login")
