import copy
import random
import math
from sqlalchemy.sql import text
from .models import SMSAssignment

WISH_HAPPINESS = {1: 100, 2: 70, 3: 50, 4: 30, 5: 15, 6: 5}
NO_WISH_HAPPINESS = -50
UNASSIGNED_PENALTY = -50000

START_TEMP = 1500.02
COOLING_RATE = 0.99997
TOTAL_ITERS = 150_000

# Number of full restarts. Each restart does a fresh greedy init + annealing run
# from a different random shuffle; we keep whichever run scores highest. More
# restarts = more tries = better odds of a good solution (at the cost of runtime).
RESTARTS = 10


def _load_data(db_session):
    students = [
        {"student_id": r[0], "grade": r[1], "grade_selector": r[2]}
        for r in db_session.execute(
            text("SELECT Student_id, grade, grade_selector FROM students_sms")
        ).fetchall()
    ]

    courses_dict = {}
    for r in db_session.execute(
        text("SELECT course_id, course_minimum_grade, course_maximum_grade, course_maximum_people, course_availibility_slot_1, course_availibility_slot_2 FROM courses")
    ).fetchall():
        available = set()
        if r[4]:
            available.add(1)
        if r[5]:
            available.add(2)
        if not available:
            # Course runs in neither slot — skip entirely so it can never be assigned.
            continue
        courses_dict[r[0]] = {
            "min_grade": r[1],
            "max_grade": r[2],
            "capacity": r[3],
            "available_sessions": available,
        }

    wish_map = {}
    # locked_map: student_id -> list of course_ids that MUST be assigned.
    # Signalled by weight == 0 in student_course (a value the frontend never
    # writes; only a raw SQL edit produces it). These bypass the optimiser and
    # are pinned into a slot before everything else, then never moved.
    locked_map = {}
    for r in db_session.execute(
        text("SELECT Student_id, Course_id, weight FROM student_course")
    ).fetchall():
        sid, cid, weight = r[0], r[1], r[2]
        if weight == 0:
            locked_map.setdefault(sid, []).append(cid)
        else:
            wish_map.setdefault(sid, {})[cid] = weight

    return students, courses_dict, wish_map, locked_map


def _eligible_courses(grade, courses_dict):
    return [
        cid for cid, c in courses_dict.items()
        if c["min_grade"] <= grade <= c["max_grade"]
    ]


def _course_available(cid, session, courses_dict):
    return session in courses_dict[cid]["available_sessions"]


def _happiness(student_id, course_id, wish_map):
    wishes = wish_map.get(student_id, {})
    weight = wishes.get(course_id)
    if weight is not None:
        return WISH_HAPPINESS.get(weight, 5)
    return NO_WISH_HAPPINESS


def _apply_locks(students, courses_dict, locked_map):
    """Pin guaranteed (weight==0) courses into slots before optimisation.

    Returns (assignment, course_load, locked) where `locked` is a set of
    (student_id, session) pairs that no later phase may modify. Two guarantees
    for the same student are spread across the two slots when possible.
    """
    assignment = {s["student_id"]: {1: None, 2: None} for s in students}
    course_load = {cid: {1: 0, 2: 0} for cid in courses_dict}
    locked = set()
    grade_of = {s["student_id"]: s["grade"] for s in students}

    for sid, course_ids in locked_map.items():
        if sid not in assignment:
            print(f"Warning: guaranteed course(s) for unknown student {sid}; skipping")
            continue
        grade = grade_of[sid]
        for cid in course_ids:
            if cid not in courses_dict:
                # Course doesn't run in any slot (or doesn't exist) — can't guarantee it.
                print(f"Warning: cannot guarantee course {cid} for student {sid} (course not runnable)")
                continue
            c = courses_dict[cid]
            if not (c["min_grade"] <= grade <= c["max_grade"]):
                print(f"Warning: student {sid} is grade-ineligible for guaranteed course {cid}; skipping")
                continue
            # Prefer a slot that is still free for this student, among the slots
            # the course actually runs in.
            placed = False
            for session in sorted(c["available_sessions"]):
                if (sid, session) in locked:
                    continue
                if assignment[sid][session] is not None:
                    continue
                assignment[sid][session] = cid
                course_load[cid][session] += 1
                locked.add((sid, session))
                placed = True
                break
            if not placed:
                print(
                    f"Warning: could not place guaranteed course {cid} for student {sid} "
                    f"(no free slot among {sorted(c['available_sessions'])}); skipping"
                )

    return assignment, course_load, locked


