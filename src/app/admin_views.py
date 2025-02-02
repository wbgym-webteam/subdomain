from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
)

admin_views = Blueprint("admin_views", __name__, static_folder="static")


@admin_views.route("/admin_dashboard")
def adminDashboard():
    return render_template("admin/admin_dashboard.html")


@admin_views.route("/tdw_panel", methods=["GET", "POST"])
def tdwPanel():
    return render_template("admin/tdw_panel.html")


@admin_views.route("/upload_file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect(url_for("admin_views.tdw_panel"))
    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("admin_views.tdw_panel"))
    file.save(f"data/tdw/uploads/{file.filename}")
    return redirect(url_for("admin_views.tdw_panel"))
