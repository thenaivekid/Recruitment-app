from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    # NOTE: role is intentionally NOT accepted from client — hardcoded to reviewer

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Scores ────────────────────────────────────────────────────────────────────

class ScoreCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    score: int = Field(ge=1, le=5)
    note: Optional[str] = ""

class ScoreOut(BaseModel):
    id: str
    candidate_id: str
    category: str
    score: int
    reviewer_id: str
    reviewer_email: Optional[str] = None
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Candidates ────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    role_applied: str = Field(min_length=1, max_length=200)
    skills: List[str] = []
    internal_notes: Optional[str] = ""

class CandidateUpdate(BaseModel):
    internal_notes: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"new", "reviewed", "hired", "rejected", "archived"}
        if v is not None and v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

class CandidateListItem(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class CandidateDetail(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    internal_notes: Optional[str] = None  # None means hidden (reviewer)
    created_at: datetime
    ai_summary: Optional[str] = None
    scores: List[ScoreOut] = []

    model_config = {"from_attributes": True}


# ── Pagination ─────────────────────────────────────────────────────────────────

class PaginatedCandidates(BaseModel):
    total: int
    offset: int
    limit: int
    items: List[CandidateListItem]


# ── AI Summary ────────────────────────────────────────────────────────────────

class SummaryResponse(BaseModel):
    candidate_id: str
    summary: str
