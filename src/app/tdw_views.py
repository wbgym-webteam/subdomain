from flask import Flask, render_template, request, redirect, url_for, Blueprint
import sqlalchemy

tdw = Blueprint("tdw", __name__)


@tdw.route("/", methods=["GET", "POST"])
def selection():
    if request.method == "POST":
        pass
    else:
        return render_template("tdw/tdw_selection.html")
