import random
import re
from datetime import date, timedelta
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from .academic_catalog import LABS_BY_SEMESTER, SUBJECTS_BY_SEMESTER, academic_year_for_semester, component_name
from .analytics import calculate_success, detect_segment, determine_risk, generate_insight
from .database import SessionLocal
from .models import AcademicEntry, AcademicRecord, AttendanceRecord, CulturalActivityFee, EngagementRecord, Faculty, FeedbackRecord, Intervention, LmsActivity, PlacementRecord, RiskPrediction, SemesterResult, SkillRecord, Student, StudentFee, StudentSegment, SuccessScore


def safe_round(value: float, digits: int = 1) -> float:
    return round(float(value), digits)


def make_student_name(index: int) -> str:
    first_names = [
        "Aarav", "Aditi", "Arjun", "Ananya", "Dev", "Diya", "Ishaan", "Isha",
        "Kabir", "Kavya", "Krish", "Meera", "Neel", "Nisha", "Reyansh", "Riya",
        "Rohan", "Saanvi", "Samir", "Tara", "Vihaan", "Zara", "Advik", "Maya",
    ]
    first_name = first_names[(index - 1) % len(first_names)]
    initial = chr(ord("A") + ((index - 1) * 7 % 26))
    return f"{first_name} {initial}."


def update_placeholder_student_names() -> None:
    db = SessionLocal()
    try:
        for student in db.query(Student).all():
            if not re.fullmatch(r"(Demo Student [A-D]|Student \d+)", student.name):
                continue
            match = re.fullmatch(r"STU-(\d+)", student.student_id)
            if not match:
                continue
            student.name = make_student_name(int(match.group(1)))
            if student.email and student.email.endswith("@campus.edu"):
                slug = student.name.replace(".", "").lower().replace(" ", ".")
                student.email = f"{slug}@campus.edu"
        db.commit()
    finally:
        db.close()


def balance_seeded_student_groups() -> None:
    db = SessionLocal()
    try:
        current_year = date.today().year
        students = (
            db.query(Student)
            .filter(Student.student_id >= "STU-0001", Student.student_id <= "STU-0240")
            .order_by(Student.student_id)
            .all()
        )
        for index, student in enumerate(students):
            semester = index % 8 + 1
            student.semester = semester
            student.year = (semester + 1) // 2
            student.cohort = str(current_year - student.year + 1)
        db.commit()
    finally:
        db.close()


