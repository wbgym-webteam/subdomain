from werkzeug.security import generate_password_hash, check_password_hash

from . import db


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



## # ------------------------------------------------------
# P-Modules

class PTStudent(db.Model):
    __tablename__ = "pt_students"  # Fixed: was __table__name

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    grade_selector = db.Column(db.Integer, nullable=False)
    logincode = db.Column(db.String(20), nullable=False)

class PTPresentation(db.Model):
    __tablename__ = "pt_presentations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    presenter = db.Column(db.String(80), nullable=False)
    teacher = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(250), nullable=True)
    slot = db.Column(db.Integer, nullable=False)
    max_students = db.Column(db.Integer, nullable=False)
    column = db.Column(db.Integer, nullable=False)
    room = db.Column(db.String(20), nullable=False)

class PTSelection(db.Model):
    __tablename__ = "pt_selections"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('pt_students.id'), nullable=False)
    presentation_id = db.Column(db.Integer, db.ForeignKey('pt_presentations.id'), nullable=False)
    ranking = db.Column(db.Integer, nullable=True)  # Add ranking column for weighted selection
    # Relationships
    student = db.relationship("PTStudent", backref=db.backref("selections", lazy=True))
    presentation = db.relationship("PTPresentation", backref=db.backref("selections", lazy=True))

class PTAssignment(db.Model):
    __tablename__ = "pt_assignments"
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('pt_students.id'), nullable=False)
    presentation_id = db.Column(db.Integer, db.ForeignKey('pt_presentations.id'), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    
    # Relationships
    student = db.relationship("PTStudent", backref=db.backref("assignments", lazy=True))
    presentation = db.relationship("PTPresentation", backref=db.backref("assignments", lazy=True))

