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



### # ------------------------------------------------------
# sms

class StudentSMS(db.Model):
    __tablename__ = "students_sms"

    Student_id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    grade_selector = db.Column(db.Integer, nullable=False)
    logincode = db.Column(db.String(20), nullable=False)
    
    #relationship for the Student_course table
    courses_in_Student_course = db.relationship("Course", 
                                               secondary="student_course",  # Use the actual table name
                                               backref="students_in_Student_course")

    #relationship for the Host table
    courses_in_Host = db.relationship("Course", 
                                     secondary="hosts",  # Use the actual table name 
                                     backref="students_in_Hosts")


class Student_course(db.Model):
    __tablename__ = "student_course"

    Student_id = db.Column(db.Integer, db.ForeignKey("students_sms.Student_id"), primary_key=True)
    Course_id = db.Column(db.Integer, db.ForeignKey("courses.course_id"), primary_key=True)
    weight = db.Column(db.Integer, nullable=False)


class Hosts(db.Model):
    __tablename__ = "hosts"

    Student_id = db.Column(db.Integer, db.ForeignKey("students_sms.Student_id"), primary_key=True)
    Course_id = db.Column(db.Integer, db.ForeignKey("courses.course_id"), primary_key=True)


class Course(db.Model):
    __tablename__ = "courses"

    course_id = db.Column(db.Integer, primary_key=True)
    course_title = db.Column(db.String, nullable=False)
    course_private = db.Column(db.Boolean, nullable=False)
    couse_description = db.Column(db.String, nullable=False)
    course_teacher = db.Column(db.String, nullable=False)