def _greedy_init(assignment, course_load, locked, students, courses_dict, wish_map):
    shuffled = students[:]
    random.shuffle(shuffled)

    for student in shuffled:
        sid = student["student_id"]
        grade = student["grade"]
        eligible = set(_eligible_courses(grade, courses_dict))
        wishes = sorted(wish_map.get(sid, {}).items(), key=lambda x: x[1])
        wished_ids = [cid for cid, _ in wishes if cid in eligible]

        for session in (1, 2):
            if (sid, session) in locked:
                continue  # guaranteed slot — leave it alone
            other_session = 2 if session == 1 else 1
            already_assigned = assignment[sid][other_session]
            for cid in wished_ids:
                if cid == already_assigned:
                    continue
                if not _course_available(cid, session, courses_dict):
                    continue
                if course_load[cid][session] < courses_dict[cid]["capacity"]:
                    assignment[sid][session] = cid
                    course_load[cid][session] += 1
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


def _simulated_annealing(assignment, course_load, locked, students, courses_dict, wish_map):
    temp = START_TEMP
    student_ids = [s["student_id"] for s in students]
    student_grade = {s["student_id"]: s["grade"] for s in students}
    course_ids = list(courses_dict.keys())

    for _ in range(TOTAL_ITERS):
        if random.random() < 0.70:
            # MOVE: reassign one student's session slot
            sid = random.choice(student_ids)
            session = random.choice((1, 2))
            if (sid, session) in locked:
                temp *= COOLING_RATE
                continue
            grade = student_grade[sid]
            eligible = _eligible_courses(grade, courses_dict)
            if not eligible:
                temp *= COOLING_RATE
                continue

            new_cid = random.choice(eligible)
            old_cid = assignment[sid][session]
            other_session = 2 if session == 1 else 1
            other_cid = assignment[sid][other_session]

            if new_cid == old_cid or new_cid == other_cid:
                temp *= COOLING_RATE
                continue

            if not _course_available(new_cid, session, courses_dict):
                temp *= COOLING_RATE
                continue

            # Check capacity (account for freeing old slot)
            new_load = course_load[new_cid][session]
            if new_load >= courses_dict[new_cid]["capacity"]:
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

            # Never swap a guaranteed slot.
            if (sid_a, session) in locked or (sid_b, session) in locked:
                temp *= COOLING_RATE
                continue

            cid_a = assignment[sid_a][session]
            cid_b = assignment[sid_b][session]

            if cid_a == cid_b:
                temp *= COOLING_RATE
                continue

            grade_a = student_grade[sid_a]
            grade_b = student_grade[sid_b]
            other_session = 2 if session == 1 else 1

            # Reject swap if it would give a student the same course in both sessions
            if cid_b is not None and cid_b == assignment[sid_a][other_session]:
                temp *= COOLING_RATE
                continue
            if cid_a is not None and cid_a == assignment[sid_b][other_session]:
                temp *= COOLING_RATE
                continue

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

            # Both courses must actually run in this session (they already did
            # for their current holder, but be defensive in case data changed).
            if cid_a is not None and not _course_available(cid_a, session, courses_dict):
                temp *= COOLING_RATE
                continue
            if cid_b is not None and not _course_available(cid_b, session, courses_dict):
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


def _fill_unassigned(assignment, course_load, locked, students, courses_dict, wish_map):
    for student in students:
        sid = student["student_id"]
        grade = student["grade"]
        eligible = _eligible_courses(grade, courses_dict)

        for session in (1, 2):
            # Locked slots are always filled (never None), so this is belt-and-braces.
            if (sid, session) in locked:
                continue
            if assignment[sid][session] is not None:
                continue
            other_session = 2 if session == 1 else 1
            already_assigned = assignment[sid][other_session]
            # Sort eligible courses by current load ascending, excluding course already in other session
            candidates = sorted(
                [cid for cid in eligible if cid != already_assigned and _course_available(cid, session, courses_dict)],
                key=lambda cid: course_load[cid][session]
            )
            for cid in candidates:
                if course_load[cid][session] < courses_dict[cid]["capacity"]:
                    assignment[sid][session] = cid
                    course_load[cid][session] += 1
                    break

    return assignment, course_load


