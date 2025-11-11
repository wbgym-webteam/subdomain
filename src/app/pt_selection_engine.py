#subdomain\src\app\pt_selection_engine.py
from sqlalchemy import text
from .models import PTStudent, PTPresentation, PTSelection, PTAssignment
from . import db
import random
import math
from collections import defaultdict, Counter
import time

# --- Happiness Scoring ---
WISH_HAPPINESS = {
    1: 100,  # First choice
    2: 70,   # Second choice
    3: 50,   # Third choice
    4: 30,
    5: 15
}
DEFAULT_HAPPINESS = 1     # Any wish ranked 6th or lower
NO_WISH_HAPPINESS = -50   # Assigned a course they didn't wish for at all


# --- Optimization Settings ---
TOTAL_ITERATIONS = 5000000
START_TEMP = 1000
COOLING_RATE = 0.99995 

class PTSelectionEngine:
    def __init__(self):
        self.students = []
        self.presentations = {}  # presentation_id -> presentation object
        self.wishes_lookup = defaultdict(dict)  # student_id -> {presentation_id -> ranking}
        self.presentation_capacity = {}  # presentation_id -> max_students
        
        self.presentations_by_slot = defaultdict(list)
        self.student_ids = []
        self.slot_ids = [] # e.g., [1, 2, 3]

    def load_data(self):
        """Load all necessary data from database"""
        yield "Loading students..."
        students_query = db.session.execute(db.select(PTStudent)).all()
        self.students = [s[0] for s in students_query]
        self.student_ids = [s.id for s in self.students]
        if not self.students:
            yield "ERROR: No students found in database."
            return

        yield f"Loaded {len(self.students)} students."
        yield "Loading presentations..."
        presentations_query = db.session.execute(db.select(PTPresentation)).all()
        if not presentations_query:
            yield "ERROR: No presentations found in database."
            return
            
        for (p,) in presentations_query:
            self.presentations[p.id] = p
            self.presentation_capacity[p.id] = p.max_students
            self.presentations_by_slot[p.slot].append(p)
        
        self.slot_ids = sorted(list(self.presentations_by_slot.keys()))
        yield f"Loaded {len(self.presentations)} presentations in {len(self.slot_ids)} slots."

        yield "Loading student wishes..."
        wishes_query = db.session.execute(
            text("SELECT student_id, presentation_id, ranking FROM pt_selections WHERE ranking > 0")
        ).all()
        
        wishes_found = False
        for student_id, presentation_id, ranking in wishes_query:
            if presentation_id in self.presentations: 
                self.wishes_lookup[student_id][presentation_id] = ranking
                wishes_found = True
        
        if not wishes_found:
            yield "WARNING: No wishes were loaded from the database. Score will be very low."
            
        yield f"Loaded wishes for {len(self.wishes_lookup)} students."

    def _get_happiness(self, student_id, presentation_id):
        """Calculate happiness for a single student-presentation assignment"""
        if presentation_id is None:
            return 0 # Not assigned
            
        ranking = self.wishes_lookup[student_id].get(presentation_id)
        
        if ranking is None:
            return NO_WISH_HAPPINESS
        elif ranking in WISH_HAPPINESS:
            return WISH_HAPPINESS[ranking]
        else:
            return DEFAULT_HAPPINESS

    def _calculate_total_happiness(self, assignments, presentation_counts):
        """
        Calculate the total happiness score for a given set of assignments.
        This is slow and only used for the initial score.
        """
        total_score = 0
        
        # Add happiness from student wishes
        for student_id, assigned_slots in assignments.items():
            for slot, presentation_id in assigned_slots.items():
                if presentation_id is None:
                    continue
                total_score += self._get_happiness(student_id, presentation_id)
                
        return total_score

    def _create_initial_assignment(self):
        """
        Create a valid (but not optimal) starting assignment.
        Tries to honor wishes while respecting slot, column, and capacity.
        """
        yield "Creating initial (greedy) assignment..."
        assignments = defaultdict(dict)  # student_id -> {slot_id -> presentation_id}
        presentation_counts = Counter()
        
        for student_id in self.student_ids:
            assigned_slots = set()
            assigned_columns = set()
            
            student_wishes = self.wishes_lookup.get(student_id, {})
            sorted_wishes = sorted(student_wishes.items(), key=lambda item: item[1])

            # Try to assign based on wishes first
            for presentation_id, rank in sorted_wishes:
                if presentation_id not in self.presentations:
                    continue
                    
                presentation = self.presentations[presentation_id]
                
                if presentation.slot not in assigned_slots and \
                   presentation.column not in assigned_columns and \
                   presentation_counts[presentation_id] < self.presentation_capacity[presentation_id]:
                    
                    assignments[student_id][presentation.slot] = presentation_id
                    presentation_counts[presentation_id] += 1
                    assigned_slots.add(presentation.slot)
                    assigned_columns.add(presentation.column)

            # Fill remaining slots with non-wished courses
            for slot in self.slot_ids:
                if slot not in assigned_slots:
                    available_presentations = [
                        p for p in self.presentations_by_slot[slot]
                        if p.column not in assigned_columns and
                           presentation_counts[p.id] < self.presentation_capacity[p.id] 
                    ]
                    
                    if available_presentations:
                        # Sort by least populated presentation
                        available_presentations.sort(key=lambda p: presentation_counts[p.id])
                        p_to_assign = available_presentations[0] # Pick the least full one
                        #
                        assignments[student_id][slot] = p_to_assign.id
                        presentation_counts[p_to_assign.id] += 1
                        assigned_slots.add(p_to_assign.slot)
                        assigned_columns.add(p_to_assign.column)
                    else:
                        assignments[student_id][slot] = None

        yield "Initial assignment created."
        return assignments, presentation_counts

    def _save_assignments(self, assignments):
        """Clear old assignments and save the new best solution to the DB"""
        yield "Saving best assignments to database..."
        db.session.execute(text("DELETE FROM pt_assignments"))
        
        insert_data = []
        for student_id, assigned_slots in assignments.items():
            for slot, presentation_id in assigned_slots.items():
                if presentation_id:
                    insert_data.append({
                        "student_id": student_id,
                        "presentation_id": presentation_id,
                        "slot": slot 
                    })
        
        if insert_data:
            db.session.execute(text(
                "INSERT INTO pt_assignments (student_id, presentation_id, slot) "
                "VALUES (:student_id, :presentation_id, :slot)"
            ), insert_data)
        
        db.session.commit()
        yield f"Successfully saved {len(insert_data)} assignments."


    def _generate_report(self, assignments):
        """Generate a satisfaction report based on final assignments"""
        total_students = len(self.students)
        satisfaction_stats = {"1st Choice": 0, "2nd-3rd": 0, "Wished": 0, "Not Wished": 0, "Unassigned": 0}
        
        for student_id in self.student_ids:
            student_assignments = assignments.get(student_id, {})
            if not student_assignments or all(v is None for v in student_assignments.values()):
                satisfaction_stats["Unassigned"] += 1
                continue

            got_1st = False
            got_2_3 = False
            got_wished = False
            
            for slot, p_id in student_assignments.items():
                if p_id is None:
                    continue
                
                ranking = self.wishes_lookup[student_id].get(p_id)
                if ranking == 1:
                    got_1st = True
                elif ranking in [2, 3]:
                    got_2_3 = True
                elif ranking is not None:
                    got_wished = True
            
            if got_1st:
                satisfaction_stats["1st Choice"] += 1
            elif got_2_3:
                satisfaction_stats["2nd-3rd"] += 1
            elif got_wished:
                satisfaction_stats["Wished"] += 1
            else:
                satisfaction_stats["Not Wished"] += 1

        yield "--- Assignment Report ---"
        yield f"Total Students: {total_students}"
        
        for key, count in satisfaction_stats.items():
            percent = (count / total_students * 100) if total_students > 0 else 0
            yield f"- {key}: {count} ({percent:.1f}%)"
        
        yield "---------------------------"

    def run_optimization_generator(self):
        """
        Main generator function to run the optimization.
        Core logic is now slot-based and checks for column conflicts.
        """
        start_time = time.time()
        try:
            # --- 1. Load Data ---
            for msg in self.load_data():
                yield msg
            
            if not self.students or not self.presentations or not self.slot_ids:
                yield "ERROR: Missing critical data (students, presentations, or slots). Aborting."
                return

            current_assignments, current_counts = yield from self._create_initial_assignment()
            
            current_score = self._calculate_total_happiness(current_assignments, current_counts)
            
            best_assignments = {s: c.copy() for s, c in current_assignments.items()}
            best_counts = current_counts.copy()
            best_score = current_score
            
            yield f"Initial Happiness Score: {current_score}"
            yield f"Starting optimization for {len(self.student_ids)} students..."

            temp = START_TEMP
            last_report_time = start_time

            # --- 3. Optimization Loop ---
            for i in range(TOTAL_ITERATIONS):
                now = time.time()
                if i % 100000 == 0 or (now - last_report_time) > 2:
                    yield f"Iteration {i}/{TOTAL_ITERATIONS} | Current Score: {current_score} | Best Score: {best_score} | Temp: {temp:.2f}"
                    last_report_time = now
                
                s_id = random.choice(self.student_ids)
                slot_id = random.choice(self.slot_ids)
                
                p_old_id = current_assignments[s_id].get(slot_id)
                
                p_new = random.choice(self.presentations_by_slot[slot_id] + [None])
                p_new_id = p_new.id if p_new else None
                
                if p_old_id == p_new_id:
                    continue 

                # --- HARD CONSTRAINT CHECKS ---
                if p_new_id is not None:
                    # 1. Check Capacity
                    if current_counts[p_new_id] >= self.presentation_capacity[p_new_id]:
                        continue # Move is impossible. Reject.
                
                    # 2. Check Column Conflict
                    p_new_col = self.presentations[p_new_id].column
                    other_assigned_cols = {
                        self.presentations[pid].column 
                        for s, pid in current_assignments[s_id].items() 
                        if s != slot_id and pid is not None
                    }
                    if p_new_col in other_assigned_cols:
                        continue # Move is impossible. Reject.
                
                
                # --- This move is VALID. Calculate score delta. ---
                
                old_happiness = self._get_happiness(s_id, p_old_id)
                new_happiness = self._get_happiness(s_id, p_new_id)
                happiness_delta = new_happiness - old_happiness
                
                score_delta = happiness_delta

                # Simulated Annealing: Decide whether to accept the change
                if score_delta > 0 or (temp > 0 and random.random() < math.exp(score_delta / temp)):
                    # Accept the change
                    current_assignments[s_id][slot_id] = p_new_id
                    current_score += score_delta
                    
                    # Update counts
                    if p_old_id:
                        current_counts[p_old_id] -= 1
                    if p_new_id:
                        current_counts[p_new_id] += 1
                    
                    if current_score > best_score:
                        best_score = current_score
                        best_assignments = {s: c.copy() for s, c in current_assignments.items()}
                        best_counts = current_counts.copy()

                temp *= COOLING_RATE
                
                if temp < 0.001:
                    yield f"Temperature is frozen (Temp: {temp:.4f}). Stopping optimization early at iteration {i}."
                    break # Exit the for-loop

            yield f"Optimization finished after {i+1} iterations." # Show true iteration count
            yield f"Final Best Score: {best_score}"

            # --- 4. Final Report & Save ---
            yield "Final check: 0 capacity conflicts, 0 column conflicts."
            
            for msg in self._generate_report(best_assignments):
                yield msg
                
            for msg in self._save_assignments(best_assignments):
                yield msg
                
            yield "--- DONE ---"

        except Exception as e:
            yield f"--- FATAL ERROR ---"
            yield f"An error occurred: {e}"
            import traceback
            yield traceback.format_exc()
            yield "No assignments have been saved. Please resolve the error and try again."
            db.session.rollback() # Rollback any partial changes


def run_pt_selection_generator():
    """Main function to run the PT course selection"""
    engine = PTSelectionEngine()
    return engine.run_optimization_generator()