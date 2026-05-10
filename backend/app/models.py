import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Index, ForeignKey
)
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="reviewer")  # reviewer | admin
    created_at = Column(DateTime, default=utcnow)

    scores = relationship("Score", back_populates="reviewer")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    role_applied = Column(String, nullable=False)
    # status: new | reviewed | hired | rejected | archived (soft-delete)
    status = Column(String, nullable=False, default="new")
    _skills = Column("skills", Text, default="[]")  # JSON array stored as text
    internal_notes = Column(Text, default="")        # admin-only
    created_at = Column(DateTime, default=utcnow)
    deleted_at = Column(DateTime, nullable=True)     # soft-delete timestamp
    ai_summary = Column(Text, nullable=True)

    scores = relationship("Score", back_populates="candidate")

    @property
    def skills(self):
        return json.loads(self._skills or "[]")

    @skills.setter
    def skills(self, value):
        self._skills = json.dumps(value)


class Score(Base):
    __tablename__ = "scores"

    id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    category = Column(String, nullable=False)
    score = Column(Integer, nullable=False)   # 1–5
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    candidate = relationship("Candidate", back_populates="scores")
    reviewer = relationship("User", back_populates="scores")


# Explicit indexes matching the spec
Index("ix_candidates_status", Candidate.status)
Index("ix_candidates_role_applied", Candidate.role_applied)
Index("ix_scores_candidate_id", Score.candidate_id)
