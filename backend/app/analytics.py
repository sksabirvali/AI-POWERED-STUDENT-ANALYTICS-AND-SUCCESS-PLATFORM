import json
from collections import Counter
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from .models import AcademicRecord, AttendanceRecord, EngagementRecord, FeedbackRecord, LmsActivity, PlacementRecord, RiskPrediction, SkillRecord, Student, StudentSegment, SuccessScore

WEIGHTS = {
    "academic": 0.30,
    "attendance": 0.15,
    "lms": 0.10,
    "assessment": 0.10,
    "placement": 0.20,
    "skills": 0.10,
    "engagement": 0.05,
}


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def to_dict(value: str | None) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def calculate_success(student: Student, db: Session) -> Dict[str, Any]:
    academic = student.academic_record
    attendance = student.attendance_record
    lms = student.lms_activity
    engagement = student.engagement_record
    placement = student.placement_record
    skills = student.skills
    feedback = student.feedback

    has_profile_data = any((academic, attendance, lms, engagement, placement, skills, feedback))
    academic_score = clamp((academic.cgpa * 20) + (academic.marks * 0.35) + ((100 - academic.backlogs * 12) * 0.4)) if academic else 0
    attendance_score = clamp(attendance.overall_attendance) if attendance else 0
    lms_score = clamp((lms.login_frequency * 0.5) + lms.assignment_completion * 0.3 + lms.quiz_performance * 0.2) if lms else 0
    assessment_score = clamp((academic.marks * 0.65) + lms.quiz_performance * 0.35) if academic and lms else 0
    placement_score = clamp((placement.aptitude_score * 0.25) + (placement.coding_score * 0.3) + (placement.mock_interview_score * 0.2) + (placement.resume_score * 0.15) + (placement.placement_training_attendance * 0.1)) if placement else 0
    skills_score = clamp((skills.technical * 0.4) + (skills.communication * 0.2) + (skills.problem_solving * 0.25) + (skills.soft_skill * 0.15)) if skills else 0
    engagement_score = clamp((engagement.events_attended * 4) + (engagement.certifications * 8) + (engagement.hackathons * 10) + (engagement.clubs * 6) + (feedback.student_satisfaction * 0.5)) if engagement and feedback else 0

    score = (
        WEIGHTS["academic"] * academic_score +
        WEIGHTS["attendance"] * attendance_score +
        WEIGHTS["lms"] * lms_score +
        WEIGHTS["assessment"] * assessment_score +
        WEIGHTS["placement"] * placement_score +
        WEIGHTS["skills"] * skills_score +
        WEIGHTS["engagement"] * engagement_score
    )

    if not has_profile_data:
        category = "Not Yet Assessed"
        positive = []
        negative = []
    elif score >= 90:
        category = "Excellent"
    elif score >= 75:
        category = "Good"
    elif score >= 60:
        category = "Needs Attention"
    else:
        category = "At Risk"

    positive = []
    negative = []

    if attendance_score >= 80:
        positive.append(f"Attendance: {attendance_score:.0f}%")
    else:
        negative.append(f"Attendance: {attendance_score:.0f}%")
    if academic_score >= 80:
        positive.append(f"Academic performance: {academic_score:.0f}%")
    else:
        negative.append(f"Academic performance: {academic_score:.0f}%")
    if placement_score >= 75:
        positive.append(f"Placement readiness: {placement_score:.0f}%")
    else:
        negative.append(f"Placement readiness: {placement_score:.0f}%")
    if skills_score >= 75:
        positive.append(f"Skill profile: {skills_score:.0f}%")
    else:
        negative.append(f"Skill profile: {skills_score:.0f}%")
    if lms_score >= 75:
        positive.append(f"LMS activity: {lms_score:.0f}%")
    else:
        negative.append(f"LMS activity: {lms_score:.0f}%")

    factors = {
        "academic": round(academic_score, 1),
        "attendance": round(attendance_score, 1),
        "lms": round(lms_score, 1),
        "assessment": round(assessment_score, 1),
        "placement": round(placement_score, 1),
        "skills": round(skills_score, 1),
        "engagement": round(engagement_score, 1),
        "score": round(score, 1),
        "band": category,
    }

    return {
        "score": round(score, 1),
        "academic": round(academic_score, 1),
        "attendance": round(attendance_score, 1),
        "lms": round(lms_score, 1),
        "assessment": round(assessment_score, 1),
        "placement": round(placement_score, 1),
        "skills": round(skills_score, 1),
        "engagement": round(engagement_score, 1),
        "band": category,
        "positive_contributors": positive[:4],
        "negative_contributors": negative[:4],
        "factors": json.dumps(factors),
    }


