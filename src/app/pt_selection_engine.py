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

# --- Capacity Settings ---
MIN_STUDENTS_PER_COURSE = 7  # Courses with fewer students will be dissolved

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

    def _recount_assignments(self, assignments):
        """
        Recount presentation enrollments from actual assignments.
        This ensures counts are always accurate and in sync with assignments.
        """
        counts = Counter()
        for student_id, assigned_slots in assignments.items():
            for slot, presentation_id in assigned_slots.items():
                if presentation_id is not None:
                    counts[presentation_id] += 1
        return counts

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

    def _resolve_overcapacity(self, assignments, presentation_counts):
        """
        STRICTLY ENFORCE capacity limits by moving excess students to their 2nd/3rd/etc choices.

        This ensures no course exceeds max_students, even if it means some students
        don't get their 1st choice.
        """
        yield "Resolving overcapacity issues (enforcing strict capacity limits)..."

        moves_made = 0
        iterations = 0
        max_iterations = 100  # Prevent infinite loops

        while iterations < max_iterations:
            iterations += 1

            # Find all overcapacity courses
            overcapacity_courses = [
                (pid, presentation_counts[pid] - self.presentation_capacity[pid])
                for pid in self.presentations
                if presentation_counts[pid] > self.presentation_capacity[pid]
            ]

            if not overcapacity_courses:
                break

            # Sort by most overcapacity first
            overcapacity_courses.sort(key=lambda x: -x[1])

            made_progress = False

            for pid, excess in overcapacity_courses:
                if presentation_counts[pid] <= self.presentation_capacity[pid]:
                    continue  # Already resolved

                presentation = self.presentations[pid]
                slot = presentation.slot

                # Find all students in this overcapacity course
                students_in_course = [
                    sid for sid in self.student_ids
                    if assignments[sid].get(slot) == pid
                ]

                # Sort students by their ranking for this course (lowest priority = moved first)
                # Students who didn't wish for this course at all are moved first
                # Then students with lower rankings (5th choice before 1st choice)
                def get_priority(sid):
                    ranking = self.wishes_lookup[sid].get(pid)
                    if ranking is None:
                        return 0  # Didn't wish for it - move first
                    return ranking  # Lower ranking = lower priority = moved first

                students_in_course.sort(key=get_priority)

                # Try to move excess students to alternatives
                students_to_move = presentation_counts[pid] - self.presentation_capacity[pid]

                for sid in students_in_course:
                    if students_to_move <= 0:
                        break

                    student_gender = self.student_genders.get(sid, 'u')

                    # Get columns already used by this student (excluding current slot)
                    used_columns = {
                        self.presentations[p].column
                        for s, p in assignments[sid].items()
                        if s != slot and p is not None
                    }

                    # Find alternative courses in the same slot
                    # Prioritize by: 1) student's wishes, 2) has capacity, 3) valid column
                    alternatives = []

                    for alt_p in self.presentations_by_slot[slot]:
                        if alt_p.id == pid:
                            continue  # Skip current course
                        if alt_p.column in used_columns:
                            continue  # Column conflict
                        if alt_p.gender != 'u' and alt_p.gender != student_gender:
                            continue  # Gender mismatch
                        if presentation_counts[alt_p.id] >= self.presentation_capacity[alt_p.id]:
                            continue  # Already full

                        # Calculate priority (prefer student's ranked wishes)
                        alt_ranking = self.wishes_lookup[sid].get(alt_p.id)
                        if alt_ranking is not None:
                            priority = alt_ranking  # 2nd choice = 2, 3rd = 3, etc.
                        else:
                            priority = 100  # Non-wished courses last

                        alternatives.append((alt_p, priority))

                    if alternatives:
                        # Sort by priority (lower = better)
                        alternatives.sort(key=lambda x: x[1])
                        best_alt = alternatives[0][0]

                        # Move student
                        old_ranking = self.wishes_lookup[sid].get(pid, "not wished")
                        new_ranking = self.wishes_lookup[sid].get(best_alt.id, "not wished")

                        assignments[sid][slot] = best_alt.id
                        presentation_counts[pid] -= 1
                        presentation_counts[best_alt.id] += 1
                        students_to_move -= 1
                        moves_made += 1
                        made_progress = True

                        yield f"  ↪ Moved student {sid} from '{presentation.title}' (rank {old_ranking}) → '{best_alt.title}' (rank {new_ranking})"

            if not made_progress:
                # No more moves possible
                break

        # Report remaining overcapacity
        remaining_overcapacity = [
            (pid, presentation_counts[pid] - self.presentation_capacity[pid])
            for pid in self.presentations
            if presentation_counts[pid] > self.presentation_capacity[pid]
        ]

        if remaining_overcapacity:
            yield f"WARNING: {len(remaining_overcapacity)} courses still overcapacity after {moves_made} moves."
            for pid, excess in remaining_overcapacity:
                p = self.presentations[pid]
                yield f"  - '{p.title}' (slot {p.slot}): {presentation_counts[pid]}/{self.presentation_capacity[pid]} (+{excess})"
            yield "  This may indicate insufficient alternative courses or column constraints."
        else:
            yield f"Successfully resolved all overcapacity issues with {moves_made} student moves."

        return assignments, presentation_counts

    def _force_fix_overcapacity(self, assignments, presentation_counts):
        """
        ABSOLUTE FINAL FIX: Force-move students from overcapacity courses.

        This is the last resort - it will move students even if it means
        giving them a course they didn't wish for, or even leaving them
        unassigned in that slot if no alternatives exist.
        """
        yield "FORCE-FIXING overcapacity violations..."

        moves_made = 0
        max_iterations = 200

        for iteration in range(max_iterations):
            # Find overcapacity courses
            overcapacity = [
                (pid, presentation_counts[pid] - self.presentation_capacity[pid])
                for pid in self.presentations
                if presentation_counts[pid] > self.presentation_capacity[pid]
            ]

            if not overcapacity:
                break

            # Sort by most overcapacity first
            overcapacity.sort(key=lambda x: -x[1])
            pid, excess = overcapacity[0]

            presentation = self.presentations[pid]
            slot = presentation.slot
            cap = self.presentation_capacity[pid]

            # Find students in this course
            students_in_course = [
                sid for sid in self.student_ids
                if assignments[sid].get(slot) == pid
            ]

            if not students_in_course:
                yield f"  ERROR: Course '{presentation.title}' shows overcapacity but no students found!"
                break

            # Sort: move students who didn't wish for this course first
            def get_priority(sid):
                ranking = self.wishes_lookup[sid].get(pid)
                if ranking is None:
                    return 0
                return ranking

            students_in_course.sort(key=get_priority)

            # Move excess students
            students_to_move = presentation_counts[pid] - cap
            moved_this_round = 0

            for sid in students_in_course:
                if moved_this_round >= students_to_move:
                    break

                student_gender = self.student_genders.get(sid, 'u')

                # Get columns already used by this student
                used_columns = {
                    self.presentations[p].column
                    for s, p in assignments[sid].items()
                    if s != slot and p is not None
                }

                # Find ANY alternative course with space
                alternatives = [
                    alt_p for alt_p in self.presentations_by_slot[slot]
                    if alt_p.id != pid and
                       alt_p.column not in used_columns and
                       (alt_p.gender == 'u' or alt_p.gender == student_gender) and
                       presentation_counts[alt_p.id] < self.presentation_capacity[alt_p.id]
                ]

                if alternatives:
                    # Prefer student's wishes if available
                    def alt_priority(alt_p):
                        ranking = self.wishes_lookup[sid].get(alt_p.id)
                        if ranking is not None:
                            return ranking
                        return 100

                    alternatives.sort(key=alt_priority)
                    best_alt = alternatives[0]

                    # Move student
                    assignments[sid][slot] = best_alt.id
                    presentation_counts[pid] -= 1
                    presentation_counts[best_alt.id] += 1
                    moves_made += 1
                    moved_this_round += 1

                    yield f"  🔧 Force-moved student {sid} from '{presentation.title}' → '{best_alt.title}'"
                else:
                    # No alternative - unassign student from this slot as last resort
                    assignments[sid][slot] = None
                    presentation_counts[pid] -= 1
                    moves_made += 1
                    moved_this_round += 1

                    yield f"  ⚠ UNASSIGNED student {sid} from '{presentation.title}' (no alternatives!)"

        # Final check
        remaining = [
            (pid, presentation_counts[pid], self.presentation_capacity[pid])
            for pid in self.presentations
            if presentation_counts[pid] > self.presentation_capacity[pid]
        ]

        if remaining:
            yield f"CRITICAL: {len(remaining)} courses STILL overcapacity after force-fix!"
            for pid, count, cap in remaining:
                yield f"  - '{self.presentations[pid].title}': {count}/{cap}"
        else:
            yield f"✓ Force-fixed {moves_made} assignments. All capacities now respected."

        return assignments, presentation_counts

    def _balance_column_loads(self, assignments, presentation_counts):
        """
        Balance enrollment between courses in the same slot AND column.

        If two courses share slot+column (e.g., slot 2, column 3) and one has 21 students
        while the other has 8, this will move students from the overloaded one to the
        underloaded one to even out the distribution.

        This sacrifices some "1st choice" fulfillment for fairer distribution.
        """
        yield "Balancing course loads within same slot/column groups..."

        # Group presentations by (slot, column)
        slot_column_groups = defaultdict(list)
        for pid, presentation in self.presentations.items():
            key = (presentation.slot, presentation.column)
            slot_column_groups[key].append(pid)

        moves_made = 0
        max_imbalance_threshold = 5  # Only balance if difference > this

        for (slot, column), pids in slot_column_groups.items():
            if len(pids) < 2:
                continue  # Need at least 2 courses to balance

            iterations = 0
            max_iterations = 50  # Prevent infinite loops per group

            while iterations < max_iterations:
                iterations += 1

                # Get current counts for courses in this group
                counts = [(pid, presentation_counts[pid]) for pid in pids]
                counts.sort(key=lambda x: x[1])  # Sort by enrollment

                min_pid, min_count = counts[0]
                max_pid, max_count = counts[-1]

                imbalance = max_count - min_count

                if imbalance <= max_imbalance_threshold:
                    break  # Balanced enough

                # Try to move a student from max_course to min_course
                max_presentation = self.presentations[max_pid]
                min_presentation = self.presentations[min_pid]

                # Find students in the overloaded course
                students_in_max = [
                    sid for sid in self.student_ids
                    if assignments[sid].get(slot) == max_pid
                ]

                # Sort by priority: move students with lower ranking for max_course first
                # or students who didn't wish for it at all
                def get_move_priority(sid):
                    ranking = self.wishes_lookup[sid].get(max_pid)
                    if ranking is None:
                        return 0  # Didn't wish for max_course - move first
                    return ranking  # Lower ranking = moved first (5th before 1st)

                students_in_max.sort(key=get_move_priority)

                moved_someone = False

                for sid in students_in_max:
                    student_gender = self.student_genders.get(sid, 'u')

                    # Check gender compatibility with min_course
                    if min_presentation.gender != 'u' and min_presentation.gender != student_gender:
                        continue  # Can't move due to gender

                    # Check if min_course is already at capacity
                    if presentation_counts[min_pid] >= self.presentation_capacity[min_pid]:
                        break  # min_course is full, can't balance further

                    # Check column constraints for this student
                    used_columns = {
                        self.presentations[p].column
                        for s, p in assignments[sid].items()
                        if s != slot and p is not None
                    }

                    # Since both courses are in the same column, if student is in max_course,
                    # they can move to min_course (same column constraint satisfied)

                    # Move the student
                    old_ranking = self.wishes_lookup[sid].get(max_pid, "not wished")
                    new_ranking = self.wishes_lookup[sid].get(min_pid, "not wished")

                    assignments[sid][slot] = min_pid
                    presentation_counts[max_pid] -= 1
                    presentation_counts[min_pid] += 1
                    moves_made += 1
                    moved_someone = True

                    yield f"  ⚖ Balanced: student {sid} from '{max_presentation.title}' ({max_count}) → '{min_presentation.title}' ({min_count}) [slot {slot}, col {column}]"
                    break  # Move one student per iteration, then re-evaluate

                if not moved_someone:
                    break  # No valid moves possible for this group

        if moves_made > 0:
            yield f"Balanced {moves_made} students across same-column courses."
        else:
            yield "No balancing needed (courses already well-distributed)."

        # Report final distribution for groups with multiple courses
        yield "Final distribution by slot/column:"
        for (slot, column), pids in sorted(slot_column_groups.items()):
            if len(pids) >= 2:
                dist = ", ".join([
                    f"'{self.presentations[pid].title}': {presentation_counts[pid]}"
                    for pid in pids
                ])
                yield f"  Slot {slot}, Col {column}: {dist}"

        return assignments, presentation_counts

    def _dissolve_underpopulated_courses(self, assignments, presentation_counts):
        """
        Dissolve courses that have fewer than MIN_STUDENTS_PER_COURSE students.

        Students from dissolved courses are moved to other courses in the same
        slot/column that have enough capacity and meet the minimum threshold.
        """
        yield f"Checking for underpopulated courses (minimum {MIN_STUDENTS_PER_COURSE} students)..."

        moves_made = 0
        dissolved_courses = []
        iterations = 0
        max_iterations = 50  # Prevent infinite loops

        while iterations < max_iterations:
            iterations += 1

            # Find courses below minimum threshold
            underpopulated = [
                (pid, presentation_counts[pid])
                for pid in self.presentations
                if 0 < presentation_counts[pid] < MIN_STUDENTS_PER_COURSE
            ]

            if not underpopulated:
                break

            # Sort by smallest first (easier to dissolve)
            underpopulated.sort(key=lambda x: x[1])

            made_progress = False

            for pid, count in underpopulated:
                if presentation_counts[pid] == 0:
                    continue  # Already dissolved
                if presentation_counts[pid] >= MIN_STUDENTS_PER_COURSE:
                    continue  # No longer underpopulated

                presentation = self.presentations[pid]
                slot = presentation.slot
                column = presentation.column

                # Find alternative courses in the same slot AND column
                # (same column so student constraints are preserved)
                same_column_alternatives = [
                    alt_p for alt_p in self.presentations_by_slot[slot]
                    if alt_p.id != pid and alt_p.column == column
                ]

                # Also consider ANY course in the slot if same-column doesn't work
                any_slot_alternatives = [
                    alt_p for alt_p in self.presentations_by_slot[slot]
                    if alt_p.id != pid
                ]

                # Find students in this underpopulated course
                students_in_course = [
                    sid for sid in self.student_ids
                    if assignments[sid].get(slot) == pid
                ]

                if not students_in_course:
                    continue

                # Try to move all students from this course
                all_moved = True
                students_moved_this_round = 0

                for sid in students_in_course:
                    student_gender = self.student_genders.get(sid, 'u')

                    # Get columns already used by this student (excluding current slot)
                    used_columns = {
                        self.presentations[p].column
                        for s, p in assignments[sid].items()
                        if s != slot and p is not None
                    }

                    # First try same-column alternatives (preserves column constraint)
                    moved = False
                    for alt_p in same_column_alternatives:
                        if alt_p.gender != 'u' and alt_p.gender != student_gender:
                            continue  # Gender mismatch
                        if presentation_counts[alt_p.id] >= self.presentation_capacity[alt_p.id]:
                            continue  # Already full

                        # Move student
                        assignments[sid][slot] = alt_p.id
                        presentation_counts[pid] -= 1
                        presentation_counts[alt_p.id] += 1
                        moves_made += 1
                        students_moved_this_round += 1
                        moved = True
                        made_progress = True
                        yield f"  🚫 Dissolving '{presentation.title}' ({count}): moved student {sid} → '{alt_p.title}'"
                        break

                    if moved:
                        continue

                    # Try any slot alternative if same-column didn't work
                    for alt_p in any_slot_alternatives:
                        if alt_p.column in used_columns:
                            continue  # Column conflict
                        if alt_p.gender != 'u' and alt_p.gender != student_gender:
                            continue  # Gender mismatch
                        if presentation_counts[alt_p.id] >= self.presentation_capacity[alt_p.id]:
                            continue  # Already full

                        # Move student
                        assignments[sid][slot] = alt_p.id
                        presentation_counts[pid] -= 1
                        presentation_counts[alt_p.id] += 1
                        moves_made += 1
                        students_moved_this_round += 1
                        moved = True
                        made_progress = True
                        yield f"  🚫 Dissolving '{presentation.title}' ({count}): moved student {sid} → '{alt_p.title}' (different column)"
                        break

                    if not moved:
                        all_moved = False

                if all_moved and presentation_counts[pid] == 0:
                    dissolved_courses.append(presentation.title)

            if not made_progress:
                break

        # Report results
        if dissolved_courses:
            yield f"Dissolved {len(dissolved_courses)} underpopulated courses: {', '.join(dissolved_courses)}"

        # Check for remaining underpopulated courses
        remaining_underpopulated = [
            (pid, presentation_counts[pid])
            for pid in self.presentations
            if 0 < presentation_counts[pid] < MIN_STUDENTS_PER_COURSE
        ]

        if remaining_underpopulated:
            yield f"WARNING: {len(remaining_underpopulated)} courses still below minimum ({MIN_STUDENTS_PER_COURSE}):"
            for pid, count in remaining_underpopulated:
                p = self.presentations[pid]
                yield f"  - '{p.title}' (slot {p.slot}, col {p.column}): {count} students"
            yield "  These courses may need to be manually handled or the minimum threshold lowered."
        elif moves_made > 0:
            yield f"Successfully moved {moves_made} students from underpopulated courses."
        else:
            yield "All courses meet the minimum enrollment threshold."

        return assignments, presentation_counts

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
        Features:
        1. Progressive Penalties (Punishes crowding exponentially).
        2. Pairwise Swapping.
        3. "Lesser of Two Evils" saving.
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
            current_assignments, current_counts = yield from self._create_initial_assignment()
            current_assignments, current_counts = yield from self._assign_students_without_wishes(current_assignments, current_counts)
             
            # Calculate initial score (with penalties)
            current_score = self._calculate_total_happiness(current_assignments, current_counts)

            # Verify capacity constraints are respected (should never fail with hard constraints)
            capacity_violations = []
            for pid, count in current_counts.items():
                if count > self.presentation_capacity[pid]:
                    capacity_violations.append((self.presentations[pid].title, count, self.presentation_capacity[pid]))
            if capacity_violations:
                yield f"WARNING: Initial assignment has {len(capacity_violations)} capacity violations!"
                for title, count, cap in capacity_violations:
                    yield f"  - '{title}': {count}/{cap}"

            # Apply initial penalties
            for s in self.student_ids:
                for slot in self.slot_ids:
                    pid = current_assignments[s].get(slot)
                    if pid is None:
                        current_score -= 50000
                    else:
                        # Column Penalty
                        p_col = self.presentations[pid].column
                        other_cols = [self.presentations[p].column for sl, p in current_assignments[s].items() if sl != slot and p]
                        if p_col in other_cols:
                            current_score -= 5000

            best_assignments = {s: c.copy() for s, c in current_assignments.items()}
            best_counts = current_counts.copy()
            best_score = current_score
            
            yield f"Initial Score: {current_score}"
            yield f"Starting optimization (Progressive Balancing)..."

            temp = START_TEMP
            last_report_time = start_time

            # --- 3. Optimization Loop ---
            for i in range(TOTAL_ITERATIONS):
                now = time.time()
                if i % 100000 == 0 or (now - last_report_time) > 2:
                    yield f"Iteration {i}/{TOTAL_ITERATIONS} | Current: {current_score} | Best: {best_score} | Temp: {temp:.2f}"
                    last_report_time = now
                
                # --- STRATEGY SELECTION ---
                is_swap = random.random() < 0.3
                
                s1_id = random.choice(self.student_ids)
                slot_id = random.choice(self.slot_ids)
                p1_old_id = current_assignments[s1_id].get(slot_id)
                
                penalty_delta = 0
                happiness_delta = 0
                
                if is_swap and p1_old_id is not None:
                    # --- SWAP MOVE ---
                    # (Swaps preserve total counts, so they naturally balance distribution)
                    s2_id = random.choice(self.student_ids)
                    if s1_id == s2_id: continue
                    p2_old_id = current_assignments[s2_id].get(slot_id)
                    
                    if p2_old_id is None or p1_old_id == p2_old_id: continue

                    # Gender Check
                    s1_gender = self.student_genders[s1_id]
                    s2_gender = self.student_genders[s2_id]
                    p1_obj = self.presentations[p1_old_id]
                    p2_obj = self.presentations[p2_old_id]

                    if (p2_obj.gender != 'u' and p2_obj.gender != s1_gender) or \
                       (p1_obj.gender != 'u' and p1_obj.gender != s2_gender):
                        continue

                    # Column Checks (S1)
                    s1_other_cols = [self.presentations[p].column for sl, p in current_assignments[s1_id].items() if sl != slot_id and p]
                    if p2_obj.column in s1_other_cols: penalty_delta -= 5000
                    if p1_obj.column in s1_other_cols: penalty_delta += 5000 

                    # Column Checks (S2)
                    s2_other_cols = [self.presentations[p].column for sl, p in current_assignments[s2_id].items() if sl != slot_id and p]
                    if p1_obj.column in s2_other_cols: penalty_delta -= 5000
                    if p2_obj.column in s2_other_cols: penalty_delta += 5000 

                    happiness_delta += (self._get_happiness(s1_id, p2_old_id) - self._get_happiness(s1_id, p1_old_id))
                    happiness_delta += (self._get_happiness(s2_id, p1_old_id) - self._get_happiness(s2_id, p2_old_id))

                    total_delta = happiness_delta + penalty_delta
                    
                    if total_delta > 0 or (temp > 0 and random.random() < math.exp(total_delta / temp)):
                        current_assignments[s1_id][slot_id] = p2_old_id
                        current_assignments[s2_id][slot_id] = p1_old_id
                        current_score += total_delta
                        if current_score > best_score:
                            best_score = current_score
                            best_assignments = {s: c.copy() for s, c in current_assignments.items()}
                            best_counts = current_counts.copy()

                else:
                    # --- REGULAR MOVE ---
                    p_new = random.choice(self.presentations_by_slot[slot_id] + [None])
                    p_new_id = p_new.id if p_new else None

                    if p1_old_id == p_new_id: continue

                    # Gender Check
                    if p_new_id:
                        p_new_obj = self.presentations[p_new_id]
                        if p_new_obj.gender != 'u' and p_new_obj.gender != self.student_genders[s1_id]:
                            continue

                    # HARD CAPACITY CONSTRAINT - Cannot exceed max_students
                    if p_new_id:
                        if current_counts[p_new_id] >= self.presentation_capacity[p_new_id]:
                            continue  # Course is full, move not allowed

                    # 1. Unassigned Penalty
                    if p_new_id is None: penalty_delta -= 50000
                    if p1_old_id is None: penalty_delta += 50000

                    # 2. Load Balancing Penalty (encourage even distribution)
                    if p_new_id:
                        # Tiny penalty for every student added (encourages spread)
                        penalty_delta -= 50

                    if p1_old_id:
                        # Reward for reducing load
                        penalty_delta += 50

                    # 3. Column/Title Penalty
                    other_items = [(self.presentations[p].column, self.presentations[p].title) 
                                   for sl, p in current_assignments[s1_id].items() if sl != slot_id and p]
                    other_cols = [x[0] for x in other_items]
                    other_titles = [x[1] for x in other_items]
                    
                    if p_new_id:
                        if self.presentations[p_new_id].column in other_cols: penalty_delta -= 5000
                        if self.presentations[p_new_id].title in other_titles: penalty_delta -= 5000
                    
                    if p1_old_id:
                        if self.presentations[p1_old_id].column in other_cols: penalty_delta += 5000
                        if self.presentations[p1_old_id].title in other_titles: penalty_delta += 5000

                    happiness_delta = self._get_happiness(s1_id, p_new_id) - self._get_happiness(s1_id, p1_old_id)
                    total_delta = happiness_delta + penalty_delta

                    if total_delta > 0 or (temp > 0 and random.random() < math.exp(total_delta / temp)):
                        # Apply Move
                        current_assignments[s1_id][slot_id] = p_new_id
                        current_score += total_delta
                        if p1_old_id: current_counts[p1_old_id] -= 1
                        if p_new_id: current_counts[p_new_id] += 1
                        
                        if current_score > best_score:
                            best_score = current_score
                            best_assignments = {s: c.copy() for s, c in current_assignments.items()}
                            best_counts = current_counts.copy()

                # Cool down
                temp *= COOLING_RATE
                if temp < 0.001: break

            yield f"Optimization finished. Best Score: {best_score}"

            # --- 4. Final Polish ---
            # Recount before each step to ensure counts stay in sync with assignments
            best_counts = self._recount_assignments(best_assignments)
            best_assignments, best_counts = yield from self._fill_missing_slots(best_assignments, best_counts)

            best_counts = self._recount_assignments(best_assignments)
            best_assignments, best_counts = yield from self._resolve_overcapacity(best_assignments, best_counts)

            best_counts = self._recount_assignments(best_assignments)
            best_assignments, best_counts = yield from self._balance_column_loads(best_assignments, best_counts)

            best_counts = self._recount_assignments(best_assignments)
            best_assignments, best_counts = yield from self._dissolve_underpopulated_courses(best_assignments, best_counts)

            best_counts = self._recount_assignments(best_assignments)
            best_assignments, best_counts = yield from self._attempt_reassignment_swaps(best_assignments, best_counts)

            # --- 5. Final Validation (recount from actual assignments) ---
            yield "Validating final assignments..."

            # Recount from actual assignments to ensure accuracy
            actual_counts = Counter()
            for student_id, assigned_slots in best_assignments.items():
                for slot, presentation_id in assigned_slots.items():
                    if presentation_id is not None:
                        actual_counts[presentation_id] += 1

            final_violations = []
            for pid in self.presentations:
                actual = actual_counts[pid]
                cap = self.presentation_capacity[pid]
                if actual > cap:
                    final_violations.append((self.presentations[pid].title, self.presentations[pid].slot, actual, cap))

            if final_violations:
                yield f"ERROR: {len(final_violations)} courses exceed capacity limits!"
                for title, slot, count, cap in final_violations:
                    yield f"  - '{title}' (slot {slot}): {count}/{cap} (+{count - cap} over)"
                yield "Will now force-fix these violations..."

                # Force-fix violations by moving excess students
                best_assignments, actual_counts = yield from self._force_fix_overcapacity(best_assignments, actual_counts)

                # Re-validate after force-fix
                actual_counts = self._recount_assignments(best_assignments)
                still_violated = [
                    (pid, actual_counts[pid], self.presentation_capacity[pid])
                    for pid in self.presentations
                    if actual_counts[pid] > self.presentation_capacity[pid]
                ]
                if still_violated:
                    yield "CRITICAL ERROR: Could not fix all capacity violations!"
                    for pid, count, cap in still_violated:
                        yield f"  - '{self.presentations[pid].title}': {count}/{cap}"
                    yield "ABORTING - will not save invalid assignments."
                    return
            else:
                yield "✓ All capacity constraints satisfied."

            # ABSOLUTE FINAL CHECK before saving
            yield "Performing absolute final capacity check..."
            final_counts = self._recount_assignments(best_assignments)
            abort_save = False

            # Show ALL course counts for debugging
            yield "--- DETAILED COURSE COUNTS ---"
            for pid in sorted(self.presentations.keys()):
                p = self.presentations[pid]
                count = final_counts[pid]
                cap = self.presentation_capacity[pid]
                status = "OK" if count <= cap else f"OVER BY {count - cap}!"
                yield f"  ID {pid}: '{p.title}' (slot {p.slot}) = {count}/{cap} [{status}]"
                if count > cap:
                    abort_save = True
            yield "--- END DETAILED COUNTS ---"

            if abort_save:
                yield "ABORTING SAVE - capacity violations detected!"
                return

            yield "✓ Final check passed - all capacities respected."

            for msg in self._generate_report(best_assignments): yield msg
            for msg in self._save_assignments(best_assignments): yield msg

            yield "--- DONE ---"

        except Exception as e:
            yield f"--- FATAL ERROR ---"
            yield f"An error occurred: {e}"
            import traceback
            yield traceback.format_exc() 
            db.session.rollback()


def run_pt_selection_generator():
    """Main function to run the PT course selection"""
    engine = PTSelectionEngine()
    return engine.run_optimization_generator()