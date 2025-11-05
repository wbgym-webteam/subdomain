from sqlalchemy import text
from .models import PTStudent, PTPresentation, PTSelection, PTAssignment
from . import db
import random
from collections import defaultdict

class PTSelectionEngine:
    def __init__(self):
        self.students = []
        self.presentations = []
        self.wishes = defaultdict(list)  # student_id -> [(presentation_id, ranking)]
        self.assignments = defaultdict(list)  # student_id -> [presentation_ids]
        self.presentation_capacity = {}  # presentation_id -> max_students
        self.presentation_assignments = defaultdict(list)  # presentation_id -> [student_ids]
        
    def load_data(self):
        """Load all necessary data from database"""
        # Load students
        students_query = db.session.execute(db.select(PTStudent)).all()
        self.students = [s[0] for s in students_query]
        
        # Load presentations
        presentations_query = db.session.execute(db.select(PTPresentation)).all()
        self.presentations = [p[0] for p in presentations_query]
        
        # Build capacity mapping
        for presentation in self.presentations:
            self.presentation_capacity[presentation.id] = presentation.max_students
        
        # Load wishes (rankings)
        wishes_query = db.session.execute(
            text("SELECT student_id, presentation_id, ranking FROM pt_selections WHERE ranking > 0 ORDER BY ranking ASC")
        ).all()
        
        for student_id, presentation_id, ranking in wishes_query:
            self.wishes[student_id].append((presentation_id, ranking))
    
    def get_presentations_by_column(self):
        """Group presentations by column"""
        columns = defaultdict(list)
        for presentation in self.presentations:
            columns[presentation.column].append(presentation)
        return columns
    
    def assign_courses(self):
        """Main assignment algorithm"""
        self.load_data()
        presentations_by_column = self.get_presentations_by_column()
        
        # Clear existing assignments
        db.session.execute(text("DELETE FROM pt_assignments"))
        db.session.commit()
        
        # For each student, try to assign one course from each column
        for student in self.students:
            student_wishes = dict(self.wishes[student.id])  # presentation_id -> ranking
            assigned_columns = set()
            
            # Sort student's wishes by ranking (lower number = higher preference)
            sorted_wishes = sorted(student_wishes.items(), key=lambda x: x[1])
            
            for presentation_id, ranking in sorted_wishes:
                # Find which column this presentation belongs to
                presentation = next((p for p in self.presentations if p.id == presentation_id), None)
                if not presentation:
                    continue
                
                column = presentation.column
                
                # Skip if we already assigned a course from this column
                if column in assigned_columns:
                    continue
                
                # Check if presentation has capacity - ensure both values are integers
                current_assignments = len(self.presentation_assignments[presentation_id])
                max_capacity = int(self.presentation_capacity[presentation_id])
                
                if current_assignments < max_capacity:
                    # Assign this presentation to the student
                    self.presentation_assignments[presentation_id].append(student.id)
                    self.assignments[student.id].append(presentation_id)
                    assigned_columns.add(column)
                    
                    # Save to database
                    db.session.execute(
                        text("INSERT INTO pt_assignments (student_id, presentation_id, slot) VALUES (:student_id, :presentation_id, :slot)"),
                        {"student_id": student.id, "presentation_id": presentation_id, "slot": presentation.slot}
                    )
        
        db.session.commit()
        
        # Fill remaining spots for students who didn't get 3 courses
        self._fill_remaining_spots(presentations_by_column)
        
        return self._generate_report()
    
    def _fill_remaining_spots(self, presentations_by_column):
        """Fill remaining spots for students who need more courses"""
        for student in self.students:
            assigned_columns = set()
            
            # Get currently assigned columns
            current_assignments = db.session.execute(
                text("SELECT presentation_id FROM pt_assignments WHERE student_id = :student_id"),
                {"student_id": student.id}
            ).all()
            
            for (presentation_id,) in current_assignments:
                presentation = next((p for p in self.presentations if p.id == presentation_id), None)
                if presentation:
                    assigned_columns.add(presentation.column)
            
            # Try to assign from remaining columns
            for column, presentations in presentations_by_column.items():
                if column in assigned_columns:
                    continue
                
                # Find available presentations in this column
                available_presentations = []
                for presentation in presentations:
                    current_count = len(self.presentation_assignments[presentation.id])
                    max_capacity = int(presentation.max_students)  # Ensure integer conversion
                    if current_count < max_capacity:
                        available_presentations.append(presentation)
                
                # Assign to first available presentation
                if available_presentations:
                    presentation = available_presentations[0]
                    self.presentation_assignments[presentation.id].append(student.id)
                    
                    db.session.execute(
                        text("INSERT INTO pt_assignments (student_id, presentation_id, slot) VALUES (:student_id, :presentation_id, :slot)"),
                        {"student_id": student.id, "presentation_id": presentation.id, "slot": presentation.slot}
                    )
                    assigned_columns.add(column)
        
        db.session.commit()
    
    def _generate_report(self):
        """Generate a report of the assignment results"""
        total_students = len(self.students)
        assigned_students = len([s for s in self.students if len(self.assignments[s.id]) > 0])
        
        # Count satisfaction levels
        satisfaction_stats = {"perfect": 0, "good": 0, "okay": 0, "poor": 0}
        
        for student in self.students:
            student_wishes = dict(self.wishes[student.id])
            assigned_presentations = self.assignments[student.id]
            
            if not assigned_presentations:
                satisfaction_stats["poor"] += 1
                continue
            
            # Calculate average ranking of assigned courses
            rankings = [student_wishes.get(p_id, 999) for p_id in assigned_presentations]
            avg_ranking = sum(rankings) / len(rankings) if rankings else 999
            
            if avg_ranking <= 2:
                satisfaction_stats["perfect"] += 1
            elif avg_ranking <= 4:
                satisfaction_stats["good"] += 1
            elif avg_ranking <= 6:
                satisfaction_stats["okay"] += 1
            else:
                satisfaction_stats["poor"] += 1
        
        return {
            "total_students": total_students,
            "assigned_students": assigned_students,
            "satisfaction": satisfaction_stats,
            "success_rate": round((assigned_students / total_students) * 100, 2) if total_students > 0 else 0
        }

def run_pt_selection():
    """Main function to run the PT course selection"""
    engine = PTSelectionEngine()
    return engine.assign_courses()
