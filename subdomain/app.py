from flask import Flask
import sqlite3 

db = sqlite3.connect("wbgym.db")

app = Flask(__name__)

@app.get("/")
def hello_world():
    return "<p>Hello, World!</p>"

