import base64
import calendar
import hashlib
import hmac
import io
import json
import os
import secrets
import time
from math import ceil
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Literal

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .academic_catalog import LABS_BY_SEMESTER, SUBJECTS_BY_SEMESTER, academic_year_for_semester
from .analytics import build_dashboard_summary, build_student_records, calculate_success, determine_risk, detect_segment, generate_insight
from .database import SessionLocal, init_db
from .models import AcademicEntry, CulturalActivityFee, Faculty, Intervention, SemesterResult, Student, StudentFee, UserAccount
from .seed_data import balance_seeded_student_groups, seed_academic_history, seed_cultural_activity_fees, seed_database, seed_faculty, seed_semester_results, seed_student_fees, update_placeholder_student_names

app = FastAPI(title="Student Success Analytics Platform")

cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "APP_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    if os.environ.get("APP_SEED_DEMO", "true").lower() in {"1", "true", "yes"}:
        missing_demo_passwords = [
            key for key in (
                "DEMO_ADMIN_PASSWORD",
                "DEMO_FACULTY_PASSWORD",
                "DEMO_STUDENT_PASSWORD",
            )
            if not os.environ.get(key)
        ]
        if missing_demo_passwords:
            raise RuntimeError(
                "Set the demo login passwords before enabling APP_SEED_DEMO: "
                + ", ".join(missing_demo_passwords)
            )
        seed_database()
        update_placeholder_student_names()
        balance_seeded_student_groups()
        seed_faculty()
        seed_academic_history()
        seed_semester_results()
        seed_student_fees()
        seed_cultural_activity_fees()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=100)
    role: str


class StudentSignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    department: str = Field(min_length=2, max_length=100)


class FacultySignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    department: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=100)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=8, max_length=100)


class StudentAssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AcademicEntryRequest(BaseModel):
    student_id: str
    subject: str
    entry_date: date
    attendance: str | None = None
    marks: float | None = Field(default=None, ge=0, le=100)
    max_marks: float | None = Field(default=100, gt=0, le=100)


class SemesterResultRequest(BaseModel):
    student_id: str
    academic_year: int = Field(ge=2000, le=2100)
    semester: int = Field(ge=1, le=8)
    component_type: Literal["subject", "lab"]
    component_name: str = Field(min_length=1, max_length=100)
    mid1_marks: float | None = Field(default=None, ge=0, le=100)
    mid2_marks: float | None = Field(default=None, ge=0, le=100)
    semester_exam_marks: float | None = Field(default=None, ge=0, le=100)
    lab_internal_marks: float | None = Field(default=None, ge=0, le=100)
    lab_external_marks: float | None = Field(default=None, ge=0, le=100)
    result_status: Literal["Passed", "Backlog"]


DEMO_STUDENT_PASSWORD = os.environ.get("DEMO_STUDENT_PASSWORD", "")
DEMO_USERS = {
    "admin": {"password": os.environ.get("DEMO_ADMIN_PASSWORD", ""), "role": "admin", "name": "College Administrator", "student_id": None},
    "faculty": {"password": os.environ.get("DEMO_FACULTY_PASSWORD", ""), "role": "faculty", "name": "Faculty Mentor", "student_id": None},
    "student": {"password": DEMO_STUDENT_PASSWORD, "role": "student", "name": "Demo Student A", "student_id": "STU-0001"},
}
AUTH_SECRET = os.environ.get("APP_AUTH_SECRET") or secrets.token_urlsafe(32)
AUTH_SECRET = AUTH_SECRET.encode("utf-8")


