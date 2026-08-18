from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.application import seed_database
from app.database import Base, get_db
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        await seed_database(session)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def register(client: httpx.AsyncClient, email: str) -> tuple[str, dict]:
    response = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "correct-horse-battery",
        "display_name": "Test Learner",
    })
    assert response.status_code == 201
    payload = response.json()
    return payload["access_token"], payload


async def test_duplicate_registration_is_conflict(client: httpx.AsyncClient) -> None:
    await register(client, "duplicate@example.com")
    response = await client.post("/api/v1/auth/register", json={
        "email": "DUPLICATE@example.com",
        "password": "correct-horse-battery",
        "display_name": "Other Learner",
    })
    assert response.status_code == 409


async def test_assessment_rejects_out_of_order_answer(client: httpx.AsyncClient) -> None:
    token, _ = await register(client, "assessment@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    started = (await client.post("/api/v1/assessment/start", headers=headers)).json()
    response = await client.post("/api/v1/assessment/answer", headers=headers, json={
        "assessment_id": started["assessment_id"],
        "item_key": "professional-1",
        "answer": "authentication authorization identity permissions access",
    })
    assert response.status_code == 400
    current = (await client.post("/api/v1/assessment/start", headers=headers)).json()
    assert current["question"]["key"] == "grammar-1"


async def test_lesson_is_not_accessible_to_another_user(client: httpx.AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    stranger_token, _ = await register(client, "stranger@example.com")
    lesson = (await client.post(
        "/api/v1/lessons/start",
        headers={"Authorization": f"Bearer {owner_token}"},
    )).json()
    response = await client.post(
        f"/api/v1/lessons/{lesson['id']}/answer",
        headers={"Authorization": f"Bearer {stranger_token}"},
        json={"answer": "We deployed to production this morning."},
    )
    assert response.status_code == 404


async def test_knowledge_ingestion_requires_admin(client: httpx.AsyncClient) -> None:
    token, _ = await register(client, "learner@example.com")
    response = await client.post(
        "/api/v1/knowledge/ingest",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", b"Safe deployment guidance")},
    )
    assert response.status_code == 403


async def test_refresh_token_rotates_and_reuse_revokes_family(client: httpx.AsyncClient) -> None:
    await register(client, "rotation@example.com")
    original = client.cookies.get("refresh_token")
    assert original
    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    replacement = client.cookies.get("refresh_token")
    assert replacement and replacement != original

    replay = await client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={original}"},
    )
    assert replay.status_code == 401
    revoked_replacement = await client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={replacement}"},
    )
    assert revoked_replacement.status_code == 401


async def test_account_deletion_requires_password_and_revokes_access(client: httpx.AsyncClient) -> None:
    token, _ = await register(client, "delete@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    denied = await client.request("DELETE", "/api/v1/me", headers=headers, json={"password": "wrong-password"})
    assert denied.status_code == 403
    deleted = await client.request("DELETE", "/api/v1/me", headers=headers, json={"password": "correct-horse-battery"})
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 401


async def test_preferences_are_persisted(client: httpx.AsyncClient) -> None:
    token, _ = await register(client, "preferences@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    saved = await client.patch("/api/v1/me/preferences", headers=headers, json={
        "daily_learning_minutes": 30,
        "native_explanations": False,
    })
    assert saved.status_code == 200
    profile = (await client.get("/api/v1/me", headers=headers)).json()["profile"]
    assert profile["daily_learning_minutes"] == 30
    assert profile["native_explanations"] is False
