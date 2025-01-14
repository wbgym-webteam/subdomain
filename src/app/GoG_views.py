from flask import Flask, render_template, request, redirect, url_for, Blueprint

GoG = Blueprint("GoG", __name__)


@GoG.route("/home")
def home():
    return render_template("GoG/home.html")
