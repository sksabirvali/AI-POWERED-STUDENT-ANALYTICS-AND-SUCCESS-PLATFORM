# AI-Powered Student Analytics & Success Platform

## Project Overview
This project is a hackathon-ready student success platform that brings together academic, attendance, LMS, engagement, placement, skill, and feedback signals into one explainable analytics system. The application supports administrators, faculty mentors, and students with a decision-support workflow that highlights success scores, intervention priorities, risk trends, and personalized recommendations.

## Problem Statement
Universities often work with disconnected data sources across academic records, attendance sheets, LMS logs, and placement pipelines. Without a unified view, faculty struggle to identify at-risk students early, recommend meaningful interventions, and explain why a student may need support.

## Solution
The platform creates a unified student data model, computes a weighted Student Success Score, identifies academic and placement risk, segments students into actionable cohorts, and surfaces explainable insights for faculty decisions. An API layer connects the backend logic to a modern enterprise dashboard in the frontend.

## Features
- College-wide and department-level dashboards
- Student search, table filtering, sorting, and profile drill-down
- Explainable success scoring (0-100 scale)
- Academic and placement risk categorization
- Student segmentation with cluster-style grouping
- AI insight generation from real dataset metrics
- Intervention tracking with mentor, priority, due date, notes, and status
- CSV upload, data validation, and quality reporting
- Responsible AI notice and decision-support language
- Demo-ready student profiles for hackathon presentation
- Demo sign-in for administrator, faculty, and student roles
- Student registration with generated student ID and the demo default password; faculty registration requires administrator approval
- Personal password changes for signed-in administrator, faculty, and student accounts
- Subject-wise M1–M4 attendance and marks capture
- Daily, weekly, monthly, and yearly academic growth and risk trends
- Student semester results for all four years / eight semesters, including two mid exams and semester exam marks for six subjects, internal/external marks for three labs, and passed/backlog status
- Yearly condonation estimate based on overall attendance: no fee at 75% or above; below 75%, ₹2,000 per started 10-percentage-point shortfall
- Student fee dashboard with four-year tuition, paid amounts, and due balances, including 3–4 annual cultural activity charges of ₹1,000–₹1,500 each (repeatable random demo data only)
- Dashboard monthly at-risk student trend for January–December, calculated from dated attendance and marks (months without records are shown as gaps)
- Personal account passwords: administrators, faculty, and students can change their signed-in account password; new faculty choose a password at registration and require admin approval
- Student-only local study assistant for questions about the signed-in student's marks, attendance, semester results, backlogs, and demo fee balance; it uses built-in guidance and does not call an external AI service
- Searchable student lookup, paginated ledger rendering, indexed grouping, and eager-loaded student records to reduce database round trips on larger rosters

## Running at larger scale

The default SQLite database is intended for local development and demonstrations. It uses WAL mode and a busy timeout, but SQLite is not suitable for heavy concurrent production traffic. For a large or highly concurrent deployment:

1. Configure a managed PostgreSQL database with `DATABASE_URL`, for example `postgresql+psycopg://user:password@host:5432/student_success`.
2. Install backend requirements, including the PostgreSQL driver.
3. Set `APP_SEED_DEMO=false` to avoid generating sample records at startup.
4. Run behind a production ASGI process manager and reverse proxy; size worker counts and connection pools for the available database and server resources, then load-test the expected peak concurrency.

The application cannot guarantee a particular number of simultaneous users without deployment-specific load testing and infrastructure sizing. A student roster size and concurrent sign-in count are different capacity measures.

## Deploy on Render

The repository includes a Render Blueprint (`render.yaml`) and a multi-stage `Dockerfile`. The blueprint deploys the frontend and FastAPI API together at one origin and provisions PostgreSQL. `/api/health` performs a database connectivity check.

1. Push this repository to GitHub.
2. In the Render dashboard, choose **New > Blueprint**, connect this GitHub repository, and apply the `render.yaml` Blueprint.
3. Enter private values when prompted for `DEMO_ADMIN_PASSWORD`, `DEMO_FACULTY_PASSWORD`, and `DEMO_STUDENT_PASSWORD`; do not paste them into GitHub or chat.
4. Wait for the Docker build and database-backed `/api/health` check to pass, then open the service URL.

