import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import event
import logging

from .database import engine, SessionLocal
from .models import Base, User, Candidate
from .auth import hash_password
from .routers import auth as auth_router
from .routers import candidates as candidates_router
from .config import settings

logger = logging.getLogger(__name__)

# Enterprise standard: Enable SQLite WAL mode for high concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

# ...
def _seed_db():
    """Seed initial data if the database is empty."""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return  # already seeded

        # Create admin user
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@techkraft.com",
            hashed_password=hash_password("Admin1234!"),
            role="admin",
        )
        # Create reviewer user
        reviewer = User(
            id=str(uuid.uuid4()),
            email="reviewer@techkraft.com",
            hashed_password=hash_password("Review1234!"),
            role="reviewer",
        )
        db.add_all([admin, reviewer])
        db.flush()

        # Create sample candidates
        candidates_data = [
            ("Alice Johnson",    "alice@example.com",   "Backend Engineer",        ["Python", "FastAPI", "PostgreSQL"],    "Strong async background."),
            ("Bob Smith",       "bob@example.com",     "Frontend Engineer",       ["React", "TypeScript", "CSS"],         "Good portfolio."),
            ("Carol White",     "carol@example.com",   "Full Stack Engineer",     ["Python", "React", "Docker"],          "Mid-level, solid fundamentals."),
            ("David Brown",     "david@example.com",   "DevOps Engineer",         ["Kubernetes", "Terraform", "AWS"],     "CI/CD expert."),
            ("Eva Martinez",    "eva@example.com",     "Data Engineer",           ["Python", "Spark", "SQL"],             "Strong data pipeline experience."),
            ("Frank Lee",       "frank@example.com",   "Backend Engineer",        ["Go", "gRPC", "Redis"],                "Prefers Go over Python."),
            ("Grace Kim",       "grace@example.com",   "Full Stack Engineer",     ["Vue", "Django", "PostgreSQL"],        "Vue + Django stack."),
            ("Henry Chen",      "henry@example.com",   "Frontend Engineer",       ["React", "Next.js", "GraphQL"],        "Next.js specialist."),
            ("Isabella Davis",  "isabella@example.com","Machine Learning Engineer",["Python", "PyTorch", "MLflow"],       "Strong ML ops background."),
            ("James Wilson",    "james@example.com",   "Backend Engineer",        ["Java", "Spring Boot", "Kafka"],       "Enterprise experience."),
            ("Kate Thompson",   "kate@example.com",    "Full Stack Engineer",     ["Python", "FastAPI", "React"],         "Great communication skills."),
            ("Liam Anderson",   "liam@example.com",    "DevOps Engineer",         ["Docker", "Ansible", "GCP"],           "Cloud-native focus."),
        ]

        statuses = ["new", "reviewed", "reviewed", "hired", "rejected", "new",
                    "reviewed", "new", "hired", "rejected", "new", "reviewed"]

        for (name, email, role, skills, notes), status in zip(candidates_data, statuses):
            c = Candidate(
                id=str(uuid.uuid4()),
                name=name,
                email=email,
                role_applied=role,
                status=status,
                internal_notes=notes,
            )
            c.skills = skills
            db.add(c)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_db()
    yield


app = FastAPI(
    title="TechKraft Recruitment API",
    description="Internal candidate scoring and review dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(candidates_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
