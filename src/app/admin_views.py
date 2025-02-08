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
    return render_template("admin/tdw_panel.html")


@admin_views.route("/tdw/upload_file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect(url_for("admin_views.tdw_panel"))
    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("admin_views.tdw_panel"))
    file.save("app/data/tdw/uploads/workbook.xlsx")

    FileHandler(file)
    return redirect("/admin/tdw/panel")


@admin_views.route("/tdw/module_status", methods=["POST"])
def module_status():
    with open("app/data/module_status.json", "r") as f:
        data = json.load(f)

    status = request.form.get("options")
    data["TdW"] = status

    with open("app/data/module_status.json", "w") as f:
        json.dump(data, f, indent=4)
