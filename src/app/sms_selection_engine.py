import random
import math
from sqlalchemy.sql import text
from .models import SMSAssignment

WISH_HAPPINESS = {1: 100, 2: 70, 3: 50, 4: 30, 5: 15, 6: 5}
NO_WISH_HAPPINESS = -50
UNASSIGNED_PENALTY = -50000

START_TEMP = 1500.0
COOLING_RATE = 0.99997
TOTAL_ITERS = 150_000


def _load_data(db_session):
    students = [
        {"student_id": r[0], "grade": r[1], "grade_selector": r[2]}
        for r in db_session.execute(
            text("SELECT Student_id, grade, grade_selector FROM students_sms")
        ).fetchall()
    ]

    courses_dict = {
        r[0]: {"min_grade": r[1], "max_grade": r[2], "capacity": r[3]}
        for r in db_session.execute(
            text("SELECT course_id, course_minimum_grade, course_maximum_grade, course_maximum_people FROM courses")
        ).fetchall()
    }

    wish_map = {}
    for r in db_session.execute(
        text("SELECT Student_id, Course_id, weight FROM student_course")
    ).fetchall():
        wish_map.setdefault(r[0], {})[r[1]] = r[2]

    return students, courses_dict, wish_map


def _eligible_courses(grade, courses_dict):
    return [
        cid for cid, c in courses_dict.items()
        if c["min_grade"] <= grade <= c["max_grade"]
    ]


def _happiness(student_id, course_id, wish_map):
    wishes = wish_map.get(student_id, {})
    weight = wishes.get(course_id)
    if weight is not None:
        return WISH_HAPPINESS.get(weight, 5)
    return NO_WISH_HAPPINESS


def _greedy_init(students, courses_dict, wish_map):
    assignment = {s["student_id"]: {1: None, 2: None} for s in students}
    course_load = {cid: {1: 0, 2: 0} for cid in courses_dict}

    shuffled = students[:]
    random.shuffle(shuffled)

    for student in shuffled:
        sid = student["student_id"]
        grade = student["grade"]
        eligible = set(_eligible_courses(grade, courses_dict))
        wishes = sorted(wish_map.get(sid, {}).items(), key=lambda x: x[1])
        wished_ids = [cid for cid, _ in wishes if cid in eligible]

        for session in (1, 2):
            assigned = False
            for cid in wished_ids:
                if course_load[cid][session] < courses_dict[cid]["capacity"]:
                    assignment[sid][session] = cid
                    course_load[cid][session] += 1
                    assigned = True
                    break
            # leave None if no wish fits; _fill_unassigned handles it later

    return assignment, course_load


def _total_happiness(assignment, wish_map):
    total = 0
    for sid, sessions in assignment.items():
        for session, cid in sessions.items():
            if cid is None:
                total += UNASSIGNED_PENALTY
            else:
                total += _happiness(sid, cid, wish_map)
    return total


def _simulated_annealing(assignment, course_load, students, courses_dict, wish_map):
    temp = START_TEMP
    student_ids = [s["student_id"] for s in students]
    student_grade = {s["student_id"]: s["grade"] for s in students}
    course_ids = list(courses_dict.keys())

    for _ in range(TOTAL_ITERS):
        if random.random() < 0.70:
            # MOVE: reassign one student's session slot
            sid = random.choice(student_ids)
            session = random.choice((1, 2))
            grade = student_grade[sid]
            eligible = _eligible_courses(grade, courses_dict)
            if not eligible:
                temp *= COOLING_RATE
                continue

            new_cid = random.choice(eligible)
            old_cid = assignment[sid][session]

            if new_cid == old_cid:
                temp *= COOLING_RATE
                continue

            # Check capacity (account for freeing old slot)
            new_load = course_load[new_cid][session]
            if new_cid != old_cid and new_load >= courses_dict[new_cid]["capacity"]:
                temp *= COOLING_RATE
                continue

            old_h = _happiness(sid, old_cid, wish_map) if old_cid is not None else UNASSIGNED_PENALTY
            new_h = _happiness(sid, new_cid, wish_map)
            delta = new_h - old_h

            if delta > 0 or random.random() < math.exp(delta / temp):
                if old_cid is not None:
                    course_load[old_cid][session] -= 1
                assignment[sid][session] = new_cid
                course_load[new_cid][session] += 1
        else:
            # SWAP: exchange two students' courses in a random session
            if len(student_ids) < 2:
                temp *= COOLING_RATE
                continue
            sid_a, sid_b = random.sample(student_ids, 2)
            session = random.choice((1, 2))

            cid_a = assignment[sid_a][session]
            cid_b = assignment[sid_b][session]

            if cid_a == cid_b:
                temp *= COOLING_RATE
                continue

            grade_a = student_grade[sid_a]
            grade_b = student_grade[sid_b]

            # Check grade eligibility for the swap
            if cid_b is not None:
                c = courses_dict[cid_b]
                if not (c["min_grade"] <= grade_a <= c["max_grade"]):
                    temp *= COOLING_RATE
                    continue
            if cid_a is not None:
                c = courses_dict[cid_a]
                if not (c["min_grade"] <= grade_b <= c["max_grade"]):
                    temp *= COOLING_RATE
                    continue

            old_h = (
                (_happiness(sid_a, cid_a, wish_map) if cid_a is not None else UNASSIGNED_PENALTY) +
                (_happiness(sid_b, cid_b, wish_map) if cid_b is not None else UNASSIGNED_PENALTY)
            )
            new_h = (
                (_happiness(sid_a, cid_b, wish_map) if cid_b is not None else UNASSIGNED_PENALTY) +
                (_happiness(sid_b, cid_a, wish_map) if cid_a is not None else UNASSIGNED_PENALTY)
            )
            delta = new_h - old_h

            if delta > 0 or random.random() < math.exp(delta / temp):
                assignment[sid_a][session] = cid_b
                assignment[sid_b][session] = cid_a
                # Swap is capacity-neutral; no load update needed

        temp *= COOLING_RATE

    return assignment, course_load