def _resolve_overcapacity(assignment, course_load, locked, students, courses_dict, wish_map):
    student_grade = {s["student_id"]: s["grade"] for s in students}

    for cid in courses_dict:
        for session in (1, 2):
            capacity = courses_dict[cid]["capacity"]
            while course_load[cid][session] > capacity:
                # Find students assigned to this overcrowded slot, sorted by happiness ascending (move worst first).
                # Guaranteed (locked) slots are never evicted, even if that leaves the course over capacity.
                victims = [
                    sid for sid, sessions in assignment.items()
                    if sessions[session] == cid and (sid, session) not in locked
                ]
                if not victims:
                    break
                victims.sort(key=lambda sid: _happiness(sid, cid, wish_map))
                moved = False
                for victim in victims:
                    grade = student_grade[victim]
                    eligible = _eligible_courses(grade, courses_dict)
                    other_session = 2 if session == 1 else 1
                    other_cid = assignment[victim][other_session]
                    candidates = sorted(
                        [c for c in eligible if c != cid and c != other_cid and _course_available(c, session, courses_dict)],
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
                    print(
                        f"Warning: could not resolve overcapacity for course {cid} session {session} "
                        f"(load {course_load[cid][session]} > capacity {capacity}); "
                        f"remaining occupants may be guaranteed/locked"
                    )
                    break

    return assignment, course_load


def _save_to_db(assignment, db_session):
    db_session.execute(text("DELETE FROM sms_assignment"))
    db_session.expire_all()

    rows = []
    for sid, sessions in assignment.items():
        for session, cid in sessions.items():
            if cid is not None:
                rows.append(SMSAssignment(student_id=sid, course_id=cid, session=session))

    db_session.bulk_save_objects(rows)
    db_session.commit()


def run_engine(db):
    students, courses_dict, wish_map, locked_map = _load_data(db.session)

    if not students:
        raise RuntimeError("No students found in database.")
    if not courses_dict:
        raise RuntimeError("No courses found in database.")

    # Locks are deterministic, so compute them once up front and reuse for every restart.
    base_assignment, base_course_load, locked = _apply_locks(students, courses_dict, locked_map)

    # Run the optimiser several times from fresh random starts and keep the best.
    best_assignment = None
    best_happiness = None
    for attempt in range(1, RESTARTS + 1):
        assignment = copy.deepcopy(base_assignment)
        course_load = copy.deepcopy(base_course_load)

        assignment, course_load = _greedy_init(assignment, course_load, locked, students, courses_dict, wish_map)
        assignment, course_load = _simulated_annealing(assignment, course_load, locked, students, courses_dict, wish_map)
        assignment, course_load = _fill_unassigned(assignment, course_load, locked, students, courses_dict, wish_map)
        assignment, course_load = _resolve_overcapacity(assignment, course_load, locked, students, courses_dict, wish_map)

        happiness = _total_happiness(assignment, wish_map)
        print(f"Engine attempt {attempt}/{RESTARTS}: happiness score = {happiness}")

        if best_happiness is None or happiness > best_happiness:
            best_happiness = happiness
            best_assignment = assignment

    assignment = best_assignment
    print(f"Engine finished. Best happiness score = {best_happiness} (over {RESTARTS} attempts)")

    _save_to_db(assignment, db.session)

    total_students = len(students)
    satisfaction_stats = {"1st Choice": 0, "2nd-3rd": 0, "Wished": 0, "Not Wished": 0, "Unassigned": 0}

    for sid, sessions in assignment.items():
        for session, cid in sessions.items():
            if cid is None:
                satisfaction_stats["Unassigned"] += 1
                continue
            if (sid, session) in locked:
                # Guaranteed slot — treat as a first-choice grant in the stats.
                satisfaction_stats["1st Choice"] += 1
                continue
            ranking = wish_map.get(sid, {}).get(cid)
            if ranking == 1:
                satisfaction_stats["1st Choice"] += 1
            elif ranking in (2, 3):
                satisfaction_stats["2nd-3rd"] += 1
            elif ranking is not None:
                satisfaction_stats["Wished"] += 1
            else:
                satisfaction_stats["Not Wished"] += 1

    return {
        "total_students": total_students,
        "satisfaction": satisfaction_stats,
        "happiness_score": best_happiness,
        "restarts": RESTARTS,
    }
