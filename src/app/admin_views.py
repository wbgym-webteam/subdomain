from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    escape,
)

admin_views = Blueprint("admin_views", __name__, static_folder="static")


@admin_views.route("/admin_dashboard")
def adminDashboard():
    return render_template("admin/admin_dashboard.html")
