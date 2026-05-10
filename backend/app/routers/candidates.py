import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user, require_admin, get_user_from_token
from ..models import User, Candidate, Score
from ..schemas import (
    CandidateCreate, CandidateUpdate, CandidateDetail,
    PaginatedCandidates, ScoreCreate, ScoreOut, SummaryResponse,
)
from ..services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateDetail, status_code=status.HTTP_201_CREATED)
def create_candidate(
    body: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = candidate_service.create_candidate(db, body)
    return candidate_service.get_candidate_detail(db, candidate.id, current_user)


@router.get("", response_model=PaginatedCandidates)
def list_candidates(
    status: Optional[str] = Query(None),
    role_applied: Optional[str] = Query(None),
    skill: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return candidate_service.get_candidates(
        db, status=status, role_applied=role_applied,
        skill=skill, keyword=keyword, offset=offset, limit=limit,
    )


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = candidate_service.get_candidate_detail(db, candidate_id, current_user)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return detail


@router.patch("/{candidate_id}", response_model=CandidateDetail)
def update_candidate(
    candidate_id: str,
    body: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = candidate_service.update_candidate(db, candidate_id, body)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate_service.get_candidate_detail(db, candidate_id, current_user)


@router.post("/{candidate_id}/scores", response_model=ScoreOut, status_code=status.HTTP_201_CREATED)
def submit_score(
    candidate_id: str,
    body: ScoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify candidate exists and is not archived
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.deleted_at.is_(None),
    ).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    score = candidate_service.create_score(db, candidate_id, body, current_user.id)
    reviewer_email = current_user.email if current_user.role == "admin" else None
    return ScoreOut(
        id=score.id,
        candidate_id=score.candidate_id,
        category=score.category,
        score=score.score,
        reviewer_id=score.reviewer_id,
        reviewer_email=reviewer_email,
        note=score.note,
        created_at=score.created_at,
    )


@router.post("/{candidate_id}/summary", response_model=SummaryResponse)
async def generate_summary(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.deleted_at.is_(None),
    ).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    summary = await candidate_service.generate_ai_summary(db, candidate_id)
    return SummaryResponse(candidate_id=candidate_id, summary=summary)


@router.get("/{candidate_id}/stream")
async def stream_scores(
    candidate_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Stretch goal: SSE endpoint that streams score updates every 2 seconds."""
    current_user = get_user_from_token(token, db)
    
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.deleted_at.is_(None),
    ).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    async def event_generator():
        seen_ids: set = set()
        for _ in range(30):  # stream for up to ~60 seconds
            scores_query = db.query(Score).filter(Score.candidate_id == candidate_id)
            if current_user.role == "reviewer":
                scores_query = scores_query.filter(Score.reviewer_id == current_user.id)

            for score in scores_query.all():
                if score.id not in seen_ids:
                    seen_ids.add(score.id)
                    data = {
                        "id": score.id,
                        "category": score.category,
                        "score": score.score,
                        "note": score.note,
                        "created_at": score.created_at.isoformat(),
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
