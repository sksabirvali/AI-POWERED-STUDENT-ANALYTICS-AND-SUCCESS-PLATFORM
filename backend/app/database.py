import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


SQLALCHEMY_DATABASE_URL = normalize_database_url(
    os.environ.get("DATABASE_URL", "sqlite:///./student_success.db")
)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(connection, _connection_record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        future=True,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from .models import AcademicEntry, AcademicRecord, AttendanceRecord, CulturalActivityFee, EngagementRecord, Faculty, FeedbackRecord, Intervention, LmsActivity, PlacementRecord, RiskPrediction, SemesterResult, SkillRecord, Student, StudentFee, StudentSegment, SuccessScore, UserAccount

    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(bind=engine)