The Blueprint sets `APP_AUTH_SECRET` to a generated value, enables synthetic demo data, and prompts for private values for `DEMO_ADMIN_PASSWORD`, `DEMO_FACULTY_PASSWORD`, and `DEMO_STUDENT_PASSWORD`. Enter the requested demo values privately in Render's setup prompt; use the same student value to enable shared demo student sign-in. Do not put real student records or shared passwords in source code. The selected free PostgreSQL database is temporary and may expire after 30 days; the free web service may sleep when idle. Do not use this tier for persistent or real student records.

For local development, copy `.env.example` to `.env` and set private credentials there. The backend loads the root `.env`, which is ignored by Git and Docker. Set all three demo passwords before running with `APP_SEED_DEMO=true`; startup fails with a clear message if any are missing. The Vite development proxy keeps local API requests same-origin; Render serves the built frontend and API from one origin, so production needs no cross-origin API URL. If you later host them separately, set `APP_CORS_ORIGINS` to only the trusted frontend origins.

The app creates missing tables at startup but does not include a schema migration tool. The initial Render database is empty, so this works for the first deployment; add and run database migrations before shipping future schema changes to a database with records.

## Architecture
- Frontend: React + TypeScript + Vite + Tailwind CSS + Recharts
- Backend: FastAPI + SQLAlchemy
- Render deployment: one Docker web service serves the built frontend and API, backed by PostgreSQL
- Analytics: weighted scoring engine plus scikit-learn model metrics
- Local database: SQLite; production database: PostgreSQL with tables for students, academic records, attendance, LMS, engagement, placement, skills, feedback, success scores, risk predictions, segments, and interventions

## Tech Stack
- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- Lucide React
- FastAPI
- SQLAlchemy
- SQLite
- pandas
- NumPy
- scikit-learn

## Success Score Formula
The success score is a weighted composite of normalized indicators:

- Academic Performance: 30%
- Attendance: 15%
- LMS Engagement: 10%
- Assessment Performance: 10%
- Placement Readiness: 20%
- Skills: 10%
- Engagement: 5%

Formula:

Success Score = 0.30 Academic + 0.15 Attendance + 0.10 LMS + 0.10 Assessment + 0.20 Placement + 0.10 Skills + 0.05 Engagement

Score bands:
- 90-100: Excellent
- 75-89: Good
- 60-74: Needs Attention
- Below 60: At Risk

## Risk Detection Methodology
Academic risk is estimated from the combination of:
- CGPA
- marks trend and subject outcomes
- active backlog count
- attendance
- assignment completion
- LMS activity

Placement risk is estimated from:
- aptitude score
- coding score
- mock interview score
- resume score
- communication ability
- placement training attendance

## Segmentation Methodology
Students are assigned to segments such as:
- High Performer
- Academically Strong but Placement Needs Improvement
- Placement Ready but Academically At Risk
- High Engagement but Low Academic Performance
- Low Engagement / Needs Mentoring
- Balanced / On Track
- Critical Intervention Required

The logic is rule-based and deterministic for explainability, with a future path to unsupervised clustering with K-Means if desired.

## AI Approach
The platform uses:
- transparent, data-driven scoring for explainability
- risk classification logic derived from actual metrics
- model-ready predictions for academic and placement risk
- deterministic insight generation based on existing student data

The backend includes actual scikit-learn evaluation metrics to report model readiness without inventing numbers.

## Database Schema
The SQLite schema includes:
- students
- academic_records
- attendance_records
- lms_activity
- engagement_records
- placement_records
- skills
- feedback
- success_scores
- risk_predictions
- student_segments
- interventions

Foreign keys are used to keep related records connected to each student.