def determine_risk(student: Student) -> Dict[str, Any]:
    academic = student.academic_record
    attendance = student.attendance_record
    lms = student.lms_activity
    placement = student.placement_record
    skills = student.skills
    if not any((academic, attendance, lms, placement, skills)):
        return {
            "academic_risk_level": "Not Assessed",
            "placement_risk_level": "Not Assessed",
            "academic_risk_probability": 0,
            "placement_risk_probability": 0,
            "overall_priority": "Needs Review",
            "reasons": ["Academic, attendance, and skills data has not been entered yet."],
        }

    academic_risk = 0
    if academic and academic.cgpa < 6.0:
        academic_risk += 35
    if attendance and attendance.overall_attendance < 70:
        academic_risk += 25
    if academic and academic.backlogs > 1:
        academic_risk += 20
    if lms and lms.assignment_completion < 65:
        academic_risk += 15
    if academic and academic.marks < 55:
        academic_risk += 15
    academic_prob = clamp(academic_risk)
    if not all((academic, attendance, lms)):
        academic_prob = max(academic_prob, 45)
    if academic_prob >= 70:
        academic_level = "High"
    elif academic_prob >= 45:
        academic_level = "Medium"
    else:
        academic_level = "Low"

    placement_risk = 0
    if placement and placement.aptitude_score < 60:
        placement_risk += 20
    if placement and placement.coding_score < 65:
        placement_risk += 20
    if placement and placement.mock_interview_score < 60:
        placement_risk += 20
    if placement and placement.resume_score < 65:
        placement_risk += 15
    if skills and skills.communication < 70:
        placement_risk += 15
    if placement and placement.placement_training_attendance < 75:
        placement_risk += 10
    placement_prob = clamp(placement_risk)
    if not all((placement, skills)):
        placement_prob = max(placement_prob, 45)
    if placement_prob >= 70:
        placement_level = "High"
    elif placement_prob >= 45:
        placement_level = "Medium"
    else:
        placement_level = "Low"

    if academic_level == "High" and placement_level == "High":
        overall_priority = "Critical"
    elif academic_level == "High" or placement_level == "High":
        overall_priority = "High"
    elif academic_level == "Medium" or placement_level == "Medium":
        overall_priority = "Medium"
    else:
        overall_priority = "Low"

    reasons = []
    if attendance and attendance.overall_attendance < 70:
        reasons.append("Attendance dropped below 70%")
    if academic and academic.backlogs > 1:
        reasons.append(f"{academic.backlogs} active backlog(s)")
    if placement and placement.coding_score < 60:
        reasons.append("Coding confidence is below benchmark")
    if skills and skills.communication < 70:
        reasons.append("Communication skill needs improvement")
    if not all((academic, attendance, lms, placement, skills)):
        reasons.append("Some academic or placement information is not recorded yet")
    if not reasons:
        reasons.append("Strong overall profile with a few optimization opportunities")

    return {
        "academic_risk_level": academic_level,
        "placement_risk_level": placement_level,
        "academic_risk_probability": round(academic_prob, 1),
        "placement_risk_probability": round(placement_prob, 1),
        "overall_priority": overall_priority,
        "reasons": reasons,
    }


def detect_segment(student: Student) -> Dict[str, Any]:
    if not any((student.academic_record, student.attendance_record, student.success_score, student.placement_record)):
        return {
            "segment_name": "New Student / Awaiting Records",
            "description": "New Student / Awaiting Records",
            "recommended_intervention": "Complete the student's first academic and attendance records",
        }
    score = student.success_score.score if student.success_score else 0
    attendance = student.attendance_record.overall_attendance if student.attendance_record else 0
    placement_score = (
        student.placement_record.aptitude_score
        + student.placement_record.coding_score
        + student.placement_record.mock_interview_score
        if student.placement_record else 0
    )
    academic = student.academic_record.cgpa if student.academic_record else 0

    if score >= 85 and placement_score < 190:
        segment = "Academically Strong but Placement Needs Improvement"
        intervention = "Placement readiness coaching and mock interviews"
    elif academic >= 8.0 and placement_score >= 220:
        segment = "High Performer"
        intervention = "Advanced placement and leadership opportunities"
    elif attendance < 70 and score < 60:
        segment = "Critical Intervention Required"
        intervention = "Immediate mentoring and attendance recovery plan"
    elif attendance >= 85 and score < 60:
        segment = "High Engagement but Low Academic Performance"
        intervention = "Academic recovery and tutoring support"
    elif score >= 60 and score < 75:
        segment = "Balanced / On Track"
        intervention = "Targeted mentoring and improvement roadmap"
    elif academic < 7.0 and attendance >= 75:
        segment = "Placement Ready but Academically At Risk"
        intervention = "Academic intervention plus subject remediation"
    else:
        segment = "Low Engagement / Needs Mentoring"
        intervention = "Mentor check-in and LMS engagement recovery"

    return {
        "segment_name": segment,
        "description": segment,
        "recommended_intervention": intervention,
    }


