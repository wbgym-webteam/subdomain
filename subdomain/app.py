from flask import Flask
from flask import render_template
import sqlite3 
from migrations import migrate

db = sqlite3.connect("wbgym.db")
migrate(db)

app = Flask(__name__)

@app.get("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.get("/home")
def home():
    return render_template("home.html")