def seed_database() -> None:
    db = SessionLocal()
    try:
        if db.query(Student).count() > 0:
            return

        departments = ["Computer Science", "Electronics", "Mechanical", "Civil", "Biotechnology", "MBA"]
        scenario_profiles = [
            {"dept": "Computer Science", "year": 3, "semester": 6, "scenario": "academic_high_placement_low"},
            {"dept": "Electronics", "year": 2, "semester": 4, "scenario": "low_attendance_risk"},
            {"dept": "Mechanical", "year": 3, "semester": 6, "scenario": "placement_ready"},
            {"dept": "Computer Science", "year": 4, "semester": 8, "scenario": "excellent"},
        ]

        for idx in range(1, 241):
            semester = ((idx - 1) % 8) + 1
            year = (semester + 1) // 2
            if idx <= 4:
                profile = scenario_profiles[idx - 1]
            else:
                profile = {
                    "dept": departments[(idx * 3) % len(departments)],
                    "year": year,
                    "semester": semester,
                    "scenario": [
                        "academic_high_placement_low",
                        "low_attendance_risk",
                        "placement_ready",
                        "excellent",
                        "moderate",
                        "engaged_low_academic",
                    ][idx % 6],
                }

            name = make_student_name(idx)
            email_slug = name.replace(".", "").lower().replace(" ", ".")
            student = Student(
                student_id=f"STU-{idx:04d}",
                name=name,
                department=profile["dept"],
                year=year,
                semester=semester,
                cohort=str(date.today().year - year + 1),
                email=f"{email_slug}@campus.edu",
                mentor=f"Mentor {((idx % 8) + 1):02d}",
            )
            db.add(student)
            db.flush()

            if profile["scenario"] == "academic_high_placement_low":
                academic = AcademicRecord(student_id=student.id, cgpa=8.7, marks=81, backlogs=1, subject_performance='{"Math": 78, "Programming": 84, "Physics": 73, "DBMS": 88}')
                attendance = AttendanceRecord(student_id=student.id, overall_attendance=88, subject_attendance='{"Math": 83, "Programming": 92, "DBMS": 90}')
                lms = LmsActivity(student_id=student.id, login_frequency=86, assignment_completion=80, quiz_performance=82, learning_activity=88)
                engagement = EngagementRecord(student_id=student.id, events_attended=5, clubs=2, hackathons=1, certifications=2, extracurricular=70)
                placement = PlacementRecord(student_id=student.id, aptitude_score=54, coding_score=62, mock_interview_score=58, resume_score=66, placement_training_attendance=73, placement_status="Needs Support")
                skills = SkillRecord(student_id=student.id, technical=84, communication=55, problem_solving=78, soft_skill=66)
                feedback = FeedbackRecord(student_id=student.id, student_satisfaction=78, faculty_feedback=82, mentor_feedback=74)
            elif profile["scenario"] == "low_attendance_risk":
                academic = AcademicRecord(student_id=student.id, cgpa=4.8, marks=44, backlogs=4, subject_performance='{"Math": 38, "Programming": 52, "Chemistry": 46, "Systems": 55}')
                attendance = AttendanceRecord(student_id=student.id, overall_attendance=52, subject_attendance='{"Math": 39, "Programming": 58, "DBMS": 54}')
                lms = LmsActivity(student_id=student.id, login_frequency=48, assignment_completion=36, quiz_performance=50, learning_activity=40)
                engagement = EngagementRecord(student_id=student.id, events_attended=0, clubs=0, hackathons=0, certifications=0, extracurricular=12)
                placement = PlacementRecord(student_id=student.id, aptitude_score=55, coding_score=48, mock_interview_score=42, resume_score=46, placement_training_attendance=50, placement_status="At Risk")
                skills = SkillRecord(student_id=student.id, technical=52, communication=46, problem_solving=58, soft_skill=35)
                feedback = FeedbackRecord(student_id=student.id, student_satisfaction=45, faculty_feedback=38, mentor_feedback=46)
            elif profile["scenario"] == "placement_ready":
                academic = AcademicRecord(student_id=student.id, cgpa=7.4, marks=74, backlogs=0, subject_performance='{"Math": 72, "Programming": 80, "Data Structures": 85, "DBMS": 78}')
                attendance = AttendanceRecord(student_id=student.id, overall_attendance=84, subject_attendance='{"Math": 79, "Programming": 89, "DBMS": 86}')
                lms = LmsActivity(student_id=student.id, login_frequency=80, assignment_completion=88, quiz_performance=84, learning_activity=82)
                engagement = EngagementRecord(student_id=student.id, events_attended=7, clubs=3, hackathons=2, certifications=4, extracurricular=82)
                placement = PlacementRecord(student_id=student.id, aptitude_score=86, coding_score=88, mock_interview_score=81, resume_score=84, placement_training_attendance=90, placement_status="Ready")
                skills = SkillRecord(student_id=student.id, technical=90, communication=78, problem_solving=88, soft_skill=81)
                feedback = FeedbackRecord(student_id=student.id, student_satisfaction=88, faculty_feedback=82, mentor_feedback=84)
            elif profile["scenario"] == "excellent":
                academic = AcademicRecord(student_id=student.id, cgpa=9.2, marks=91, backlogs=0, subject_performance='{"Math": 94, "Programming": 96, "Algorithms": 92, "DBMS": 95}')
                attendance = AttendanceRecord(student_id=student.id, overall_attendance=96, subject_attendance='{"Math": 94, "Programming": 98, "DBMS": 96}')
                lms = LmsActivity(student_id=student.id, login_frequency=94, assignment_completion=96, quiz_performance=92, learning_activity=95)
                engagement = EngagementRecord(student_id=student.id, events_attended=10, clubs=4, hackathons=3, certifications=6, extracurricular=90)
                placement = PlacementRecord(student_id=student.id, aptitude_score=92, coding_score=94, mock_interview_score=89, resume_score=93, placement_training_attendance=95, placement_status="Excellent")
                skills = SkillRecord(student_id=student.id, technical=96, communication=85, problem_solving=94, soft_skill=88)
                feedback = FeedbackRecord(student_id=student.id, student_satisfaction=94, faculty_feedback=96, mentor_feedback=92)
            elif profile["scenario"] == "moderate":
                academic = AcademicRecord(student_id=student.id, cgpa=7.1, marks=70, backlogs=1, subject_performance='{"Math": 68, "Programming": 74, "DBMS": 71, "Economics": 72}')
                attendance = AttendanceRecord(student_id=student.id, overall_attendance=76, subject_attendance='{"Math": 72, "Programming": 78, "DBMS": 74}')
                lms = LmsActivity(student_id=student.id, login_frequency=70, assignment_completion=72, quiz_performance=69, learning_activity=75)
                engagement = EngagementRecord(student_id=student.id, events_attended=3, clubs=1, hackathons=0, certifications=1, extracurricular=58)
                placement = PlacementRecord(student_id=student.id, aptitude_score=72, coding_score=71, mock_interview_score=66, resume_score=71, placement_training_attendance=78, placement_status="In Progress")
                skills = SkillRecord(student_id=student.id, technical=75, communication=74, problem_solving=70, soft_skill=68)
                feedback = FeedbackRecord(student_id=student.id, student_satisfaction=72, faculty_feedback=73, mentor_feedback=70)
            else:
                academic = AcademicRecord(student_id=student.id, cgpa=6.9, marks=68, backlogs=2, subject_performance='{"Math": 62, "Programming": 73, "DBMS": 69, "Networking": 64}')
                attendance = AttendanceRecord(student_id=student.id, overall_attendance=81, subject_attendance='{"Math": 78, "Programming": 84, "DBMS": 82}')
                lms = LmsActivity(student_id=student.id, login_frequency=91, assignment_completion=74, quiz_performance=62, learning_activity=88)
                engagement = EngagementRecord(student_id=student.id, events_attended=6, clubs=1, hackathons=2, certifications=1, extracurricular=72)
                placement = PlacementRecord(student_id=student.id, aptitude_score=63, coding_score=69, mock_interview_score=60, resume_score=65, placement_training_attendance=80, placement_status="Needs Support")
                skills = SkillRecord(student_id=student.id, technical=82, communication=54, problem_solving=72, soft_skill=68)
                feedback = FeedbackRecord(student_id=student.id, student_satisfaction=66, faculty_feedback=62, mentor_feedback=69)

            db.add_all([academic, attendance, lms, engagement, placement, skills, feedback])
            db.flush()

            profile = calculate_success(student, db)
            risk_profile = determine_risk(student)
            segment = detect_segment(student)
            score_record = SuccessScore(
                student_id=student.id,
                score=profile["score"],
                academic=profile["academic"],
                attendance=profile["attendance"],
                lms=profile["lms"],
                assessment=profile["assessment"],
                placement=profile["placement"],
                skills=profile["skills"],
                engagement=profile["engagement"],
                factors=profile["factors"],
            )
            risk_record = RiskPrediction(
                student_id=student.id,
                academic_risk_level=risk_profile["academic_risk_level"],
                placement_risk_level=risk_profile["placement_risk_level"],
                academic_risk_probability=risk_profile["academic_risk_probability"],
                placement_risk_probability=risk_profile["placement_risk_probability"],
                overall_priority=risk_profile["overall_priority"],
                reasons='; '.join(risk_profile["reasons"]),
            )
            segment_record = StudentSegment(
                student_id=student.id,
                segment_name=segment["segment_name"],
                description=segment["description"],
                recommended_intervention=segment["recommended_intervention"],
            )
            db.add_all([score_record, risk_record, segment_record])

            intervention = Intervention(
                student_id=student.id,
                title=f"{segment['segment_name']} Recovery Plan",
                mentor=student.mentor or "Faculty Mentor",
                priority=risk_profile["overall_priority"],
                due_date=date.today(),
                notes=segment["recommended_intervention"],
                status="Not Started",
                reason='; '.join(risk_profile["reasons"]),
                action=segment["recommended_intervention"],
            )
            db.add(intervention)

        db.commit()
    finally:
        db.close()