def generate_insight(student: Student) -> str:
    attendance = student.attendance_record.overall_attendance if student.attendance_record else 0
    score = student.success_score.score if student.success_score else 0
    academic = student.academic_record.cgpa if student.academic_record else 0
    placement = student.placement_record if student.placement_record else None
    lms = student.lms_activity if student.lms_activity else None

    positive_bits = []
    risk_bits = []
    if attendance >= 80:
        positive_bits.append(f"attendance of {attendance:.0f}%")
    if academic >= 7.5:
        positive_bits.append(f"CGPA of {academic:.2f}")
    if lms and lms.assignment_completion >= 70:
        positive_bits.append("strong LMS completion")
    if placement and placement.coding_score >= 75:
        positive_bits.append("strong coding readiness")
    if attendance < 70:
        risk_bits.append(f"attendance at {attendance:.0f}%")
    if student.academic_record and student.academic_record.backlogs > 1:
        risk_bits.append(f"{student.academic_record.backlogs} active backlogs")
    if placement and placement.aptitude_score < 60:
        risk_bits.append("low aptitude performance")

    positive = ", ".join(positive_bits[:2]) if positive_bits else "a stable profile"
    risk_summary = ", ".join(risk_bits[:2]) if risk_bits else "no immediate academic blockers"
    return (
        f"Student {student.student_id} currently has a Success Score of {score:.0f}. "
        f"Key strengths include {positive}. The biggest concerns are {risk_summary}. "
        f"Recommended action is to prioritize academic mentoring and targeted skill intervention."
    )


def build_dashboard_summary(students: List[Student]) -> Dict[str, Any]:
    if not students:
        return {
            "total_students": 0,
            "average_success_score": 0,
            "students_at_risk": 0,
            "academic_risk_count": 0,
            "placement_risk_count": 0,
            "average_attendance": 0,
            "average_placement_readiness": 0,
            "success_distribution": [],
            "risk_trends": [],
            "department_summary": [],
        }

    scores = [student.success_score.score if student.success_score else 0 for student in students]
    attendance_values = [student.attendance_record.overall_attendance if student.attendance_record else 0 for student in students]
    placement_values = [
        (student.placement_record.aptitude_score + student.placement_record.coding_score + student.placement_record.mock_interview_score) / 3
        if student.placement_record else 0 for student in students
    ]

    success_distribution = [
        {"range": "90-100", "count": sum(1 for s in scores if 90 <= s <= 100)},
        {"range": "75-89", "count": sum(1 for s in scores if 75 <= s < 90)},
        {"range": "60-74", "count": sum(1 for s in scores if 60 <= s < 75)},
        {"range": "Below 60", "count": sum(1 for s in scores if s < 60)},
    ]

    department_summary = []
    by_dept: Dict[str, List[float]] = {}
    for student in students:
        by_dept.setdefault(student.department, []).append(student.success_score.score if student.success_score else 0)
    for dept, values in by_dept.items():
        department_summary.append({"department": dept, "avg_score": round(sum(values) / len(values), 1)})

    risk_trends = [
        {"month": "Jan", "risk": len([s for s in students if s.risk_prediction and s.risk_prediction.academic_risk_probability >= 60])},
        {"month": "Feb", "risk": len([s for s in students if s.risk_prediction and s.risk_prediction.academic_risk_probability >= 55])},
        {"month": "Mar", "risk": len([s for s in students if s.risk_prediction and s.risk_prediction.academic_risk_probability >= 50])},
        {"month": "Apr", "risk": len([s for s in students if s.risk_prediction and s.risk_prediction.academic_risk_probability >= 45])},
    ]

    return {
        "total_students": len(students),
        "average_success_score": round(sum(scores) / len(scores), 1),
        "students_at_risk": sum(
            1
            for s in students
            if (s.success_score and s.success_score.score < 60)
            or (s.risk_prediction and s.risk_prediction.overall_priority in {"High", "Critical"})
        ),
        "academic_risk_count": sum(1 for s in students if s.risk_prediction and s.risk_prediction.academic_risk_level in {"Medium", "High"}),
        "placement_risk_count": sum(1 for s in students if s.risk_prediction and s.risk_prediction.placement_risk_level in {"Medium", "High"}),
        "average_attendance": round(sum(attendance_values) / len(attendance_values), 1),
        "average_placement_readiness": round(sum(placement_values) / len(placement_values), 1),
        "success_distribution": success_distribution,
        "risk_trends": risk_trends,
        "department_summary": department_summary,
    }


def build_student_records(students: List[Student]) -> List[Dict[str, Any]]:
    rows = []
    for student in students:
        score = student.success_score.score if student.success_score else 0
        rows.append({
            "student_id": student.student_id,
            "name": student.name,
            "department": student.department,
            "year": student.year,
            "semester": student.semester,
            "cgpa": round(student.academic_record.cgpa, 2) if student.academic_record else 0,
            "attendance": round(student.attendance_record.overall_attendance, 1) if student.attendance_record else 0,
            "success_score": round(score, 1),
            "academic_risk": student.risk_prediction.academic_risk_level if student.risk_prediction else "Not Yet Assessed",
            "placement_risk": student.risk_prediction.placement_risk_level if student.risk_prediction else "Not Yet Assessed",
            "segment": student.segment.segment_name if student.segment else (
                "New Student / Awaiting Records" if not any((
                    student.academic_record,
                    student.attendance_record,
                    student.success_score,
                    student.placement_record,
                )) else "Balanced / On Track"
            ),
            "intervention_priority": student.risk_prediction.overall_priority if student.risk_prediction else "Needs Review",
            "mentor": student.mentor,
        })
    return rows
