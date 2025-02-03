from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ------------------------------------------------------
# Admin Panel


class adminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ------------------------------------------------------
# Game of Grapes


class gogUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ------------------------------------------------------
# TdW


class Presentation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ID = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    abstract = db.Column(db.String(250))
    presenter = db.Column(db.String(80), nullable=False)
    grades = db.Column(
        db.String(20), nullable=False
    )  # Which grades the presentation is for
    max_students = db.Column(db.Integer, nullable=False)
    # students --> Col


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ID = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    # presentation --> Col
