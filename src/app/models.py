from werkzeug.security import generate_password_hash, check_password_hash

from . import db

# ------------------------------------------------------
# # Game of Grapes


class gogUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# # ------------------------------------------------------
# TdW


class Presentation(db.Model):
    __tablename__ = "presentations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    presenter = db.Column(db.String(80), nullable=False)
    abstract = db.Column(db.String(250))
    grades = db.Column(
        db.String(20), nullable=False
    )  # Which grades the presentation is for


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    grade_selector = db.Column(db.Integer, nullable=False)
    logincode = db.Column(db.String(20), nullable=False)


class Selection(db.Model):
    __tablename__ = "selections"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    presentation_id = db.Column(db.Integer, nullable=False)


class BlockedPresentation(db.Model):
    __tablename__ = "blocked_presentations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    presentation_id = db.Column(db.Integer, nullable=False)