## API Documentation
The backend exposes endpoints such as:
- POST /api/auth/login
- POST /api/auth/password (authenticated password change)
- POST /api/student/assistant (authenticated student-only records lookup and study guidance)
- GET /api/faculty (administrator only)
- GET /api/students (administrator/faculty; student must request only their own student_id)
- GET /api/academic/trends?period=daily|weekly|monthly|yearly&student_id=STU-0001
- GET /api/academic/semester-results?student_id=STU-0001
- POST /api/academic/semester-results (administrator/faculty result entry)
- GET /api/fees?student_id=STU-0001 (includes annual cultural activity charges in total fees and due balances)
- POST /api/academic/entries
- GET /api/dashboard/summary
- GET /api/dashboard/summary?year=2026 (monthly risk trend for the requested year; defaults to the current year)
- GET /api/students
- GET /api/students?search=Aarav&limit=10 (authenticated name/ID lookup; `offset` and `limit` support paging)
- GET /api/students/{student_id}
- GET /api/students/{student_id}/insights
- GET /api/students/{student_id}/risk
- GET /api/students/{student_id}/score
- GET /api/segments
- GET /api/interventions
- POST /api/interventions
- PUT /api/interventions/{id}
- GET /api/analytics/trends
- GET /api/analytics/departments
- POST /api/data/upload
- GET /api/data/quality
- GET /api/model/metrics

FastAPI auto-generates OpenAPI docs at:
- http://localhost:8000/docs

## Installation
### Backend
1. Open a terminal in the backend folder
2. Install dependencies:
   `python -m pip install -r requirements.txt`

### Frontend
1. Open a terminal in the frontend folder
2. Install dependencies:
   `npm install`

## Running Frontend
From the frontend folder:

`npm run dev -- --host 0.0.0.0`

Frontend URL:
- http://localhost:5173

## Running Backend
From the backend folder:

`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

Backend URL:
- http://localhost:8000

## Sample Data
The platform automatically seeds 240 synthetic students with realistic patterns, including:
- high academic + low placement readiness
- low attendance + falling marks + backlogs
- strong placement readiness + average academics
- excellent overall performers
- academic and placement risk profiles

Demo students are easy to identify during the product demo.
The database seeds four years of synthetic weekly class records for M1, M2, M3, and M4, so each student's attendance and marks journey has at least eight semesters of history. Existing demo databases are backfilled with the missing older records without replacing existing entries.
For the local demo, semester-result sample data covers all eight semesters for every student. Semester-specific course and lab labels are illustrative placeholders and should be replaced with the college curriculum and verified marks in a real deployment. Attendance condonation is estimated per calendar year from recorded class sessions; it is not a payment transaction.
Student tuition, payments, due balances, and cultural activity charges are stable generated demo figures only, not official invoices or payment records. Demo activity charges are automatically included in the annual total and balance due. Replace these figures with verified finance-system data before making financial decisions.
Seeded demo student names use generated first names and initials while retaining stable student IDs (for example, `Aarav A.` / `STU-0001`).

## Demo Login Accounts
Local/demo account passwords are read from the untracked `.env` file; set `DEMO_ADMIN_PASSWORD`, `DEMO_FACULTY_PASSWORD`, and `DEMO_STUDENT_PASSWORD` there. Seeded students sign in with their student ID and the configured student password. New student registrations also use the configured student password; the signup response does not disclose that shared password. Students can change their password after signing in.

Administrators can view all student records and the faculty directory. Faculty can view all student records. Student sign-in is scoped to the supplied student ID and shows only that student's information. Administrators and faculty can record a student's attendance and/or marks for a subject and date. Student accounts can view their own subject growth and risk trends but cannot edit records. The daily view is based on dated class records; weekly, monthly, and yearly views aggregate those same records. These demo credentials are intended only for local presentation, not deployment.

Successful sign-in issues a short-lived signed session token used by the API to enforce those role restrictions. Set a strong `APP_AUTH_SECRET` in the environment for stable token signing; without one, local development generates an ephemeral secret at startup and existing sessions expire on restart.


## Demo Flow
1. Open the Admin Dashboard
2. Review top KPIs and department trends
3. Open the student table and select a high-risk student
4. View the detailed student profile and score contributors
5. Review AI-generated insight and intervention recommendation
6. Switch to segmentation view
7. Upload or preview CSV integration
8. Review decision-intelligence insights and governance notice

## Future Enhancements
- Production-grade auth and RBAC
- Real data source integrations with SIS/LMS systems
- K-Means clustering based on full dataset analysis
- Forecasting of retention and dropout risk
- PDF report generation and schedule exports
- Student feedback loops and action tracking dashboards

## Responsible AI
This system clearly communicates that:
- risk scores are decision-support indicators
- predictions are not final judgments
- recommendations require faculty review
- no unnecessary sensitive personal attributes are used
- outputs are explainable and traceable to actual student data
- privacy and data protection principles are respected for institutional use