def seed_faculty() -> None:
    db = SessionLocal()
    try:
        if db.query(Faculty).count():
            return
        faculty_members = [
            ("FAC-001", "Aarav Sharma", "Computer Science", "Senior Lecturer", "aarav.sharma@campus.edu"),
            ("FAC-002", "Priya Nair", "Electronics", "Assistant Professor", "priya.nair@campus.edu"),
            ("FAC-003", "Kabir Rao", "Mechanical", "Assistant Professor", "kabir.rao@campus.edu"),
            ("FAC-004", "Meera Iyer", "Civil", "Senior Lecturer", "meera.iyer@campus.edu"),
            ("FAC-005", "Rohan Das", "Biotechnology", "Assistant Professor", "rohan.das@campus.edu"),
            ("FAC-006", "Ananya Patel", "MBA", "Lecturer", "ananya.patel@campus.edu"),
            ("FAC-007", "Dev Menon", "Computer Science", "Lecturer", "dev.menon@campus.edu"),
            ("FAC-008", "Sara Khan", "Electronics", "Lecturer", "sara.khan@campus.edu"),
        ]
        db.add_all([
            Faculty(
                faculty_id=faculty_id,
                name=name,
                department=department,
                designation=designation,
                email=email,
                mentor_code=f"Mentor {index:02d}",
            )
            for index, (faculty_id, name, department, designation, email) in enumerate(faculty_members, start=1)
        ])
        db.commit()
    finally:
        db.close()


