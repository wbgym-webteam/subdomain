from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
)

import json

from .tdw_filehandler import FileHandler

admin_views = Blueprint("admin_views", __name__, static_folder="static")

# ------------------------------------------------------------------
# Routing


@admin_views.route("/admin_dashboard")
def adminDashboard():
    return render_template("admin/admin_dashboard.html")


@admin_views.route("/tdw/panel", methods=["GET", "POST"])
def tdwPanel():
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        ms = module_status["modules"]["TdW"]
    return render_template("admin/tdw_panel.html", status=ms)


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
