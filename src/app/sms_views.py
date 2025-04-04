from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlalchemy
from sqlalchemy import text

# TODO: Import the models from the models.py file

from . import db

sms = Blueprint("sms", __name__)

# ---------------------------------------------------------------
# SMS Routes
# ---------------------------------------------------------------
#
# This is the view that the logged in student will see


@sms.route("/", methods=["GET", "POST"])
def selection():
    if session.get("logged_in", True) == True:
        if request.method == "POST":
            student_id = session.get("sms_student_id")
            if student_id is None:
                return redirect("/login")
            student_id = str(student_id)