def _fill_unassigned(assignment, course_load, students, courses_dict, wish_map):
    for student in students:
        sid = student["student_id"]
        grade = student["grade"]
        eligible = _eligible_courses(grade, courses_dict)

        for session in (1, 2):
            if assignment[sid][session] is not None:
                continue
            # Sort eligible courses by current load ascending
            candidates = sorted(
                eligible,
                key=lambda cid: course_load[cid][session]
            )
            for cid in candidates:
                if course_load[cid][session] < courses_dict[cid]["capacity"]:
                    assignment[sid][session] = cid
                    course_load[cid][session] += 1
                    break

    return assignment, course_load


def _resolve_overcapacity(assignment, course_load, students, courses_dict, wish_map):
    student_grade = {s["student_id"]: s["grade"] for s in students}

    for cid in courses_dict:
        for session in (1, 2):
            capacity = courses_dict[cid]["capacity"]
            while course_load[cid][session] > capacity:
                # Find students assigned to this overcrowded slot, sorted by happiness ascending (move worst first)
                victims = [
                    sid for sid, sessions in assignment.items()
                    if sessions[session] == cid
                ]
                if not victims:
                    break
                victims.sort(key=lambda sid: _happiness(sid, cid, wish_map))
                moved = False
                for victim in victims:
                    grade = student_grade[victim]
                    eligible = _eligible_courses(grade, courses_dict)
                    candidates = sorted(
                        [c for c in eligible if c != cid],
                        key=lambda c: course_load[c][session]
                    )
                    for alt in candidates:
                        if course_load[alt][session] < courses_dict[alt]["capacity"]:
                            assignment[victim][session] = alt
                            course_load[cid][session] -= 1
                            course_load[alt][session] += 1
                            moved = True
                            break
                    if moved:
                        break
                if not moved:
                    print(f"Warning: could not resolve overcapacity for course {cid} session {session}")
                    break

    return assignment, course_load


def _save_to_db(assignment, db_session):
    db_session.execute(text("DELETE FROM sms_assignment"))

    rows = []
    for sid, sessions in assignment.items():
        for session, cid in sessions.items():
            if cid is not None:
                rows.append(SMSAssignment(student_id=sid, course_id=cid, session=session))

    db_session.bulk_save_objects(rows)
    db_session.commit()


def run_engine(db):
    students, courses_dict, wish_map = _load_data(db.session)

    if not students:
        raise RuntimeError("No students found in database.")
    if not courses_dict:
        raise RuntimeError("No courses found in database.")

    assignment, course_load = _greedy_init(students, courses_dict, wish_map)
    assignment, course_load = _simulated_annealing(assignment, course_load, students, courses_dict, wish_map)
    assignment, course_load = _fill_unassigned(assignment, course_load, students, courses_dict, wish_map)
    assignment, course_load = _resolve_overcapacity(assignment, course_load, students, courses_dict, wish_map)
    _save_to_db(assignment, db.session)

    assigned_s1 = sum(1 for s in assignment.values() if s[1] is not None)
    assigned_s2 = sum(1 for s in assignment.values() if s[2] is not None)
    unassigned = sum(
        (1 if s[1] is None else 0) + (1 if s[2] is None else 0)
        for s in assignment.values()
    )
    total_happiness = _total_happiness(assignment, wish_map)

    return {
        "total_students": len(students),
        "assigned_session1": assigned_s1,
        "assigned_session2": assigned_s2,
        "unassigned": unassigned,
        "total_happiness": total_happiness,
    }
