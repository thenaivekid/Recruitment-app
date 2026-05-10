import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User
from app.auth import hash_password
import uuid

# ── In-memory SQLite for tests ────────────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    # Seed an admin and two reviewers
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@test.com",
        hashed_password=hash_password("Admin1234!"),
        role="admin",
    )
    reviewer1 = User(
        id=str(uuid.uuid4()),
        email="reviewer1@test.com",
        hashed_password=hash_password("Review1234!"),
        role="reviewer",
    )
    reviewer2 = User(
        id=str(uuid.uuid4()),
        email="reviewer2@test.com",
        hashed_password=hash_password("Review1234!"),
        role="reviewer",
    )
    db.add_all([admin, reviewer1, reviewer2])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── Test 1: Admin can create a candidate and response has expected fields ──────

@pytest.mark.asyncio
async def test_create_candidate_as_admin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await get_token(client, "admin@test.com", "Admin1234!")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": "Test Candidate",
            "email": "testcandidate@example.com",
            "role_applied": "Backend Engineer",
            "skills": ["Python", "FastAPI"],
        }
        resp = await client.post("/candidates", json=payload, headers=headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Candidate"
    assert data["email"] == "testcandidate@example.com"
    assert data["role_applied"] == "Backend Engineer"
    assert "Python" in data["skills"]
    assert data["status"] == "new"
    assert "id" in data


# ── Test 2: Reviewer cannot see another reviewer's scores ─────────────────────

@pytest.mark.asyncio
async def test_reviewer_cannot_see_other_reviewer_scores():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin_token = await get_token(client, "admin@test.com", "Admin1234!")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Create candidate as admin
        resp = await client.post(
            "/candidates",
            json={"name": "Isolated Candidate", "email": "iso@example.com",
                  "role_applied": "QA Engineer", "skills": []},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        candidate_id = resp.json()["id"]

        # Reviewer1 submits a score
        r1_token = await get_token(client, "reviewer1@test.com", "Review1234!")
        r1_headers = {"Authorization": f"Bearer {r1_token}"}
        score_resp = await client.post(
            f"/candidates/{candidate_id}/scores",
            json={"category": "Technical", "score": 4, "note": "Good problem solver"},
            headers=r1_headers,
        )
        assert score_resp.status_code == 201

        # Reviewer2 fetches the candidate detail — should see 0 scores (not reviewer1's)
        r2_token = await get_token(client, "reviewer2@test.com", "Review1234!")
        r2_headers = {"Authorization": f"Bearer {r2_token}"}
        detail_resp = await client.get(f"/candidates/{candidate_id}", headers=r2_headers)

    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["scores"] == [], "Reviewer2 must not see Reviewer1's scores"
    assert detail["internal_notes"] is None, "Reviewer must not see internal_notes"


# ── Test 3: Admin can see all scores from all reviewers ───────────────────────

@pytest.mark.asyncio
async def test_admin_sees_all_scores():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin_token = await get_token(client, "admin@test.com", "Admin1234!")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Create candidate
        resp = await client.post(
            "/candidates",
            json={"name": "Multi-Score Candidate", "email": "multi@example.com",
                  "role_applied": "Full Stack Engineer", "skills": ["React"]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        candidate_id = resp.json()["id"]

        # Both reviewers submit scores
        for email, category in [("reviewer1@test.com", "Technical"), ("reviewer2@test.com", "Communication")]:
            token = await get_token(client, email, "Review1234!")
            await client.post(
                f"/candidates/{candidate_id}/scores",
                json={"category": category, "score": 3},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Admin should see both scores
        detail_resp = await client.get(f"/candidates/{candidate_id}", headers=admin_headers)

    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["scores"]) == 2, "Admin must see all reviewers' scores"
    categories = {s["category"] for s in detail["scores"]}
    assert "Technical" in categories
    assert "Communication" in categories
    # Admin sees internal_notes
    assert detail["internal_notes"] is not None
