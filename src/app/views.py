from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
)

views = Blueprint("views", __name__, static_folder="static")

@views.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@views.route("/home")
def home():
    return render_template("home.html")