def seed_academic_history() -> None:
    db = SessionLocal()
    try:
        demo_student_ids = [f"STU-{index:04d}" for index in range(1, 241)]
        students = db.query(Student).filter(Student.student_id.in_(demo_student_ids)).all()
        existing_entries = {
            (student_id, subject, entry_date)
            for student_id, subject, entry_date in db.query(
                AcademicEntry.student_id,
                AcademicEntry.subject,
                AcademicEntry.entry_date,
            ).all()
        }
        subjects = ["M1", "M2", "M3", "M4"]
        subject_offsets = [-4.0, 1.0, -1.5, 4.0]
        today = date.today()
        entries = []
        for student in students:
            academic = student.academic_record
            attendance = student.attendance_record
            base_marks = min(96.0, max(32.0, (academic.cgpa * 10.0 + academic.marks) / 2.0)) if academic else 65.0
            base_attendance = attendance.overall_attendance if attendance else 75.0
            declining = student.student_id == "STU-0002" or (academic and academic.backlogs >= 3)
            for week in range(207, -1, -1):
                week_start = today - timedelta(days=today.weekday() + 7 + week * 7)
                for subject_index, subject in enumerate(subjects):
                    session_date = week_start - timedelta(days=week_start.weekday()) + timedelta(days=subject_index)
                    entry_key = (student.id, subject, session_date)
                    if entry_key in existing_entries:
                        continue
                    marks_growth = (103 - week) * (-0.08 if declining else 0.035)
                    attendance_growth = (103 - week) * (-0.055 if declining else 0.015)
                    entries.append(
                        AcademicEntry(
                            student_id=student.id,
                            subject=subject,
                            entry_date=session_date,
                            attendance="Present" if ((week * 13 + student.id * 7 + subject_index * 19) % 100) < min(100, max(0, base_attendance + attendance_growth)) else "Absent",
                            marks=round(min(100, max(0, base_marks + subject_offsets[subject_index] + marks_growth)), 1),
                            max_marks=100.0,
                        )
                    )
                    existing_entries.add(entry_key)
        db.bulk_save_objects(entries)
        db.commit()
    finally:
        db.close()


