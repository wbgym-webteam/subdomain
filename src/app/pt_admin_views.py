#subdomain\src\app\pt_admin_views.py
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    send_file,
    Response,
    current_app
)

from sqlalchemy import text

import json
import os
import zipfile
import html
import traceback
from .pt_filehandler import FileHandlerPT

from .models import PTStudent, PTPresentation, PTSelection
from . import db
from .pt_logincode_export import export_logincodes as export_logincodesPT
from .pt_selection_export import SelectionExporter as SelectionExporterPT
from .pt_selection_engine import run_pt_selection_generator

pt_admin_views = Blueprint("pt_admin_views", __name__, static_folder="static")

# ------------------------------------------------------------------
# Decorator
from functools import wraps


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            # Preserve the original URL for redirect after login
            return redirect(f"/admin_login?next={request.url}")
        return f(*args, **kwargs)

    return decorated_function


# ------------------------------------------------------------------
# Routing for PT admin views

@pt_admin_views.route("/admin/pt/panel", methods=["GET", "POST"])  # Added /admin prefix
@admin_required
def pt_Panel():
    with open("app/data/module_status.json", "r") as f:
        module_status = json.load(f)
        ms = module_status["modules"]["PT"]
    return render_template("admin/pt_panel.html", status=ms)


@pt_admin_views.route("/admin/pt/upload_file", methods=["POST"])
@admin_required
def pt_upload_file():
    if "file" not in request.files:
        return redirect("/admin/pt/panel")  # Use absolute path
    file = request.files["file"]
    if file.filename == "":
        return redirect("/admin/pt/panel")  # Use absolute path
    
    # Create upload directory if it doesn't exist
    upload_dir = "app/data/pt/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Check if this is a names file upload
    file_type = request.form.get("file_type", "data")
    
    if file_type == "names":
        # Save as names file
        file_path = os.path.join(upload_dir, "names_workbook.xlsx")
        file.save(file_path)
        print("Names file uploaded successfully")
    else:
        # Save as regular data file
        file_path = os.path.join(upload_dir, "workbook.xlsx")
        file.save(file_path)
        FileHandlerPT()
        print("Data file uploaded and processed successfully")

    return redirect("/admin/pt/panel")  # Use absolute path


@pt_admin_views.route("/admin/pt/module_status", methods=["POST"])
@admin_required
def pt_module_status():
    with open("app/data/module_status.json", "r") as f:
        data = json.load(f)

    current_status = data["modules"]["PT"]

    if current_status == "active":
        data["modules"]["PT"] = "inactive"
    else:
        data["modules"]["PT"] = "active"

    with open("app/data/module_status.json", "w") as f:
        json.dump(data, f, indent=4)

    return redirect("/admin/pt/panel")  # Use absolute path

@pt_admin_views.route("/admin/pt/export_logincodes", methods=["POST"])
@admin_required
def pt_export_logincodes_route():
    if request.method == "POST":
        export_logincodesPT()
        return redirect("/admin/pt/panel")  # Use absolute path
    
@pt_admin_views.route("/admin/pt/download_logincodes", methods=["GET"])  # Added /admin prefix
@admin_required
def pt_download_logincodes():  # Ensure this function is used for the pt route
    current_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(current_dir, 'data', 'pt', 'downloads')
    return send_from_directory(download_dir, "PT_Logincodes.zip", as_attachment=True)


@pt_admin_views.route("/admin/pt/export_wishes", methods=["POST"])
@admin_required
def pt_export_wishes():
    try:
        print("Starting PT wishes export...")
        result_file_path = SelectionExporterPT(db)
        if result_file_path and os.path.exists(result_file_path):
            print(f"Export successful, file created at: {result_file_path}")
            return redirect("/admin/pt/panel")
        else:
            print("Export failed - no file created")
            return redirect("/admin/pt/panel")
    except Exception as e:
        print(f"Error exporting wishes: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")  # Use absolute path


