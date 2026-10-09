from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StudentSummary(BaseModel):
    student_id: str
    name: str
    department: str
    year: int
    semester: int
    cgpa: float
    attendance: float
    success_score: float
    academic_risk: str
    placement_risk: str
    segment: str
    intervention_priority: str
    mentor: Optional[str] = None


class DashboardSummary(BaseModel):
    total_students: int
    average_success_score: float
    students_at_risk: int
    academic_risk_count: int
    placement_risk_count: int
    average_attendance: float
    average_placement_readiness: float
    success_distribution: List[Dict[str, Any]]
    risk_trends: List[Dict[str, Any]]
    department_summary: List[Dict[str, Any]]


class StudentDetail(BaseModel):
    student_id: str
    name: str
    department: str
    year: int
    semester: int
    cgpa: float
    attendance: float
    success_score: float
    academic_risk: str
    placement_risk: str
    overall_risk: str
    segment: str
    mentor: Optional[str]
    academic: Dict[str, Any]
    attendance_breakdown: Dict[str, Any]
    lms: Dict[str, Any]
    engagement: Dict[str, Any]
    placement: Dict[str, Any]
    skills: Dict[str, Any]
    feedback: Dict[str, Any]
    reasons: List[str]
    positive_contributors: List[str]
    negative_contributors: List[str]
    insight: str


class InterventionCreate(BaseModel):
    student_id: str
    title: str
    mentor: str
    priority: str = Field(default="Medium")
    due_date: date
    notes: Optional[str] = None
    status: str = Field(default="Not Started")
    reason: Optional[str] = None
    action: Optional[str] = None


class InterventionUpdate(BaseModel):
    title: Optional[str] = None
    mentor: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    action: Optional[str] = None


class DataQualityResponse(BaseModel):
    total_records: int
    valid_records: int
    missing_values: int
    duplicate_records: int
    quality_percentage: float
    columns: List[str]
    preview: List[Dict[str, Any]]


class ModelMetrics(BaseModel):
    academic: Dict[str, float]
    placement: Dict[str, float]
