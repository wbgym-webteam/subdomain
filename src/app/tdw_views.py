from flask import Flask, render_template, request, redirect, url_for, Blueprint, session
import sqlalchemy

tdw = Blueprint("tdw", __name__)


@tdw.route("/", methods=["GET", "POST"])
def selection():
    if session["tdw.student_id"]:
        if request.method == "POST":
            pass
        else:
            return render_template("tdw/tdw_selection.html")
    else:
        return redirect("/login")