@pt_admin_views.route("/admin/pt/download_wishes", methods=["GET"])
@admin_required
def pt_download_wishes():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(current_dir, 'data', 'pt', 'downloads')
        file_name = "Kurs_Wuensche.xlsx"
        file_path = os.path.join(download_dir, file_name)
        print(f"Looking for file at: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        if not os.path.exists(file_path):
            print("File not found, creating export first...")
            result_file_path = SelectionExporterPT(db)
            if not result_file_path or not os.path.exists(result_file_path):
                print("Could not create export file")
                return redirect("/admin/pt/panel")
        return send_from_directory(
            download_dir,
            file_name,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print(f"Error downloading wishes: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")  # Use absolute path

@pt_admin_views.route("/admin/pt/run_selection", methods=["POST"])
@admin_required
def pt_run_selection():
    """
    This route now returns a streaming response of *just*
    HTML log fragments, not a full page.
    """
    app_ctx = current_app._get_current_object()

    def stream_progress(app):
        # 4. Wrap the *entire* generator in the app context.
        with app.app_context():
            try:
                # 2. Run the generator and stream its output
                engine_generator = run_pt_selection_generator()
                for log_line in engine_generator:
                    # Escape the log line to prevent HTML injection
                    safe_line = html.escape(log_line)
                    
                    # Add some color coding for readability
                    if "ERROR" in log_line or "FATAL" in log_line or "WARNING" in log_line:
                        yield f'<p class="error">{safe_line}</p>'
                    elif "Iteration" in log_line:
                        yield f'<p class="iteration">{safe_line}</p>'
                    elif "--- Assignment Report ---" in log_line or "- " in log_line:
                        yield f'<p class="report">{safe_line}</p>'
                    elif "--- DONE ---" in log_line or "Successfully saved" in log_line:
                        yield f'<p class="success">{safe_line}</p>'
                    else:
                        yield f'<p>{safe_line}</p>'
                    
                    # Flush buffer
                    yield " " 
                
                yield '<p class="done">Engine run finished.</p>'

            except Exception as e:
                safe_error = html.escape(str(e))
                safe_traceback = html.escape(traceback.format_exc())
                yield f'<p class="error">A critical error occurred in the view: {safe_error}</p>'
                yield f'<p class="error">{safe_traceback}</p>'

    # Return the streaming response
    return Response(stream_progress(app_ctx), mimetype='text/html')

@pt_admin_views.route("/admin/pt/view_assignments", methods=["GET"])
@admin_required
def pt_view_assignments():
    try:
        # Get all assignments with student and presentation details
        assignments_query = db.session.execute(
            text("""
                SELECT 
                    s.first_name, s.last_name, s.grade,
                    p.title, p.presenter, p.slot, p.column, p.room
                FROM pt_assignments a
                JOIN pt_students s ON a.student_id = s.id
                JOIN pt_presentations p ON a.presentation_id = p.id
                ORDER BY s.last_name, s.first_name, p.slot
            """)
        ).all()
        
        # Get assignment report from session if available
        report = session.get('assignment_report', {})
        
        return render_template(
            "admin/pt_assignments.html", 
            assignments=assignments_query,
            report=report
        )
    except Exception as e:
        print(f"Error viewing assignments: {e}")
        return redirect("/admin/pt/panel")

@pt_admin_views.route("/admin/pt/export_assignments", methods=["GET"])
@admin_required
def pt_export_assignments():
    try:
        import pandas as pd
        
        # Get all assignments with details
        assignments_query = db.session.execute(
            text("""
                SELECT 
                    s.first_name, s.last_name, s.grade, s.logincode,
                    p.title, p.presenter, p.teacher, p.description, 
                    p.slot, p.column, p.room, p.max_students
                FROM pt_assignments a
                JOIN pt_students s ON a.student_id = s.id
                JOIN pt_presentations p ON a.presentation_id = p.id
                ORDER BY s.last_name, s.first_name, p.slot
            """)
        ).all()
        
        # Convert to DataFrame
        df = pd.DataFrame(assignments_query, columns=[
            'First Name', 'Last Name', 'Grade', 'Login Code',
            'Course Title', 'Presenter', 'Teacher', 'Description',
            'Slot', 'Column', 'Room', 'Max Students'
        ])
        
        # Create download directory
        download_dir = os.path.join('app', 'data', 'pt', 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        # Save to Excel
        file_path = os.path.join(download_dir, 'PT_Assignments.xlsx')
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Assignments', index=False)
            
            # Create separate sheets for each slot
            for slot in [1, 2, 3]:
                slot_df = df[df['Slot'] == slot]
                slot_df.to_excel(writer, sheet_name=f'Slot {slot}', index=False)
        
        return send_from_directory(
            download_dir,
            'PT_Assignments.xlsx',
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        print(f"Error exporting assignments: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")

@pt_admin_views.route("/admin/pt/export_assignments_pdf", methods=["GET"])
@admin_required
def pt_export_assignments_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Create download directory with absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(current_dir, 'data', 'pt', 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        print(f"Download directory: {download_dir}")
        
        # Create PDF file path
        pdf_filename = 'PT_Schüler_Stundenpläne.pdf'
        pdf_path = os.path.join(download_dir, pdf_filename)
        
        print(f"PDF path: {pdf_path}")
        
        # Get all students with their assignments first to check if any exist
        students_query = db.session.execute(
            text("""
                SELECT DISTINCT s.id, s.first_name, s.last_name, s.grade, s.grade_selector
                FROM pt_students s
                JOIN pt_assignments a ON s.id = a.student_id
                ORDER BY s.last_name, s.first_name
            """)
        ).all()
        
        if not students_query:
            print("No students with assignments found")
            # Create a simple PDF with no assignments message
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story = [Paragraph("Keine PT-Kurszuordnungen gefunden.", styles['Title'])]
            doc.build(story)
        else:
            print(f"Found {len(students_query)} students with assignments")
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            story = []
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            student_title_style = ParagraphStyle(
                'StudentTitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=colors.black
            )
            
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=10,
                alignment=TA_LEFT
            )
            
            # Add main title page
            story.append(Paragraph("PT-Kurszuordnungen", title_style))
            story.append(Spacer(1, 2*cm))
            story.append(Paragraph(f"Schüler-Stundenpläne - {len(students_query)} Schüler", styles['Heading2']))
            story.append(PageBreak())
            
            # Generate page for each student
            for i, student in enumerate(students_query):
                student_id, first_name, last_name, grade, grade_selector = student
                
                # Add student header
                story.append(Paragraph(f"{last_name}, {first_name}", student_title_style))
                story.append(Paragraph(f"Klasse: {grade} | Klassenbezeichnung: {grade_selector}", info_style))
                story.append(Spacer(1, 0.5*cm))
                
                # Get student's assignments
                assignments_query = db.session.execute(
                    text("""
                        SELECT p.title, p.presenter, p.teacher, p.slot, p.room, p.description
                        FROM pt_assignments a
                        JOIN pt_presentations p ON a.presentation_id = p.id
                        WHERE a.student_id = :student_id
                        ORDER BY p.slot
                    """),
                    {"student_id": student_id}
                ).all()
                
                if assignments_query:
                    # Create table data
                    table_data = [
                        ['Block', 'Kurstitel', 'Referent', 'Lehrer', 'Raum']
                    ]
                    
                    for assignment in assignments_query:
                        title, presenter, teacher, slot, room, description = assignment
                        # Handle None values
                        table_data.append([
                            f"Block {slot}",
                            title or "N/A",
                            presenter or "N/A",
                            teacher or "N/A",
                            room or "N/A"
                        ])
                    
                    # Create and style the table
                    table = Table(table_data, colWidths=[2*cm, 6*cm, 3*cm, 3*cm, 2*cm])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 1*cm))
                    
                    # Add course descriptions if they exist
                    has_descriptions = any(assignment[5] for assignment in assignments_query if assignment[5])
                    if has_descriptions:
                        story.append(Paragraph("Kursbeschreibungen:", styles['Heading3']))
                        story.append(Spacer(1, 0.3*cm))
                        
                        for assignment in assignments_query:
                            title, presenter, teacher, slot, room, description = assignment
                            if description and description.strip():
                                desc_text = f"<b>Block {slot} - {title}:</b> {description}"
                                story.append(Paragraph(desc_text, info_style))
                                story.append(Spacer(1, 0.2*cm))
                else:
                    story.append(Paragraph("Keine Kurszuordnungen für diesen Schüler gefunden.", info_style))
                
                # Add page break except for the last student
                if i < len(students_query) - 1:
                    story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
        
        # Verify the file was created
        if not os.path.exists(pdf_path):
            print(f"PDF file was not created at {pdf_path}")
            return redirect("/admin/pt/panel")
        
        print(f"PDF created successfully at {pdf_path}")
        print(f"File size: {os.path.getsize(pdf_path)} bytes")
        
        # Send file using relative path from app directory
        return send_from_directory(
            os.path.join('data', 'pt', 'downloads'),
            pdf_filename,
            as_attachment=True,
            mimetype="application/pdf"
        )
        
    except ImportError as e:
        print(f"Missing reportlab library: {e}")
        print("Please install reportlab: pip install reportlab")
        return redirect("/admin/pt/panel")
    except Exception as e:
        print(f"Error exporting PDF: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")

@pt_admin_views.route("/admin/pt/export_room_lists_pdf", methods=["GET"])
@admin_required
def pt_export_room_lists_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Create download directory with absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(current_dir, 'data', 'pt', 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        print(f"Download directory: {download_dir}")
        
        # Create PDF file path
        pdf_filename = 'PT_Raum_Listen.pdf'
        pdf_path = os.path.join(download_dir, pdf_filename)
        
        print(f"PDF path: {pdf_path}")
        
        # Get all room assignments organized by room and slot
        room_assignments_query = db.session.execute(
            text("""
                SELECT 
                    p.room, p.slot, p.title, p.presenter, p.teacher, p.description,
                    s.first_name, s.last_name, s.grade, s.logincode
                FROM pt_assignments a
                JOIN pt_students s ON a.student_id = s.id
                JOIN pt_presentations p ON a.presentation_id = p.id
                ORDER BY p.room, p.slot, s.last_name, s.first_name
            """)
        ).all()
        
        if not room_assignments_query:
            print("No room assignments found")
            # Create a simple PDF with no assignments message
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story = [Paragraph("Keine PT-Raumzuordnungen gefunden.", styles['Title'])]
            doc.build(story)
        else:
            print(f"Found {len(room_assignments_query)} room assignments")
            
            # Organize data by room and slot
            room_data = {}
            for assignment in room_assignments_query:
                room, slot, title, presenter, teacher, description, first_name, last_name, grade, logincode = assignment
                
                if room not in room_data:
                    room_data[room] = {}
                
                if slot not in room_data[room]:
                    room_data[room][slot] = {
                        'course_info': {
                            'title': title,
                            'presenter': presenter,
                            'teacher': teacher,
                            'description': description
                        },
                        'students': []
                    }
                
                room_data[room][slot]['students'].append({
                    'first_name': first_name,
                    'last_name': last_name,
                    'grade': grade,
                    'logincode': logincode
                })
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            story = []
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            room_title_style = ParagraphStyle(
                'RoomTitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=colors.black
            )
            
            course_title_style = ParagraphStyle(
                'CourseTitle',
                parent=styles['Heading3'],
                fontSize=14,
                spaceAfter=15,
                alignment=TA_LEFT,
                textColor=colors.darkgreen
            )
            
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=10,
                alignment=TA_LEFT
            )
            
            # Add main title page
            story.append(Paragraph("PT-Raumzuordnungslisten", title_style))
            story.append(Spacer(1, 2*cm))
            story.append(Paragraph(f"Raumlisten - {len(room_data)} Räume", styles['Heading2']))
            story.append(PageBreak())
            
            # Generate pages for each room and slot combination
            room_count = 0
            total_rooms = sum(len(slots) for slots in room_data.values())
            
            for room, slots in sorted(room_data.items()):
                for slot, slot_data in sorted(slots.items()):
                    room_count += 1
                    
                    # Room and slot header
                    story.append(Paragraph(f"Raum: {room}", room_title_style))
                    story.append(Paragraph(f"Block {slot}", course_title_style))
                    story.append(Spacer(1, 0.5*cm))
                    
                    # Course information
                    course = slot_data['course_info']
                    story.append(Paragraph(f"<b>Kurs:</b> {course['title']}", info_style))
                    story.append(Paragraph(f"<b>Referent:</b> {course['presenter'] or 'N/A'}", info_style))
                    story.append(Paragraph(f"<b>Lehrer:</b> {course['teacher'] or 'N/A'}", info_style))
                    
                    if course['description'] and course['description'].strip():
                        story.append(Paragraph(f"<b>Beschreibung:</b> {course['description']}", info_style))
                    
                    story.append(Spacer(1, 0.5*cm))
                    
                    # Student list
                    students = slot_data['students']
                    story.append(Paragraph(f"<b>Schüler ({len(students)}):</b>", course_title_style))
                    
                    if students:
                        # Create student table
                        table_data = [
                            ['Nr.', 'Nachname', 'Vorname', 'Klasse', 'Login-Code']
                        ]
                        
                        for i, student in enumerate(students, 1):
                            table_data.append([
                                str(i),
                                student['last_name'] or 'N/A',
                                student['first_name'] or 'N/A',
                                str(student['grade']) or 'N/A',
                                student['logincode'] or 'N/A'
                            ])
                        
                        # Create and style the table
                        table = Table(table_data, colWidths=[1*cm, 4*cm, 4*cm, 2*cm, 3*cm])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 11),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 9),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Number column center
                            ('ALIGN', (1, 1), (2, -1), 'LEFT'),    # Name columns left
                            ('ALIGN', (3, 1), (-1, -1), 'CENTER'), # Grade and login center
                        ]))
                        
                        story.append(table)
                    else:
                        story.append(Paragraph("Keine Schüler diesem Kurs zugeordnet.", info_style))
                    
                    # Add signature line
                    story.append(Spacer(1, 1*cm))
                    story.append(Paragraph("Unterschrift Lehrer: ________________________", info_style))
                    
                    # Add page break except for the last room/slot combination
                    if room_count < total_rooms:
                        story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
        
        # Verify the file was created
        if not os.path.exists(pdf_path):
            print(f"PDF file was not created at {pdf_path}")
            return redirect("/admin/pt/panel")
        
        print(f"PDF created successfully at {pdf_path}")
        print(f"File size: {os.path.getsize(pdf_path)} bytes")
        
        # Send file using relative path from app directory
        return send_from_directory(
            os.path.join('data', 'pt', 'downloads'),
            pdf_filename,
            as_attachment=True,
            mimetype="application/pdf"
        )
        
    except ImportError as e:
        print(f"Missing reportlab library: {e}")
        print("Please install reportlab: pip install reportlab")
        return redirect("/admin/pt/panel")
    except Exception as e:
        print(f"Error exporting room lists PDF: {e}")
        import traceback
        traceback.print_exc()
        return redirect("/admin/pt/panel")