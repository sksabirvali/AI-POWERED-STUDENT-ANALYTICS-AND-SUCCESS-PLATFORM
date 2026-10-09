from sqlalchemy import Column, Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (Index("ix_students_year_semester", "year", "semester"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    cohort = Column(String, nullable=False)
    email = Column(String, nullable=True)
    mentor = Column(String, nullable=True)

    academic_record = relationship("AcademicRecord", back_populates="student", uselist=False)
    attendance_record = relationship("AttendanceRecord", back_populates="student", uselist=False)
    lms_activity = relationship("LmsActivity", back_populates="student", uselist=False)
    engagement_record = relationship("EngagementRecord", back_populates="student", uselist=False)
    placement_record = relationship("PlacementRecord", back_populates="student", uselist=False)
    skills = relationship("SkillRecord", back_populates="student", uselist=False)
    feedback = relationship("FeedbackRecord", back_populates="student", uselist=False)
    success_score = relationship("SuccessScore", back_populates="student", uselist=False)
    risk_prediction = relationship("RiskPrediction", back_populates="student", uselist=False)
    segment = relationship("StudentSegment", back_populates="student", uselist=False)
    interventions = relationship("Intervention", back_populates="student")


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    email = Column(String, nullable=False)
    mentor_code = Column(String, unique=True, nullable=False)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True, index=True)
    status = Column(String, nullable=False, default="active")


class AcademicRecord(Base):
    __tablename__ = "academic_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    cgpa = Column(Float, nullable=False)
    marks = Column(Float, nullable=False)
    backlogs = Column(Integer, default=0)
    subject_performance = Column(Text, nullable=True)

    student = relationship("Student", back_populates="academic_record")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    overall_attendance = Column(Float, nullable=False)
    subject_attendance = Column(Text, nullable=True)

    student = relationship("Student", back_populates="attendance_record")


class LmsActivity(Base):
    __tablename__ = "lms_activity"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    login_frequency = Column(Float, nullable=False)
    assignment_completion = Column(Float, nullable=False)
    quiz_performance = Column(Float, nullable=False)
    learning_activity = Column(Float, nullable=False)

    student = relationship("Student", back_populates="lms_activity")


class EngagementRecord(Base):
    __tablename__ = "engagement_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    events_attended = Column(Integer, default=0)
    clubs = Column(Integer, default=0)
    hackathons = Column(Integer, default=0)
    certifications = Column(Integer, default=0)
    extracurricular = Column(Float, default=0.0)

    student = relationship("Student", back_populates="engagement_record")


class PlacementRecord(Base):
    __tablename__ = "placement_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    aptitude_score = Column(Float, nullable=False)
    coding_score = Column(Float, nullable=False)
    mock_interview_score = Column(Float, nullable=False)
    resume_score = Column(Float, nullable=False)
    placement_training_attendance = Column(Float, nullable=False)
    placement_status = Column(String, default="In Progress")

    student = relationship("Student", back_populates="placement_record")


class SkillRecord(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    technical = Column(Float, nullable=False)
    communication = Column(Float, nullable=False)
    problem_solving = Column(Float, nullable=False)
    soft_skill = Column(Float, nullable=False)

    student = relationship("Student", back_populates="skills")


class FeedbackRecord(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    student_satisfaction = Column(Float, nullable=False)
    faculty_feedback = Column(Float, nullable=False)
    mentor_feedback = Column(Float, nullable=False)

    student = relationship("Student", back_populates="feedback")


class SuccessScore(Base):
    __tablename__ = "success_scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    score = Column(Float, nullable=False)
    academic = Column(Float, nullable=False)
    attendance = Column(Float, nullable=False)
    lms = Column(Float, nullable=False)
    assessment = Column(Float, nullable=False)
    placement = Column(Float, nullable=False)
    skills = Column(Float, nullable=False)
    engagement = Column(Float, nullable=False)
    factors = Column(Text, nullable=True)

    student = relationship("Student", back_populates="success_score")


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    academic_risk_level = Column(String, nullable=False)
    placement_risk_level = Column(String, nullable=False)
    academic_risk_probability = Column(Float, nullable=False)
    placement_risk_probability = Column(Float, nullable=False)
    overall_priority = Column(String, nullable=False)
    reasons = Column(Text, nullable=True)

    student = relationship("Student", back_populates="risk_prediction")


class StudentSegment(Base):
    __tablename__ = "student_segments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    segment_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    recommended_intervention = Column(String, nullable=True)

    student = relationship("Student", back_populates="segment")


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    title = Column(String, nullable=False)
    mentor = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    due_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="Not Started")
    reason = Column(Text, nullable=True)
    action = Column(Text, nullable=True)

    student = relationship("Student", back_populates="interventions")


class AcademicEntry(Base):
    __tablename__ = "academic_entries"
    __table_args__ = (
        UniqueConstraint("student_id", "subject", "entry_date", name="uq_student_subject_date"),
        Index("ix_academic_student_date", "student_id", "entry_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    entry_date = Column(Date, nullable=False, index=True)
    attendance = Column(String, nullable=True)
    marks = Column(Float, nullable=True)
    max_marks = Column(Float, nullable=True)

    student = relationship("Student")


class SemesterResult(Base):
    __tablename__ = "semester_results"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "academic_year",
            "semester",
            "component_type",
            "component_name",
            name="uq_semester_component_result",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    academic_year = Column(Integer, nullable=False, index=True)
    semester = Column(Integer, nullable=False)
    component_type = Column(String, nullable=False)
    component_name = Column(String, nullable=False)
    mid1_marks = Column(Float, nullable=True)
    mid2_marks = Column(Float, nullable=True)
    semester_exam_marks = Column(Float, nullable=True)
    lab_internal_marks = Column(Float, nullable=True)
    lab_external_marks = Column(Float, nullable=True)
    result_status = Column(String, nullable=False)

    student = relationship("Student")


class StudentFee(Base):
    __tablename__ = "student_fees"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year", name="uq_student_fee_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    academic_year = Column(Integer, nullable=False, index=True)
    total_fee = Column(Integer, nullable=False)
    paid_fee = Column(Integer, nullable=False)

    student = relationship("Student")


class CulturalActivityFee(Base):
    __tablename__ = "cultural_activity_fees"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year", "activity_name", name="uq_student_cultural_activity_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    academic_year = Column(Integer, nullable=False, index=True)
    activity_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)

    student = relationship("Student")
