import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_and_get_job(client: AsyncClient) -> None:
    payload = {"title": "Backend Engineer", "company": "Acme Corp", "location": "Remote"}

    create_response = await client.post("/api/v1/jobs", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == payload["title"]
    assert created["status"] == "new"

    get_response = await client.get(f"/api/v1/jobs/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["company"] == "Acme Corp"


async def test_list_jobs(client: AsyncClient) -> None:
    await client.post("/api/v1/jobs", json={"title": "Job A", "company": "Co A"})
    await client.post("/api/v1/jobs", json={"title": "Job B", "company": "Co B"})

    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_update_job(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/jobs", json={"title": "Old Title", "company": "Co"})
    job_id = create_response.json()["id"]

    update_response = await client.patch(f"/api/v1/jobs/{job_id}", json={"status": "applied"})
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "applied"
    assert update_response.json()["title"] == "Old Title"


async def test_delete_job(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/jobs", json={"title": "To Delete", "company": "Co"})
    job_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/jobs/{job_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 404


async def test_get_job_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/jobs/999999")
    assert response.status_code == 404
