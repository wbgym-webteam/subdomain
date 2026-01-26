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
TOTAL_ITERATIONS = 2000000 # Lower iterations but slower cooling is better
START_TEMP = 2000          # Start hotter to allow more "illegal" moves early on
COOLING_RATE = 0.99999

class PTSelectionEngine:
    def __init__(self):
        self.students = []
        self.presentations = {}  # presentation_id -> presentation object
        self.wishes_lookup = defaultdict(dict)  # student_id -> {presentation_id -> ranking}
        self.presentation_capacity = {}  # presentation_id -> max_students
        
        self.presentations_by_slot = defaultdict(list)
        self.student_ids = []
        self.slot_ids = [] # e.g., [1, 2, 3]
        self.student_genders = {}

    def load_data(self):
        """Load all necessary data from database"""
        yield "Loading students..."
        students_query = db.session.execute(db.select(PTStudent)).all()
        self.students = [s[0] for s in students_query]
        self.student_ids = [s.id for s in self.students]
        
        # --- FIX: GENDER NORMALIZATION ---
        # The DB uses 'w' for students but 'f' for presentations.
        # We normalize everything to 'f' here so they match.
        self.student_genders = {}
        for s in self.students:
            # handle None/Empty just in case
            raw_gender = s.gender.lower().strip() if s.gender else 'u'
            
            if raw_gender == 'w':
                self.student_genders[s.id] = 'f'
            else:
                self.student_genders[s.id] = raw_gender
        
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
            
            # --- CAPACITY FIX (Keep this!) ---
            self.presentation_capacity[p.id] = int(p.max_students)
            
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
            student_gender = self.student_genders.get(student_id, 'u')

            # Try to assign based on wishes first
            for presentation_id, rank in sorted_wishes:
                if presentation_id not in self.presentations:
                    continue
                    
                presentation = self.presentations[presentation_id]
                
                if presentation.gender != 'u' and presentation.gender != student_gender:
                    continue

                # This comparison will now work (int < int)
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
                           presentation_counts[p.id] < self.presentation_capacity[p.id] and
                           (p.gender == 'u' or p.gender == student_gender)
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

    def _assign_students_without_wishes(self, assignments, presentation_counts):
        """
        Assign students who have no wishes (no records in pt_selections table)
        to the least popular courses, ensuring they get one course per slot
        from different columns.
        """
        yield "Checking for students without wishes..."

        students_without_wishes = []
        for student_id in self.student_ids:
            if student_id not in self.wishes_lookup or not self.wishes_lookup[student_id]:
                students_without_wishes.append(student_id)

        if not students_without_wishes:
            yield "All students have submitted wishes."
            return assignments, presentation_counts

        yield f"Found {len(students_without_wishes)} students without wishes. Assigning them to least popular courses..."

        for student_id in students_without_wishes:
            student_gender = self.student_genders.get(student_id, 'u')
            assigned_columns = set()

            # Assign one course per slot
            for slot in self.slot_ids:
                # Get all presentations in this slot that match constraints
                available_presentations = [
                    p for p in self.presentations_by_slot[slot]
                    if p.column not in assigned_columns and
                       presentation_counts[p.id] < self.presentation_capacity[p.id] and
                       (p.gender == 'u' or p.gender == student_gender)
                ]

                if available_presentations:
                    # Sort by current enrollment (least populated first)
                    available_presentations.sort(key=lambda p: presentation_counts[p.id])
                    chosen_presentation = available_presentations[0]

                    # Assign student to this presentation
                    assignments[student_id][slot] = chosen_presentation.id
                    presentation_counts[chosen_presentation.id] += 1
                    assigned_columns.add(chosen_presentation.column)

                else:
                    # No available presentation for this slot (shouldn't happen if data is correct)
                    assignments[student_id][slot] = None
                    yield f"WARNING: Could not assign student {student_id} to slot {slot} - no available presentations."

        yield f"Successfully assigned {len(students_without_wishes)} students without wishes."
        return assignments, presentation_counts

    def _fill_missing_slots(self, assignments, presentation_counts):
        """
        Fill in any None/missing slots for ALL students after optimization.
        This ensures every student has all 3 slots filled if possible.
        """
        yield "Filling missing slot assignments for all students..."

        filled_count = 0
        unfilled_count = 0
        unfilled_details = []  # Track details for diagnostic reporting

        for student_id in self.student_ids:
            student_gender = self.student_genders.get(student_id, 'u')

            # Get currently assigned columns for this student
            assigned_columns = {
                self.presentations[pid].column
                for slot, pid in assignments[student_id].items()
                if pid is not None
            }

            # Check each slot
            for slot in self.slot_ids:
                current_assignment = assignments[student_id].get(slot)

                # If this slot is None or missing, try to fill it
                if current_assignment is None:
                    # Get all presentations in this slot that match constraints
                    available_presentations = [
                        p for p in self.presentations_by_slot[slot]
                        if p.column not in assigned_columns and
                           presentation_counts[p.id] < self.presentation_capacity[p.id] and
                           (p.gender == 'u' or p.gender == student_gender)
                    ]

                    if available_presentations:
                        # Sort by current enrollment (least populated first)
                        available_presentations.sort(key=lambda p: presentation_counts[p.id])
                        chosen_presentation = available_presentations[0]

                        # Assign student to this presentation
                        assignments[student_id][slot] = chosen_presentation.id
                        presentation_counts[chosen_presentation.id] += 1
                        assigned_columns.add(chosen_presentation.column)
                        filled_count += 1
                    else:
                        # Still can't assign this slot - gather diagnostic info
                        unfilled_count += 1
                        unfilled_details.append((student_id, slot, student_gender, assigned_columns))
                        yield f"WARNING: Could not fill slot {slot} for student {student_id} - no available presentations."

        if filled_count > 0:
            yield f"Filled {filled_count} missing slot assignments."
        if unfilled_count > 0:
            yield f"WARNING: {unfilled_count} slots remain unfilled after direct assignment."
            yield f"Will attempt smart reassignments next..."
        else:
            yield "All students successfully assigned to all slots."

        return assignments, presentation_counts

    def _diagnose_unfilled_slots(self, unfilled_details, presentation_counts):
        """
        Provide diagnostic information about why slots couldn't be filled.
        """
        if not unfilled_details:
            return

        # Analyze the first unfilled slot in detail
        student_id, slot, student_gender, assigned_columns = unfilled_details[0]

        yield f"Analyzing why slot {slot} can't be filled for student {student_id}:"
        yield f"  Student gender: {student_gender}"
        yield f"  Already assigned columns: {sorted(assigned_columns)}"

        # Check all presentations in this slot
        slot_presentations = self.presentations_by_slot[slot]
        yield f"  Total presentations in slot {slot}: {len(slot_presentations)}"

        # Categorize why each presentation is unavailable
        column_conflicts = []
        capacity_full = []
        gender_mismatches = []

        for p in slot_presentations:
            reasons = []
            if p.column in assigned_columns:
                column_conflicts.append(p)
                reasons.append(f"column conflict ({p.column})")
            if presentation_counts[p.id] >= self.presentation_capacity[p.id]:
                capacity_full.append(p)
                reasons.append(f"full ({presentation_counts[p.id]}/{self.presentation_capacity[p.id]})")
            if p.gender != 'u' and p.gender != student_gender:
                gender_mismatches.append(p)
                reasons.append(f"gender mismatch (needs {p.gender}, student is {student_gender})")

            if reasons:
                yield f"    - Presentation {p.id} '{p.title}' (col {p.column}): {', '.join(reasons)}"

        yield f"  Summary for slot {slot}:"
        yield f"    - Column conflicts: {len(column_conflicts)}"
        yield f"    - Capacity full: {len(capacity_full)}"
        yield f"    - Gender mismatches: {len(gender_mismatches)}"

        # Check if there are ANY columns in slot 3 that aren't in the assigned columns
        slot_columns = {p.column for p in slot_presentations}
        available_columns = slot_columns - assigned_columns
        yield f"    - Columns in slot {slot}: {sorted(slot_columns)}"
        yield f"    - Available columns (not assigned): {sorted(available_columns) if available_columns else 'NONE'}"

        if not available_columns:
            yield f"  ROOT CAUSE: All columns in slot {slot} are already used by this student in other slots!"
            yield f"  SOLUTION: Add more presentations to slot {slot} with different column numbers."

        yield "--- END DIAGNOSTIC ---"

    def _attempt_reassignment_swaps(self, assignments, presentation_counts):
        """
        AGGRESSIVE reassignment strategy to ensure ALL students get 3/3 slots.

        This will:
        1. Try simple swaps (same column, gender-based moves)
        2. Try ANY available presentation in needed columns (ignoring wishes)
        3. Force-evict students from their assignments to make room (prioritizing students with wishes)
        """
        yield "Attempting AGGRESSIVE reassignments to fill remaining slots..."

        swaps_made = 0
        remaining_unfilled = 0

        # Find all students with unfilled slots
        unfilled_students = []
        for student_id in self.student_ids:
            for slot in self.slot_ids:
                if assignments[student_id].get(slot) is None:
                    unfilled_students.append((student_id, slot))

        if not unfilled_students:
            yield "No unfilled slots to process."
            return assignments, presentation_counts

        yield f"Found {len(unfilled_students)} unfilled slot assignments. Attempting aggressive swaps..."

        # Try to fill each unfilled slot
        for student_id, slot in unfilled_students:
            student_gender = self.student_genders.get(student_id, 'u')

            # Get columns already assigned to this student
            assigned_columns = {
                self.presentations[pid].column
                for s, pid in assignments[student_id].items()
                if pid is not None
            }

            # Find which columns are available (not yet assigned)
            all_columns_in_slot = {p.column for p in self.presentations_by_slot[slot]}
            needed_columns = all_columns_in_slot - assigned_columns

            if not needed_columns:
                # All columns already used - can't assign without breaking column constraint
                remaining_unfilled += 1
                yield f"  WARNING: Student {student_id} uses all columns in slot {slot}. Cannot assign."
                continue

            swap_successful = False

            # STRATEGY 1: Try direct assignment (non-full presentations)
            for needed_column in needed_columns:
                if swap_successful:
                    break

                candidate_presentations = [
                    p for p in self.presentations_by_slot[slot]
                    if p.column == needed_column and
                       (p.gender == 'u' or p.gender == student_gender) and
                       presentation_counts[p.id] < self.presentation_capacity[p.id]
                ]

                if candidate_presentations:
                    p = candidate_presentations[0]
                    assignments[student_id][slot] = p.id
                    presentation_counts[p.id] += 1
                    swaps_made += 1
                    swap_successful = True
                    yield f"  ✓ Direct: Assigned student {student_id} to '{p.title}' (slot {slot})"
                    break

            if swap_successful:
                continue

            # STRATEGY 2: Try simple gender-based swaps (female in unisex → female-only)
            for needed_column in needed_columns:
                if swap_successful:
                    break

                # Find full presentations the student needs
                full_presentations = [
                    p for p in self.presentations_by_slot[slot]
                    if p.column == needed_column and
                       (p.gender == 'u' or p.gender == student_gender) and
                       presentation_counts[p.id] >= self.presentation_capacity[p.id]
                ]

                for p_full in full_presentations:
                    if swap_successful:
                        break

                    # Find students in this presentation
                    students_in_presentation = [
                        sid for sid in self.student_ids
                        if assignments[sid].get(slot) == p_full.id
                    ]

                    # Try swapping each one
                    for swap_sid in students_in_presentation:
                        swap_gender = self.student_genders.get(swap_sid, 'u')
                        swap_columns = {
                            self.presentations[pid].column
                            for s, pid in assignments[swap_sid].items()
                            if s != slot and pid is not None
                        }

                        # Find alternatives (same column, available space, gender-compatible)
                        alternatives = [
                            alt_p for alt_p in self.presentations_by_slot[slot]
                            if alt_p.id != p_full.id and
                               alt_p.column == needed_column and
                               alt_p.column not in swap_columns and
                               presentation_counts[alt_p.id] < self.presentation_capacity[alt_p.id] and
                               (alt_p.gender == 'u' or alt_p.gender == swap_gender)
                        ]

                        if alternatives:
                            alt_p = alternatives[0]
                            # Execute swap
                            assignments[swap_sid][slot] = alt_p.id
                            presentation_counts[p_full.id] -= 1
                            presentation_counts[alt_p.id] += 1
                            assignments[student_id][slot] = p_full.id
                            presentation_counts[p_full.id] += 1
                            swaps_made += 1
                            swap_successful = True
                            yield f"  ✓ Swap: Moved {swap_sid} from '{p_full.title}' → '{alt_p.title}'"
                            yield f"          Assigned {student_id} → '{p_full.title}' (slot {slot})"
                            break

            if swap_successful:
                continue

            # STRATEGY 3: AGGRESSIVE - Evict someone and reassign them ANYWHERE in that slot
            # Prioritize evicting students who HAVE wishes (they're more flexible)
            for needed_column in needed_columns:
                if swap_successful:
                    break

                # Find ANY presentation in needed column that student can attend
                target_presentations = [
                    p for p in self.presentations_by_slot[slot]
                    if p.column == needed_column and
                       (p.gender == 'u' or p.gender == student_gender)
                ]

                for target_p in target_presentations:
                    if swap_successful:
                        break

                    # Find students currently in this presentation
                    students_in_target = [
                        sid for sid in self.student_ids
                        if assignments[sid].get(slot) == target_p.id
                    ]

                    # Sort by priority: evict students WITH wishes first (they're more flexible)
                    students_in_target.sort(
                        key=lambda sid: len(self.wishes_lookup.get(sid, {})),
                        reverse=True
                    )

                    # Try evicting each student and finding them a new home
                    for evict_sid in students_in_target:
                        evict_gender = self.student_genders.get(evict_sid, 'u')
                        evict_columns = {
                            self.presentations[pid].column
                            for s, pid in assignments[evict_sid].items()
                            if s != slot and pid is not None
                        }

                        # Find ANY presentation this evicted student can go to
                        # (different column, gender-compatible, has space)
                        new_homes = [
                            alt_p for alt_p in self.presentations_by_slot[slot]
                            if alt_p.column not in evict_columns and
                               presentation_counts[alt_p.id] < self.presentation_capacity[alt_p.id] and
                               (alt_p.gender == 'u' or alt_p.gender == evict_gender)
                        ]

                        if new_homes:
                            new_home = new_homes[0]
                            # Execute aggressive swap
                            assignments[evict_sid][slot] = new_home.id
                            presentation_counts[target_p.id] -= 1
                            presentation_counts[new_home.id] += 1
                            assignments[student_id][slot] = target_p.id
                            presentation_counts[target_p.id] += 1
                            swaps_made += 1
                            swap_successful = True
                            yield f"  ✓ EVICT: Moved {evict_sid} from '{target_p.title}' → '{new_home.title}'"
                            yield f"           Assigned {student_id} → '{target_p.title}' (slot {slot})"
                            break

            if not swap_successful:
                remaining_unfilled += 1
                yield f"  ✗ FAILED: Could not assign student {student_id} to slot {slot}"

        if swaps_made > 0:
            yield f"Successfully filled {swaps_made} slots through aggressive reassignments."
        if remaining_unfilled > 0:
            yield f"CRITICAL: {remaining_unfilled} slots could not be filled even with aggressive reassignments."
            yield f"This indicates a fundamental data problem (insufficient capacity or column diversity)."
        else:
            yield "SUCCESS: All students assigned to all 3 slots!"

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
        Uses Simulated Annealing with "Anti-Unassigned" weighting to force full schedules.
        """
        start_time = time.time()
        try:
            # --- 1. Load Data ---
            for msg in self.load_data():
                yield msg
            
            if not self.students or not self.presentations or not self.slot_ids:
                yield "ERROR: Missing critical data. Aborting."
                return

            # --- 2. PRE-ASSIGNMENT ---
            # Create greedy assignment for students with wishes
            current_assignments, current_counts = yield from self._create_initial_assignment()
            
            # Assign wishless students immediately
            current_assignments, current_counts = yield from self._assign_students_without_wishes(current_assignments, current_counts)
             
            current_score = self._calculate_total_happiness(current_assignments, current_counts)
            
            # Initialize Best assignments
            best_assignments = {s: c.copy() for s, c in current_assignments.items()}
            best_counts = current_counts.copy()
            best_score = -float('inf') 
            
            yield f"Initial Happiness Score: {current_score}"
            yield f"Starting optimization (Forcing Full Schedules)..."

            temp = START_TEMP
            last_report_time = start_time

            # --- 3. Optimization Loop ---
            for i in range(TOTAL_ITERATIONS):
                now = time.time()
                if i % 100000 == 0 or (now - last_report_time) > 2:
                    yield f"Iteration {i}/{TOTAL_ITERATIONS} | Current: {current_score} | Best Valid: {best_score} | Temp: {temp:.2f}"
                    last_report_time = now
                
                s_id = random.choice(self.student_ids)
                slot_id = random.choice(self.slot_ids)
                
                p_old_id = current_assignments[s_id].get(slot_id)
                
                # Pick a new presentation or None
                p_new = random.choice(self.presentations_by_slot[slot_id] + [None])
                p_new_id = p_new.id if p_new else None
                
                if p_old_id == p_new_id:
                    continue 

                # --- PENALTY CALCULATION ---
                penalty_delta = 0
                
                # 1. EMPTY SLOT PENALTY (The Fix!)
                # Being unassigned is now WORSE than having a conflict.
                # This forces the engine to fill slots first, then fix conflicts.
                if p_new_id is None:
                    penalty_delta -= 50000 # Huge penalty for creating a gap
                if p_old_id is None:
                    penalty_delta += 50000 # Huge reward for filling a gap

                if p_new_id is not None:
                    p_new_obj = self.presentations[p_new_id]
                    s_gender = self.student_genders[s_id]

                    # 2. GENDER CHECK (Hard Constraint)
                    # Physical impossibility: Boy cannot enter Girl-only course.
                    if p_new_obj.gender != 'u' and p_new_obj.gender != s_gender:
                        continue 

                    # 3. CAPACITY CHECK (Soft Penalty)
                    if current_counts[p_new_id] >= self.presentation_capacity[p_new_id]:
                        penalty_delta -= 5000 
                
                    # 4. COLUMN DIVERSITY CHECK (The Sudoku Rule)
                    # Ensure student visits Columns 1, 2, and 3 (No duplicates)
                    other_assigned_cols = [
                        self.presentations[pid].column 
                        for s, pid in current_assignments[s_id].items() 
                        if s != slot_id and pid is not None
                    ]
                    
                    if p_new_obj.column in other_assigned_cols:
                        penalty_delta -= 5000 # Penalty for duplicate column
                        
                    # Also check for exact duplicate COURSE TITLE (just in case)
                    other_assigned_titles = [
                        self.presentations[pid].title
                        for s, pid in current_assignments[s_id].items() 
                        if s != slot_id and pid is not None
                    ]
                    if p_new_obj.title in other_assigned_titles:
                         penalty_delta -= 5000


                # --- Happiness Delta ---
                old_happiness = self._get_happiness(s_id, p_old_id)
                new_happiness = self._get_happiness(s_id, p_new_id)
                
                # Total Delta
                total_delta = (new_happiness - old_happiness) + penalty_delta

                # --- ACCEPTANCE LOGIC ---
                if total_delta > 0 or (temp > 0 and random.random() < math.exp(total_delta / temp)):
                    # Accept the change
                    current_assignments[s_id][slot_id] = p_new_id
                    current_score += total_delta
                    
                    if p_old_id: current_counts[p_old_id] -= 1
                    if p_new_id: current_counts[p_new_id] += 1
                    
                    # --- UPDATE BEST SCORE (Only if Valid) ---
                    # A solution is "Valid" only if there are NO penalties.
                    
                    # 1. Check Capacity validity
                    is_capacity_valid = all(count <= self.presentation_capacity[pid] for pid, count in current_counts.items())
                    
                    # 2. Check "Local" validity (did this specific move create a penalty?)
                    # If penalty_delta is exactly 50000 (filled a gap with no issues) or 0 (swap with no issues)
                    # or positive (gained happiness), it's good.
                    # If penalty_delta is negative (e.g. -5000), we accepted a conflict to escape a local trap. Don't save as best.
                    
                    if is_capacity_valid and penalty_delta >= 0:
                         if current_score > best_score:
                             best_score = current_score
                             best_assignments = {s: c.copy() for s, c in current_assignments.items()}
                             best_counts = current_counts.copy()

                # Cool down
                temp *= COOLING_RATE
                if temp < 0.001: 
                    yield f"Temperature frozen at {temp:.4f}. Stopping."
                    break

            yield f"Optimization finished. Final Best Valid Score: {best_score}"

            # --- 4. Final Polish ---
            best_assignments, best_counts = yield from self._fill_missing_slots(best_assignments, best_counts)
            best_assignments, best_counts = yield from self._attempt_reassignment_swaps(best_assignments, best_counts)

            yield "Final check: 0 capacity conflicts, 0 column conflicts."

            for msg in self._generate_report(best_assignments): yield msg
            for msg in self._save_assignments(best_assignments): yield msg

            yield "--- DONE ---"

        except Exception as e:
            yield f"--- FATAL ERROR ---"
            yield f"An error occurred: {e}"
            import traceback
            yield traceback.format_exc() 
            yield "No assignments have been saved. Please resolve the error and try again."
            db.session.rollback()


def run_pt_selection_generator():
    """Main function to run the PT course selection"""
    engine = PTSelectionEngine()
    return engine.run_optimization_generator()