def seed_semester_results() -> None:
    db = SessionLocal()
    try:
        today = date.today()
        results = []
        demo_student_ids = [f"STU-{index:04d}" for index in range(1, 241)]
        existing_results = (
            db.query(SemesterResult)
            .join(Student, SemesterResult.student_id == Student.id)
            .filter(Student.student_id.in_(demo_student_ids))
            .all()
        )
        result_groups = {}
        for result in existing_results:
            if result.component_type not in {"subject", "lab"} or not 1 <= result.semester <= 8:
                continue
            components = SUBJECTS_BY_SEMESTER[result.semester] if result.component_type == "subject" else LABS_BY_SEMESTER[result.semester]
            if result.component_name.startswith("Subject ") or result.component_name.startswith("Lab "):
                try:
                    component_index = int(result.component_name.split(" ", 1)[1])
                    result.component_name = component_name(result.semester, result.component_type, component_index)
                except (ValueError, IndexError):
                    continue
            if result.component_name in components:
                key = (
                    result.student_id,
                    academic_year_for_semester(result.semester, today.year),
                    result.semester,
                    result.component_type,
                    result.component_name,
                )
                result_groups.setdefault(key, []).append(result)

        existing_keys = set()
        for key, matching_results in result_groups.items():
            keeper = next((result for result in matching_results if result.academic_year == key[1]), matching_results[0])
            for duplicate in matching_results:
                if duplicate is not keeper:
                    db.delete(duplicate)
            keeper.academic_year = key[1]
            keeper.component_name = key[4]
            existing_keys.add(key)
        db.flush()

        for student in db.query(Student).filter(Student.student_id.in_(demo_student_ids)).all():
            base_marks = student.academic_record.marks if student.academic_record else 65.0
            for semester in range(1, 9):
                academic_year = academic_year_for_semester(semester, today.year)
                for component_type, component_list in (("subject", SUBJECTS_BY_SEMESTER[semester]), ("lab", LABS_BY_SEMESTER[semester])):
                    for component_index, name in enumerate(component_list, start=1):
                        key = (student.id, academic_year, semester, component_type, name)
                        if key in existing_keys:
                            continue
                        variation = ((student.id * 7 + semester * 11 + component_index * 13) % 25) - 12
                        mid1 = round(min(100, max(0, base_marks + variation - 3)), 1)
                        mid2 = round(min(100, max(0, base_marks + variation + 2)), 1)
                        if component_type == "subject":
                            semester_marks = round(min(100, max(0, base_marks + variation)), 1)
                            is_backlog = semester_marks < 40 or (
                                student.academic_record is not None
                                and component_index <= min(student.academic_record.backlogs, 2)
                                and semester == student.semester
                            )
                            results.append(SemesterResult(
                                student_id=student.id,
                                academic_year=academic_year,
                                semester=semester,
                                component_type=component_type,
                                component_name=name,
                                mid1_marks=mid1,
                                mid2_marks=mid2,
                                semester_exam_marks=semester_marks,
                                result_status="Backlog" if is_backlog else "Passed",
                            ))
                        else:
                            results.append(SemesterResult(
                                student_id=student.id,
                                academic_year=academic_year,
                                semester=semester,
                                component_type=component_type,
                                component_name=name,
                                lab_internal_marks=round(min(100, max(0, base_marks + variation + 4)), 1),
                                lab_external_marks=round(min(100, max(0, base_marks + variation - 2)), 1),
                                result_status="Passed" if base_marks + variation >= 40 else "Backlog",
                            ))
                        existing_keys.add(key)
        db.bulk_save_objects(results)
        db.commit()
    finally:
        db.close()


def seed_student_fees(student_ids: set[str] | None = None) -> None:
    db = SessionLocal()
    try:
        this_year = date.today().year
        existing = {
            (student_id, academic_year)
            for student_id, academic_year in db.query(StudentFee.student_id, StudentFee.academic_year).all()
        }
        fee_records = []
        student_query = db.query(Student)
        if student_ids is not None:
            student_query = student_query.filter(Student.student_id.in_(student_ids))
        for student in student_query.all():
            for year_offset in range(4):
                academic_year = this_year - 3 + year_offset
                key = (student.id, academic_year)
                if key in existing:
                    continue
                generator = random.Random(f"{student.student_id}:{academic_year}:demo-fees")
                total_fee = generator.randrange(45000, 90001, 1000)
                paid_fee = generator.randrange(0, total_fee // 1000 + 1) * 1000
                fee_records.append(StudentFee(
                    student_id=student.id,
                    academic_year=academic_year,
                    total_fee=total_fee,
                    paid_fee=paid_fee,
                ))
                existing.add(key)
        db.bulk_save_objects(fee_records)
        db.commit()
    finally:
        db.close()


def seed_cultural_activity_fees(student_ids: set[str] | None = None) -> None:
    db = SessionLocal()
    try:
        activity_names = [
            "Cultural Festival",
            "Freshers Celebration",
            "Annual Day",
            "Music and Arts Fest",
        ]
        this_year = date.today().year
        existing = {
            (student_id, academic_year, activity_name)
            for student_id, academic_year, activity_name in db.query(
                CulturalActivityFee.student_id,
                CulturalActivityFee.academic_year,
                CulturalActivityFee.activity_name,
            ).all()
        }
        activity_fees = []
        student_query = db.query(Student)
        if student_ids is not None:
            student_query = student_query.filter(Student.student_id.in_(student_ids))
        for student in student_query.all():
            for year_offset in range(4):
                academic_year = this_year - 3 + year_offset
                generator = random.Random(f"{student.student_id}:{academic_year}:cultural-activities")
                activity_count = generator.choice((3, 4))
                for activity_name in activity_names[:activity_count]:
                    key = (student.id, academic_year, activity_name)
                    if key in existing:
                        continue
                    activity_fees.append(CulturalActivityFee(
                        student_id=student.id,
                        academic_year=academic_year,
                        activity_name=activity_name,
                        amount=generator.randint(1000, 1500),
                    ))
                    existing.add(key)
        db.bulk_save_objects(activity_fees)
        db.commit()
    finally:
        db.close()
