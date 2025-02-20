from docx import Document
from sqlalchemy import text
from . import db


def get_all_students():
    return db.session.execute(
        text(
            "SELECT first_name, last_name, grade, grade_selector, logincode FROM students ORDER BY grade, grade_selector"
        )
    ).fetchall()


def export_logincodes(query):
    pass