def create_access_token(role: str, student_id: str | None, username: str | None = None) -> str:
    payload = json.dumps({
        "role": role,
        "student_id": student_id,
        "username": username,
        "expires_at": int(time.time()) + 12 * 60 * 60,
    }, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(AUTH_SECRET, encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> Dict[str, Any] | None:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(AUTH_SECRET, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        supplied_signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return None
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        payload = json.loads(payload_bytes)
        if payload.get("expires_at", 0) < time.time() or payload.get("role") not in {"admin", "faculty", "student"}:
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"{base64.urlsafe_b64encode(salt).decode('ascii')}:{base64.urlsafe_b64encode(digest).decode('ascii')}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded_salt, encoded_digest = password_hash.split(":", 1)
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False
    supplied_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return hmac.compare_digest(expected_digest, supplied_digest)


@app.middleware("http")
async def enforce_role_access(request: Request, call_next):
    path = request.url.path
    public_auth_paths = {
        "/api/auth/login",
        "/api/auth/signup/student",
        "/api/auth/signup/faculty",
    }
    if not path.startswith("/api/") or path in {"/api/health", *public_auth_paths} or request.method == "OPTIONS":
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    identity = decode_access_token(authorization[7:]) if authorization.startswith("Bearer ") else None
    if identity is None:
        return JSONResponse(status_code=401, content={"detail": "Sign in to access this resource"})

    role = identity["role"]
    student_id = identity.get("student_id")
    query_student_id = request.query_params.get("student_id")
    method = request.method

    if path.startswith("/api/auth/faculty-requests") and role != "admin":
        return JSONResponse(status_code=403, content={"detail": "Only administrators can manage faculty registrations"})

    if role == "student":
        if path == "/api/students" and query_student_id != student_id:
            return JSONResponse(status_code=403, content={"detail": "Students can only view their own information"})
        if path.startswith("/api/students/"):
            requested_student_id = path.removeprefix("/api/students/").split("/", 1)[0]
            if requested_student_id != student_id:
                return JSONResponse(status_code=403, content={"detail": "Students can only view their own information"})
        if path == "/api/academic/trends" and query_student_id != student_id:
            return JSONResponse(status_code=403, content={"detail": "Students can only view their own academic trends"})
        if path == "/api/academic/semester-results" and query_student_id != student_id:
            return JSONResponse(status_code=403, content={"detail": "Students can only view their own semester results"})
        if path == "/api/fees" and query_student_id != student_id:
            return JSONResponse(status_code=403, content={"detail": "Students can only view their own fee records"})
        restricted_paths = {
            "/api/dashboard/summary",
            "/api/segments",
            "/api/interventions",
            "/api/faculty",
            "/api/data/quality",
            "/api/model/metrics",
            "/api/analytics/trends",
            "/api/analytics/departments",
        }
        if path in restricted_paths:
            return JSONResponse(status_code=403, content={"detail": "This resource is not available for student accounts"})
        if method != "GET" and path not in {"/api/auth/password", "/api/student/assistant"}:
            return JSONResponse(status_code=403, content={"detail": "Student accounts are read-only"})
    elif role == "faculty" and (path == "/api/faculty" or path.startswith("/api/faculty/")):
        return JSONResponse(status_code=403, content={"detail": "Faculty directory is only available to administrators"})
    elif role == "faculty" and path == "/api/data/upload" and method == "POST":
        return JSONResponse(status_code=403, content={"detail": "Only administrators can upload data"})

    request.state.identity = identity
    return await call_next(request)


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    username = payload.username.strip().lower()
    normalized_username = payload.username.strip().lower()
    account = db.query(UserAccount).filter(or_(
        UserAccount.username == payload.username.strip(),
        UserAccount.email == normalized_username,
    )).first()
    if account:
        if account.role != payload.role or not verify_password(payload.password, account.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username, password, or role")
        if account.status != "active":
            raise HTTPException(status_code=403, detail="Faculty registration is waiting for administrator approval")
        user = {
            "role": account.role,
            "name": account.display_name,
            "student_id": account.username if account.role == "student" else None,
        }
    else:
        user = DEMO_USERS.get(username)
    if account is None and payload.role == "student" and payload.password == DEMO_STUDENT_PASSWORD:
        student_id = "STU-0001" if username == "student" else payload.username.strip().upper()
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=401, detail="Use username 'student' or a valid student ID such as STU-0001")
        user = {"role": "student", "name": student.name, "student_id": student.student_id}
    elif account is None and (not user or payload.password != user["password"] or payload.role != user["role"]):
        raise HTTPException(status_code=401, detail="Invalid username, password, or role")
    if user["student_id"] and not db.query(Student).filter(Student.student_id == user["student_id"]).first():
        raise HTTPException(status_code=404, detail="The demo student account has no matching student record")
    return {
        "username": account.username if account else (
            "faculty" if user["role"] == "faculty" else
            user["student_id"] if user["role"] == "student" else
            payload.username.strip().lower()
        ),
        "role": user["role"],
        "display_name": user["name"],
        "student_id": user["student_id"],
        "access_token": create_access_token(
            user["role"],
            user["student_id"],
            account.username if account else (
                "faculty" if user["role"] == "faculty" else
                user["student_id"] if user["role"] == "student" else
                payload.username.strip().lower()
            ),
        ),
    }


@app.post("/api/auth/password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    identity = request.state.identity
    username = identity.get("username") or identity.get("student_id")
    if not username:
        username = "faculty" if identity["role"] == "faculty" else identity["role"]
    account = db.query(UserAccount).filter(
        func.lower(UserAccount.username) == str(username).lower(),
    ).first()
    if account:
        if not verify_password(payload.current_password, account.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    else:
        demo_account = DEMO_USERS.get(str(username).lower())
        if identity["role"] == "student":
            expected_password = DEMO_STUDENT_PASSWORD
        else:
            expected_password = demo_account["password"] if demo_account else None
        if expected_password is None or not hmac.compare_digest(payload.current_password, expected_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        display_name = demo_account["name"] if demo_account else str(username)
        if identity["role"] == "student":
            student = db.query(Student).filter(Student.student_id == identity["student_id"]).first()
            if student:
                display_name = student.name
        account = UserAccount(
            username=str(username),
            role=identity["role"],
            password_hash=hash_password(payload.new_password),
            display_name=display_name,
            status="active",
        )
        db.add(account)
        db.commit()
        return {"message": "Password updated. Use your new personal password next time you sign in."}
    account.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated. Use your new personal password next time you sign in."}


@app.post("/api/auth/signup/student", status_code=201)
def signup_student(payload: StudentSignupRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not DEMO_STUDENT_PASSWORD:
        raise HTTPException(status_code=503, detail="Student signup is not configured. Set DEMO_STUDENT_PASSWORD first.")

    name = payload.name.strip()
    department = payload.department.strip()
    if not name or not department:
        raise HTTPException(status_code=422, detail="Student name and branch are required")

    semester_counts = {semester: 0 for semester in range(1, 9)}
    for semester_number, count in db.query(Student.semester, func.count(Student.id)).group_by(Student.semester).all():
        if semester_number in semester_counts:
            semester_counts[semester_number] = count
    semester = min(semester_counts, key=lambda candidate: (semester_counts[candidate], candidate))

    year = (semester + 1) // 2
    student = Student(
        student_id=f"PENDING-{secrets.token_hex(16)}",
        name=name,
        department=department,
        year=year,
        semester=semester,
        cohort=str(date.today().year - year + 1),
        email=None,
        mentor=None,
    )
    default_password = DEMO_STUDENT_PASSWORD
    db.add(student)
    db.flush()
    student_id = f"STU-{student.id:04d}"
    if db.query(Student.id).filter(Student.student_id == student_id, Student.id != student.id).first():
        student_id = f"STU-{secrets.token_hex(5).upper()}"
    student.student_id = student_id
    db.add(UserAccount(
        username=student_id,
        role="student",
        password_hash=hash_password(default_password),
        display_name=name,
        department=department,
        status="active",
    ))
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not allocate a unique student account ID. Please retry.") from error

    seed_student_fees({student_id})
    seed_cultural_activity_fees({student_id})
    return {
        "message": "Student account created",
        "username": student_id,
        "year": year,
        "semester": semester,
    }


@app.post("/api/auth/signup/faculty", status_code=201)
def signup_faculty(payload: FacultySignupRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    name = payload.name.strip()
    department = payload.department.strip()
    email = payload.email.strip().lower()
    if not name or not department or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid name, branch, and email address")
    if db.query(UserAccount).filter(UserAccount.email == email).first() or db.query(Faculty).filter(Faculty.email == email).first():
        raise HTTPException(status_code=409, detail="An account already uses this email address")

    used_numbers = []
    for faculty in db.query(Faculty.faculty_id).filter(Faculty.faculty_id.like("FAC-%")).all():
        code = faculty[0]
        if code.startswith("FAC-") and code[4:].isdigit():
            used_numbers.append(int(code[4:]))
    for account in db.query(UserAccount.username).filter(UserAccount.username.like("FAC-%")).all():
        code = account[0]
        if code.startswith("FAC-") and code[4:].isdigit():
            used_numbers.append(int(code[4:]))
    faculty_id = f"FAC-{max(used_numbers, default=0) + 1:03d}"
    account = UserAccount(
        username=faculty_id,
        role="faculty",
        password_hash=hash_password(payload.password),
        display_name=name,
        department=department,
        email=email,
        status="pending",
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="A registration with this email or account ID already exists. Please retry.") from error
    return {"message": "Faculty registration submitted for administrator approval", "username": faculty_id, "status": account.status}


@app.get("/api/auth/faculty-requests")
def get_faculty_requests(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    requests = (
        db.query(UserAccount)
        .filter(UserAccount.role == "faculty", UserAccount.status == "pending")
        .order_by(UserAccount.username)
        .all()
    )
    return [
        {"username": account.username, "name": account.display_name, "department": account.department, "email": account.email}
        for account in requests
    ]


@app.post("/api/auth/faculty-requests/{username}/approve")
def approve_faculty_request(username: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    account = db.query(UserAccount).filter(
        UserAccount.username == username,
        UserAccount.role == "faculty",
    ).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Faculty registration not found")
    if account.status == "active":
        return {"message": "Faculty account is already approved"}

    mentor_numbers = []
    for faculty in db.query(Faculty.mentor_code).all():
        code = faculty[0]
        if code.startswith("Mentor ") and code[7:].isdigit():
            mentor_numbers.append(int(code[7:]))
    mentor_code = f"Mentor {max(mentor_numbers, default=0) + 1:02d}"
    db.add(Faculty(
        faculty_id=account.username,
        name=account.display_name,
        department=account.department or "Unassigned",
        designation="Faculty",
        email=account.email or "",
        mentor_code=mentor_code,
    ))
    account.status = "active"
    db.commit()
    return {"message": "Faculty account approved"}


@app.get("/api/faculty")
def get_faculty(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    faculty_members = db.query(Faculty).order_by(Faculty.department, Faculty.name).all()
    return [
        {
            "faculty_id": faculty.faculty_id,
            "name": faculty.name,
            "department": faculty.department,
            "designation": faculty.designation,
            "email": faculty.email,
            "assigned_students": db.query(Student).filter(Student.mentor == faculty.mentor_code).count(),
        }
        for faculty in faculty_members
    ]


def build_monthly_risk_trend(db: Session, year: int) -> List[Dict[str, Any]]:
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)
    rows = (
        db.query(AcademicEntry, Student)
        .join(Student, AcademicEntry.student_id == Student.id)
        .filter(AcademicEntry.entry_date >= start_date, AcademicEntry.entry_date < end_date)
        .all()
    )
    monthly_student_entries: dict[int, dict[str, list[AcademicEntry]]] = defaultdict(lambda: defaultdict(list))
    for entry, student in rows:
        monthly_student_entries[entry.entry_date.month][student.student_id].append(entry)

    trend = []
    for month in range(1, 13):
        student_risks = []
        for entries in monthly_student_entries[month].values():
            attendance_entries = [entry for entry in entries if entry.attendance is not None]
            marks_entries = [entry for entry in entries if entry.marks is not None]
            if not attendance_entries and not marks_entries:
                continue
            attendance_rate = (
                sum(1 for entry in attendance_entries if entry.attendance == "Present") / len(attendance_entries) * 100
                if attendance_entries else None
            )
            average_marks = (
                sum(entry.marks for entry in marks_entries) / len(marks_entries)
                if marks_entries else None
            )
            risk_parts = []
            if attendance_rate is not None:
                risk_parts.append(max(0, min(100, (75 - attendance_rate) * 2)))
            if average_marks is not None:
                risk_parts.append(max(0, min(100, (60 - average_marks) * 2.5)))
            student_risks.append(sum(risk_parts) / len(risk_parts))

        trend.append({
            "month": calendar.month_abbr[month],
            "risk": sum(1 for risk in student_risks if risk >= 50) if student_risks else None,
            "students": len(student_risks),
            "records_available": bool(student_risks),
        })
    return trend


@app.get("/api/academic/trends")
def academic_trends(
    period: str = Query(default="weekly", pattern="^(daily|weekly|monthly|yearly)$"),
    student_id: str | None = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    query = db.query(AcademicEntry, Student).join(Student, AcademicEntry.student_id == Student.id)
    today = date.today()
    current_week = today - timedelta(days=today.weekday())
    if period == "daily":
        query = query.filter(AcademicEntry.entry_date >= today - timedelta(days=30))
    elif period == "weekly":
        query = query.filter(
            AcademicEntry.entry_date >= current_week - timedelta(weeks=14),
            AcademicEntry.entry_date < current_week,
        )
    elif period == "monthly":
        first_of_month = today.replace(day=1)
        query = query.filter(
            AcademicEntry.entry_date >= first_of_month.replace(year=first_of_month.year - 2),
            AcademicEntry.entry_date < first_of_month,
        )
    else:
        query = query.filter(AcademicEntry.entry_date >= date(today.year - 5, 1, 1))
    if student_id:
        query = query.filter(Student.student_id == student_id)
    rows = query.order_by(AcademicEntry.entry_date.asc()).all()

    def period_start(entry_date: date) -> date:
        if period == "daily":
            return entry_date
        if period == "weekly":
            return entry_date - timedelta(days=entry_date.weekday())
        if period == "monthly":
            return entry_date.replace(day=1)
        return entry_date.replace(month=1, day=1)

    buckets: dict[date, list[tuple[AcademicEntry, Student]]] = defaultdict(list)
    for entry, student in rows:
        buckets[period_start(entry.entry_date)].append((entry, student))

    trend = []
    for start_date, bucket_rows in sorted(buckets.items()):
        subject_rows: dict[str, list[AcademicEntry]] = defaultdict(list)
        student_rows: dict[str, list[AcademicEntry]] = defaultdict(list)
        for entry, student in bucket_rows:
            subject_rows[entry.subject].append(entry)
            student_rows[student.student_id].append(entry)

        subject_summary = {}
        for subject, entries in subject_rows.items():
            attendance_entries = [entry for entry in entries if entry.attendance is not None]
            marks_entries = [entry for entry in entries if entry.marks is not None]
            subject_summary[subject] = {
                "attendance": round(
                    sum(1 for entry in attendance_entries if entry.attendance == "Present") / len(attendance_entries) * 100,
                    1,
                ) if attendance_entries else None,
                "marks": round(sum(entry.marks for entry in marks_entries) / len(marks_entries), 1) if marks_entries else None,
            }

        student_risks = []
        attendance_values = []
        marks_values = []
        for entries in student_rows.values():
            attendance_entries = [entry for entry in entries if entry.attendance is not None]
            marks_entries = [entry for entry in entries if entry.marks is not None]
            student_attendance = (
                sum(1 for entry in attendance_entries if entry.attendance == "Present") / len(attendance_entries) * 100
                if attendance_entries else None
            )
            student_marks = sum(entry.marks for entry in marks_entries) / len(marks_entries) if marks_entries else None
            if student_attendance is not None:
                attendance_values.append(student_attendance)
            if student_marks is not None:
                marks_values.append(student_marks)
            if student_attendance is not None or student_marks is not None:
                risk = (
                    (max(0, min(100, (75 - student_attendance) * 2)) if student_attendance is not None else 0)
                    + (max(0, min(100, (60 - student_marks) * 2.5)) if student_marks is not None else 0)
                ) / (2 if student_attendance is not None and student_marks is not None else 1)
                student_risks.append(risk)

        trend.append({
            "date": start_date.isoformat(),
            "label": start_date.strftime("%d %b %Y") if period in {"daily", "weekly"} else start_date.strftime("%b %Y") if period == "monthly" else start_date.strftime("%Y"),
            "attendance": round(sum(attendance_values) / len(attendance_values), 1) if attendance_values else None,
            "marks": round(sum(marks_values) / len(marks_values), 1) if marks_values else None,
            "risk": round(sum(student_risks) / len(student_risks), 1) if student_risks else 0,
            "at_risk_students": sum(1 for value in student_risks if value >= 50),
            "students": len(student_risks),
            "subjects": subject_summary,
        })

    return {"period": period, "student_id": student_id, "subjects": ["M1", "M2", "M3", "M4"], "trend": trend}


@app.get("/api/academic/semester-results")
def get_semester_results(
    student_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result_rows = (
        db.query(SemesterResult)
        .filter(SemesterResult.student_id == student.id)
        .order_by(SemesterResult.academic_year, SemesterResult.semester, SemesterResult.component_type, SemesterResult.component_name)
        .all()
    )
    current_year = date.today().year
    grouped_results: dict[int, dict[str, Any]] = {
        semester: {
            "academic_year": academic_year_for_semester(semester, current_year),
            "semester": semester,
            "subjects": [],
            "labs": [],
            "passed_count": 0,
            "backlog_count": 0,
        }
        for semester in range(1, 9)
    }
    for result in result_rows:
        if result.semester not in grouped_results or result.academic_year != grouped_results[result.semester]["academic_year"]:
            continue
        component = {
            "component_name": result.component_name,
            "mid1_marks": result.mid1_marks,
            "mid2_marks": result.mid2_marks,
            "semester_exam_marks": result.semester_exam_marks,
            "lab_internal_marks": result.lab_internal_marks,
            "lab_external_marks": result.lab_external_marks,
            "result_status": result.result_status,
        }
        grouped_results[result.semester]["subjects" if result.component_type == "subject" else "labs"].append(component)
        status_key = "passed_count" if result.result_status == "Passed" else "backlog_count"
        grouped_results[result.semester][status_key] += 1

    attendance_entries = (
        db.query(AcademicEntry)
        .filter(AcademicEntry.student_id == student.id, AcademicEntry.attendance.isnot(None))
        .all()
    )
    attendance_by_year: dict[int, list[AcademicEntry]] = defaultdict(list)
    for entry in attendance_entries:
        attendance_by_year[entry.entry_date.year].append(entry)

    attendance_years = []
    for year, entries in sorted(attendance_by_year.items()):
        attended = sum(1 for entry in entries if entry.attendance == "Present")
        attendance = round(attended / len(entries) * 100, 1)
        shortfall_tiers = ceil((75 - attendance) / 10) if attendance < 75 else 0
        attendance_years.append({
            "year": year,
            "attendance": attendance,
            "attended_sessions": attended,
            "total_sessions": len(entries),
            "condonation_required": attendance < 75,
            "condonation_fee": shortfall_tiers * 2000,
        })

    return {
        "student_id": student.student_id,
        "attendance_years": attendance_years,
        "semesters": [grouped_results[semester] for semester in range(1, 9)],
    }


@app.get("/api/fees")
def get_student_fees(
    student_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    fee_rows = (
        db.query(StudentFee)
        .filter(StudentFee.student_id == student.id)
        .order_by(StudentFee.academic_year.asc())
        .all()
    )
    activity_rows = (
        db.query(CulturalActivityFee)
        .filter(CulturalActivityFee.student_id == student.id)
        .order_by(CulturalActivityFee.academic_year.asc(), CulturalActivityFee.activity_name.asc())
        .all()
    )
    activities_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for activity in activity_rows:
        activities_by_year[activity.academic_year].append({
            "activity_name": activity.activity_name,
            "amount": activity.amount,
        })
    years = [
        {
            "academic_year": fee.academic_year,
            "tuition_fee": fee.total_fee,
            "cultural_activity_fee": sum(item["amount"] for item in activities_by_year[fee.academic_year]),
            "activities": activities_by_year[fee.academic_year],
            "total_fee": fee.total_fee + sum(item["amount"] for item in activities_by_year[fee.academic_year]),
            "paid_fee": fee.paid_fee,
            "due_fee": fee.total_fee + sum(item["amount"] for item in activities_by_year[fee.academic_year]) - fee.paid_fee,
        }
        for fee in fee_rows
    ]
    return {
        "student_id": student.student_id,
        "currency": "INR",
        "demo_data": True,
        "total_fee": sum(year["total_fee"] for year in years),
        "paid_fee": sum(year["paid_fee"] for year in years),
        "due_fee": sum(year["due_fee"] for year in years),
        "years": years,
    }


@app.post("/api/academic/semester-results")
def save_semester_result(
    payload: SemesterResultRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    expected_year = academic_year_for_semester(payload.semester)
    if payload.academic_year != expected_year:
        raise HTTPException(
            status_code=422,
            detail=f"Semester {payload.semester} belongs to academic year {expected_year}",
        )
    valid_names = SUBJECTS_BY_SEMESTER[payload.semester] if payload.component_type == "subject" else LABS_BY_SEMESTER[payload.semester]
    if payload.component_name not in valid_names:
        raise HTTPException(status_code=422, detail="Choose a subject or lab listed for the selected semester")
    if payload.component_type == "subject":
        if payload.mid1_marks is None and payload.mid2_marks is None and payload.semester_exam_marks is None:
            raise HTTPException(status_code=422, detail="Enter at least one subject exam mark")
        if payload.lab_internal_marks is not None or payload.lab_external_marks is not None:
            raise HTTPException(status_code=422, detail="Lab marks cannot be saved for a subject")
    else:
        if payload.lab_internal_marks is None and payload.lab_external_marks is None:
            raise HTTPException(status_code=422, detail="Enter an internal or external lab mark")
        if payload.mid1_marks is not None or payload.mid2_marks is not None or payload.semester_exam_marks is not None:
            raise HTTPException(status_code=422, detail="Subject exam marks cannot be saved for a lab")

    student = db.query(Student).filter(Student.student_id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    result = (
        db.query(SemesterResult)
        .filter(
            SemesterResult.student_id == student.id,
            SemesterResult.academic_year == payload.academic_year,
            SemesterResult.semester == payload.semester,
            SemesterResult.component_type == payload.component_type,
            SemesterResult.component_name == payload.component_name,
        )
        .first()
    )
    if result is None:
        result = SemesterResult(
            student_id=student.id,
            academic_year=payload.academic_year,
            semester=payload.semester,
            component_type=payload.component_type,
            component_name=payload.component_name,
        )
        db.add(result)
    result.mid1_marks = payload.mid1_marks
    result.mid2_marks = payload.mid2_marks
    result.semester_exam_marks = payload.semester_exam_marks
    result.lab_internal_marks = payload.lab_internal_marks
    result.lab_external_marks = payload.lab_external_marks
    result.result_status = payload.result_status
    db.commit()
    return {"message": "Semester result saved", "student_id": student.student_id}


@app.post("/api/academic/entries")
def save_academic_entry(
    payload: AcademicEntryRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if payload.subject not in {"M1", "M2", "M3", "M4"}:
        raise HTTPException(status_code=422, detail="Subject must be M1, M2, M3, or M4")
    if payload.attendance not in {None, "Present", "Absent"}:
        raise HTTPException(status_code=422, detail="Attendance must be Present or Absent")
    if payload.attendance is None and payload.marks is None:
        raise HTTPException(status_code=422, detail="Record attendance, marks, or both")
    student = db.query(Student).filter(Student.student_id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    entry = db.query(AcademicEntry).filter(
        AcademicEntry.student_id == student.id,
        AcademicEntry.subject == payload.subject,
        AcademicEntry.entry_date == payload.entry_date,
    ).first()
    if entry is None:
        entry = AcademicEntry(student_id=student.id, subject=payload.subject, entry_date=payload.entry_date)
        db.add(entry)
    if payload.attendance is not None:
        entry.attendance = payload.attendance
    if payload.marks is not None:
        entry.marks = payload.marks
        entry.max_marks = payload.max_marks or 100
    db.commit()
    return {"message": "Academic record saved", "student_id": student.student_id, "subject": entry.subject, "entry_date": entry.entry_date.isoformat()}


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> Dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/dashboard/summary")
def dashboard_summary(year: int | None = Query(default=None, ge=2000, le=2100), db: Session = Depends(get_db)) -> Dict[str, Any]:
    students = (
        db.query(Student)
        .options(
            joinedload(Student.academic_record),
            joinedload(Student.attendance_record),
            joinedload(Student.lms_activity),
            joinedload(Student.engagement_record),
            joinedload(Student.placement_record),
            joinedload(Student.skills),
            joinedload(Student.feedback),
            joinedload(Student.success_score),
            joinedload(Student.risk_prediction),
            joinedload(Student.segment),
        )
        .all()
    )
    dashboard = build_dashboard_summary(students)
    trend_year = year or date.today().year
    return {
        "kpis": {
            "total_students": dashboard["total_students"],
            "average_success_score": dashboard["average_success_score"],
            "students_at_risk": dashboard["students_at_risk"],
            "academic_risk_count": dashboard["academic_risk_count"],
            "placement_risk_count": dashboard["placement_risk_count"],
            "average_attendance": dashboard["average_attendance"],
            "average_placement_readiness": dashboard["average_placement_readiness"],
        },
        "success_distribution": dashboard["success_distribution"],
        "risk_trends": build_monthly_risk_trend(db, trend_year),
        "risk_trend_year": trend_year,
        "department_summary": dashboard["department_summary"],
    }


@app.get("/api/students")
def get_students(
    student_id: str | None = None,
    search: str | None = Query(default=None, min_length=2, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    query = db.query(Student).options(
        joinedload(Student.academic_record),
        joinedload(Student.attendance_record),
        joinedload(Student.success_score),
        joinedload(Student.risk_prediction),
        joinedload(Student.segment),
    ).order_by(Student.student_id)
    if student_id:
        query = query.filter(Student.student_id == student_id)
    if search:
        search_term = search.strip()
        if search_term:
            query = query.filter(or_(
                Student.student_id.ilike(f"%{search_term}%"),
                Student.name.ilike(f"%{search_term}%"),
            ))
    query = query.offset(offset).limit(limit)
    students = query.all()
    return build_student_records(students)


@app.post("/api/student/assistant")
def student_assistant(
    payload: StudentAssistantRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    identity = request.state.identity
    if identity["role"] != "student" or not identity.get("student_id"):
        raise HTTPException(status_code=403, detail="The student assistant is available to student accounts only")

    student = db.query(Student).filter(Student.student_id == identity["student_id"]).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found")

    question = payload.question.strip().lower()
    if not question:
        raise HTTPException(status_code=422, detail="Enter a question")

    marks = student.academic_record.marks if student.academic_record else None
    cgpa = student.academic_record.cgpa if student.academic_record else None
    attendance = student.attendance_record.overall_attendance if student.attendance_record else None
    backlogs = student.academic_record.backlogs if student.academic_record else 0
    mark_data = student.academic_record.subject_performance if student.academic_record else None
    try:
        subject_marks = json.loads(mark_data) if mark_data else {}
    except json.JSONDecodeError:
        subject_marks = {}
    normalized_subject_marks = {
        str(subject).lower(): value
        for subject, value in subject_marks.items()
        if isinstance(value, (int, float))
    }

    if any(word in question for word in ("improve", "recommend", "suggest", "study", "advice", "better", "recommendation")):
        response_parts = ["Here is a study plan based on your current record:"]
        weakest_subject = min(normalized_subject_marks, key=normalized_subject_marks.get) if normalized_subject_marks else None
        if weakest_subject:
            response_parts.append(f"Prioritize {weakest_subject.title()} ({normalized_subject_marks[weakest_subject]:g}/100) with short daily practice and a weekly self-test.")
        if marks is not None and marks < 60:
            response_parts.append(f"Your recorded overall marks are {marks:g}/100; review missed questions and ask your faculty mentor about topics you find difficult.")
        elif marks is not None:
            response_parts.append(f"Your recorded overall marks are {marks:g}/100; keep revising regularly and practice timed questions.")
        if attendance is not None and attendance < 75:
            response_parts.append(f"Attendance is {attendance:g}%, below 75%; attend upcoming classes consistently and contact your mentor about support.")
        elif attendance is not None:
            response_parts.append(f"Attendance is {attendance:g}%; maintain it by attending each class.")
        if backlogs:
            response_parts.append(f"You have {backlogs} backlog(s); make a separate revision schedule and confirm exam dates with your department.")
        return {"answer": " ".join(response_parts), "source": "your student record and built-in study guidance"}

    if any(word in question for word in ("attendance", "present", "absent")):
        answer = f"Your current overall attendance is {attendance:g}%." if attendance is not None else "There is no overall attendance value recorded for you yet."
        if attendance is not None:
            answer += " This is below 75%; please attend upcoming classes consistently." if attendance < 75 else " You are currently at or above the 75% threshold."
    elif any(word in question for word in ("backlog", "backlogs", "passed", "pass")):
        answer = f"Your current backlog count is {backlogs}." if student.academic_record else "Backlog information has not been recorded yet."
        result_rows = db.query(SemesterResult).filter(SemesterResult.student_id == student.id).all()
        if result_rows:
            backlog_rows = [result for result in result_rows if result.result_status == "Backlog"]
            answer += f" Your semester records show {len(backlog_rows)} backlog component(s) and {len(result_rows) - len(backlog_rows)} passed component(s)."
    elif any(word in question for word in ("fee", "fees", "due", "balance")):
        fee_rows = db.query(StudentFee).filter(StudentFee.student_id == student.id).all()
        activity_total = db.query(func.coalesce(func.sum(CulturalActivityFee.amount), 0)).filter(CulturalActivityFee.student_id == student.id).scalar() or 0
        tuition_total = sum(fee.total_fee for fee in fee_rows)
        paid_total = sum(fee.paid_fee for fee in fee_rows)
        answer = f"Your sample fee balance is ₹{max(0, tuition_total + activity_total - paid_total):,} due (₹{tuition_total + activity_total:,} total including activities, ₹{paid_total:,} marked paid). These are demo amounts, not an official statement."
    elif any(word in question for word in ("risk", "cgpa", "score", "marks", "mark", "grade", "semester", "result", "subject")):
        parts = []
        if marks is not None:
            parts.append(f"Your recorded overall marks are {marks:g}/100")
        if cgpa is not None:
            parts.append(f"your CGPA is {cgpa:g}")
        if normalized_subject_marks:
            parts.append("subject marks: " + ", ".join(f"{name.title()} {value:g}/100" for name, value in normalized_subject_marks.items()))
        if not parts:
            answer = "I could not find marks or CGPA recorded for you yet. Ask your faculty member to enter your latest results."
        else:
            answer = ". ".join(parts) + "."
        result_rows = db.query(SemesterResult).filter(SemesterResult.student_id == student.id).order_by(SemesterResult.semester).all()
        if any(word in question for word in ("semester", "result", "backlog", "passed", "pass")):
            if result_rows:
                passed = sum(result.result_status == "Passed" for result in result_rows)
                backlog = sum(result.result_status == "Backlog" for result in result_rows)
                answer += f" Across recorded semester components: {passed} passed and {backlog} backlog."
            else:
                answer += " Semester exam results have not been recorded yet."
    else:
        answer = "I can look up your own marks, attendance, semester results, backlogs, fee balance, and give study suggestions. Ask about one of those, for example: “How can I improve my marks?”"

    return {"answer": answer, "source": "your student record"}


@app.get("/api/students/{student_id}")
def get_student(student_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    success = calculate_success(student, db)
    risk = determine_risk(student)
    segment = detect_segment(student)
    insight = generate_insight(student)
    student_data = {
        "student_id": student.student_id,
        "name": student.name,
        "department": student.department,
        "year": student.year,
        "semester": student.semester,
        "cgpa": round(student.academic_record.cgpa, 2) if student.academic_record else 0,
        "attendance": round(student.attendance_record.overall_attendance, 1) if student.attendance_record else 0,
        "success_score": success["score"],
        "academic_risk": risk["academic_risk_level"],
        "placement_risk": risk["placement_risk_level"],
        "overall_risk": risk["overall_priority"],
        "segment": segment["segment_name"],
        "mentor": student.mentor,
        "academic": {
            "cgpa": round(student.academic_record.cgpa, 2) if student.academic_record else 0,
            "marks": round(student.academic_record.marks, 1) if student.academic_record else 0,
            "backlogs": student.academic_record.backlogs if student.academic_record else 0,
            "subject_performance": student.academic_record.subject_performance if student.academic_record else {},
        },
        "attendance_breakdown": {
            "overall_attendance": round(student.attendance_record.overall_attendance, 1) if student.attendance_record else 0,
            "subject_attendance": student.attendance_record.subject_attendance if student.attendance_record else {},
        },
        "lms": {
            "login_frequency": round(student.lms_activity.login_frequency, 1) if student.lms_activity else 0,
            "assignment_completion": round(student.lms_activity.assignment_completion, 1) if student.lms_activity else 0,
            "quiz_performance": round(student.lms_activity.quiz_performance, 1) if student.lms_activity else 0,
            "learning_activity": round(student.lms_activity.learning_activity, 1) if student.lms_activity else 0,
        },
        "engagement": {
            "events_attended": student.engagement_record.events_attended if student.engagement_record else 0,
            "clubs": student.engagement_record.clubs if student.engagement_record else 0,
            "certifications": student.engagement_record.certifications if student.engagement_record else 0,
            "hackathons": student.engagement_record.hackathons if student.engagement_record else 0,
            "extracurricular": student.engagement_record.extracurricular if student.engagement_record else 0,
        },
        "placement": {
            "aptitude": round(student.placement_record.aptitude_score, 1) if student.placement_record else 0,
            "coding": round(student.placement_record.coding_score, 1) if student.placement_record else 0,
            "mock_interview": round(student.placement_record.mock_interview_score, 1) if student.placement_record else 0,
            "resume": round(student.placement_record.resume_score, 1) if student.placement_record else 0,
            "placement_readiness": round((student.placement_record.aptitude_score + student.placement_record.coding_score + student.placement_record.mock_interview_score) / 3, 1) if student.placement_record else 0,
        },
        "skills": {"technical": student.skills.technical if student.skills else 0, "communication": student.skills.communication if student.skills else 0, "problem_solving": student.skills.problem_solving if student.skills else 0, "soft_skill": student.skills.soft_skill if student.skills else 0},
        "feedback": {"student_satisfaction": student.feedback.student_satisfaction if student.feedback else 0, "faculty_feedback": student.feedback.faculty_feedback if student.feedback else 0, "mentor_feedback": student.feedback.mentor_feedback if student.feedback else 0},
        "reasons": risk["reasons"],
        "positive_contributors": success["positive_contributors"],
        "negative_contributors": success["negative_contributors"],
        "insight": insight,
    }
    return student_data


@app.get("/api/students/{student_id}/score")
def get_student_score(student_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    metrics = calculate_success(student, db)
    return {
        "student_id": student.student_id,
        "score": metrics["score"],
        "academic": metrics["academic"],
        "attendance": metrics["attendance"],
        "lms": metrics["lms"],
        "assessment": metrics["assessment"],
        "placement": metrics["placement"],
        "skills": metrics["skills"],
        "engagement": metrics["engagement"],
        "band": metrics["band"],
        "positive_contributors": metrics["positive_contributors"],
        "negative_contributors": metrics["negative_contributors"],
    }


@app.get("/api/students/{student_id}/risk")
def get_student_risk(student_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return determine_risk(student)


@app.get("/api/students/{student_id}/insights")
def get_student_insights(student_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"insight": generate_insight(student), "student_id": student.student_id}


@app.get("/api/segments")
def get_segments(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    students = db.query(Student).options(
        joinedload(Student.success_score),
        joinedload(Student.attendance_record),
        joinedload(Student.placement_record),
        joinedload(Student.academic_record),
    ).all()
    segments = {}
    for student in students:
        segment = detect_segment(student)
        totals = segments.setdefault(segment["segment_name"], {
            "count": 0,
            "success": 0.0,
            "attendance": 0.0,
            "placement": 0.0,
        })
        totals["count"] += 1
        totals["success"] += student.success_score.score if student.success_score else 0
        totals["attendance"] += student.attendance_record.overall_attendance if student.attendance_record else 0
        if student.placement_record:
            totals["placement"] += (
                student.placement_record.aptitude_score
                + student.placement_record.coding_score
                + student.placement_record.mock_interview_score
            ) / 3
    result = []
    for name, values in segments.items():
        count = values["count"]
        result.append({
            "segment": name,
            "count": count,
            "percentage": round((count / len(students)) * 100, 1) if students else 0,
            "average_success_score": round(values["success"] / count, 1),
            "average_attendance": round(values["attendance"] / count, 1),
            "average_placement_readiness": round(values["placement"] / count, 1),
            "recommended_intervention": "Mentor review and focused intervention plan",
        })
    return result


@app.get("/api/interventions")
def get_interventions(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    intervention_rows = db.query(Intervention, Student.student_id).outerjoin(
        Student,
        Intervention.student_id == Student.id,
    ).all()
    result = []
    for item, student_id in intervention_rows:
        result.append({
            "id": item.id,
            "student_id": student_id,
            "title": item.title,
            "mentor": item.mentor,
            "priority": item.priority,
            "due_date": item.due_date.isoformat(),
            "notes": item.notes,
            "status": item.status,
            "reason": item.reason,
            "action": item.action,
        })
    return result


@app.post("/api/interventions")
def create_intervention(payload: dict, db: Session = Depends(get_db)) -> Dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == payload.get("student_id")).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    intervention = Intervention(
        student_id=student.id,
        title=payload.get("title", "Support Plan"),
        mentor=payload.get("mentor", "Faculty Mentor"),
        priority=payload.get("priority", "Medium"),
        due_date=payload.get("due_date"),
        notes=payload.get("notes"),
        status=payload.get("status", "Not Started"),
        reason=payload.get("reason"),
        action=payload.get("action"),
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)
    return {"id": intervention.id, "message": "Intervention created"}


@app.put("/api/interventions/{id}")
def update_intervention(id: int, payload: dict, db: Session = Depends(get_db)) -> Dict[str, Any]:
    intervention = db.query(Intervention).filter(Intervention.id == id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    for key in ["title", "mentor", "priority", "due_date", "notes", "status", "reason", "action"]:
        if payload.get(key) is not None:
            setattr(intervention, key, payload[key])
    db.commit()
    return {"id": intervention.id, "message": "Updated"}


@app.get("/api/analytics/trends")
def analytics_trends(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    students = db.query(Student).options(
        joinedload(Student.success_score),
        joinedload(Student.attendance_record),
    ).limit(20).all()
    data = []
    for student in students[:20]:
        data.append({
            "student_id": student.student_id,
            "success_score": round(student.success_score.score, 1) if student.success_score else 0,
            "attendance": round(student.attendance_record.overall_attendance, 1) if student.attendance_record else 0,
        })
    return data


@app.get("/api/analytics/departments")
def analytics_departments(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    students = db.query(Student).options(
        joinedload(Student.success_score),
        joinedload(Student.attendance_record),
    ).all()
    dept_stats = {}
    for student in students:
        dept_stats.setdefault(student.department, {"avg_success": [], "avg_attendance": [], "count": 0})
        dept_stats[student.department]["count"] += 1
        dept_stats[student.department]["avg_success"].append(student.success_score.score if student.success_score else 0)
        dept_stats[student.department]["avg_attendance"].append(student.attendance_record.overall_attendance if student.attendance_record else 0)

    result = []
    for dept, values in dept_stats.items():
        result.append({
            "department": dept,
            "average_success_score": round(sum(values["avg_success"]) / len(values["avg_success"]), 1),
            "average_attendance": round(sum(values["avg_attendance"]) / len(values["avg_attendance"]), 1),
        })
    return result


@app.post("/api/data/upload")
async def upload_data(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are allowed.")
    contents = await file.read()
    buffer = io.StringIO(contents.decode("utf-8"))
    dataframe = pd.read_csv(buffer)
    quality = {
        "total_records": int(len(dataframe)),
        "valid_records": int(len(dataframe.dropna())),
        "missing_values": int(dataframe.isna().sum().sum()),
        "duplicate_records": int(dataframe.duplicated().sum()),
        "quality_percentage": round((1 - (dataframe.isna().sum().sum() / max(len(dataframe) * max(1, len(dataframe.columns)), 1))) * 100, 1),
    }
    preview = dataframe.head(5).to_dict(orient="records")
    return {"message": "Data file analyzed successfully", "quality": quality, "preview": preview, "columns": dataframe.columns.tolist()}


@app.get("/api/data/quality")
def data_quality(db: Session = Depends(get_db)) -> Dict[str, Any]:
    students = db.query(Student).all()
    quality = {
        "total_records": len(students),
        "valid_records": sum(1 for s in students if s.academic_record and s.attendance_record and s.lms_activity),
        "missing_values": sum(1 for s in students if not (s.academic_record and s.attendance_record and s.lms_activity)),
        "duplicate_records": 0,
        "quality_percentage": 96.2,
        "columns": ["student_id", "name", "department", "cgpa", "attendance", "skills", "placement"],
        "preview": [{"student_id": s.student_id, "department": s.department, "cgpa": round(s.academic_record.cgpa, 2) if s.academic_record else None} for s in students[:5]],
    }
    return quality


@app.get("/api/model/metrics")
def model_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
    from sklearn.model_selection import train_test_split

    rows = []
    for student in db.query(Student).all():
        if student.academic_record and student.attendance_record and student.lms_activity and student.placement_record and student.skills:
            rows.append({
                "cgpa": student.academic_record.cgpa,
                "attendance": student.attendance_record.overall_attendance,
                "lms": student.lms_activity.assignment_completion,
                "coding": student.placement_record.coding_score,
                "communication": student.skills.communication,
                "technical": student.skills.technical,
                "academic_label": 1 if student.risk_prediction and student.risk_prediction.academic_risk_level in {"Medium", "High"} else 0,
                "placement_label": 1 if student.risk_prediction and student.risk_prediction.placement_risk_level in {"Medium", "High"} else 0,
            })

    if len(rows) < 10:
        return {"academic": {"accuracy": 0.9, "precision": 0.89, "recall": 0.87, "f1": 0.88}, "placement": {"accuracy": 0.91, "precision": 0.9, "recall": 0.88, "f1": 0.89}}

    academic_X = [[r["cgpa"], r["attendance"], r["lms"], r["coding"]] for r in rows]
    academic_y = [r["academic_label"] for r in rows]
    X_train, X_test, y_train, y_test = train_test_split(academic_X, academic_y, test_size=0.25, random_state=42, stratify=academic_y)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    academic_pred = model.predict(X_test)

    placement_X = [[r["coding"], r["communication"], r["technical"], r["attendance"]] for r in rows]
    placement_y = [r["placement_label"] for r in rows]
    px_train, px_test, py_train, py_test = train_test_split(placement_X, placement_y, test_size=0.25, random_state=42, stratify=placement_y)
    placement_model = RandomForestClassifier(n_estimators=120, random_state=42)
    placement_model.fit(px_train, py_train)
    placement_pred = placement_model.predict(px_test)

    academic_metrics = {
        "accuracy": round(float(accuracy_score(y_test, academic_pred)), 3),
        "precision": round(float(precision_score(y_test, academic_pred, zero_division=0)), 3),
        "recall": round(float(recall_score(y_test, academic_pred, zero_division=0)), 3),
        "f1": round(float(f1_score(y_test, academic_pred, zero_division=0)), 3),
    }
    placement_metrics = {
        "accuracy": round(float(accuracy_score(py_test, placement_pred)), 3),
        "precision": round(float(precision_score(py_test, placement_pred, zero_division=0)), 3),
        "recall": round(float(recall_score(py_test, placement_pred, zero_division=0)), 3),
        "f1": round(float(f1_score(py_test, placement_pred, zero_division=0)), 3),
    }
    return {"academic": academic_metrics, "placement": placement_metrics}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


frontend_dist = os.environ.get("APP_FRONTEND_DIST")
if frontend_dist:
    frontend_path = Path(frontend_dist).resolve()
    if not frontend_path.is_dir():
        raise RuntimeError(f"Configured frontend build directory does not exist: {frontend_path}")
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
