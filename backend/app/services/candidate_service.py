import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from .. import models, schemas


def _candidate_to_list_item(c: models.Candidate) -> schemas.CandidateListItem:
    return schemas.CandidateListItem(
        id=c.id,
        name=c.name,
        email=c.email,
        role_applied=c.role_applied,
        status=c.status,
        skills=c.skills,
        created_at=c.created_at,
    )


def get_candidates(
    db: Session,
    status: Optional[str] = None,
    role_applied: Optional[str] = None,
    skill: Optional[str] = None,
    keyword: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> schemas.PaginatedCandidates:
    """
    All filtering is done in SQL — not in Python — to avoid the O(N) bug
    described in the assignment's debugging signal.
    """
    query = db.query(models.Candidate).filter(
        models.Candidate.deleted_at.is_(None),
        models.Candidate.status != "archived",
    )

    if status:
        query = query.filter(models.Candidate.status == status)
    if role_applied:
        role_fuzzy = f"%{role_applied.replace(' ', '%')}%"
        query = query.filter(models.Candidate.role_applied.ilike(role_fuzzy))
    if skill:
        # SQLite JSON stored as text — use wildcard fuzzy matching (e.g. "pyth" matches "Python")
        skill_fuzzy = f"%{skill.replace(' ', '%')}%"
        query = query.filter(models.Candidate._skills.ilike(skill_fuzzy))
    if keyword:
        kw_fuzzy = f"%{keyword.replace(' ', '%')}%"
        query = query.filter(
            or_(
                models.Candidate.name.ilike(kw_fuzzy),
                models.Candidate.email.ilike(kw_fuzzy),
                models.Candidate.role_applied.ilike(kw_fuzzy),
            )
        )

    total = query.count()
    candidates = (
        query.order_by(models.Candidate.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return schemas.PaginatedCandidates(
        total=total,
        offset=offset,
        limit=limit,
        items=[_candidate_to_list_item(c) for c in candidates],
    )


def get_candidate_detail(
    db: Session,
    candidate_id: str,
    current_user: models.User,
) -> schemas.CandidateDetail:
    candidate = (
        db.query(models.Candidate)
        .filter(
            models.Candidate.id == candidate_id,
            models.Candidate.deleted_at.is_(None),
        )
        .first()
    )
    if not candidate:
        return None

    # Scores: reviewers see only their own; admins see all
    scores_query = db.query(models.Score).filter(
        models.Score.candidate_id == candidate_id
    )
    if current_user.role == "reviewer":
        scores_query = scores_query.filter(
            models.Score.reviewer_id == current_user.id
        )

    scores_orm = scores_query.order_by(models.Score.created_at.desc()).all()

    score_outs = []
    for s in scores_orm:
        reviewer_email = s.reviewer.email if s.reviewer else None
        score_outs.append(
            schemas.ScoreOut(
                id=s.id,
                candidate_id=s.candidate_id,
                category=s.category,
                score=s.score,
                reviewer_id=s.reviewer_id,
                reviewer_email=reviewer_email if current_user.role == "admin" else None,
                note=s.note or "",
                created_at=s.created_at,
            )
        )

    return schemas.CandidateDetail(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        role_applied=candidate.role_applied,
        status=candidate.status,
        skills=candidate.skills,
        internal_notes=candidate.internal_notes if current_user.role == "admin" else None,
        created_at=candidate.created_at,
        ai_summary=candidate.ai_summary,
        scores=score_outs,
    )


def create_candidate(
    db: Session, body: schemas.CandidateCreate
) -> models.Candidate:
    candidate = models.Candidate(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        role_applied=body.role_applied,
        internal_notes=body.internal_notes or "",
    )
    candidate.skills = body.skills
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def create_score(
    db: Session,
    candidate_id: str,
    body: schemas.ScoreCreate,
    reviewer_id: str,
) -> models.Score:
    score = models.Score(
        id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        category=body.category,
        score=body.score,
        reviewer_id=reviewer_id,
        note=body.note or "",
    )
    db.add(score)
    # Update candidate status to reviewed if new
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id
    ).first()
    if candidate and candidate.status == "new":
        candidate.status = "reviewed"
    db.commit()
    db.refresh(score)
    return score


async def generate_ai_summary(db: Session, candidate_id: str) -> str:
    """
    Mock async LLM call — simulates a 2-second external API call.
    In production this would be: await openai_client.chat.completions.create(...)
    """
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        models.Candidate.deleted_at.is_(None),
    ).first()
    if not candidate:
        return None

    await asyncio.sleep(2)  # simulate async LLM latency

    scores = db.query(models.Score).filter(
        models.Score.candidate_id == candidate_id
    ).all()

    avg_score = (
        round(sum(s.score for s in scores) / len(scores), 1) if scores else None
    )
    categories = list({s.category for s in scores})

    summary = (
        f"{candidate.name} applied for {candidate.role_applied}. "
        f"Skills: {', '.join(candidate.skills) if candidate.skills else 'N/A'}. "
        f"{'Evaluated across: ' + ', '.join(categories) + '. ' if categories else ''}"
        f"{'Average score: ' + str(avg_score) + '/5. ' if avg_score else ''}"
        f"Overall status: {candidate.status}."
    )

    candidate.ai_summary = summary
    db.commit()
    return summary


def update_candidate(
    db: Session,
    candidate_id: str,
    body: schemas.CandidateUpdate,
) -> Optional[models.Candidate]:
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        models.Candidate.deleted_at.is_(None),
    ).first()
    if not candidate:
        return None
    if body.internal_notes is not None:
        candidate.internal_notes = body.internal_notes
    if body.status is not None:
        candidate.status = body.status
        # Soft delete: set deleted_at when archived
        if body.status == "archived":
            candidate.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(candidate)
    return candidate
