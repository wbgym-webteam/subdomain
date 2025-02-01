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


@admin_views.route("/admin_login", methods=["GET", "POST"])
def adminLogin():
    if request.method == "POST":
        pass
    else:
        return render_template("admin/admin_login.html")


@admin_views.route("/")
def adminDashboard():
    return render_template("admin/admin_dashboard.html")
